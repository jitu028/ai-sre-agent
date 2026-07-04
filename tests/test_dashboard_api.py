import pytest
from fastapi.testclient import TestClient
from app import app
from services.incident_manager import incident_manager

client = TestClient(app)

@pytest.fixture(autouse=True)
def reset_incident_state():
    # Automatically reset to healthy baseline before each test
    import asyncio
    asyncio.run(incident_manager.restore_service())

def test_dashboard_homepage():
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

def test_status_endpoint():
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert data["state"] == "Healthy"
    assert data["availability"] == 100.0
    assert data["deployment_status"] == "HEALTHY"

def test_logs_endpoint():
    response = client.get("/api/logs")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) > 0

def test_metrics_endpoint():
    response = client.get("/api/metrics")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) > 0

def test_trigger_incident():
    response = client.post("/api/trigger_incident")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    
    # Verify status changed
    status_resp = client.get("/api/status")
    assert status_resp.json()["state"] in ["Incident Detected", "Investigation", "Root Cause Found", "Waiting Approval"]

def test_chat_interaction():
    response = client.post("/api/chat", json={"text": "How is the system?"})
    assert response.status_code == 200
    
    # Check that message got appended to chat history
    chat_resp = client.get("/api/chat")
    messages = chat_resp.json()
    assert any(m["sender"] == "Operator" and m["text"] == "How is the system?" for m in messages)

def test_manual_rollback():
    response = client.post("/api/rollback")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    
    # Verify progress initiated
    status_resp = client.get("/api/status")
    assert status_resp.json()["state"] == "Executing"
