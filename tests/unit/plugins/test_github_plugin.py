import json
from pathlib import Path

import httpx

from agentforge.plugins.base import PluginContext
from agentforge.plugins.github import GitHubPlugin
from agentforge.security.permissions import Permission, PermissionManager


def test_github_plugin_lists_issues_without_mixing_in_pull_requests(tmp_path: Path) -> None:
    token = "ghp_test_token_that_must_not_leak_123456"  # noqa: S105 - fake test token

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == f"Bearer {token}"
        assert request.url.path == "/repos/acme/widgets/issues"
        return httpx.Response(
            200,
            json=[
                {
                    "number": 1,
                    "title": "A bug",
                    "body": "Steps to reproduce",
                    "state": "open",
                    "labels": [{"name": "bug"}],
                    "html_url": "https://github.com/acme/widgets/issues/1",
                    "user": {"login": "alice"},
                },
                {
                    "number": 2,
                    "title": "A PR",
                    "pull_request": {"url": "https://api.github.com/pulls/2"},
                },
            ],
        )

    plugin = GitHubPlugin(
        token=token,
        transport=httpx.MockTransport(handler),
        resolve_dns=False,
    )
    context = PluginContext(
        tmp_path,
        PermissionManager({Permission.GITHUB_READ}),
    )

    result = plugin.execute(
        "list_issues",
        {"owner": "acme", "repo": "widgets", "limit": 10},
        context,
    )

    assert result.ok is True
    assert [issue["number"] for issue in result.data["issues"]] == [1]
    assert token not in json.dumps(result.model_dump())


def test_github_plugin_returns_pr_diff_with_expected_media_type(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Accept"] == "application/vnd.github.diff"
        return httpx.Response(200, text="diff --git a/a.py b/a.py\n+print('safe')")

    plugin = GitHubPlugin(
        transport=httpx.MockTransport(handler),
        resolve_dns=False,
    )
    context = PluginContext(tmp_path, PermissionManager({Permission.GITHUB_READ}))

    result = plugin.execute(
        "get_pull_request_diff",
        {"owner": "acme", "repo": "widgets", "number": 7},
        context,
    )

    assert result.ok is True
    assert result.data["number"] == 7
    assert result.data["diff"].startswith("diff --git")


def test_issue_draft_is_never_submitted_or_sent_over_network(tmp_path: Path) -> None:
    def unexpected_request(request: httpx.Request) -> httpx.Response:
        raise AssertionError(f"Unexpected network request: {request.url}")

    plugin = GitHubPlugin(
        transport=httpx.MockTransport(unexpected_request),
        resolve_dns=False,
    )
    context = PluginContext(tmp_path, PermissionManager(set()))

    result = plugin.execute(
        "draft_issue",
        {
            "owner": "acme",
            "repo": "widgets",
            "title": "Proposed issue",
            "body": "Review before submitting.",
            "labels": ["documentation"],
        },
        context,
    )

    assert result.ok is True
    assert result.data["submitted"] is False
    assert result.data["draft"]["title"] == "Proposed issue"


def test_github_read_permission_is_checked_before_network(tmp_path: Path) -> None:
    called = False

    def unexpected_request(request: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        return httpx.Response(200, json={})

    plugin = GitHubPlugin(
        transport=httpx.MockTransport(unexpected_request),
        resolve_dns=False,
    )
    context = PluginContext(tmp_path, PermissionManager(set()))

    result = plugin.execute("repository", {"owner": "acme", "repo": "widgets"}, context)

    assert result.ok is False
    assert result.error is not None
    assert result.error.code == "permission_denied"
    assert called is False
