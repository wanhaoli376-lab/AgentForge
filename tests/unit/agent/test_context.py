import pytest
from pydantic import ValidationError

from agentforge.agent.context import ExecutionPlan, SkillSelection


@pytest.mark.parametrize(
    ("model_type", "payload"),
    [
        (SkillSelection, {"skills": [], "unexpected": "ignored"}),
        (
            ExecutionPlan,
            {
                "rationale": "inspect",
                "steps": [
                    {
                        "plugin": "filesystem",
                        "action": "list",
                        "arguments": {},
                        "unexpected": "ignored",
                    }
                ],
            },
        ),
    ],
)
def test_llm_control_models_reject_unknown_fields(model_type: type, payload: dict) -> None:
    with pytest.raises(ValidationError):
        model_type.model_validate(payload)
