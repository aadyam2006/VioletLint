"""Compatibility wrapper: explanations are generated locally without a fake API key."""

from ai_analyzer import analyze_code


def explain_code(code: str, language: str = "Auto detect") -> str:
    result = analyze_code(code, language)
    return result["explanation"]
