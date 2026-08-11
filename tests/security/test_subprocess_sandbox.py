import sys
from pathlib import Path

from agentforge.security.sandbox import ProcessSandbox
from agentforge.security.secret_filter import SecretFilter


def test_subprocess_filters_environment_redacts_and_limits_output(tmp_path: Path) -> None:
    sandbox = ProcessSandbox(
        secret_filter=SecretFilter(),
        max_output_chars=24,
        base_environment={"PATH": "", "OPENAI_API_KEY": "sk-env-secret-value"},
    )
    code = (
        "import os; "
        "print(os.getenv('OPENAI_API_KEY', 'missing')); "
        "print('sk-output-secret-value'); "
        "print('x' * 100)"
    )

    result = sandbox.run([sys.executable, "-c", code], cwd=tmp_path, timeout=5)

    assert result.exit_code == 0
    assert result.timed_out is False
    assert result.truncated is True
    assert "sk-env-secret-value" not in result.stdout
    assert "sk-output-secret-value" not in result.stdout
    assert len(result.stdout) <= 24


def test_subprocess_timeout_stops_the_direct_child(tmp_path: Path) -> None:
    sandbox = ProcessSandbox(secret_filter=SecretFilter(), max_output_chars=1_000)

    result = sandbox.run(
        [sys.executable, "-c", "import time; time.sleep(2)"],
        cwd=tmp_path,
        timeout=0.05,
    )

    assert result.timed_out is True
    assert result.exit_code != 0
