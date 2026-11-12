# VioletLint

A dark blue-and-cyan Streamlit workspace for learning from code reviews. VioletLint supports Python, Java, C, and C++ syntax parsing and selected warning checks. The analyzer is static; an optional **Run code in sandbox** action sends a single-file program to Judge0 and displays its output or errors.

> 🚀 **Live Interactive Demo:** [Open VioletLint](https://violetlint.streamlit.app/) ↗
> Click the link to try the code review studio in your browser.

## Run locally

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
```

## Interface

The app opens with a bold blue-and-cyan landing hero, refined type, and quick feature cards, followed by a dark code workspace with the editor beside review settings. Choose a language or use auto-detect, then select a full review or syntax-only view. **Analyze my code** only inspects the source; **Run code in sandbox** is a separate, optional action.

## Run a program

Click **Run code in sandbox** to compile/execute a single-file Python, Java, C, or C++ program and view stdout, stderr, compile errors, runtime, and memory. Optional stdin can be entered under **Program input**. Runs are submitted to Judge0 CE over HTTPS, not executed by the Streamlit server. The integration applies time and memory limits, disables network access for the submitted program, and limits source/input/output sizes. Java examples should use a `Main` class.

Running code sends the pasted source and stdin to Judge0. Do not submit passwords, API keys, private source code, or other sensitive information. The hosted Judge0 endpoint may have availability, language-version, or usage limits. A self-hosted or authenticated Judge0 endpoint can be configured in Streamlit secrets:

```toml
JUDGE0_API_URL = "https://your-judge0-host"
JUDGE0_AUTH_TOKEN = "your-token-if-required"
```

The token is optional when the configured Judge0 instance does not require authentication. Never commit real credentials to GitHub.

## Supported analysis

- Python: Python's AST parser reports syntax errors. Selected checks identify constant division by zero, mutable default arguments, bare `except`, suspicious endless loops, and a narrow name/operation mismatch case.
- Java, C, and C++: Tree-sitter parses source and reports syntax error locations. Selected pattern checks warn about Java string identity comparisons and unsafe C/C++ buffer functions or likely missing `&` in `scanf` destinations.
- All supported languages: a rough loop-based complexity estimate and a compact source outline are shown.

The results also include a heuristic auxiliary-space estimate, example replacements for a few recognized warning patterns, and a conditional hash set/map optimization tip for nested comparison loops. These suggestions only apply when their stated conditions fit the program.

These are static checks, not a complete compiler, type checker, security scanner, or proof of correctness. They can miss real defects and can flag code that is intentional. Replacement examples are provided only for a few recognized patterns and should be reviewed before use. The static analyzer does not execute user code; the separate sandbox run only executes after the user explicitly clicks its button. Time and space complexity estimates are approximate for every language, especially when called functions, recursion, library behavior, or input sizes affect the result.

## Adding checks

Add deterministic rules to `_python_findings` or `_common_findings` in `ai_analyzer.py`. Keep findings specific: severity, source line, rule identifier, explanation, and an optional suggestion. Prefer warnings for suspicious patterns that are not certainly incorrect. Add a sample demonstrating both the trigger and a nearby safe case before introducing a new rule.
