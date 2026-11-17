import pytest

from ai_analyzer import analyze_code


RULE_SAMPLES = [
    (
        "python.unused-variable",
        "def calculate():\n    result = 42\n    return 0\n",
        "def calculate():\n    result = 42\n    return result\n",
    ),
    (
        "python.none-equality",
        "if value == None:\n    pass\n",
        "if value is None:\n    pass\n",
    ),
    (
        "python.shadowed-builtin",
        "def render(list):\n    return list\n",
        "def render(items):\n    return items\n",
    ),
    (
        "python.unreachable-code",
        "def calculate():\n    return 1\n    print('never reached')\n",
        "def calculate():\n    print('before exit')\n    return 1\n",
    ),
    (
        "python.open-without-with",
        "def read_file(path):\n    file = open(path)\n    return file.read()\n",
        "def read_file(path):\n    with open(path) as file:\n        return file.read()\n",
    ),
    (
        "python.literal-identity",
        "if answer is 42:\n    pass\n",
        "if answer == 42:\n    pass\n",
    ),
    (
        "python.duplicate-dict-key",
        "settings = {'mode': 'fast', 'mode': 'safe'}\n",
        "settings = {'mode': 'safe', 'retries': 3}\n",
    ),
    (
        "python.dynamic-execution",
        "result = eval(user_expression)\n",
        "result = int(user_text)\n",
    ),
    (
        "python.broad-except",
        "try:\n    work()\nexcept Exception:\n    recover()\n",
        "try:\n    work()\nexcept ValueError:\n    recover()\n",
    ),
    (
        "python.assert-false",
        "assert False\n",
        "assert is_valid\n",
    ),
]


@pytest.mark.parametrize("rule,sample", [(rule, trigger) for rule, trigger, _ in RULE_SAMPLES], ids=[
    f"{rule}: should trigger" for rule, _, _ in RULE_SAMPLES
])
def test_python_rule_should_trigger(rule, sample):
    result = analyze_code(sample, "Python")
    assert any(finding["rule"] == rule for finding in result["findings"]), sample


@pytest.mark.parametrize("rule,sample", [(rule, safe) for rule, _, safe in RULE_SAMPLES], ids=[
    f"{rule}: should not trigger" for rule, _, _ in RULE_SAMPLES
])
def test_python_rule_should_not_trigger(rule, sample):
    result = analyze_code(sample, "Python")
    assert not any(finding["rule"] == rule for finding in result["findings"]), sample
