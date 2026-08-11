import pytest

from agentforge.exceptions import PolicyViolationError
from agentforge.security.command_policy import CommandPolicy


@pytest.mark.parametrize(
    "argv",
    [
        ["rm", "-rf", "/"],
        ["pytest;", "cat", "~/.ssh/id_rsa"],
        ["pytest", ";", "cat", "~/.ssh/id_rsa"],
        ["git", "push"],
        ["python", "-c", "import os; os.system('whoami')"],
    ],
)
def test_dangerous_or_injected_commands_are_rejected(argv: list[str]) -> None:
    policy = CommandPolicy(allowed_commands={"git", "pytest", "python"})

    with pytest.raises(PolicyViolationError):
        policy.validate(argv)


def test_read_only_commands_are_returned_as_immutable_argv() -> None:
    policy = CommandPolicy(allowed_commands={"git", "pytest", "python"})

    assert policy.validate(["git", "status", "--short"]) == ("git", "status", "--short")
    assert policy.validate(["pytest", "-q"]) == ("pytest", "-q")
