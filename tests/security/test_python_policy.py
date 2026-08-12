import pytest

from agentforge.exceptions import PolicyViolationError
from agentforge.security.python_policy import PythonCodePolicy


def test_python_policy_accepts_allowlisted_standard_library_imports() -> None:
    tree = PythonCodePolicy().validate(
        "import json\nfrom collections import Counter\nprint(json.dumps(Counter('aba')))"
    )

    assert len(tree.body) == 3


@pytest.mark.parametrize(
    ("code", "message"),
    [
        ("", "must not be empty"),
        ("if", "invalid syntax"),
        ("import os", "import is not allowlisted: os"),
        ("from . import helper", "Relative Python imports"),
        ("eval('1 + 1')", "Blocked Python call: eval"),
        ("print(value.__class__)", "Private and dunder attribute"),
        ("print(__builtins__)", "Blocked Python name"),
        ("def _private():\n    return 1", "Private and dunder function"),
        ("async def _private():\n    return 1", "Private and dunder function"),
    ],
)
def test_python_policy_rejects_unsafe_language_features(code: str, message: str) -> None:
    with pytest.raises(PolicyViolationError, match=message):
        PythonCodePolicy().validate(code)


def test_python_policy_enforces_the_configured_source_size_limit() -> None:
    with pytest.raises(PolicyViolationError, match="size limit"):
        PythonCodePolicy(max_code_chars=5).validate("print(1)")
