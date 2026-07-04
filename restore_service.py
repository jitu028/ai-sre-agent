#!/usr/bin/env python3
import os
import httpx

DASHBOARD_URL = os.getenv("DASHBOARD_URL", "http://localhost:8000/api/restore")

def restore_service():
    print("🔄 Restoring system to healthy baseline...")
    try:
        response = httpx.post(DASHBOARD_URL)
        if response.status_code == 200:
            print("✅ System successfully restored to Healthy baseline.")
            print(response.json().get("message", ""))
        else:
            print(f"❌ Failed to restore system. Status: {response.status_code}")
    except Exception as e:
        print(f"❌ Failed to reach dashboard at {DASHBOARD_URL}: {e}")

if __name__ == "__main__":
    restore_service()
