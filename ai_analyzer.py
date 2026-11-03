"""Static, non-executing code analysis for the AI Code Mentor app."""

from __future__ import annotations

import ast
import re
from dataclasses import asdict, dataclass
from typing import Iterable


LANGUAGES = ("Auto detect", "Python", "Java", "C", "C++")
TREE_SITTER_NAMES = {"Java": "java", "C": "c", "C++": "cpp"}


@dataclass
class Finding:
    severity: str
    line: int
    column: int
    message: str
    rule: str
    suggestion: str = ""


def detect_language(code: str, requested: str = "Auto detect") -> str:
    """Prefer an explicit choice; use conservative signatures for auto-detection."""
    if requested in LANGUAGES[1:]:
        return requested
    stripped = code.lstrip()
    if re.search(r"#\s*include\s*[<\"]", code):
        return "C++" if re.search(r"#\s*include\s*<\s*(iostream|string|vector)\b|\bstd::", code) else "C"
    if (re.search(r"\b(public|private|protected)\s+(static\s+)?(class|interface|enum)\b|\bSystem\.out\.", code)
            or re.search(r"\bclass\s+\w+[\s\S]{0,200}\b(public|static|void|String)\b", code)):
        return "Java"
    if re.search(r"\b(def|elif|lambda|None|True|False)\b|^\s*#.*", code, re.M) or re.search(r"\bprint\s*\(", code):
        return "Python"
    if re.search(r"\b(int|char|float|double|void)\s+\w+\s*\([^;]*\)\s*\{", code):
        return "C"
    if stripped:
        return "Unknown"
    return "Unknown"


def _add(findings: list[Finding], severity: str, line: int, message: str,
         rule: str, suggestion: str = "", column: int = 1) -> None:
    findings.append(Finding(severity, max(1, line), max(1, column), message, rule, suggestion))


def _python_findings(code: str) -> tuple[list[Finding], ast.AST | None]:
    findings: list[Finding] = []
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        _add(findings, "Error", exc.lineno or 1, exc.msg, "syntax.python", column=exc.offset or 1,
             suggestion="Fix the syntax error before relying on the other analysis results.")
        return findings, None

    parents: dict[ast.AST, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent

    for node in ast.walk(tree):
        if isinstance(node, (ast.Div, ast.FloorDiv, ast.Mod)):
            parent = parents.get(node)
            if isinstance(parent, ast.BinOp) and isinstance(parent.right, ast.Constant) and parent.right.value == 0:
                _add(findings, "Error", parent.lineno, "Division or modulo by the constant zero.", "python.zero-division",
                     "Use a non-zero divisor or guard this operation.", parent.col_offset + 1)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if any(isinstance(default, (ast.List, ast.Dict, ast.Set)) for default in node.args.defaults):
                _add(findings, "Warning", node.lineno, f"Function '{node.name}' uses a mutable default argument.",
                     "python.mutable-default", "Use None as the default and create the mutable value inside the function.", node.col_offset + 1)
            # Flag an obvious disagreement between a function's name and its returned operator.
            expected = {"add": ast.Sub, "sum": ast.Sub, "subtract": ast.Add, "difference": ast.Add,
                        "multiply": ast.Div, "product": ast.Div}
            opposite = expected.get(node.name.lower())
            if opposite:
                for child in ast.walk(node):
                    if isinstance(child, ast.Return) and isinstance(child.value, ast.BinOp) and isinstance(child.value.op, opposite):
                        _add(findings, "Warning", child.lineno,
                             f"Function '{node.name}' may not match the operation in its return expression.",
                             "python.name-operation-mismatch", "Check that the function name and returned operation agree.", child.col_offset + 1)
                        break
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            _add(findings, "Warning", node.lineno, "A bare except catches every exception, including interrupts.",
                 "python.bare-except", "Catch the specific exception types this code can handle.", node.col_offset + 1)
        if isinstance(node, ast.While) and isinstance(node.test, ast.Constant) and node.test.value is True:
            if not any(isinstance(n, (ast.Break, ast.Return, ast.Raise)) for n in ast.walk(node)):
                _add(findings, "Warning", node.lineno, "This while True loop has no visible break, return, or raise.",
                     "python.possible-infinite-loop", "Confirm the loop has a deliberate exit condition.", node.col_offset + 1)

    return findings, tree


def _tree_sitter_findings(code: str, language: str) -> list[Finding]:
    findings: list[Finding] = []
    try:
        from tree_sitter_language_pack import get_parser
        parser = get_parser(TREE_SITTER_NAMES[language])
        tree = parser.parse(code.encode("utf-8"))
    except Exception as exc:  # keep app useful and be honest if a parser cannot load
        _add(findings, "Warning", 1, f"The {language} syntax parser could not be loaded ({type(exc).__name__}); syntax could not be checked.",
             "parser.unavailable", "Check that tree-sitter-language-pack installed successfully.")
        return findings

    root = tree.root_node
    stack = [root]
    errors: list[object] = []
    while stack:
        node = stack.pop()
        if node.is_error or node.is_missing:
            errors.append(node)
            # The parent error often encloses every child; report its smallest useful leaves.
            if node.is_error and node.children:
                stack.extend(reversed(node.children))
            continue
        stack.extend(reversed(node.children))
    unique: set[tuple[int, int, str]] = set()
    for node in sorted(errors, key=lambda n: (n.start_point.row, n.start_point.column, n.end_point.row)):
        line = node.start_point.row + 1
        col = node.start_point.column + 1
        label = "Missing syntax element" if node.is_missing else "Could not parse this syntax"
        key = (line, col, label)
        if key not in unique:
            unique.add(key)
            _add(findings, "Error", line, label, f"syntax.{language.lower().replace('+', 'p')}",
                 "Check punctuation, braces, declarations, and language version.", col)
    return findings


def _common_findings(code: str, language: str) -> list[Finding]:
    findings: list[Finding] = []
    for number, line in enumerate(code.splitlines(), 1):
        if re.search(r"\b(TODO|FIXME)\b", line, re.I):
            _add(findings, "Info", number, "This line is marked TODO/FIXME; confirm the work is complete.", "common.todo")
    if language == "Java":
        for m in re.finditer(r'("(?:\\.|[^"\\])*"\s*==|==\s*"(?:\\.|[^"\\])*")', code):
            _add(findings, "Warning", code.count("\n", 0, m.start()) + 1,
                 "Java string values are compared with ==; this compares object identity.", "java.string-equality",
                 "Use .equals() for string content comparison.", m.start() - code.rfind("\n", 0, m.start()))
    if language in {"C", "C++"}:
        for m in re.finditer(r"\b(?:gets|strcpy)\s*\(", code):
            _add(findings, "Warning", code.count("\n", 0, m.start()) + 1,
                 f"Use of {m.group(0).split('(')[0]} can write beyond a destination buffer.", "c.unsafe-buffer-function",
                 "Use a bounds-checked alternative and validate input sizes.", m.start() - code.rfind("\n", 0, m.start()))
        for m in re.finditer(r"\bscanf\s*\(\s*\"([^\"]*)\"([^;]*)", code):
            fmt, args = m.group(1), m.group(2)
            conversions = len(re.findall(r"%(?!%)[-+ #0]*\d*(?:\.\d+)?[hlLzjt]*[diuoxXfFeEgGaAcspn]", fmt))
            if conversions and args.strip() and args.count(",") + 1 >= conversions:
                if re.search(r"%[diuoxXfFeEgGaAcspn]", fmt) and not re.search(r"&\s*\w+", args):
                    _add(findings, "Warning", code.count("\n", 0, m.start()) + 1,
                         "scanf arguments for numeric conversions usually need address-of (&).", "c.scanf-address",
                         "Pass the address of each destination, for example &value.", m.start() + 1)
    return findings


def _complexity(code: str, language: str, tree: ast.AST | None) -> str:
    if language == "Python" and tree is not None:
        def depth(node: ast.AST, current: int = 0) -> int:
            here = current + 1 if isinstance(node, (ast.For, ast.AsyncFor, ast.While)) else current
            return max([here, *(depth(child, here) for child in ast.iter_child_nodes(node))])
        loops = depth(tree)
        return "O(n^2) or higher (estimated nested loops)" if loops >= 2 else "O(n) (estimated loop)" if loops == 1 else "O(1) (no loop detected)"
    lines = code.splitlines()
    loop_depths = []
    brace_depth = 0
    for line in lines:
        if re.search(r"\b(for|while)\s*\(", line):
            loop_depths.append(brace_depth + line.count("{") - line.count("}"))
        brace_depth = max(0, brace_depth + line.count("{") - line.count("}"))
    nested = len(loop_depths) >= 2 and max(loop_depths) - min(loop_depths) >= 1
    return "O(n^2) or higher (estimated nested loops)" if nested else "O(n) (estimated loop)" if loop_depths else "Not estimated: no loop structure detected"


def analyze_code(code: str, requested_language: str = "Auto detect") -> dict:
    language = detect_language(code, requested_language)
    findings: list[Finding] = []
    tree: ast.AST | None = None
    if language == "Python":
        findings, tree = _python_findings(code)
    elif language in TREE_SITTER_NAMES:
        findings = _tree_sitter_findings(code, language)
    else:
        _add(findings, "Info", 1, "Select Python, Java, C, or C++ for supported analysis.", "language.unsupported")

    findings.extend(_common_findings(code, language))
    findings.sort(key=lambda f: ({"Error": 0, "Warning": 1, "Info": 2}.get(f.severity, 3), f.line, f.column))
    errors = sum(f.severity == "Error" for f in findings)
    warnings = sum(f.severity == "Warning" for f in findings)
    if not findings:
        findings.append(Finding("Info", 1, 1,
            "No issues were found by the checks available for this language. This does not prove the program is bug-free.",
            "analysis.no-findings"))

    explanation = f"Analyzed as {language}. Analysis is static: the submitted program is not executed."
    parser_unavailable = language not in {"Python", *TREE_SITTER_NAMES} or any(f.rule == "parser.unavailable" for f in findings)
    syntax_errors = any(f.severity == "Error" and f.rule.startswith("syntax.") for f in findings)
    syntax_status = "Unavailable" if parser_unavailable else "Errors found" if syntax_errors else "No syntax errors found"
    return {
        "language": language,
        "explanation": explanation,
        "findings": [asdict(f) for f in findings],
        "bugs": findings,
        "errors": errors,
        "warnings": warnings,
        "complexity": _complexity(code, language, tree),
        "fix": None,
        "syntax_ok": None if parser_unavailable else not syntax_errors,
        "syntax_status": syntax_status,
        "limitations": "Static checks can identify syntax errors and known suspicious patterns, but cannot prove correctness or detect every logic bug.",
    }
