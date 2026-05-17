"""Tests for pipeline API endpoints."""
import pytest
import uuid
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_list_pipelines_empty(client):
    resp = await client.get("/api/v1/pipelines/")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_trigger_pipeline(client):
    with patch("app.routers.pipelines.orchestrator") as mock_orch:
        mock_orch.run_pipeline = AsyncMock(return_value={
            "pipeline_id": str(uuid.uuid4()),
            "can_deploy": True,
            "risk_level": "low",
            "stages": {},
        })
        resp = await client.post("/api/v1/pipelines/trigger", json={
            "repo": "acme-corp/payment-service",
            "commit_sha": "abc1234567890" * 3,
            "commit_message": "feat: test commit",
            "branch": "main",
        })
    assert resp.status_code == 202
    data = resp.json()
    assert "pipeline_id" in data
    assert data["status"] == "running"


@pytest.mark.asyncio
async def test_get_pipeline_not_found(client):
    resp = await client.get(f"/api/v1/pipelines/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_analytics_overview(client):
    resp = await client.get("/api/v1/analytics/overview")
    assert resp.status_code == 200
    data = resp.json()
    assert "success_rate" in data
    assert "open_incidents" in data
    assert "ci_time_saved_percent" in data


@pytest.mark.asyncio
async def test_analytics_pipeline_trends(client):
    resp = await client.get("/api/v1/analytics/pipeline-trends?days=7")
    assert resp.status_code == 200
    data = resp.json()
    assert "labels" in data
    assert len(data["labels"]) == 7


@pytest.mark.asyncio
async def test_agent_stats(client):
    resp = await client.get("/api/v1/agents/stats/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "active_agents" in data
    assert "agents" in data
    assert len(data["agents"]) == 7


@pytest.mark.asyncio
async def test_health_check(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_quality_gates_crud(client):
    # Create
    resp = await client.post("/api/v1/quality-gates/", json={
        "name": "Test Coverage Gate",
        "gate_type": "coverage",
        "threshold_value": 80,
        "threshold_operator": "gte",
    })
    assert resp.status_code == 201
    gate_id = resp.json()["id"]

    # List
    resp = await client.get("/api/v1/quality-gates/")
    assert resp.status_code == 200
    assert any(g["id"] == gate_id for g in resp.json())

    # Toggle
    resp = await client.patch(f"/api/v1/quality-gates/{gate_id}/toggle")
    assert resp.status_code == 200

    # Delete
    resp = await client.delete(f"/api/v1/quality-gates/{gate_id}")
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_create_incident(client):
    with patch("app.routers.incidents.orchestrator") as mock_orch:
        mock_orch.run_incident = AsyncMock(return_value={
            "severity": "sev2",
            "root_cause_commit": None,
            "root_cause_summary": "Under investigation",
        })
        resp = await client.post("/api/v1/incidents/", json={
            "title": "Test incident",
            "severity": "sev2",
            "service": "test-service",
        })
    assert resp.status_code == 202
    assert "incident_id" in resp.json()


@pytest.mark.asyncio
async def test_github_webhook_ping(client):
    resp = await client.post(
        "/api/v1/webhooks/github",
        json={"zen": "Speak like a human."},
        headers={
            "X-GitHub-Event": "ping",
            "X-Hub-Signature-256": "sha256=invalid",
        },
    )
    # Signature check passes because GITHUB_WEBHOOK_SECRET is empty in test env
    assert resp.status_code in (200, 202)
