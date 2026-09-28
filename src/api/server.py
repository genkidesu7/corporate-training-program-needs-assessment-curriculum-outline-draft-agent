"""AgentCore Platform v1.0"""

# Standalone HTTP entry point for the agent.
# Entry points are adapters only — no business logic here.
# For platform-level routing, AgentGateway calls agent.invoke() directly.

import asyncio
import os
import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from langgraph.checkpoint.memory import MemorySaver
from pydantic import BaseModel

from framework.schemas.invocation_context import InvocationContext
from framework.schemas.trust_level import TrustLevel
from framework.secrets.context import bound_secrets
from framework.utils.config_loader import load_config
from shared.secrets import InMemoryProvider, factory as secrets_factory
from shared.secrets.chained_provider import ChainedSecretProvider
from src.graph.graph import EduC2030CorporateTrainingNeedsAssessmentAgent

# Same config_dir / "config.yaml" convention as AgentRegistry._compile_and_cache()
# — absent config.yaml is tolerated, matching the registry's own `if exists()
# else {}` guard. Without this, the standalone adapter always ran with
# config={}, so max_retry/timeout_s/hitl.enabled/memory_enabled never reached
# Graph() on this path.
_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "config.yaml"
_config = load_config(str(_CONFIG_PATH)) if _CONFIG_PATH.exists() else {}

# A bare secrets_factory(...) only ever returns a DotenvProvider (reads
# env/agents/edu/edu-c2-030/.env.<env> files) — it has no visibility into
# secrets the Marketplace/container runtime injects as real process env vars
# (Agent Settings' "User-defined Environment Variables", or `docker run -e`).
# Chain an env-backed provider ahead of it so either source works.
_DECLARED_SECRETS = ("AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOYMENT")
_env_provider = InMemoryProvider({key: os.environ[key] for key in _DECLARED_SECRETS if key in os.environ})
_secrets_provider = ChainedSecretProvider(
    _env_provider,
    secrets_factory(namespace="edu", agent_name="edu-c2-030"),
    namespace="edu",
    agent_name="edu-c2-030",
)
agent = EduC2030CorporateTrainingNeedsAssessmentAgent(config=_config)


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Compile and provision secrets once for the process lifetime — not at
    import time, so a bare `import src.api.server` (e.g. for a test) never
    has the side effect of compiling the graph."""
    # Mirror AgentRegistry._compile_and_cache()'s conditional checkpointer —
    # hitl.enabled or memory_enabled needs one, or interrupt()/memory
    # silently no-ops on this path. A private MemorySaver per process is the
    # standalone-path equivalent (this process runs exactly one agent).
    hitl_enabled = agent.config.get("hitl", {}).get("enabled", False)
    needs_checkpointer = agent.config.get("memory_enabled") or hitl_enabled
    agent.compile(checkpointer=MemorySaver() if needs_checkpointer else None)
    agent.provision_secrets(_secrets_provider)
    yield


app = FastAPI(title="EDU-C2-030", lifespan=_lifespan)


class InvokeRequest(BaseModel):
    input: str
    session_id: str = ""


def _bearer_matches(supplied: str, expected: str) -> bool:
    """Constant-time bearer comparison that is safe for non-ASCII header input."""
    return secrets.compare_digest(supplied.encode(), f"Bearer {expected}".encode())


def _resolve_standalone_trust(
    current: TrustLevel, authorization: str, invoke_auth_token: str | None, internal_runner_token: str | None
) -> TrustLevel:
    """Authenticate standalone callers without allowing external-token elevation.

    STG_INTERNAL_RUNNER_TOKEN is a distinct, CI-generated deployment credential.
    It is considered only for an anonymous caller and maps exactly to INTERNAL;
    INVOKE_AUTH_TOKEN remains VERIFIED_EXTERNAL. Middleware-established trust is
    never changed.
    """
    if current is not TrustLevel.ANONYMOUS:
        return current
    if internal_runner_token and _bearer_matches(authorization, internal_runner_token):
        return TrustLevel.INTERNAL
    if invoke_auth_token and _bearer_matches(authorization, invoke_auth_token):
        return TrustLevel.VERIFIED_EXTERNAL
    if internal_runner_token or invoke_auth_token:
        raise HTTPException(status_code=401, detail="Token is invalid or expired.")
    return TrustLevel.ANONYMOUS


@app.post("/invoke")
async def invoke(req: InvokeRequest, request: Request) -> dict[str, Any]:
    # This adapter is the entry-point auth boundary (standalone equivalent of
    # platform AuthMiddleware). Both values are deployment-level caller
    # credentials, not agent secrets: no InvocationContext exists before this
    # boundary, so ctx.secrets does not apply.
    trust = _resolve_standalone_trust(
        getattr(request.state, "trust_level", TrustLevel.ANONYMOUS),
        request.headers.get("authorization", ""),
        os.environ.get("INVOKE_AUTH_TOKEN"),
        os.environ.get("STG_INTERNAL_RUNNER_TOKEN"),
    )
    with bound_secrets(agent._secrets_provider):
        ctx = InvocationContext(
            session_id=req.session_id or str(uuid4()),
            caller_trust_level=trust,
            caller_id=getattr(request.state, "caller_id", ""),
        )
        # agent.invoke() is sync and its nodes call asyncio.run() internally.
        # Calling it directly from this async route would raise "asyncio.run()
        # cannot be called from a running event loop" inside the node, which
        # the node's except-Exception silently turns into status: "error" — a
        # 200 response with no visible crash (implementation_rule.md rule 3).
        # asyncio.to_thread offloads it and propagates the current
        # contextvars.Context automatically, which bound_secrets() requires.
        return await asyncio.to_thread(agent.invoke, req.input, ctx=ctx)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "agent": "edu-c2-030"}
