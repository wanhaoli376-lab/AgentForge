"""Read-only GitHub API plugin with constrained destinations and response sizes."""

import json
import os
from collections.abc import Mapping
from typing import Any, ClassVar, Literal
from urllib.parse import quote, urlsplit

import httpx
from pydantic import BaseModel, ConfigDict, Field

from agentforge.exceptions import GitHubAPIError
from agentforge.plugins.base import Plugin, PluginContext, PluginResult
from agentforge.security.network_policy import NetworkPolicy
from agentforge.security.permissions import Permission


class GitHubArguments(BaseModel):
    """Strict base for GitHub action input."""

    model_config = ConfigDict(extra="forbid")

    owner: str = Field(pattern=r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")
    repo: str = Field(pattern=r"^[A-Za-z0-9_.-]{1,100}$")


class GitHubListArguments(GitHubArguments):
    state: Literal["open", "closed", "all"] = "open"
    limit: int = Field(default=30, ge=1, le=100)


class GitHubPullRequestArguments(GitHubArguments):
    number: int = Field(ge=1)


class GitHubPullRequestFilesArguments(GitHubPullRequestArguments):
    limit: int = Field(default=100, ge=1, le=100)


class GitHubCommitArguments(GitHubArguments):
    ref: str | None = Field(default=None, max_length=200)
    limit: int = Field(default=30, ge=1, le=100)


class IssueDraftArguments(GitHubArguments):
    title: str = Field(min_length=1, max_length=256)
    body: str = Field(default="", max_length=65_536)
    labels: tuple[str, ...] = Field(default=(), max_length=20)


class GitHubClient:
    """Small GET-only GitHub API adapter."""

    def __init__(
        self,
        *,
        token: str | None = None,
        api_url: str = "https://api.github.com",
        timeout: float = 15.0,
        max_response_bytes: int = 1_000_000,
        transport: httpx.BaseTransport | None = None,
        resolve_dns: bool = True,
        allowed_domains: tuple[str, ...] | None = None,
    ) -> None:
        self._api_url = api_url.rstrip("/")
        hostname = urlsplit(self._api_url).hostname
        if hostname is None:
            raise ValueError("GitHub api_url must include a hostname")
        self._network_policy = NetworkPolicy(allowed_domains or (hostname,))
        self._resolve_dns = resolve_dns
        self._max_response_bytes = max_response_bytes
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "AgentForge/0.1",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        credential = token if token is not None else os.getenv("GITHUB_TOKEN")
        if credential:
            headers["Authorization"] = f"Bearer {credential}"
        self._client = httpx.Client(
            headers=headers,
            timeout=timeout,
            transport=transport,
            follow_redirects=False,
            trust_env=False,
        )

    def get_json(
        self,
        path: str,
        *,
        params: Mapping[str, str | int] | None = None,
        accept: str | None = None,
    ) -> Any:
        content = self._get(path, params=params, accept=accept)
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise GitHubAPIError("GitHub returned invalid JSON") from exc

    def get_text(self, path: str, *, accept: str) -> str:
        return self._get(path, accept=accept)

    def _get(
        self,
        path: str,
        *,
        params: Mapping[str, str | int] | None = None,
        accept: str | None = None,
    ) -> str:
        if not path.startswith("/") or ".." in path:
            raise GitHubAPIError("GitHub API path is invalid")
        url = f"{self._api_url}{path}"
        self._network_policy.validate_url(url, resolve_dns=self._resolve_dns)
        headers = {"Accept": accept} if accept is not None else None
        try:
            with self._client.stream(
                "GET",
                url,
                params=params,
                headers=headers,
            ) as response:
                if response.status_code < 200 or response.status_code >= 300:
                    raise GitHubAPIError(
                        f"GitHub API request failed with status {response.status_code}"
                    )
                chunks: list[bytes] = []
                size = 0
                for chunk in response.iter_bytes():
                    size += len(chunk)
                    if size > self._max_response_bytes:
                        raise GitHubAPIError("GitHub response exceeded the configured size limit")
                    chunks.append(chunk)
        except httpx.HTTPError as exc:
            raise GitHubAPIError("GitHub API request failed due to a network error") from exc
        return b"".join(chunks).decode("utf-8", errors="replace")


class GitHubPlugin(Plugin):
    """Expose bounded repository, Issue, PR, diff, and commit reads."""

    name = "github"
    description = "Read GitHub repositories, Issues, Pull Requests, diffs, and commits."
    action_models: ClassVar = {
        "repository": GitHubArguments,
        "list_issues": GitHubListArguments,
        "list_pull_requests": GitHubListArguments,
        "get_pull_request": GitHubPullRequestArguments,
        "get_pull_request_files": GitHubPullRequestFilesArguments,
        "get_pull_request_diff": GitHubPullRequestArguments,
        "list_commits": GitHubCommitArguments,
        "draft_issue": IssueDraftArguments,
    }
    action_permissions: ClassVar = {
        "repository": frozenset({Permission.GITHUB_READ}),
        "list_issues": frozenset({Permission.GITHUB_READ}),
        "list_pull_requests": frozenset({Permission.GITHUB_READ}),
        "get_pull_request": frozenset({Permission.GITHUB_READ}),
        "get_pull_request_files": frozenset({Permission.GITHUB_READ}),
        "get_pull_request_diff": frozenset({Permission.GITHUB_READ}),
        "list_commits": frozenset({Permission.GITHUB_READ}),
        "draft_issue": frozenset(),
    }

    def __init__(
        self,
        *,
        read_only: bool = True,
        token: str | None = None,
        api_url: str = "https://api.github.com",
        timeout: float = 15.0,
        max_response_bytes: int = 1_000_000,
        transport: httpx.BaseTransport | None = None,
        resolve_dns: bool = True,
        allowed_domains: tuple[str, ...] | None = None,
    ) -> None:
        self.read_only = read_only
        self._client = GitHubClient(
            token=token,
            api_url=api_url,
            timeout=timeout,
            max_response_bytes=max_response_bytes,
            transport=transport,
            resolve_dns=resolve_dns,
            allowed_domains=allowed_domains,
        )

    def _execute(
        self,
        action: str,
        arguments: BaseModel,
        context: PluginContext,
    ) -> PluginResult:
        del context
        if action == "draft_issue":
            args = IssueDraftArguments.model_validate(arguments.model_dump())
            return PluginResult.success(
                {
                    "draft": {
                        "owner": args.owner,
                        "repo": args.repo,
                        "title": args.title,
                        "body": args.body,
                        "labels": args.labels,
                    },
                    "submitted": False,
                }
            )

        payload = arguments.model_dump()
        owner = str(payload["owner"])
        repo = str(payload["repo"])
        root = self._repo_path(owner, repo)
        if action == "repository":
            return PluginResult.success({"repository": self._repository(root)})
        if action == "list_issues":
            list_args = GitHubListArguments.model_validate(arguments.model_dump())
            return PluginResult.success({"issues": self._issues(root, list_args)})
        if action == "list_pull_requests":
            list_args = GitHubListArguments.model_validate(arguments.model_dump())
            return PluginResult.success({"pull_requests": self._pulls(root, list_args)})
        if action == "get_pull_request":
            pr_args = GitHubPullRequestArguments.model_validate(arguments.model_dump())
            return PluginResult.success({"pull_request": self._pull_request(root, pr_args.number)})
        if action == "get_pull_request_files":
            files_args = GitHubPullRequestFilesArguments.model_validate(arguments.model_dump())
            return PluginResult.success(
                {"files": self._pull_request_files(root, files_args.number, files_args.limit)}
            )
        if action == "get_pull_request_diff":
            pr_args = GitHubPullRequestArguments.model_validate(arguments.model_dump())
            diff = self._client.get_text(
                f"{root}/pulls/{pr_args.number}",
                accept="application/vnd.github.diff",
            )
            return PluginResult.success({"number": pr_args.number, "diff": diff})
        if action == "list_commits":
            commit_args = GitHubCommitArguments.model_validate(arguments.model_dump())
            return PluginResult.success({"commits": self._commits(root, commit_args)})
        raise GitHubAPIError(f"GitHub action was not dispatched: {action}")

    @staticmethod
    def _repo_path(owner: str, repo: str) -> str:
        return f"/repos/{quote(owner, safe='')}/{quote(repo, safe='')}"

    def _repository(self, root: str) -> dict[str, Any]:
        item = self._as_dict(self._client.get_json(root))
        license_data = self._dict_field(item, "license")
        owner_data = self._dict_field(item, "owner")
        return {
            "id": item.get("id"),
            "full_name": item.get("full_name"),
            "description": item.get("description"),
            "private": item.get("private"),
            "default_branch": item.get("default_branch"),
            "html_url": item.get("html_url"),
            "stars": item.get("stargazers_count"),
            "forks": item.get("forks_count"),
            "open_issues": item.get("open_issues_count"),
            "license": license_data.get("spdx_id"),
            "owner": owner_data.get("login"),
        }

    def _issues(self, root: str, args: GitHubListArguments) -> list[dict[str, Any]]:
        items = self._as_list(
            self._client.get_json(
                f"{root}/issues",
                params={"state": args.state, "per_page": args.limit},
            )
        )
        return [self._issue(item) for item in items if "pull_request" not in item]

    def _pulls(self, root: str, args: GitHubListArguments) -> list[dict[str, Any]]:
        items = self._as_list(
            self._client.get_json(
                f"{root}/pulls",
                params={"state": args.state, "per_page": args.limit},
            )
        )
        return [self._pull_summary(item) for item in items]

    def _pull_request(self, root: str, number: int) -> dict[str, Any]:
        item = self._as_dict(self._client.get_json(f"{root}/pulls/{number}"))
        summary = self._pull_summary(item)
        summary.update(
            {
                "additions": item.get("additions"),
                "deletions": item.get("deletions"),
                "changed_files": item.get("changed_files"),
                "commits": item.get("commits"),
                "mergeable": item.get("mergeable"),
            }
        )
        return summary

    def _pull_request_files(self, root: str, number: int, limit: int) -> list[dict[str, Any]]:
        items = self._as_list(
            self._client.get_json(
                f"{root}/pulls/{number}/files",
                params={"per_page": limit},
            )
        )
        return [
            {
                "filename": item.get("filename"),
                "status": item.get("status"),
                "additions": item.get("additions"),
                "deletions": item.get("deletions"),
                "changes": item.get("changes"),
                "patch": self._trim(item.get("patch")),
            }
            for item in items
        ]

    def _commits(self, root: str, args: GitHubCommitArguments) -> list[dict[str, Any]]:
        params: dict[str, str | int] = {"per_page": args.limit}
        if args.ref:
            params["sha"] = args.ref
        items = self._as_list(self._client.get_json(f"{root}/commits", params=params))
        commits = []
        for item in items:
            commit = self._dict_field(item, "commit")
            author = self._dict_field(commit, "author")
            commits.append(
                {
                    "sha": item.get("sha"),
                    "message": self._trim(commit.get("message")),
                    "author": author.get("name"),
                    "date": author.get("date"),
                    "html_url": item.get("html_url"),
                }
            )
        return commits

    @classmethod
    def _issue(cls, item: dict[str, Any]) -> dict[str, Any]:
        labels = cls._dict_list_field(item, "labels")
        user = cls._dict_field(item, "user")
        return {
            "number": item.get("number"),
            "title": item.get("title"),
            "body": cls._trim(item.get("body")),
            "state": item.get("state"),
            "labels": [label.get("name") for label in labels],
            "author": user.get("login"),
            "html_url": item.get("html_url"),
        }

    @classmethod
    def _pull_summary(cls, item: dict[str, Any]) -> dict[str, Any]:
        user = cls._dict_field(item, "user")
        base = cls._dict_field(item, "base")
        head = cls._dict_field(item, "head")
        return {
            "number": item.get("number"),
            "title": item.get("title"),
            "body": cls._trim(item.get("body")),
            "state": item.get("state"),
            "draft": item.get("draft"),
            "author": user.get("login"),
            "base": base.get("ref"),
            "head": head.get("ref"),
            "html_url": item.get("html_url"),
        }

    @staticmethod
    def _trim(value: object, limit: int = 20_000) -> object:
        if isinstance(value, str) and len(value) > limit:
            return value[:limit] + "\n[TRUNCATED]"
        return value

    @staticmethod
    def _as_dict(value: object) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise GitHubAPIError("GitHub returned an unexpected object")
        return value

    @staticmethod
    def _dict_field(item: dict[str, Any], key: str) -> dict[str, Any]:
        value = item.get(key)
        return value if isinstance(value, dict) else {}

    @classmethod
    def _dict_list_field(cls, item: dict[str, Any], key: str) -> list[dict[str, Any]]:
        value = item.get(key)
        if not isinstance(value, list):
            return []
        return [cls._as_dict(entry) for entry in value if isinstance(entry, dict)]

    @classmethod
    def _as_list(cls, value: object) -> list[dict[str, Any]]:
        if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
            raise GitHubAPIError("GitHub returned an unexpected list")
        return [cls._as_dict(item) for item in value]
