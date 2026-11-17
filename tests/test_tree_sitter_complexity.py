import pytest

from ai_analyzer import analyze_code


NESTED_LOOPS = {
    "C": "void work(int n) { for (int i = 0; i < n; ++i) { for (int j = 0; j < n; ++j) { use(i, j); } } }",
    "C++": "void work(int n) { for (int i = 0; i < n; ++i) { for (int j = 0; j < n; ++j) { use(i, j); } } }",
    "Java": "class Demo { void work(int n) { for (int i = 0; i < n; ++i) { for (int j = 0; j < n; ++j) { use(i, j); } } } void use(int i, int j) {} }",
}


@pytest.mark.parametrize("language,code", NESTED_LOOPS.items())
def test_tree_sitter_detects_nested_loops(language, code):
    result = analyze_code(code, language)
    assert result["time_complexity"].startswith("O(n²)"), result["time_complexity"]


@pytest.mark.parametrize("language,code", {
    "C": "void work(int n) { for (int i = 0; i < n; ++i) { use(i); } for (int j = 0; j < n; ++j) { use(j); } }",
    "C++": "void work(int n) { for (int i = 0; i < n; ++i) { use(i); } for (int j = 0; j < n; ++j) { use(j); } }",
    "Java": "class Demo { void work(int n) { for (int i = 0; i < n; ++i) { use(i); } for (int j = 0; j < n; ++j) { use(j); } } void use(int i) {} }",
}.items())
def test_tree_sitter_does_not_confuse_sequential_loops_with_nesting(language, code):
    result = analyze_code(code, language)
    assert result["time_complexity"].startswith("O(n)"), result["time_complexity"]
