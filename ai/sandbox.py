"""Sandboxed execution of model-generated analysis code.

A snippet runs in a restricted namespace that exposes only a copy of the
active DataFrame (``df``) and the analysis libraries (``pd``/``np``/``px``/
``go``). There is no ``__import__``, ``open``, ``eval``/``exec``, file, or
network access, so the worst a snippet can do is raise or compute a wrong
value -- it cannot touch the filesystem, secrets, or the network.

Note: CPython sandboxing is not bulletproof against a *determined* adversary
crafting malicious bytecode-level escapes. This is a guardrail against
accidental or destructive operations in a personal tool, not a hardened
security boundary for hostile input.
"""
import builtins as _builtins
import contextlib
import io
import traceback

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Builtins a snippet may use. Deliberately absent: __import__, open, eval,
# exec, compile, input, globals, vars, getattr/setattr/delattr -- removing the
# usual import/file/network escape hatches.
_SAFE_BUILTIN_NAMES = [
    "abs", "all", "any", "bool", "dict", "divmod", "enumerate", "filter",
    "float", "format", "frozenset", "int", "len", "list", "map", "max", "min",
    "print", "range", "repr", "reversed", "round", "set", "slice", "sorted",
    "str", "sum", "tuple", "zip", "True", "False", "None",
]


def _safe_builtins():
    out = {}
    for name in _SAFE_BUILTIN_NAMES:
        if hasattr(_builtins, name):
            out[name] = getattr(_builtins, name)
    return out


def run_code(code, df):
    """Execute ``code`` against a copy of ``df`` in a restricted namespace.

    The snippet may assign ``result`` (number/str/DataFrame/Series) and/or
    ``fig`` (a plotly figure). Returns a dict:
    ``{ok, stdout, result, fig, error}`` where ``error`` is a short traceback
    string on failure (and ``ok`` is False).
    """
    namespace = {
        "__builtins__": _safe_builtins(),
        "df": df.copy() if df is not None else None,
        "pd": pd,
        "np": np,
        "px": px,
        "go": go,
        "result": None,
        "fig": None,
    }
    buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(buffer):
            exec(code, namespace)  # sandboxed: restricted builtins, no imports
        return {
            "ok": True,
            "stdout": buffer.getvalue(),
            "result": namespace.get("result"),
            "fig": namespace.get("fig"),
            "error": None,
        }
    except Exception:
        return {
            "ok": False,
            "stdout": buffer.getvalue(),
            "result": None,
            "fig": None,
            "error": traceback.format_exc(limit=3),
        }


def result_to_text(res, max_chars=2000):
    """Summarize an execution result as plain text to feed back to the model."""
    parts = []
    if res["stdout"].strip():
        parts.append("STDOUT:\n" + res["stdout"].strip()[:max_chars])

    val = res["result"]
    if isinstance(val, pd.DataFrame):
        parts.append(
            f"RESULT is a DataFrame, shape {val.shape}:\n"
            + val.head(20).to_string()[:max_chars]
        )
    elif isinstance(val, pd.Series):
        parts.append(
            f"RESULT is a Series, length {len(val)}:\n"
            + val.head(20).to_string()[:max_chars]
        )
    elif val is not None:
        parts.append("RESULT: " + str(val)[:max_chars])

    if res["fig"] is not None:
        parts.append("A plotly figure was produced and shown to the user.")

    if not parts:
        parts.append("Code ran with no `result`, `fig`, or printed output.")

    return "\n\n".join(parts)
