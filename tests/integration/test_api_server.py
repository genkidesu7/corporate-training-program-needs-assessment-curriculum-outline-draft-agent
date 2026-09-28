# Test Rule 3 (.claude/rules/test_rule.md): every FastAPI route that wraps a
# sync agent.invoke() needs an HTTP-level test on a real ASGI transport, not
# just an in-process sync call — this is the only way to reproduce the
# async-route -> sync-invoke -> asyncio.run() boundary bug (agent.invoke()'s
# nodes call asyncio.run() internally; calling it directly from an async
# route without asyncio.to_thread raises "asyncio.run() cannot be called
# from a running event loop" inside the node, silently turned into
# status: "error" by the node's except-Exception).

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.server import _lifespan, app


@pytest.fixture(autouse=True)
def _mock_mode(monkeypatch):
    monkeypatch.setenv("USE_MOCK", "true")


@pytest.mark.asyncio
async def test_invoke_endpoint_succeeds_over_http(monkeypatch):
    monkeypatch.setenv("INVOKE_AUTH_TOKEN", "test-token")
    transport = ASGITransport(app=app)
    async with _lifespan(app), AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/invoke",
            json={"input": '{"role_cohorts": ["sales"], "target_dss_level": "DX-Standard"}'},
            headers={"Authorization": "Bearer test-token"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"


@pytest.mark.asyncio
async def test_invoke_endpoint_rejects_bad_token(monkeypatch):
    monkeypatch.setenv("INVOKE_AUTH_TOKEN", "test-token")
    transport = ASGITransport(app=app)
    async with _lifespan(app), AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/invoke",
            json={"input": '{"role_cohorts": ["sales"], "target_dss_level": "DX-Standard"}'},
            headers={"Authorization": "Bearer wrong-token"},
        )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
