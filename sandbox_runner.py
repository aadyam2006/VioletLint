"""Run user code through the Judge0 sandbox API (never on the Streamlit host)."""

from __future__ import annotations

import json
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


MAX_SOURCE_BYTES = 12_000
MAX_STDIN_BYTES = 2_000
MAX_OUTPUT_CHARS = 12_000
PENDING_STATUS_IDS = {1, 2}  # In Queue, Processing


class SandboxError(RuntimeError):
    """A safe, user-displayable error returned while contacting Judge0."""


def _request_json(url: str, *, method: str = "GET", payload: dict | None = None,
                  headers: dict[str, str] | None = None, timeout: float = 8) -> dict | list:
    request_headers = {"Accept": "application/json", **(headers or {})}
    data = None
    if payload is not None:
        request_headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")
    request = Request(url, data=data, headers=request_headers, method=method)
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read(1500).decode("utf-8", errors="replace")
        raise SandboxError(f"Judge0 returned HTTP {exc.code}: {detail}") from None
    except (URLError, TimeoutError, OSError) as exc:
        raise SandboxError(f"Could not reach the code sandbox: {exc}") from None
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise SandboxError("The code sandbox returned an unreadable response.") from None


def _find_language_id(languages: list[dict], language: str) -> int:
    if language == "Python":
        matches = [item for item in languages if item.get("name", "").startswith("Python")]
    elif language == "Java":
        matches = [item for item in languages if item.get("name", "").startswith("Java")]
    elif language == "C":
        matches = [item for item in languages if item.get("name", "").startswith("C (")]
    elif language == "C++":
        matches = [item for item in languages if item.get("name", "").startswith("C++")]
    else:
        matches = []
    if not matches:
        raise SandboxError(f"Judge0 does not currently list an active {language} runtime.")
    # Judge0 usually returns one version per language; choosing the highest ID
    # picks the newest listed version when several are offered.
    return int(max(matches, key=lambda item: int(item["id"]))["id"])


def run_code(source: str, language: str, stdin: str = "", *,
             api_url: str = "https://ce.judge0.com", api_token: str = "") -> dict:
    """Submit one file, poll briefly, and return stdout/stderr/status metadata."""
    if not source.strip():
        raise SandboxError("Paste some code before running it.")
    if len(source.encode("utf-8")) > MAX_SOURCE_BYTES:
        raise SandboxError(f"Code is too large. Keep it under {MAX_SOURCE_BYTES:,} bytes.")
    if len(stdin.encode("utf-8")) > MAX_STDIN_BYTES:
        raise SandboxError(f"Input is too large. Keep it under {MAX_STDIN_BYTES:,} bytes.")

    base = api_url.strip().rstrip("/")
    if not base.startswith("https://"):
        raise SandboxError("The Judge0 endpoint must use HTTPS.")
    headers = {"X-Auth-Token": api_token} if api_token else {}
    languages = _request_json(f"{base}/languages", headers=headers)
    if not isinstance(languages, list):
        raise SandboxError("Judge0 returned an invalid language list.")
    language_id = _find_language_id(languages, language)

    submission = {
        "source_code": source,
        "language_id": language_id,
        "stdin": stdin,
        "cpu_time_limit": 2,
        "cpu_extra_time": 1,
        "wall_time_limit": 5,
        "memory_limit": 131072,
        "stack_limit": 64000,
        "max_processes_and_or_threads": 20,
        "max_file_size": 1024,
        "enable_network": False,
    }
    created = _request_json(
        f"{base}/submissions/?base64_encoded=false&wait=false",
        method="POST", payload=submission, headers=headers,
    )
    token = created.get("token") if isinstance(created, dict) else None
    if not token:
        raise SandboxError("Judge0 did not provide a run token.")

    fields = "stdout,stderr,compile_output,status,time,memory,exit_code,message"
    query = urlencode({"base64_encoded": "false", "fields": fields})
    deadline = time.monotonic() + 12
    result: dict = {}
    while time.monotonic() < deadline:
        result = _request_json(f"{base}/submissions/{token}?{query}", headers=headers)
        if not isinstance(result, dict):
            raise SandboxError("Judge0 returned an invalid run result.")
        status = result.get("status") or {}
        if status.get("id") not in PENDING_STATUS_IDS:
            break
        time.sleep(0.5)
    else:
        raise SandboxError("The run is still queued. Please try again in a moment.")

    status = result.get("status") or {}
    result["status_description"] = status.get("description", "Finished")
    for key in ("stdout", "stderr", "compile_output", "message"):
        value = result.get(key)
        if isinstance(value, str) and len(value) > MAX_OUTPUT_CHARS:
            result[key] = value[:MAX_OUTPUT_CHARS] + "\n… output truncated …"
    return result
