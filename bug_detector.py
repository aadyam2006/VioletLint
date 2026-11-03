"""Compatibility wrapper for callers using the original bug_detector module."""

from ai_analyzer import analyze_code


def detect_bugs(code: str, language: str = "Auto detect") -> list[dict]:
    return analyze_code(code, language)["findings"]
