#!/usr/bin/env python3
import os
import time
import httpx
import random

PAYMENT_SERVICE_URL = os.getenv("PAYMENT_SERVICE_URL", "http://localhost:8080/payment")

def simulate_http500():
    print("📈 Simulating Payment Requests...")
    print("Sending POST requests to payment service on port 8080...")
    
    count = 0
    errors = 0
    success = 0
    
    try:
        while True:
            amount = round(random.uniform(5.0, 6000.0), 2)
            payload = {
                "amount": amount,
                "currency": "USD",
                "payment_method": "credit_card" if amount < 5000 else "bank_transfer"
            }
            
            try:
                response = httpx.post(PAYMENT_SERVICE_URL, json=payload, timeout=2.0)
                count += 1
                if response.status_code == 200:
                    success += 1
                    print(f"[{count}] SUCCESS: Paid ${amount:.2f} - Txn ID: {response.json().get('transaction_id')}")
                else:
                    errors += 1
                    print(f"[{count}] ERROR {response.status_code}: {response.json().get('detail')}")
            except httpx.RequestError as e:
                print(f"❌ Connection error: Could not reach payment service at {PAYMENT_SERVICE_URL}. Is it running?")
                print("   Run the service using: uvicorn app:app --port 8080 (in sample-payment-service directory)")
                break
                
            time.sleep(1.0)
            
    except KeyboardInterrupt:
        print("\nStopping traffic simulation.")
        print(f"Summary: Total Sent: {count} | Successes: {success} | Failures: {errors}")

if __name__ == "__main__":
    simulate_http500()
