# AI Code Mentor

A Streamlit learning tool for static code review. It supports Python, Java, C, and C++ syntax parsing and selected warning checks. The submitted program is never executed.

## Run locally

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
```

## Supported analysis

- Python: Python's AST parser reports syntax errors. Selected checks identify constant division by zero, mutable default arguments, bare `except`, suspicious endless loops, and a narrow name/operation mismatch case.
- Java, C, and C++: Tree-sitter parses source and reports syntax error locations. Selected pattern checks warn about Java string identity comparisons and unsafe C/C++ buffer functions or likely missing `&` in `scanf` destinations.
- All supported languages: a rough loop-based complexity estimate and a compact source outline are shown.

These are static checks, not a complete compiler, type checker, security scanner, or proof of correctness. They can miss real defects and can flag code that is intentional. The app does not execute user code. Complexity estimates are especially approximate for Java, C, and C++.

## Adding checks

Add deterministic rules to `_python_findings` or `_common_findings` in `ai_analyzer.py`. Keep findings specific: severity, source line, rule identifier, explanation, and an optional suggestion. Prefer warnings for suspicious patterns that are not certainly incorrect. Add a sample demonstrating both the trigger and a nearby safe case before introducing a new rule.
