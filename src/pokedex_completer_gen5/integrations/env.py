from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv


def load_environment() -> None:
    """Load local environment variables from `.env` when present.

    GitHub Actions and production hosts should provide real environment variables directly.
    Local development gets `.env` convenience. Secrets still do not belong in Git.
    """
    load_dotenv(dotenv_path=Path.cwd() / ".env", override=False)
    load_dotenv(override=False)
