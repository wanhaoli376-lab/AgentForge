# Live OpenAI API Smoke Test

The normal CI suite never receives an OpenAI API key. It uses deterministic adapters and mocked
HTTP responses so pull requests cannot spend API quota or exfiltrate a credential.

Maintainers can separately verify the packaged OpenAI adapter with the manually triggered
`Live API smoke test` workflow. The workflow makes one small Responses API request and expects the
exact marker `AGENTFORGE_LIVE_OK`.

## One-time repository setup

1. Create a GitHub Environment named `live-api`.
2. Limit its deployment branches to `main`.
3. Add a required maintainer reviewer.
4. Add an Environment secret named `OPENAI_API_KEY` using a least-privilege OpenAI project key
   with an appropriate spend limit.

Do not add this key as a repository secret, commit it to configuration, paste it into workflow
inputs, or make this workflow run on `pull_request`.

## Run the check

1. Open **Actions → Live API smoke test → Run workflow**.
2. Select `main` and keep `gpt-5.6-luna`, or enter another model ID the project explicitly supports.
3. Approve the `live-api` Environment deployment when GitHub requests review.
4. Confirm the `OpenAI Responses API` job succeeds.

The same test can be run locally only when explicitly intended:

```bash
export OPENAI_API_KEY="your-project-key"
export AGENTFORGE_LIVE_API=1
export AGENTFORGE_MODEL=gpt-5.6-luna
pytest tests/live/test_openai_api.py -q
```

The request is billed to the configured OpenAI project. Leave `AGENTFORGE_LIVE_API` unset during
normal development; the test will be skipped.
