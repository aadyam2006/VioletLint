"""Run single-file programs through OnlineCompiler's remote sandbox."""

from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


MAX_SOURCE_BYTES = 12_000
MAX_STDIN_BYTES = 2_000
MAX_OUTPUT_CHARS = 12_000
RUN_URL = "https://api.onlinecompiler.io/api/run-code-sync/"
COMPILERS = {
    "Python": "python-3.14",
    "Java": "openjdk-25",
    "C": "gcc-15",
    "C++": "g++-15",
}


class SandboxError(RuntimeError):
    """A concise, user-displayable error from the code runner."""


def _api_key() -> str:
    """Read the API key from environment or Streamlit secrets, never the UI."""
    key = os.environ.get("ONLINECOMPILER_API_KEY", "").strip()
    if key:
        return key
    try:
        import streamlit as st

        return str(st.secrets.get("ONLINECOMPILER_API_KEY", "")).strip()
    except Exception:
        return ""


def _friendly_http_error(exc: HTTPError) -> SandboxError:
    detail = exc.read(1200).decode("utf-8", errors="replace")
    if exc.code in {401, 403}:
        return SandboxError(
            "OnlineCompiler rejected the API key. Check that ONLINECOMPILER_API_KEY "
            "is set correctly in Streamlit Secrets."
        )
    if exc.code == 429:
        return SandboxError(
            "The free compiler service is busy or this account reached a usage limit. "
            "Wait a little and check the OnlineCompiler dashboard; no run was started."
        )
    if exc.code >= 500:
        return SandboxError("OnlineCompiler is temporarily unavailable. Try again later.")
    return SandboxError(f"OnlineCompiler returned HTTP {exc.code}: {detail}")


def run_code(source: str, language: str, stdin: str = "") -> dict:
    """Compile/run one file remotely and return output and status details."""
    if not source.strip():
        raise SandboxError("Paste some code before running it.")
    if len(source.encode("utf-8")) > MAX_SOURCE_BYTES:
        raise SandboxError(f"Code is too large. Keep it under {MAX_SOURCE_BYTES:,} bytes.")
    if len(stdin.encode("utf-8")) > MAX_STDIN_BYTES:
        raise SandboxError(f"Input is too large. Keep it under {MAX_STDIN_BYTES:,} bytes.")
    if language not in COMPILERS:
        raise SandboxError("Choose Python, Java, C, or C++ before running this code.")

    key = _api_key()
    if not key:
        raise SandboxError(
            "Code running needs a free OnlineCompiler API key. Add ONLINECOMPILER_API_KEY "
            "to Streamlit Cloud → Manage app → Settings → Secrets, then restart the app. "
            "For local VS Code, put it in .streamlit/secrets.toml. Do not paste the key here or commit it to GitHub."
        )

    payload = json.dumps(
        {"compiler": COMPILERS[language], "code": source, "input": stdin}
    ).encode("utf-8")
    request = Request(
        RUN_URL,
        data=payload,
        headers={
            "Authorization": key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=40) as response:
            data = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise _friendly_http_error(exc) from None
    except (URLError, TimeoutError, OSError) as exc:
        raise SandboxError(f"Could not reach OnlineCompiler: {exc}") from None
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise SandboxError("OnlineCompiler returned an unreadable response.") from None

    if not isinstance(data, dict):
        raise SandboxError("OnlineCompiler returned an invalid execution result.")

    status = str(data.get("status", ""))
    exit_code = data.get("exit_code")
    error_text = data.get("error") or ""
    result = {
        "stdout": data.get("output") or "",
        "stderr": error_text if status != "success" else "",
        # The API uses the same `error` field for compiler and runtime stderr.
        "compiler_error": "",
        "compiler_output": "",
        "exit_code": str(exit_code if exit_code is not None else (0 if status == "success" else 1)),
        "signal": data.get("signal") or "",
        "status_description": (
            "Finished" if status == "success"
            else (status.replace("_", " ").title() or "Execution failed")
        ),
        "runtime": data.get("time") or "",
        "memory": data.get("memory") or "",
        "message": "",
    }
    for key_name in ("stdout", "stderr", "compiler_error", "compiler_output"):
        value = result[key_name]
        if isinstance(value, str) and len(value) > MAX_OUTPUT_CHARS:
            result[key_name] = value[:MAX_OUTPUT_CHARS] + "\n… output truncated …"
    return result
