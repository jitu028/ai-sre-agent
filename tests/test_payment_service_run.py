import os
import sys
import importlib.util
import pytest
from fastapi.testclient import TestClient

# Load the payment service app dynamically to avoid sys.modules caching conflicts
module_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../sample-payment-service/app.py"))
spec = importlib.util.spec_from_file_location("payment_app", module_path)
payment_app = importlib.util.module_from_spec(spec)
sys.modules["payment_app"] = payment_app
spec.loader.exec_module(payment_app)

client = TestClient(payment_app.app)

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert "status" in response.json()
    assert response.json()["status"] == "online"

def test_health_endpoint_healthy():
    # Ensure BAD_CONFIG env is false/unset
    os.environ["ENABLE_BAD_CONFIG"] = "false"
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_health_endpoint_unhealthy():
    os.environ["ENABLE_BAD_CONFIG"] = "true"
    response = client.get("/health")
    assert response.status_code == 500
    assert "detail" in response.json()
    assert "Unhealthy" in response.json()["detail"]
    os.environ["ENABLE_BAD_CONFIG"] = "false" # Reset

def test_payment_processing_success():
    os.environ["ENABLE_BAD_CONFIG"] = "false"
    payload = {"amount": 250.0, "currency": "USD", "payment_method": "credit_card"}
    response = client.post("/payment", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["amount"] == 250.0
    assert "transaction_id" in response.json()

def test_payment_processing_failure():
    os.environ["ENABLE_BAD_CONFIG"] = "true"
    payload = {"amount": 250.0, "currency": "USD", "payment_method": "credit_card"}
    response = client.post("/payment", json=payload)
    assert response.status_code == 500
    assert "detail" in response.json()
    assert "MISSING_PAYMENT_KEY" in response.json()["detail"]
    os.environ["ENABLE_BAD_CONFIG"] = "false" # Reset

def test_metrics_endpoint():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "requests_total" in response.json()
    assert "payments_processed" in response.json()
