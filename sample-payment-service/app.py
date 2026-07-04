import os
import sys
import time
import uuid
import random
import logging
from typing import Dict, Any
from fastapi import FastAPI, Request, Response, HTTPException, status
from pydantic import BaseModel

app = FastAPI(title="Sample Payment Service", version="1.0.0")

# Setup configuration
SERVICE_NAME = os.getenv("K_SERVICE", "sample-payment-service")
REVISION = os.getenv("K_REVISION", "sample-payment-service-v1")
REGION = os.getenv("GCP_REGION", "us-central1")

# Configure structured JSON logging
class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        # Default structured fields
        log_data: Dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S.%fZ"),
            "severity": record.levelname,
            "message": record.getMessage(),
            "service": SERVICE_NAME,
            "revision": REVISION,
            "region": REGION,
        }
        
        # Inject request-specific context if available
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        if hasattr(record, "trace_id"):
            log_data["trace_id"] = record.trace_id
            
        # Include exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
            
        # JSON formatting
        import json
        return json.dumps(log_data)

# Setup root logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JsonFormatter())
logger.handlers = [handler]

# Simple in-memory metrics
metrics_store = {
    "requests_total": 0,
    "payments_processed": 0,
    "payments_failed": 0,
    "total_revenue": 0.0,
    "latencies": []
}

class PaymentRequest(BaseModel):
    amount: float
    currency: str = "USD"
    payment_method: str = "credit_card"

@app.middleware("http")
async def add_context_and_log(request: Request, call_next):
    # Generate unique trace and request ID
    request_id = str(uuid.uuid4())
    trace_id = request.headers.get("X-Cloud-Trace-Context", f"trace-{uuid.uuid4().hex}")
    
    # Store request context in middleware
    request.state.request_id = request_id
    request.state.trace_id = trace_id
    
    start_time = time.time()
    metrics_store["requests_total"] += 1
    
    # Custom logger adapter to inject request context
    class ContextAdapter(logging.LoggerAdapter):
        def process(self, msg, kwargs):
            kwargs["extra"] = {
                "request_id": request_id,
                "trace_id": trace_id
            }
            return msg, kwargs
            
    req_logger = ContextAdapter(logger, {})
    req_logger.info(f"Incoming request {request.method} {request.url.path}")
    
    try:
        response = await call_next(request)
        duration = time.time() - start_time
        metrics_store["latencies"].append(duration)
        # Keep latencies size bounded
        if len(metrics_store["latencies"]) > 1000:
            metrics_store["latencies"] = metrics_store["latencies"][-1000:]
            
        req_logger.info(f"Completed request with status_code={response.status_code} in {duration:.4f}s")
        return response
    except Exception as e:
        duration = time.time() - start_time
        req_logger.error(f"Request failed: {str(e)}", exc_info=True)
        metrics_store["payments_failed"] += 1
        raise

@app.get("/")
def read_root():
    return {"service": SERVICE_NAME, "revision": REVISION, "status": "online"}

@app.get("/health")
def health_check(request: Request):
    # If bad config is enabled, the service might be unhealthy
    enable_bad_config = os.getenv("ENABLE_BAD_CONFIG", "false").lower() == "true"
    
    if enable_bad_config:
        logger.error("Health check failed due to bad configuration: ENABLE_BAD_CONFIG is true", extra={
            "request_id": getattr(request.state, "request_id", "unknown"),
            "trace_id": getattr(request.state, "trace_id", "unknown")
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Service Unhealthy: Configuration Error"
        )
    return {"status": "healthy", "service": SERVICE_NAME, "revision": REVISION}

@app.post("/payment")
async def process_payment(payment: PaymentRequest, request: Request):
    request_id = getattr(request.state, "request_id", "unknown")
    trace_id = getattr(request.state, "trace_id", "unknown")
    
    class ContextAdapter(logging.LoggerAdapter):
        def process(self, msg, kwargs):
            kwargs["extra"] = {"request_id": request_id, "trace_id": trace_id}
            return msg, kwargs
            
    req_logger = ContextAdapter(logger, {})
    
    req_logger.info(f"Processing payment request for amount={payment.amount} {payment.currency}")
    
    # Check for ENABLE_BAD_CONFIG
    enable_bad_config = os.getenv("ENABLE_BAD_CONFIG", "false").lower() == "true"
    if enable_bad_config:
        req_logger.error("Fatal exception during payment verification: MISSING_PAYMENT_KEY")
        metrics_store["payments_failed"] += 1
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Configuration Failure: MISSING_PAYMENT_KEY"
        )
        
    # Simulate payment processing
    # Simulate a warning log sometimes
    if payment.amount > 5000:
        req_logger.warning(f"High-value payment request detected: {payment.amount} {payment.currency}")
        
    # Simulate a minor rate limit or warning
    if random.random() < 0.05:
        req_logger.warning("Upstream gateway response delayed, retrying connection...")
        time.sleep(0.1)
        
    time.sleep(random.uniform(0.05, 0.25))  # Simulate network latency
    
    metrics_store["payments_processed"] += 1
    metrics_store["total_revenue"] += payment.amount
    
    req_logger.info(f"Payment processed successfully for amount={payment.amount}")
    
    return {
        "status": "success",
        "transaction_id": f"txn_{uuid.uuid4().hex[:12]}",
        "amount": payment.amount,
        "currency": payment.currency
    }

@app.get("/metrics")
def get_metrics():
    latencies = metrics_store["latencies"]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
    p95_latency = sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0.0
    
    # Return custom JSON metrics (can also be Prometheus format, but JSON is easier for our agent)
    return {
        "requests_total": metrics_store["requests_total"],
        "payments_processed": metrics_store["payments_processed"],
        "payments_failed": metrics_store["payments_failed"],
        "total_revenue": metrics_store["total_revenue"],
        "latency": {
            "avg": avg_latency,
            "p95": p95_latency
        }
    }
