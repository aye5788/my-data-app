"""DeepSeek-backed AI workspace (chat over the app + active dataset)."""
import streamlit as st
from openai import OpenAI

MODEL = "deepseek-chat"


def _get_client():
    """Build a DeepSeek client from secrets, or return None if unconfigured."""
    try:
        return OpenAI(
            base_url="https://api.deepseek.com",
            api_key=st.secrets["DEEPSEEK_API_KEY"],
        )
    except KeyError:
        return None


def get_current_context(df):
    """Build a context string describing the app + active DataFrame for the LLM."""
    context_parts = []

    try:
        with open("app.py", "r") as f:
            app_snippet = "\n".join(f.read().splitlines()[:50])
        context_parts.append(
            "--- app.py snippet ---\n" + app_snippet + "\n--- End of app.py snippet ---"
        )
    except FileNotFoundError:
        context_parts.append("`app.py` file not found for context.")

    if df is not None and not df.empty:
        context_parts.append("\n--- Active DataFrame Context ---")
        context_parts.append(f"DataFrame Shape: {df.shape}")
        context_parts.append("DataFrame Columns and dtypes:")
        for col, dtype in df.dtypes.items():
            context_parts.append(f"- {col}: {dtype}")
        context_parts.append("--- End of DataFrame Context ---")
    else:
        context_parts.append("\nNo active DataFrame loaded yet.")

    return "\n".join(context_parts)


def render_ai_workspace(df):
    """Render the DeepSeek chat workspace."""
    st.header("🤖 AI Workspace (DeepSeek)")

    client = _get_client()
    if client is None:
        st.warning(
            "DeepSeek AI Workspace is not configured. "
            "Please ensure `DEEPSEEK_API_KEY` is set in your Streamlit secrets."
        )
        return

    if "messages" not in st.session_state:
        initial_context = get_current_context(df)
        st.session_state.messages = [
            {
                "role": "system",
                "content": "You are a helpful AI assistant. Here is the current "
                f"application and data context:\n{initial_context}",
            }
        ]

    for message in st.session_state.messages:
        if message["role"] != "system":
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    if prompt := st.chat_input("Ask me anything about the data or app..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""

            messages_for_api = []
            system_message_content = next(
                (m["content"] for m in st.session_state.messages if m["role"] == "system"),
                None,
            )
            if system_message_content:
                messages_for_api.append({"role": "system", "content": system_message_content})
            for msg in st.session_state.messages:
                if msg["role"] != "system":
                    messages_for_api.append(msg)

            try:
                for response in client.chat.completions.create(
                    model=MODEL,
                    messages=messages_for_api,
                    stream=True,
                ):
                    full_response += response.choices[0].delta.content or ""
                    message_placeholder.markdown(full_response + "▌")
                message_placeholder.markdown(full_response)
            except Exception as e:
                st.error(f"Error communicating with DeepSeek API: {e}")
                full_response = "I'm sorry, I couldn't get a response from the AI."
                message_placeholder.markdown(full_response)
        st.session_state.messages.append({"role": "assistant", "content": full_response})
