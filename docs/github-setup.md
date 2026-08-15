# GitHub Setup

This repo uses GitHub Actions for CI and optional deployment/publishing workflows.

## Repository secrets

Configured secrets should include:

```text
OPENAI_API_KEY
ANTHROPIC_API_KEY
GOOGLE_API_KEY
HF_TOKEN
PYPI_API_TOKEN
SUPABASE_URL
SUPABASE_PUBLISHABLE_KEY
SUPABASE_SECRET_KEY
```

Optional alias also supported by code:

```text
SUPABASE_SERVICE_ROLE_KEY
```

Do not commit these values. Do not paste them into issues, PRs, logs, or chat.

## Actions to enable

Go to:

```text
Repo -> Settings -> Actions -> General
```

Recommended settings:

```text
Actions permissions: Allow all actions and reusable workflows
Workflow permissions: Read repository contents permission
Allow GitHub Actions to create and approve pull requests: Off
```

The current workflows request only the permissions they need.

## Workflows

### CI

File:

```text
.github/workflows/ci.yml
```

Runs automatically on:

```text
push to main
pull requests to main
```

Checks:

```text
uv sync --extra dev
uv run ruff check .
uv run pytest -q
```

No secrets required.

### Secrets smoke check

File:

```text
.github/workflows/secrets-smoke.yml
```

Run manually from:

```text
Repo -> Actions -> Secrets smoke check -> Run workflow
```

It checks that expected secret names are configured. It does not print secret values.

### Publish to PyPI

File:

```text
.github/workflows/publish-pypi.yml
```

Run manually from:

```text
Repo -> Actions -> Publish to PyPI -> Run workflow
```

Requires:

```text
PYPI_API_TOKEN
```

Do not run until the package metadata/version is ready for a real release.

## Branch protection recommendation

After CI passes once, go to:

```text
Repo -> Settings -> Branches -> Add branch protection rule
```

Branch name pattern:

```text
main
```

Recommended:

```text
Require a pull request before merging: On, once collaborators exist
Require status checks to pass before merging: On
Require branches to be up to date before merging: On
Require conversation resolution before merging: On
Do not allow force pushes: On
Do not allow deletions: On
```

For solo early development, branch protection can wait until the first stable milestone. Don't over-bureaucratize the puppy.

## Secret scanning and Dependabot

Recommended GitHub settings:

```text
Settings -> Code security and analysis
```

Enable if available:

```text
Secret scanning
Push protection
Dependabot alerts
Dependabot security updates
```

## Variables

Non-secret config can go under:

```text
Settings -> Secrets and variables -> Actions -> Variables
```

Useful future variables:

```text
BIZHAWK_BRIDGE_HOST=127.0.0.1
BIZHAWK_BRIDGE_PORT=8765
APP_ENV=development
```

Do not put API keys in variables. Variables are not secrets.
