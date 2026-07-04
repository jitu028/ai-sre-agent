#!/usr/bin/env python3
import os
import time
import httpx
import random
import asyncio

PAYMENT_SERVICE_URL = os.getenv("PAYMENT_SERVICE_URL", "http://localhost:8080/payment")

async def send_request(client, req_id):
    amount = round(random.uniform(10.0, 100.0), 2)
    payload = {
        "amount": amount,
        "currency": "USD",
        "payment_method": "credit_card"
    }
    
    start_time = time.time()
    try:
        response = await client.post(PAYMENT_SERVICE_URL, json=payload, timeout=5.0)
        duration = (time.time() - start_time) * 1000
        if response.status_code == 200:
            print(f"Request #{req_id} completed: status={response.status_code}, latency={duration:.1f}ms")
        else:
            print(f"Request #{req_id} failed: status={response.status_code}, latency={duration:.1f}ms")
        return duration
    except Exception as e:
        print(f"Request #{req_id} connection failed: {e}")
        return None

async def main():
    print("⚡ Starting High Latency Traffic Generator...")
    print(f"Targeting {PAYMENT_SERVICE_URL} with concurrent requests to simulate load...")
    
    async with httpx.AsyncClient() as client:
        req_id = 0
        try:
            while True:
                # Spawn 5 concurrent requests
                tasks = [send_request(client, req_id + i) for i in range(5)]
                req_id += 5
                
                await asyncio.gather(*tasks)
                await asyncio.sleep(0.5)
        except KeyboardInterrupt:
            print("\nStopped latency simulation.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
