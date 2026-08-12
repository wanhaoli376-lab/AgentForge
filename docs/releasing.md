# Release Guide

AgentForge keeps three names deliberately separate:

- project and repository: **AgentForge**;
- Python import package and CLI: `agentforge`;
- PyPI distribution: `agentforge-secure`.

Users install `agentforge-secure` but continue to run `agentforge` and import `agentforge`.
Unrelated projects use similar distribution and import names, so users should install AgentForge in
its own virtual environment rather than co-installing another AgentForge distribution.

## One-time publisher setup

Use PyPI Trusted Publishing rather than a long-lived API token.

1. Sign in to <https://pypi.org> and open the account publishing settings.
2. Add a pending GitHub publisher with these exact values:

   | Field | Value |
   | --- | --- |
   | PyPI project name | `agentforge-secure` |
   | GitHub owner | `wanhaoli376-lab` |
   | GitHub repository | `AgentForge` |
   | Workflow filename | `release.yml` |
   | Environment | `pypi` |

3. In the GitHub repository settings, create an environment named `pypi`. Add a required
   maintainer approval when the repository plan supports deployment reviewers.

Names are normalized by package indexes, so spelling and hyphenation must match. A pending
publisher can create the PyPI project on the first successful upload.

## Release checklist

1. Confirm `main` CI is green and no security finding is unresolved.
2. Update the version in both `pyproject.toml` and `src/agentforge/__init__.py`.
3. Move the matching changelog section from `Unreleased` to the release date.
4. Build locally with `python -m build` and run `python -m twine check --strict dist/*`.
5. Create a GitHub Release whose tag is exactly `v<version>`. Mark alpha, beta, and release
   candidate versions as pre-releases.
6. Approve the `pypi` environment deployment. The release workflow builds a fresh wheel and source
   distribution, checks them, and publishes with a short-lived OIDC credential.
7. Verify the public package from a clean environment:

   ```bash
   python -m pip install "agentforge-secure==0.1.0a1"
   agentforge version
   ```

PyPI files are immutable. Never delete and recreate a tag to replace an uploaded artifact; fix the
problem, increment the version, and publish a new release.

## Workflow security

The build job has read-only repository access. The separate publish job receives only the OIDC and
read permissions it needs, contains no checkout or arbitrary shell step, and uses a dedicated
GitHub environment. Every third-party Action is pinned to a full commit SHA.

Do not add `pull_request_target`, a stored PyPI token, or a manual upload step to the trusted
workflow. Review changes to `.github/workflows/release.yml` as credential-equivalent security code.
