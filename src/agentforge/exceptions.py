"""Shared, user-safe AgentForge exceptions."""


class AgentForgeError(Exception):
    """Base exception with a stable machine-readable error code."""

    code = "agentforge_error"


class PermissionDeniedError(AgentForgeError):
    """Raised when a configured capability is not granted."""

    code = "permission_denied"


class PolicyViolationError(AgentForgeError):
    """Raised when an operation violates a security policy."""

    code = "policy_violation"


class PluginExecutionError(AgentForgeError):
    """Raised for expected, safe-to-report plugin failures."""

    code = "plugin_execution_error"


class MissingCredentialError(AgentForgeError):
    """Raised when an explicitly required credential is unavailable."""

    code = "missing_credential"


class LLMError(AgentForgeError):
    """Raised when an LLM request or response cannot be used."""

    code = "llm_error"


class PlanValidationError(AgentForgeError):
    """Raised when model output is not a valid, executable plan."""

    code = "invalid_plan"


class GitHubAPIError(AgentForgeError):
    """Raised for bounded, safe-to-report GitHub API failures."""

    code = "github_api_error"
