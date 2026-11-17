"""Static, non-executing code analysis for the AI Code Mentor app."""

from __future__ import annotations

import ast
import builtins
import importlib
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


def _parse_tree_sitter(code: str, language: str):
    """Parse with the installed, language-specific Tree-sitter grammar wheel."""
    from tree_sitter import Language, Parser

    grammar = importlib.import_module(f"tree_sitter_{TREE_SITTER_NAMES[language]}")
    parser = Parser(Language(grammar.language()))
    return parser.parse(code.encode("utf-8"))


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
            # A lightweight local scope check. Nested functions/classes have their own scope.
            scoped_nodes: list[ast.AST] = []
            pending = list(node.body)
            while pending:
                child = pending.pop()
                if child is not node and isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                    continue
                scoped_nodes.append(child)
                pending.extend(ast.iter_child_nodes(child))
            local_stores: dict[str, ast.AST] = {}
            loaded: set[str] = set()
            for child in scoped_nodes:
                if isinstance(child, ast.Name):
                    if isinstance(child.ctx, ast.Store):
                        local_stores.setdefault(child.id, child)
                    elif isinstance(child.ctx, ast.Load):
                        loaded.add(child.id)
            arguments = {arg.arg for arg in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs)}
            if node.args.vararg:
                arguments.add(node.args.vararg.arg)
            if node.args.kwarg:
                arguments.add(node.args.kwarg.arg)
            for name, target in local_stores.items():
                if name not in loaded and name not in arguments and not name.startswith("_"):
                    _add(findings, "Warning", target.lineno, f"Local variable '{name}' is assigned but never read.",
                         "python.unused-variable", "Remove it or use it if the assignment is needed.", target.col_offset + 1)
                if name in dir(builtins):
                    _add(findings, "Warning", target.lineno, f"Local variable '{name}' shadows a Python built-in name.",
                         "python.shadowed-builtin", "Choose a different name so the built-in remains available.", target.col_offset + 1)
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            _add(findings, "Warning", node.lineno, "A bare except catches every exception, including interrupts.",
                 "python.bare-except", "Catch the specific exception types this code can handle.", node.col_offset + 1)
        if isinstance(node, ast.ExceptHandler) and isinstance(node.type, ast.Name) and node.type.id in {"Exception", "BaseException"}:
            _add(findings, "Warning", node.lineno, f"Catching {node.type.id} can hide unrelated failures.",
                 "python.broad-except", "Catch the specific exception types expected here.", node.col_offset + 1)
        if isinstance(node, ast.While) and isinstance(node.test, ast.Constant) and node.test.value is True:
            if not any(isinstance(n, (ast.Break, ast.Return, ast.Raise)) for n in ast.walk(node)):
                _add(findings, "Warning", node.lineno, "This while True loop has no visible break, return, or raise.",
                     "python.possible-infinite-loop", "Confirm the loop has a deliberate exit condition.", node.col_offset + 1)

        if isinstance(node, ast.Compare):
            for operator, comparator in zip(node.ops, node.comparators):
                if isinstance(operator, (ast.Eq, ast.NotEq)) and isinstance(comparator, ast.Constant) and comparator.value is None:
                    _add(findings, "Warning", node.lineno, "Compare with None using identity, not equality.",
                         "python.none-equality", "Use 'is None' or 'is not None'.", node.col_offset + 1)
                    break

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name in dir(builtins):
            _add(findings, "Warning", node.lineno, f"'{node.name}' shadows a Python built-in name.",
                 "python.shadowed-builtin", "Choose a different name so the built-in remains available.", node.col_offset + 1)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for arg in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs):
                if arg.arg in dir(builtins):
                    _add(findings, "Warning", arg.lineno, f"Parameter '{arg.arg}' shadows a Python built-in name.",
                         "python.shadowed-builtin", "Rename the parameter to preserve access to the built-in.", arg.col_offset + 1)

        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {"eval", "exec"}:
            _add(findings, "Warning", node.lineno, f"Dynamic {node.func.id}() execution can run arbitrary source text.",
                 "python.dynamic-execution", "Avoid dynamic execution or strictly constrain and validate its input.", node.col_offset + 1)
        if isinstance(node, ast.Assert) and isinstance(node.test, ast.Constant) and node.test.value is False:
            _add(findings, "Warning", node.lineno, "assert False always raises AssertionError when reached.",
                 "python.assert-false", "Use an explicit exception or replace this with the intended condition.", node.col_offset + 1)
        if isinstance(node, ast.Compare) and any(isinstance(op, (ast.Is, ast.IsNot)) for op in node.ops):
            if any(isinstance(value, ast.Constant) and value.value is not None and not isinstance(value.value, bool)
                   for value in (node.left, *node.comparators)):
                _add(findings, "Warning", node.lineno, "Identity comparison is used with a value literal.",
                     "python.literal-identity", "Use == or != for value comparison; reserve is for identity checks such as None.", node.col_offset + 1)

        if isinstance(node, ast.Dict):
            seen_keys: set[object] = set()
            for key in node.keys:
                if isinstance(key, ast.Constant):
                    try:
                        if key.value in seen_keys:
                            _add(findings, "Warning", key.lineno, f"Duplicate dictionary key {key.value!r}; the later value replaces the earlier one.",
                                 "python.duplicate-dict-key", "Remove the duplicate key or correct the intended value.", key.col_offset + 1)
                        seen_keys.add(key.value)
                    except TypeError:
                        pass

    # Flag open() calls that are not part of a with-item context expression.
    managed_open_calls = {
        id(child)
        for with_node in ast.walk(tree) if isinstance(with_node, (ast.With, ast.AsyncWith))
        for item in with_node.items
        for child in ast.walk(item.context_expr)
        if isinstance(child, ast.Call) and isinstance(child.func, ast.Name) and child.func.id == "open"
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "open" and id(node) not in managed_open_calls:
            _add(findings, "Warning", node.lineno, "File opened without a with statement may not be closed reliably.",
                 "python.open-without-with", "Use 'with open(...) as file:' so the file closes automatically.", node.col_offset + 1)

    # Find statements directly following an unconditional terminator in each block.
    for parent in ast.walk(tree):
        for _, statements in ast.iter_fields(parent):
            if not isinstance(statements, list) or not statements or not all(isinstance(item, ast.stmt) for item in statements):
                continue
            terminated = False
            for statement in statements:
                if terminated:
                    _add(findings, "Warning", statement.lineno, "This statement is unreachable after an unconditional exit.",
                         "python.unreachable-code", "Move it before the return/raise/break/continue or remove it.", statement.col_offset + 1)
                if isinstance(statement, (ast.Return, ast.Raise, ast.Break, ast.Continue)):
                    terminated = True

    return findings, tree


def _tree_sitter_findings(code: str, language: str) -> list[Finding]:
    findings: list[Finding] = []
    try:
        tree = _parse_tree_sitter(code, language)
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
    loop_depth: int | None = 0
    recursive = False

    if language == "Python" and tree is not None:
        def measure(node: ast.AST, current: int = 0) -> int:
            here = current + 1 if isinstance(node, (ast.For, ast.AsyncFor, ast.While)) else current
            return max([here, *(measure(child, here) for child in ast.iter_child_nodes(node))])
        loop_depth = measure(tree)
        function_names = {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
        recursive = any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in function_names for n in ast.walk(tree))
    elif language in TREE_SITTER_NAMES:
        try:
            syntax_tree = _parse_tree_sitter(code, language)
            loop_nodes = {"for_statement", "enhanced_for_statement", "for_range_loop", "while_statement", "do_statement"}

            def max_loop_depth(node: object, depth: int = 0) -> int:
                current = depth + (1 if getattr(node, "type", "") in loop_nodes else 0)
                return max([current, *(max_loop_depth(child, current) for child in getattr(node, "children", ()))])

            loop_depth = max_loop_depth(syntax_tree.root_node)
        except Exception:
            loop_depth = None
        for function_name in re.findall(r"\b(?:void|int|char|float|double|String|boolean)\s+(\w+)\s*\([^)]*\)\s*\{", code):
            if len(re.findall(rf"\b{re.escape(function_name)}\s*\(", code)) > 1:
                recursive = True
                break

    has_sort = bool(re.search(r"\b(?:sorted|sort|Arrays\.sort|Collections\.sort|std::sort)\s*\(|\.sort\s*\(", code))
    has_linear_library_call = bool(re.search(r"\b(?:strcpy|strncpy|strlen|strcmp|memcpy|memmove)\s*\(|\.contains\s*\(|\.indexOf\s*\(", code))
    repeated_linear_lookup = loop_depth is not None and loop_depth >= 1 and bool(re.search(
        r"\bif\b[^\n]*\bin\s+[A-Za-z_]\w*|\.contains\s*\(|\.indexOf\s*\(|\bstd::find\s*\(", code))
    if loop_depth is None:
        time = "Not estimated (Tree-sitter structure unavailable)"
    elif loop_depth >= 2:
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
    enumerates_duplicate_pairs = loop_depth is not None and loop_depth >= 2 and indexed_pair_comparison and pair_output
    prints_duplicate_values = (
        loop_depth is not None and loop_depth >= 2
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
    elif ((loop_depth is not None and loop_depth >= 2 and has_pair_comparison) or repeated_linear_lookup):
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
