def answer_question(code: str, question: str, analysis: dict | None = None) -> str:
    """A transparent local helper; does not call a pretend or hard-coded AI API."""
    q = question.casefold()
    if analysis is None:
        return "Analyze your code first so I can refer to its findings."
    if any(word in q for word in ("bug", "error", "warning", "issue")):
        findings = analysis.get("findings", [])
        if not findings:
            return "The configured checks did not find an issue. That does not prove the code is correct."
        return "Findings from the configured static checks:\n\n" + "\n".join(
            f"- {f['severity']} at line {f['line']}: {f['message']}" for f in findings
        )
    if "complex" in q or "big o" in q:
        return f"The static estimate is {analysis.get('complexity', 'unavailable')}. This is a heuristic, not a proof."
    if any(word in q for word in ("language", "written", "which")):
        return f"The code was analyzed as {analysis.get('language', 'Unknown')}."
    if any(word in q for word in ("what does", "explain", "purpose")):
        return (f"The code was analyzed as {analysis.get('language', 'Unknown')}. "
                "The app does not execute it; review the findings and the code outline above for details.")
    return "I can summarize the detected language, findings, and complexity estimate. Try asking about bugs, errors, or complexity."
