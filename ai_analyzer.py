"""Static, non-executing code analysis for the AI Code Mentor app."""

from __future__ import annotations

import ast
import re
from dataclasses import asdict, dataclass


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
    replacement: str = ""


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
         rule: str, suggestion: str = "", column: int = 1, replacement: str = "") -> None:
    findings.append(Finding(severity, max(1, line), max(1, column), message, rule, suggestion, replacement))


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
            corrected_operator = {"add": "+", "sum": "+", "subtract": "-", "difference": "-",
                                  "multiply": "*", "product": "*"}
            opposite = expected.get(node.name.lower())
            if opposite:
                for child in ast.walk(node):
                    if isinstance(child, ast.Return) and isinstance(child.value, ast.BinOp) and isinstance(child.value.op, opposite):
                        _add(findings, "Warning", child.lineno,
                             f"Function '{node.name}' may not match the operation in its return expression.",
                             "python.name-operation-mismatch", "Check that the function name and returned operation agree.",
                             child.col_offset + 1,
                             f"return {ast.unparse(child.value.left)} {corrected_operator[node.name.lower()]} {ast.unparse(child.value.right)}")
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
        for m in re.finditer(r'("(?:\\.|[^"\\])*"|\b[A-Za-z_]\w*)\s*==\s*("(?:\\.|[^"\\])*"|\b[A-Za-z_]\w*)', code):
            left, right = m.group(1), m.group(2)
            if '"' not in left and '"' not in right:
                continue
            expression = f"{left}.equals({right})" if '"' not in left else f"{right}.equals({left})"
            _add(findings, "Warning", code.count("\n", 0, m.start()) + 1,
                 "Java string values are compared with ==; this compares object identity.", "java.string-equality",
                 "Use .equals() for string content comparison.", m.start() - code.rfind("\n", 0, m.start()), expression)
    if language in {"C", "C++"}:
        for m in re.finditer(r"\b(?:gets|strcpy)\s*\(", code):
            call_end = code.find(")", m.end())
            replacement = ""
            if call_end >= 0 and m.group(0).lstrip().startswith("strcpy"):
                args = [part.strip() for part in code[m.end():call_end].split(",", 1)]
                if len(args) == 2 and re.fullmatch(r"[A-Za-z_]\w*", args[0]) and re.fullmatch(r'"[^"\\]*"', args[1]):
                    namespace = "std::" if language == "C++" and code[max(0, m.start() - 5):m.start()].endswith("std::") else ""
                    replacement = f'{namespace}snprintf({args[0]}, sizeof {args[0]}, "%s", {args[1]})'
            buffer_suggestion = "Use a bounds-checked alternative and validate input sizes."
            if replacement:
                buffer_suggestion += " Include <cstdio> for std::snprintf in C++, or <stdio.h> for snprintf in C."
            _add(findings, "Warning", code.count("\n", 0, m.start()) + 1,
                 f"Use of {m.group(0).split('(')[0]} can write beyond a destination buffer.", "c.unsafe-buffer-function",
                 buffer_suggestion, m.start() - code.rfind("\n", 0, m.start()), replacement)
        for m in re.finditer(r"\bscanf\s*\(\s*\"([^\"]*)\"([^;]*)", code):
            fmt, args = m.group(1), m.group(2)
            conversions = len(re.findall(r"%(?!%)[-+ #0]*\d*(?:\.\d+)?[hlLzjt]*[diuoxXfFeEgGaAcspn]", fmt))
            if conversions and args.strip() and args.count(",") + 1 >= conversions:
                if re.search(r"%[diuoxXfFeEgGaAcspn]", fmt) and not re.search(r"&\s*\w+", args):
                    arg_match = re.search(r",\s*([A-Za-z_]\w*)", args)
                    replacement = ""
                    if arg_match:
                        full_call_end = code.find(")", m.start())
                        if full_call_end >= 0:
                            call = code[m.start():full_call_end + 1]
                            relative_arg_start = m.start(2) + arg_match.start() - m.start()
                            replacement = call[:relative_arg_start] + call[relative_arg_start:].replace(
                                arg_match.group(1), "&" + arg_match.group(1), 1)
                    _add(findings, "Warning", code.count("\n", 0, m.start()) + 1,
                         "scanf arguments for numeric conversions usually need address-of (&).", "c.scanf-address",
                         "Pass the address of each destination, for example &value.", m.start() + 1, replacement)
    return findings


def _complexity_report(code: str, language: str, tree: ast.AST | None) -> dict:
    """Return explicitly heuristic time/auxiliary-space estimates and a narrow optimization tip."""
    loop_depth = 0
    recursive = False

    if language == "Python" and tree is not None:
        def measure(node: ast.AST, current: int = 0) -> int:
            here = current + 1 if isinstance(node, (ast.For, ast.AsyncFor, ast.While)) else current
            return max([here, *(measure(child, here) for child in ast.iter_child_nodes(node))])
        loop_depth = measure(tree)
        function_names = {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
        recursive = any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in function_names for n in ast.walk(tree))
    elif language in TREE_SITTER_NAMES:
        brace_depth = 0
        depths: list[int] = []
        for line in code.splitlines():
            if re.search(r"\b(for|while)\s*\(", line):
                depths.append(max(0, brace_depth))
            brace_depth = max(0, brace_depth + line.count("{") - line.count("}"))
        loop_depth = (max(depths) - min(depths) + 1) if len(depths) > 1 else len(depths)
        for function_name in re.findall(r"\b(?:void|int|char|float|double|String|boolean)\s+(\w+)\s*\([^)]*\)\s*\{", code):
            if len(re.findall(rf"\b{re.escape(function_name)}\s*\(", code)) > 1:
                recursive = True
                break

    has_sort = bool(re.search(r"\b(?:sorted|sort|Arrays\.sort|Collections\.sort|std::sort)\s*\(|\.sort\s*\(", code))
    has_linear_library_call = bool(re.search(r"\b(?:strcpy|strncpy|strlen|strcmp|memcpy|memmove)\s*\(|\.contains\s*\(|\.indexOf\s*\(", code))
    repeated_linear_lookup = loop_depth >= 1 and bool(re.search(
        r"\bif\b[^\n]*\bin\s+[A-Za-z_]\w*|\.contains\s*\(|\.indexOf\s*\(|\bstd::find\s*\(", code))
    if loop_depth >= 2:
        time = "O(n²) or higher (estimated nested loops)"
    elif repeated_linear_lookup:
        time = "O(n²) estimated (loop with repeated linear search)"
    elif has_sort:
        time = "O(n log n) (sorting pattern detected)"
    elif loop_depth == 1:
        time = "O(n) (estimated single loop)"
    elif has_linear_library_call:
        time = "O(n) (known linear operation detected)"
    elif recursive:
        time = "Not estimated (recursive calls need input-specific analysis)"
    else:
        time = "O(1) apparent work (called functions may add cost)"

    if re.search(r"\b(?:append|extend|push_back|emplace_back)\s*\(|\b(?:malloc|calloc|realloc)\s*\(|\bnew\s+\w+\s*\[|\b(?:ArrayList|HashMap|HashSet|Vector|vector|unordered_map|unordered_set)\s*<|\b(?:list|dict|set)\s*\(", code):
        space = "O(n) estimated auxiliary space (growing collection/allocation detected)"
    elif recursive:
        space = "O(n) estimated call stack (recursive call detected)"
    else:
        space = "O(1) estimated auxiliary space (no growing storage detected)"

    optimizations: list[dict[str, str]] = []
    has_pair_comparison = bool(re.search(r"(?:==|\.equals\s*\(|\bcompare\s*\()", code))
    indexed_pair_match = re.search(
        r"\b([A-Za-z_]\w*)\s*\[\s*i\s*\]\s*==\s*\1\s*\[\s*j\s*\]", code)
    indexed_pair_comparison = indexed_pair_match is not None
    collection_name = indexed_pair_match.group(1) if indexed_pair_match else "values"
    pair_output = bool(re.search(
        r"\.\s*(?:push_back|append|add)\s*\([^;\n]*(?:\bi\b[^;\n]*\bj\b|\bj\b[^;\n]*\bi\b)", code))
    enumerates_duplicate_pairs = loop_depth >= 2 and indexed_pair_comparison and pair_output
    prints_duplicate_values = (
        loop_depth >= 2
        and indexed_pair_comparison
        and bool(re.search(r"\b(?:cout|printf|print|println)\b", code))
        and not enumerates_duplicate_pairs
    )

    if enumerates_duplicate_pairs:
        pair_examples = {
            "Python": (
                "from collections import defaultdict\n"
                "previous = defaultdict(list)\n"
                "pairs = []\n"
                "for j, value in enumerate(values):\n"
                "    for i in previous[value]:\n"
                "        pairs.append((i, j, value))\n"
                "    previous[value].append(j)"
            ),
            "Java": (
                "Map<Integer, List<Integer>> previous = new HashMap<>();\n"
                "for (int j = 0; j < values.length; j++) {\n"
                "    List<Integer> indexes = previous.get(values[j]);\n"
                "    if (indexes != null) for (int i : indexes) pairs.add(i + \",\" + j);\n"
                "    previous.computeIfAbsent(values[j], k -> new ArrayList<>()).add(j);\n"
                "}"
            ),
            "C++": (
                "std::unordered_map<int, std::vector<int>> previous;\n"
                "for (int j = 0; j < static_cast<int>(values.size()); ++j) {\n"
                "    auto& indexes = previous[values[j]];\n"
                "    for (int i : indexes) duplicatePairs.push_back({i, j});\n"
                "    indexes.push_back(j);\n"
                "}"
            ),
            "C": (
                "Use a hash table from each value to its earlier indexes.\n"
                "For each value, emit pairs only with those earlier indexes,\n"
                "then add the current index to that value's list."
            ),
        }
        optimizations.append({
            "title": "Group earlier indexes by value",
            "detail": (
                "This preserves every matching index pair. It takes expected O(n + k) time, "
                "where k is the number of pairs produced, and O(n + k) space when storing "
                "the output. If many values are equal, k can be O(n²), so that worst case "
                "cannot be avoided while returning every pair. A hash set alone would not "
                "preserve all pairs."
            ),
            "example": pair_examples.get(language, "Group prior indexes by value before comparing."),
        })
    elif prints_duplicate_values:
        count_examples = {
            "Python": (
                "from collections import defaultdict\n"
                "prior_count = defaultdict(int)\n"
                f"for value in {collection_name}:\n"
                "    for _ in range(prior_count[value]):\n"
                "        print('Duplicate:', value)\n"
                "    prior_count[value] += 1"
            ),
            "Java": (
                "Map<Integer, Integer> priorCount = new HashMap<>();\n"
                f"for (int value : {collection_name}) {{\n"
                "    int count = priorCount.getOrDefault(value, 0);\n"
                "    for (int match = 0; match < count; match++)\n"
                "        System.out.println(\"Duplicate: \" + value);\n"
                "    priorCount.put(value, count + 1);\n"
                "}"
            ),
            "C++": (
                "std::unordered_map<int, std::size_t> priorCount;\n"
                f"for (int value : {collection_name}) {{\n"
                "    auto& count = priorCount[value];\n"
                "    for (std::size_t match = 0; match < count; ++match)\n"
                "        std::cout << \"Duplicate: \" << value << '\\n';\n"
                "    ++count;\n"
                "}"
            ),
            "C": (
                "Use a hash table to count earlier occurrences of each value.\n"
                "For each value, emit one duplicate message per earlier occurrence,\n"
                "then increment its count."
            ),
        }
        optimizations.append({
            "title": "Count earlier occurrences with a hash map",
            "detail": (
                "This avoids comparing values that differ. It takes expected O(n + k) time, "
                "where k is the number of duplicate messages, and O(u) extra space for u "
                "distinct values. The worst case is still O(n²) when the output itself has "
                "O(n²) duplicate messages. Message order may differ from the nested-loop version."
            ),
            "example": count_examples.get(language, "Count earlier occurrences by value in a hash map."),
        })
    elif (loop_depth >= 2 and has_pair_comparison) or repeated_linear_lookup:
        examples = {
            "Python": "lookup = set(values)\nfor item in queries:\n    if item in lookup:\n        ...",
            "Java": "Set<Integer> lookup = new HashSet<>(values);\nfor (int item : queries) {\n    if (lookup.contains(item)) { /* ... */ }\n}",
            "C++": "std::unordered_set<int> lookup(values.begin(), values.end());\nfor (int item : queries) {\n    if (lookup.contains(item)) { /* ... */ }\n}",
            "C": "Use a hash table for membership checks, or sort once and use binary search.",
        }
        optimizations.append({
            "title": "Check whether a hash set or map can replace repeated searches",
            "detail": "If the repeated inner work only searches for a matching value, indexing values can often reduce O(n²) time to expected O(n), using O(n) extra space. Keep the repeated search when every comparison is required.",
            "example": examples.get(language, "Use a hash set/map for repeated membership checks."),
        })

    return {"time": time, "space": space, "optimizations": optimizations}


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
    complexity_report = _complexity_report(code, language, tree)
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
        "complexity": complexity_report["time"],
        "time_complexity": complexity_report["time"],
        "space_complexity": complexity_report["space"],
        "optimizations": complexity_report["optimizations"],
        "fix": None,
        "syntax_ok": None if parser_unavailable else not syntax_errors,
        "syntax_status": syntax_status,
        "limitations": "Complexity and space results are heuristic estimates, not proofs. Static checks cannot detect every bug or safely rewrite every program.",
    }
