#!/usr/bin/env python3
import os
import sys
import httpx

DASHBOARD_URL = os.getenv("DASHBOARD_URL", "http://localhost:8000/api/trigger_incident")
PAYMENT_SERVICE_URL = os.getenv("PAYMENT_SERVICE_URL", "http://localhost:8080/payment")

def trigger_incident():
    print("🚀 Triggering SRE Incident...")
    
    # 1. Trigger incident on dashboard simulation
    try:
        response = httpx.post(DASHBOARD_URL)
        if response.status_code == 200:
            print("✅ Successfully triggered incident on Dashboard SRE State Machine.")
            print(response.json().get("message", ""))
        else:
            print(f"⚠️ Dashboard returned status code {response.status_code}")
    except Exception as e:
        print(f"❌ Failed to reach dashboard at {DASHBOARD_URL}: {e}")
        print("   Make sure the dashboard app is running (python app.py)")
        
    # 2. Trigger high HTTP 500s directly on local payment service if running
    try:
        # Note: In a real GCP setup, this would be done by triggering traffic or config
        print("\n🔍 Checking for running Payment Service (port 8080)...")
        # Attempt to make a call to payment service to verify if running
        health_resp = httpx.get("http://localhost:8080/health", timeout=1.0)
        if health_resp.status_code == 200:
            print("✅ Payment service is running. Simulating traffic with errors...")
            # Set bad config in env if running in same terminal or trigger it
            # The dashboard's tool rollback will reset this
            print("💡 In a live cluster, this is triggered by deploying a new revision with bad configuration.")
        else:
            print("⚠️ Payment service returned unhealthy status.")
    except Exception:
        print("ℹ️ Payment service is not running locally on port 8080. (Simulation mode active)")

if __name__ == "__main__":
    trigger_incident()
