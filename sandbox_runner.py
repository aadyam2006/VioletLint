"""Submit single-file programs to Wandbox's remote compiler sandbox."""

from __future__ import annotations

import json
from functools import lru_cache
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


MAX_SOURCE_BYTES = 12_000
MAX_STDIN_BYTES = 2_000
MAX_OUTPUT_CHARS = 12_000
WANDBOX_API = "https://wandbox.org/api"


class SandboxError(RuntimeError):
    """A concise, user-displayable error from the code runner."""


def _request_json(url: str, *, payload: dict | None = None, timeout: float = 25) -> dict | list:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = Request(url, data=data, headers=headers)
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read(1000).decode("utf-8", errors="replace")
        raise SandboxError(f"Wandbox returned HTTP {exc.code}: {detail}") from None
    except (URLError, TimeoutError, OSError) as exc:
        raise SandboxError(f"Could not reach Wandbox: {exc}") from None
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise SandboxError("Wandbox returned an unreadable response.") from None


@lru_cache(maxsize=1)
def _compiler_list() -> tuple[dict, ...]:
    """Cache the compiler catalog so repeated runs don't keep fetching it."""
    entries = _request_json(f"{WANDBOX_API}/list.json", timeout=10)
    if not isinstance(entries, list):
        raise SandboxError("Wandbox returned an invalid compiler list.")
    return tuple(item for item in entries if isinstance(item, dict))


def _find_compiler(language: str) -> str:
    entries = [item for item in _compiler_list() if item.get("language") == language]
    # Prefer stable compiler versions over experimental HEAD builds.
    entries = [item for item in entries if "head" not in item.get("name", "").lower()]
    if language == "C":
        entries = [item for item in entries if item.get("name", "").startswith("gcc-")]
    elif language == "C++":
        entries = [item for item in entries if item.get("name", "").startswith("gcc-")]
    elif language == "Python":
        entries = [item for item in entries if item.get("name", "").startswith("cpython-")]
    elif language == "Java":
        entries = [item for item in entries if item.get("name", "").startswith("openjdk-")]
    if not entries:
        raise SandboxError(f"Wandbox does not currently list a stable {language} compiler.")
    return str(entries[0]["name"])


def run_code(source: str, language: str, stdin: str = "") -> dict:
    """Compile/run one file remotely and return output and status details."""
    if not source.strip():
        raise SandboxError("Paste some code before running it.")
    if len(source.encode("utf-8")) > MAX_SOURCE_BYTES:
        raise SandboxError(f"Code is too large. Keep it under {MAX_SOURCE_BYTES:,} bytes.")
    if len(stdin.encode("utf-8")) > MAX_STDIN_BYTES:
        raise SandboxError(f"Input is too large. Keep it under {MAX_STDIN_BYTES:,} bytes.")
    if language not in {"Python", "Java", "C", "C++"}:
        raise SandboxError("Choose Python, Java, C, or C++ before running this code.")

    compiler = _find_compiler(language)
    response = _request_json(
        f"{WANDBOX_API}/compile.json",
        payload={"compiler": compiler, "code": source, "stdin": stdin, "save": False},
    )
    if not isinstance(response, dict):
        raise SandboxError("Wandbox returned an invalid execution result.")

    status = str(response.get("status", ""))
    compiler_error = response.get("compiler_error") or ""
    compiler_output = response.get("compiler_output") or ""
    result = {
        "stdout": response.get("program_output") or "",
        "stderr": response.get("program_error") or "",
        "compiler_error": compiler_error,
        "compiler_output": compiler_output,
        "exit_code": status,
        "signal": response.get("signal") or "",
        "status_description": "Finished" if status == "0" else "Execution failed",
    }
    for key in ("stdout", "stderr", "compiler_error", "compiler_output"):
        value = result[key]
        if isinstance(value, str) and len(value) > MAX_OUTPUT_CHARS:
            result[key] = value[:MAX_OUTPUT_CHARS] + "\n… output truncated …"
    return result
