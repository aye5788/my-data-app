"""DeepSeek-backed AI workspace.

Two modes:
- **Compute** (default): the model writes pandas/plotly snippets that run in a
  sandbox against the active DataFrame. Results (numbers/tables/charts) come
  back into the chat and the model interprets them. When a snippet errors, the
  traceback is fed back so the model can diagnose, patch, and re-run -- a
  bounded self-healing loop.
- **Describe-only**: plain streaming chat over a summary of the data (no code
  execution), for when you just want to talk about it.
"""
import re

import pandas as pd
import streamlit as st
from openai import OpenAI

from ai.sandbox import run_code, result_to_text

MODEL = "deepseek-chat"

# Bound the self-healing loop so it can't run forever.
MAX_FIX_ATTEMPTS = 3      # corrected re-runs after an error
MAX_MODEL_CALLS = 8       # hard ceiling on model round-trips per question

_CODE_FENCE = re.compile(r"```(?:python)?\s*\n(.*?)```", re.DOTALL)

_COMPUTE_RULES = """You are a data analyst working inside a Streamlit app, with \
a live pandas DataFrame named `df` (the user's active dataset).

When answering needs computation on the data, reply with ONE Python code block:
```python
# use only: df, pd, np, px (plotly express), go (plotly graph objects)
# no imports, no file or network access are available
result = ...        # assign your answer: a number, string, DataFrame, or Series
# for a chart, build a plotly figure and assign it to `fig`
```
Rules for code:
- Assign the answer to `result` and/or a plotly figure to `fig`. Do not call
  .show(); do not print large frames.
- Keep prose minimal when you emit code -- you'll get the output next and can
  explain it then.
After the code runs you receive its output (or an error traceback):
- On success: interpret the result for the user in plain English. Emit more
  code ONLY if genuinely more computation is needed.
- On error: briefly say what went wrong, then emit corrected code.
If the question is conceptual and needs no computation (including helping debug
code the user pastes), just answer in prose with no code block."""

_DESCRIBE_RULES = (
    "You are a helpful data analyst. Discuss the user's dataset and app using "
    "the context below. You cannot run code; answer from the summary."
)


def _get_client():
    """Build a DeepSeek client from secrets, or return None if unconfigured."""
    try:
        return OpenAI(
            base_url="https://api.deepseek.com",
            api_key=st.secrets["DEEPSEEK_API_KEY"],
        )
    except KeyError:
        return None


def _data_context(df):
    """Schema + a sample of the active DataFrame for the system prompt."""
    if df is None or df.empty:
        return "No active DataFrame is loaded yet."
    lines = [f"DataFrame shape: {df.shape}", "Columns and dtypes:"]
    for col, dtype in df.dtypes.items():
        lines.append(f"- {col}: {dtype}")
    if isinstance(df.index, pd.DatetimeIndex):
        lines.append(f"Index: DatetimeIndex ({df.index.name or 'unnamed'})")
    try:
        lines.append("Sample rows:\n" + df.head(5).to_string()[:1500])
    except Exception:
        pass
    return "\n".join(lines)


def _system_prompt(df, compute):
    rules = _COMPUTE_RULES if compute else _DESCRIBE_RULES
    return f"{rules}\n\n--- Active data context ---\n{_data_context(df)}"


def extract_code(text):
    """Return the first fenced python block in ``text``, or None."""
    m = _CODE_FENCE.search(text or "")
    return m.group(1).strip() if m else None


def _stream(client, api_messages, container):
    """Stream a model reply into ``container``; return the full text."""
    full = ""
    placeholder = container.empty()
    try:
        for chunk in client.chat.completions.create(
            model=MODEL, messages=api_messages, stream=True
        ):
            full += chunk.choices[0].delta.content or ""
            placeholder.markdown(full + "▌")
        placeholder.markdown(full)
    except Exception as e:
        full = f"_Error communicating with DeepSeek: {e}_"
        placeholder.markdown(full)
    return full


def _render_artifacts(container, artifacts, key_prefix):
    """Render stored figures/tables (used live and when replaying history)."""
    for i, (kind, obj) in enumerate(artifacts):
        if kind == "figure":
            container.plotly_chart(obj, use_container_width=True, key=f"{key_prefix}_fig_{i}")
        elif kind == "dataframe":
            container.dataframe(obj, use_container_width=True, key=f"{key_prefix}_df_{i}")


def _run_compute_loop(client, df, base_messages, assistant_box):
    """Drive the write-code -> run -> interpret/fix loop. Returns (md, artifacts)."""
    api_messages = list(base_messages)
    transcript = []
    artifacts = []
    fixes = 0

    for step in range(MAX_MODEL_CALLS):
        reply = _stream(client, api_messages, assistant_box)
        transcript.append(reply)
        api_messages.append({"role": "assistant", "content": reply})

        code = extract_code(reply)
        if not code:
            break  # plain interpretation / conceptual answer -> done

        res = run_code(code, df)

        if res["fig"] is not None:
            assistant_box.plotly_chart(
                res["fig"], use_container_width=True, key=f"live_fig_{step}"
            )
            artifacts.append(("figure", res["fig"]))
        if isinstance(res["result"], (pd.DataFrame, pd.Series)):
            shown = res["result"].to_frame() if isinstance(res["result"], pd.Series) else res["result"]
            assistant_box.dataframe(shown, use_container_width=True, key=f"live_df_{step}")
            artifacts.append(("dataframe", shown))

        status = "✅ ran" if res["ok"] else "⚠️ error"
        with assistant_box.expander(f"Code {status}", expanded=not res["ok"]):
            st.code(code, language="python")
            if res["stdout"].strip():
                st.text(res["stdout"][:2000])
            if res["error"]:
                st.text(res["error"])
        transcript.append(f"\n*(code {status})*\n")

        feedback = result_to_text(res)
        tag = "EXECUTION SUCCEEDED" if res["ok"] else "EXECUTION FAILED"
        api_messages.append({"role": "user", "content": f"[{tag}]\n{feedback}"})

        if not res["ok"]:
            fixes += 1
            if fixes > MAX_FIX_ATTEMPTS:
                assistant_box.warning(
                    f"Stopped after {MAX_FIX_ATTEMPTS} fix attempts — last error shown above."
                )
                break

    return "\n".join(transcript), artifacts


def render_ai_workspace(df):
    """Render the DeepSeek chat workspace (compute or describe-only)."""
    st.header("🤖 AI Workspace (DeepSeek)")

    client = _get_client()
    if client is None:
        st.warning(
            "DeepSeek AI Workspace is not configured. "
            "Set `DEEPSEEK_API_KEY` in your Streamlit secrets."
        )
        return

    compute = st.toggle(
        "Compute mode (run code on the data)",
        value=True,
        help="The assistant writes pandas/plotly code that runs in a sandbox on "
        "your active dataset, interprets the result, and fixes its own errors. "
        "Turn off for plain describe-only chat.",
    )
    if st.button("Clear chat"):
        st.session_state.pop("ai_messages", None)
        st.rerun()

    if "ai_messages" not in st.session_state:
        st.session_state.ai_messages = []  # only user/assistant turns; system is built fresh

    # Replay history (with any stored charts/tables).
    for idx, msg in enumerate(st.session_state.ai_messages):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            _render_artifacts(st.container(), msg.get("artifacts", []), f"hist_{idx}")

    prompt = st.chat_input("Ask about the data — e.g. '20-day vol of close' or 'why did this error?'")
    if not prompt:
        return

    st.session_state.ai_messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    base_messages = [{"role": "system", "content": _system_prompt(df, compute)}]
    base_messages += [
        {"role": m["role"], "content": m["content"]} for m in st.session_state.ai_messages
    ]

    with st.chat_message("assistant"):
        box = st.container()
        if compute:
            content, artifacts = _run_compute_loop(client, df, base_messages, box)
        else:
            content, artifacts = _stream(client, base_messages, box), []

    st.session_state.ai_messages.append(
        {"role": "assistant", "content": content, "artifacts": artifacts}
    )
