"""AgentCore Platform v1.0"""

# Shared mock-mode resolution helper. Every service that gates real-vs-mock
# behavior must call mock_mode_enabled() instead of re-deriving the flag —
# see .claude/rules/implementation_rule.md rule 1.
#
# USE_MOCK is the canonical flag (what tests set). STG_MOCK_MODE is what the
# deploy-stg CI job actually exports to the uvicorn process — both must be
# checked here so a future rename only needs one edit.

import os
from pathlib import Path

from dotenv import dotenv_values

_env: dict[str, str | None] = dotenv_values(Path(__file__).parent.parent.parent / ".env")

_TRUE_VALUES = ("1", "true", "yes")


def _get_flag(key: str) -> str:
    """OS env takes precedence over .env file."""
    return os.environ.get(key) or _env.get(key) or ""


def mock_mode_enabled() -> bool:
    """True if either USE_MOCK or STG_MOCK_MODE is set to a truthy value."""
    return _get_flag("USE_MOCK").lower() in _TRUE_VALUES or _get_flag("STG_MOCK_MODE").lower() in _TRUE_VALUES
