# VioletLint

A dark, purple-themed Streamlit workspace for learning from code reviews. VioletLint supports Python, Java, C, and C++ syntax parsing and selected warning checks. The submitted program is never executed.

## Run locally

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
```

## Interface

The app opens with a bold violet landing hero, refined type, and quick feature cards, followed by a dark code workspace with the editor beside review settings. Choose a language or use auto-detect, then select a full review or syntax-only view.

## Supported analysis

- Python: Python's AST parser reports syntax errors. Selected checks identify constant division by zero, mutable default arguments, bare `except`, suspicious endless loops, and a narrow name/operation mismatch case.
- Java, C, and C++: Tree-sitter parses source and reports syntax error locations. Selected pattern checks warn about Java string identity comparisons and unsafe C/C++ buffer functions or likely missing `&` in `scanf` destinations.
- All supported languages: a rough loop-based complexity estimate and a compact source outline are shown.

The results also include a heuristic auxiliary-space estimate, example replacements for a few recognized warning patterns, and a conditional hash set/map optimization tip for nested comparison loops. These suggestions only apply when their stated conditions fit the program.

These are static checks, not a complete compiler, type checker, security scanner, or proof of correctness. They can miss real defects and can flag code that is intentional. Replacement examples are provided only for a few recognized patterns and should be reviewed before use. The app does not execute user code. Time and space complexity estimates are approximate for every language, especially when called functions, recursion, library behavior, or input sizes affect the result.

## Adding checks

Add deterministic rules to `_python_findings` or `_common_findings` in `ai_analyzer.py`. Keep findings specific: severity, source line, rule identifier, explanation, and an optional suggestion. Prefer warnings for suspicious patterns that are not certainly incorrect. Add a sample demonstrating both the trigger and a nearby safe case before introducing a new rule.
