"""Compatibility wrapper for the complexity estimate in the main analyzer."""

from ai_analyzer import analyze_code


def analyze_complexity(code: str, language: str = "Auto detect") -> str:
    return analyze_code(code, language)["complexity"]
