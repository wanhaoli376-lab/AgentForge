"""Conservative AST checks for the experimental Python Plugin."""

import ast
from collections.abc import Collection

from agentforge.exceptions import PolicyViolationError


class PythonCodePolicy(ast.NodeVisitor):
    """Reject direct access to I/O, dynamic execution, and interpreter internals."""

    _BLOCKED_CALLS = frozenset(
        {
            "__import__",
            "breakpoint",
            "compile",
            "eval",
            "exec",
            "getattr",
            "globals",
            "input",
            "locals",
            "open",
            "setattr",
            "vars",
        }
    )

    def __init__(
        self,
        allowed_imports: Collection[str] = (
            "collections",
            "csv",
            "datetime",
            "decimal",
            "fractions",
            "functools",
            "itertools",
            "json",
            "math",
            "random",
            "re",
            "statistics",
            "string",
        ),
        *,
        max_code_chars: int = 100_000,
    ) -> None:
        self._allowed_imports = frozenset(allowed_imports)
        self._max_code_chars = max_code_chars

    def validate(self, code: str) -> ast.Module:
        if not code.strip():
            raise PolicyViolationError("Python code must not be empty")
        if len(code) > self._max_code_chars:
            raise PolicyViolationError("Python code exceeds the configured size limit")
        try:
            tree = ast.parse(code, mode="exec")
        except SyntaxError as exc:
            raise PolicyViolationError(f"Python code has invalid syntax: {exc.msg}") from exc
        self.visit(tree)
        return tree

    def visit_Import(self, node: ast.Import) -> None:  # noqa: N802 - ast visitor interface
        for alias in node.names:
            self._require_allowed_import(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:  # noqa: N802
        if node.level or node.module is None:
            raise PolicyViolationError("Relative Python imports are not allowed")
        self._require_allowed_import(node.module)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        if isinstance(node.func, ast.Name) and node.func.id in self._BLOCKED_CALLS:
            raise PolicyViolationError(f"Blocked Python call: {node.func.id}")
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:  # noqa: N802
        if node.attr.startswith("_"):
            raise PolicyViolationError("Private and dunder attribute access is blocked")
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:  # noqa: N802
        if node.id.startswith("__") or node.id in self._BLOCKED_CALLS:
            raise PolicyViolationError(f"Blocked Python name: {node.id}")

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        if node.name.startswith("_"):
            raise PolicyViolationError("Private and dunder function names are blocked")
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        if node.name.startswith("_"):
            raise PolicyViolationError("Private and dunder function names are blocked")
        self.generic_visit(node)

    def _require_allowed_import(self, module: str) -> None:
        root = module.split(".", 1)[0]
        if root not in self._allowed_imports:
            raise PolicyViolationError(f"Python import is not allowlisted: {root}")
