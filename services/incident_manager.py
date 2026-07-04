import os
import asyncio
import time
import random
import uuid
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

from models.incident import (
    TimelineEvent, LogEntry, SystemMetrics, 
    ChatMessage, AIReasoning, CloudRunInfo, 
    IncidentReport, SystemStatus
)

logger = logging.getLogger("services.incident_manager")

INCIDENTS_POOL = [
    {
        "type": "config_bug",
        "title": "High HTTP 500 Error Rate on sample-payment-service",
        "alert": "Cloud Monitoring Alert Triggered: High HTTP 500 Error Rate on sample-payment-service",
        "chat_start": "Alert: High HTTP 500 Error Rate detected on sample-payment-service",
        "symptoms": "HTTP Error Rate rose to 92.5%, average latency increased to 450ms, health checks failing.",
        "evidence": "Active revision: sample-payment-service-v15. Environment variables: ENABLE_BAD_CONFIG=true, MISSING_PAYMENT_KEY=true. Cloud Logging: Tracebacks show ValueError('MISSING_PAYMENT_KEY') in POST /payment endpoint.",
        "root_cause": "Faulty configuration key ENABLE_BAD_CONFIG enabled on revision sample-payment-service-v15, causing the code to raise MISSING_PAYMENT_KEY errors on payment endpoints.",
        "recommended_action": "Rollback traffic to the previous healthy revision: sample-payment-service-v14.",
        "confidence_score": 98.5,
        "estimated_recovery_time": "30 seconds",
        "badge_status": "DEGRADED",
        "log_message": "Request failed: 500 Internal Server Error - Fatal exception during payment verification: MISSING_PAYMENT_KEY"
    },
    {
        "type": "latency_spike",
        "title": "Spike in API Latency on sample-payment-service",
        "alert": "Cloud Monitoring Alert Triggered: p99 Latency > 1500ms on sample-payment-service",
        "chat_start": "Alert: Average latency spiked to 2150ms on sample-payment-service",
        "symptoms": "Average API latency increased from 110ms to 2150ms. Payment queue size is growing rapidly.",
        "evidence": "Active revision: sample-payment-service-v15. Environment variables: DB_CONNECTION_TIMEOUT=30s. Stackdriver trace reveals a synchronous connection pooling deadlock in database client queries.",
        "root_cause": "Synchronous DB connection starvation in revision v15 under concurrent load, causing queries to pile up and timeout.",
        "recommended_action": "Rollback traffic to stable revision v14 which implements async connection pooling.",
        "confidence_score": 96.0,
        "estimated_recovery_time": "20 seconds",
        "badge_status": "DEGRADED",
        "log_message": "WARNING: synchronous database connection starved after 30000ms. Retrying query..."
    },
    {
        "type": "oom_crash",
        "title": "Container Crash Loop Back-off on sample-payment-service",
        "alert": "Cloud Run Alert Triggered: Container Instance restarts exceeding threshold",
        "chat_start": "Alert: Container crash loops and 503 Service Unavailable errors on payment service",
        "symptoms": "Service availability dropped to 42.0%, container memory consumption spiked to 100%, triggering OOM-Kills and restarts.",
        "evidence": "Active revision: sample-payment-service-v15. Cloud Run Events: Instance crashed with exit code 137 (OOM-Killed). Memory profiling indicates a memory leak in the transaction routing cache loop.",
        "root_cause": "Unbounded caching memory leak introduced in revision v15, triggering immediate container termination under moderate load.",
        "recommended_action": "Rollback traffic to stable revision v14 to restore memory ceiling and service stability.",
        "confidence_score": 99.0,
        "estimated_recovery_time": "45 seconds",
        "badge_status": "DEGRADED",
        "log_message": "ERROR: Memory usage limit reached. Out of Memory (OOM) event imminent. Swapping cached items to disk..."
    },
    {
        "type": "schema_bug",
        "title": "API Validation Failures on payment endpoint",
        "alert": "Cloud Monitoring Alert Triggered: High Bad Request (4xx) rate on POST /payment",
        "chat_start": "Alert: Spike in client requests receiving 400 Bad Request responses",
        "symptoms": "400 Error Rate increased to 78.4%. Standard checkout transactions are failing validation checks.",
        "evidence": "Active revision: sample-payment-service-v15. Logs: TypeError('NoneType' object is not iterable) on parsing transaction metadata schema inside request middleware.",
        "root_cause": "A newly deployed payload validation schema in v15 makes the optional 'metadata' field mandatory, breaking compatibility with mobile checkout clients.",
        "recommended_action": "Rollback traffic to revision v14 which supports backwards-compatible optional fields.",
        "confidence_score": 95.5,
        "estimated_recovery_time": "15 seconds",
        "badge_status": "DEGRADED",
        "log_message": "ERROR: Invalid JSON schema parse error: TypeError('NoneType' object is not iterable) on payload: 'metadata'"
    },
    {
        "type": "credential_expiry",
        "title": "Payment Merchant Authentication Failures",
        "alert": "Cloud Monitoring Alert Triggered: High rate of 401 Unauthorized errors on payment processing",
        "chat_start": "Alert: Spikes in 401 Unauthorized responses from gateway integrations",
        "symptoms": "Successful transactions dropped to 0%, merchant processing integration returns persistent AUTH_FAILED response.",
        "evidence": "Active revision: sample-payment-service-v15. Cloud Secret Manager Audit: Merchant key token expired on 2026-07-04. Active container environment is using expired secret token.",
        "root_cause": "Secret Manager token expiration combined with missing automatic secret rotation, causing external gateway authentication to fail.",
        "recommended_action": "Rollback configuration to stable revision v14 which contains a valid rotated credential set.",
        "confidence_score": 97.0,
        "estimated_recovery_time": "30 seconds",
        "badge_status": "DEGRADED",
        "log_message": "ERROR: External Merchant Processing Gateway Auth Failed: 401 Unauthorized - Key expired on 2026-07-04"
    }
]

class IncidentManager:
    def __init__(self):
        self.demo_mode = os.getenv("DEMO_MODE", "true").lower() == "true"
        
        # System State
        self.state = "Healthy" # Healthy, Incident Detected, Investigation, Root Cause Found, Waiting Approval, Executing, Verification, Recovered, Closed
        self.availability = 100.0
        self.latency = 110.0
        self.error_rate = 0.0
        self.current_revision = "sample-payment-service-v14"
        self.previous_revision = "sample-payment-service-v13"
        self.traffic_split = {self.current_revision: 100}
        self.deployment_status = "HEALTHY"
        self.remediation_progress = 0
        self.remediation_step = "Idle" # Executing Rollback, Updating Traffic, Waiting for Deployment, Health Verification, Completed
        
        # Data lists
        self.timeline: List[TimelineEvent] = []
        self.logs: List[LogEntry] = []
        self.metrics_history: List[SystemMetrics] = []
        self.chat_history: List[ChatMessage] = []
        
        # AI Panels
        self.ai_reasoning: Optional[AIReasoning] = None
        self.incident_report: Optional[IncidentReport] = None
        
        # Active incident tracking
        self.active_incident_id = None
        self.incident_start_time = None
        self.active_incident_config = None
        
        # Real GCP ADK references
        self.active_adk_session_id = None
        self.active_adk_runner = None
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "gcp-adk-demo-028")
        self.region = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
        
        # Generate initial history
        self.initialize_metrics_history()
        self.generate_initial_logs()
        
        # Lock for thread safety
        self.lock = asyncio.Lock()
        
        # Query GCP revisions state flag
        self._revisions_initialized = False
        
    def initialize_metrics_history(self):
        """Pre-populate 30 minutes of normal metrics."""
        now = time.time()
        for i in range(30):
            t = now - (30 - i) * 60
            timestamp_str = datetime.fromtimestamp(t).strftime("%H:%M:%S")
            self.metrics_history.append(
                SystemMetrics(
                    timestamp=timestamp_str,
                    request_rate=round(random.uniform(10.0, 15.0), 2),
                    latency=round(random.uniform(90.0, 120.0), 2),
                    cpu=round(random.uniform(15.0, 30.0), 2),
                    memory=round(random.uniform(40.0, 45.0), 2),
                    http_500_rate=0.0
                )
            )

    async def initialize_revisions(self):
        """Query real revisions from GCP on startup to set initial revision states."""
        if self.demo_mode:
            return
            
        try:
            from googleapiclient import discovery
            import google.auth
            
            credentials, project_id = google.auth.default()
            run_client = discovery.build('run', 'v1', credentials=credentials, client_options={"api_endpoint": f"https://{self.region}-run.googleapis.com"})
            
            service_path = f"namespaces/{project_id}/services/sample-payment-service"
            service = run_client.namespaces().services().get(name=service_path).execute()
            
            traffic = service.get("spec", {}).get("traffic", [])
            active_revision = None
            for t in traffic:
                if t.get("percent") == 100 or (t.get("percent", 0) > 0 and not active_revision):
                    active_revision = t.get("revisionName")
                    
            if active_revision:
                self.current_revision = active_revision
                
            parent = f"namespaces/{project_id}"
            result = run_client.namespaces().revisions().list(
                parent=parent,
                labelSelector="serving.knative.dev/service=sample-payment-service"
            ).execute()
            
            items = result.get("items", [])
            items.sort(key=lambda x: x.get("metadata", {}).get("creationTimestamp", ""), reverse=True)
            
            names = [item.get("metadata", {}).get("name") for item in items]
            if len(names) > 1:
                if active_revision == names[0]:
                    self.previous_revision = names[1]
                else:
                    self.previous_revision = names[0]
                    
            logger.info(f"Initialized revisions from GCP: current={self.current_revision}, previous={self.previous_revision}")
        except Exception as e:
            logger.warning(f"Failed to initialize revisions from GCP on startup: {e}")

    async def get_payment_service_url(self) -> str:
        try:
            from googleapiclient import discovery
            import google.auth
            credentials, project_id = google.auth.default()
            run_client = discovery.build('run', 'v1', credentials=credentials, client_options={"api_endpoint": f"https://{self.region}-run.googleapis.com"})
            service = run_client.namespaces().services().get(
                name=f"namespaces/{project_id}/services/sample-payment-service"
            ).execute()
            return service.get("status", {}).get("url", "")
        except Exception:
            return ""
            
    def generate_initial_logs(self):
        """Generate normal system logs."""
        now = time.time()
        for i in range(20):
            t = now - (20 - i) * 10
            self.logs.append(
                LogEntry(
                    timestamp=datetime.fromtimestamp(t).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                    severity="INFO",
                    message=f"Completed request with status_code=200 in {random.uniform(0.08, 0.12):.4f}s",
                    service="sample-payment-service",
                    revision=self.current_revision,
                    region="us-central1",
                    request_id=f"req-{uuid.uuid4().hex[:8]}",
                    trace_id=f"trace-{uuid.uuid4().hex[:12]}"
                )
            )

    async def update_metrics(self):
        """Call this periodically to update the current metrics stream."""
        if not self._revisions_initialized and not self.demo_mode:
            self._revisions_initialized = True
            asyncio.create_task(self.initialize_revisions())
            
        async with self.lock:
            now_str = datetime.now().strftime("%H:%M:%S")
            
            if self.demo_mode:
                # Change metrics based on state
                if self.state in ["Healthy", "Recovered", "Closed"]:
                    self.error_rate = 0.0
                    self.availability = 100.0
                    self.latency = round(random.uniform(90.0, 120.0), 2)
                    h500 = 0.0
                elif self.state in ["Incident Detected", "Investigation", "Root Cause Found", "Waiting Approval"]:
                    inc_type = self.active_incident_config["type"] if self.active_incident_config else "config_bug"
                    
                    if inc_type == "latency_spike":
                        self.error_rate = round(random.uniform(15.0, 30.0), 2)
                        self.latency = round(random.uniform(1800.0, 2400.0), 2)
                        h500 = self.error_rate
                    elif inc_type == "oom_crash":
                        self.error_rate = round(random.uniform(50.0, 70.0), 2)
                        self.latency = round(random.uniform(450.0, 750.0), 2)
                        h500 = self.error_rate
                    elif inc_type == "schema_bug":
                        self.error_rate = round(random.uniform(70.0, 85.0), 2)
                        self.latency = round(random.uniform(140.0, 250.0), 2)
                        h500 = self.error_rate
                    elif inc_type == "credential_expiry":
                        self.error_rate = round(random.uniform(95.0, 100.0), 2)
                        self.latency = round(random.uniform(180.0, 320.0), 2)
                        h500 = self.error_rate
                    else: # config_bug
                        self.error_rate = round(random.uniform(85.0, 95.0), 2)
                        self.latency = round(random.uniform(350.0, 520.0), 2)
                        h500 = self.error_rate
                        
                    self.availability = round(100.0 - self.error_rate, 2)
                else: # Executing, Verification
                    # Recovering metrics
                    progress_factor = (100 - self.remediation_progress) / 100.0
                    self.error_rate = round(random.uniform(10.0, 30.0) * progress_factor, 2)
                    self.availability = round(100.0 - self.error_rate, 2)
                    self.latency = round(random.uniform(120.0, 200.0) if self.remediation_progress > 50 else random.uniform(250.0, 380.0), 2)
                    h500 = self.error_rate
                    
                cpu_val = round(random.uniform(40.0, 60.0) if self.state != "Healthy" else random.uniform(15.0, 30.0), 2)
                mem_val = round(random.uniform(65.0, 75.0) if self.state != "Healthy" else random.uniform(40.0, 45.0), 2)
            else:
                # Active synthetic probing to get real live data!
                import httpx
                url = await self.get_payment_service_url()
                if url:
                    probe_url = f"{url.rstrip('/')}/payment"
                    latencies = []
                    errors = 0
                    total = 3
                    
                    for _ in range(total):
                        try:
                            start = time.time()
                            res = await asyncio.to_thread(httpx.get, probe_url, timeout=2.0)
                            elapsed = (time.time() - start) * 1000
                            latencies.append(elapsed)
                            if res.status_code == 500:
                                errors += 1
                        except Exception:
                            latencies.append(2000.0)
                            errors += 1
                            
                    avg_latency = sum(latencies) / len(latencies) if latencies else 110.0
                    error_pct = (errors / total) * 100.0
                    
                    self.latency = round(avg_latency, 2)
                    self.error_rate = round(error_pct, 2)
                    self.availability = round(100.0 - self.error_rate, 2)
                    h500 = self.error_rate
                    
                    cpu_val = round(random.uniform(50.0, 70.0) if self.error_rate > 50 else random.uniform(15.0, 25.0), 2)
                    mem_val = round(random.uniform(70.0, 80.0) if self.error_rate > 50 else random.uniform(40.0, 45.0), 2)
                else:
                    self.latency = 110.0
                    self.error_rate = 0.0
                    self.availability = 100.0
                    h500 = 0.0
                    cpu_val = 20.0
                    mem_val = 42.0
                
            new_metric = SystemMetrics(
                timestamp=now_str,
                request_rate=round(random.uniform(8.0, 16.0), 2),
                latency=self.latency,
                cpu=cpu_val,
                memory=mem_val,
                http_500_rate=h500
            )
            
            self.metrics_history.append(new_metric)
            if len(self.metrics_history) > 30:
                self.metrics_history.pop(0)
                
            # Log generation
            if self.demo_mode:
                if self.state in ["Incident Detected", "Investigation", "Root Cause Found", "Waiting Approval"]:
                    if random.random() < 0.7:
                        msg = self.active_incident_config["log_message"] if self.active_incident_config else "Request failed: 500 Internal Server Error - Fatal exception during payment verification: MISSING_PAYMENT_KEY"
                        self.logs.insert(0, LogEntry(
                            timestamp=datetime.now().strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                            severity="ERROR",
                            message=msg,
                            service="sample-payment-service",
                            revision=self.current_revision,
                            region="us-central1",
                            request_id=f"req-{uuid.uuid4().hex[:8]}",
                            trace_id="trace-critical-err"
                        ))
                else:
                    if random.random() < 0.5:
                        self.logs.insert(0, LogEntry(
                            timestamp=datetime.now().strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                            severity="INFO",
                            message=f"Completed request with status_code=200 in {random.uniform(0.08, 0.12):.4f}s",
                            service="sample-payment-service",
                            revision=self.current_revision,
                            region="us-central1",
                            request_id=f"req-{uuid.uuid4().hex[:8]}",
                            trace_id=f"trace-{uuid.uuid4().hex[:12]}"
                        ))
            else:
                # Query real Cloud Logging to show real service logs in the dashboard!
                try:
                    from tools.gcp_mcp import read_recent_logs
                    res = read_recent_logs("sample-payment-service", 20)
                    if res.get("status") == "success":
                        gcp_logs = []
                        for log in res.get("logs", []):
                            gcp_logs.append(
                                LogEntry(
                                    timestamp=log.get("timestamp"),
                                    severity=log.get("severity"),
                                    message=log.get("message"),
                                    service=log.get("service"),
                                    revision=log.get("revision"),
                                    region=log.get("region"),
                                    request_id=log.get("request_id"),
                                    trace_id=log.get("trace_id")
                                )
                            )
                        if gcp_logs:
                            self.logs = gcp_logs
                except Exception as e:
                    logger.warning(f"Failed to query real GCP logs for dashboard: {e}")
            
            # Keep logs size bounded
            if len(self.logs) > 100:
                self.logs = self.logs[:100]

    def add_timeline_event(self, message: str, severity: str = "INFO"):
        now_str = datetime.now().strftime("%H:%M:%S")
        self.timeline.insert(0, TimelineEvent(timestamp=now_str, message=message, severity=severity))

    def add_chat_message(self, sender: str, text: str, options: Optional[List[str]] = None):
        now_str = datetime.now().strftime("%H:%M:%S")
        self.chat_history.append(ChatMessage(
            id=str(uuid.uuid4()),
            sender=sender,
            text=text,
            timestamp=now_str,
            options=options
        ))

    async def update_cloud_run_env(self, service_name: str, env_vars: dict) -> bool:
        """Helper to update environment variables on the real Cloud Run service in GCP."""
        try:
            from googleapiclient import discovery
            import google.auth
            
            credentials, project_id = google.auth.default()
            run_client = discovery.build('run', 'v1', credentials=credentials, client_options={"api_endpoint": f"https://{self.region}-run.googleapis.com"})
            service_path = f"namespaces/{project_id}/services/{service_name}"
            
            # Fetch service
            service = run_client.namespaces().services().get(name=service_path).execute()
            
            # Locate env variables
            containers = service["spec"]["template"]["spec"]["containers"]
            if not containers:
                return False
                
            env_list = containers[0].get("env", [])
            
            # Update values
            for k, v in env_vars.items():
                found = False
                for env_item in env_list:
                    if env_item.get("name") == k:
                        env_item["value"] = v
                        found = True
                        break
                if not found:
                    env_list.append({"name": k, "value": v})
                    
            containers[0]["env"] = env_list
            
            # Reset traffic targets so new revision takes traffic
            if "spec" in service and "traffic" in service["spec"]:
                service["spec"]["traffic"] = [
                    {
                        "percent": 100,
                        "latestRevision": True
                    }
                ]
            
            # Replace service
            run_client.namespaces().services().replaceService(
                name=service_path,
                body=service
            ).execute()
            return True
        except Exception as e:
            logger.error(f"Failed to update Cloud Run env: {e}", exc_info=True)
            return False

    async def trigger_incident(self):
        """Simulate/trigger an incident on the real GCP service."""
        async with self.lock:
            if self.state != "Healthy":
                return
            
            # Select random incident from our 5-incident pool
            self.active_incident_config = random.choice(INCIDENTS_POOL)
            
            self.state = "Incident Detected"
            self.active_incident_id = f"INC-{random.randint(1000, 9999)}"
            self.incident_start_time = time.time()
            self.deployment_status = self.active_incident_config["badge_status"]
            
            # Reset timeline and add alert event
            self.timeline = []
            self.add_timeline_event(self.active_incident_config["alert"], "ERROR")
            self.add_timeline_event("Service availability dropped below SLO (99.9%)", "WARNING")
            
            # Clear chat and start AI agent interaction
            self.chat_history = []
            self.add_chat_message("System", self.active_incident_config["chat_start"])
            
            if self.demo_mode:
                # Enable bad configuration (mock)
                os.environ["ENABLE_BAD_CONFIG"] = "true"
                self.previous_revision = "sample-payment-service-v14"
                self.current_revision = "sample-payment-service-v15"
                self.traffic_split = {self.current_revision: 100}
                asyncio.create_task(self.run_sre_agent_flow())
            else:
                # Fallback to config bug for real GCP testing
                self.active_incident_config = INCIDENTS_POOL[0]
                logger.info("Triggering real incident in GCP by setting ENABLE_BAD_CONFIG=true")
                success = await self.update_cloud_run_env("sample-payment-service", {"ENABLE_BAD_CONFIG": "true"})
                if success:
                    self.add_timeline_event("Successfully updated Cloud Run configuration: ENABLE_BAD_CONFIG=true", "INFO")
                    self.add_chat_message("System", "Updating Cloud Run configuration to inject bug revision. Traffic will automatically route 100% to the new revision once ready.")
                else:
                    self.add_timeline_event("Failed to update Cloud Run configuration in GCP", "ERROR")
                    self.add_chat_message("System", "Error updating Cloud Run configuration in GCP. Check credentials.")
                
                asyncio.create_task(self.run_real_sre_agent_flow())

    async def run_sre_agent_flow(self):
        """Orchestrates the AI SRE Agent lifecycle transitions (Simulated)."""
        await asyncio.sleep(2)
        self.state = "Investigation"
        self.add_timeline_event("AI Agent Started: IncidentResponseAgent initialized", "INFO")
        self.add_chat_message("AI", "Incident detected on sample-payment-service. Commencing automated triage...")
        
        await asyncio.sleep(2.5)
        self.add_timeline_event("Reading Logs: Querying Cloud Logging for severity=ERROR", "INFO")
        self.add_chat_message("AI", f"Querying Cloud Logging. Found anomalous tracebacks correlating with symptoms.")
        
        await asyncio.sleep(2.5)
        self.add_timeline_event("Analyzing Metrics: Querying Cloud Monitoring error rate and latency", "INFO")
        self.add_chat_message("AI", f"Checking Cloud Run Revisions... Active revision is {self.current_revision}. Investigating revision specs...")
        
        await asyncio.sleep(2.5)
        self.state = "Root Cause Found"
        self.add_timeline_event(f"Root Cause Found: {self.active_incident_config['title']}", "SUCCESS")
        
        self.ai_reasoning = AIReasoning(
            observed_symptoms=self.active_incident_config["symptoms"],
            evidence=self.active_incident_config["evidence"],
            reasoning=f"The incident coincided with the deployment of revision v15. The telemetry and log metrics confirm a localized issue inside this container revision. Rolling back traffic to stable v14 will resolve the issue immediately.",
            confidence_score=self.active_incident_config["confidence_score"],
            root_cause=self.active_incident_config["root_cause"],
            recommended_action=self.active_incident_config["recommended_action"],
            estimated_recovery_time=self.active_incident_config["estimated_recovery_time"]
        )
        
        self.add_chat_message("AI", f"Root Cause Identified: {self.active_incident_config['root_cause']}")
        
        await asyncio.sleep(2)
        self.state = "Waiting Approval"
        self.add_timeline_event("Waiting for Human Approval: Rollback request submitted", "WARNING")
        self.add_chat_message("AI", f"Recommendation: {self.active_incident_config['recommended_action']} Do you approve?", options=["Approve", "Reject"])

    async def run_real_sre_agent_flow(self):
        """Runs the real ADK SRE Agent to triage the GCP incident."""
        await asyncio.sleep(15)
        
        async with self.lock:
            self.state = "Investigation"
            self.add_timeline_event("AI Agent Started: IncidentResponseAgent initialized", "INFO")
            self.add_chat_message("AI", "Incident detected on sample-payment-service. Commencing automated triage...")
            
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService
        from google.genai import types
        from agents.incident_agent import agent_instance
        
        session_service = InMemorySessionService()
        session_id = f"sre-session-{int(time.time())}"
        await session_service.create_session(app_name="ai_sre_agent", user_id="operator", session_id=session_id)
        
        runner = Runner(agent=agent_instance, app_name="ai_sre_agent", session_service=session_service)
        self.active_adk_session_id = session_id
        self.active_adk_runner = runner
        
        prompt = (
            "An alert has been triggered for 'sample-payment-service'. The HTTP 500 error rate is high and latency has spiked. "
            "Please investigate the incident using your GCP tools (monitoring, logging, revisions), identify the root cause, "
            "recommend remediation (a rollback), ask the operator for approval, and stop."
        )
        
        try:
            async for event in runner.run_async(
                user_id="operator",
                session_id=session_id,
                new_message=types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
            ):
                if event.is_final_response():
                    text_response = event.content.parts[0].text
                    self.add_chat_message("AI", text_response)
                    
                    async with self.lock:
                        self.state = "Waiting Approval"
                        self.ai_reasoning = AIReasoning(
                            observed_symptoms="HTTP Error Rate rose to 100%, average latency increased, health checks failing.",
                            evidence="Active revision: sample-payment-service-v15. Environment variables: ENABLE_BAD_CONFIG=true. Cloud Logging: Tracebacks show ValueError('MISSING_PAYMENT_KEY') in POST /payment endpoint.",
                            reasoning="The incident coincided with the deployment of revision v15. The error logs pinpoint a missing configuration key. Rolling back traffic to the previous healthy revision will resolve the issue immediately.",
                            confidence_score=98.5,
                            root_cause="Faulty configuration key ENABLE_BAD_CONFIG enabled on the active revision, causing the code to raise MISSING_PAYMENT_KEY errors on payment endpoints.",
                            recommended_action="Rollback service traffic to the previous healthy revision.",
                            estimated_recovery_time="20 seconds"
                        )
                        self.add_timeline_event("Waiting for Human Approval: Rollback request submitted", "WARNING")
        except Exception as e:
            logger.error(f"Error in SRE agent run: {e}", exc_info=True)
            self.add_chat_message("System", f"Error during AI Agent execution: {e}")

    async def approve_rollback(self):
        """Execute rollback when approved by user."""
        async with self.lock:
            if self.state != "Waiting Approval":
                return
            
            self.state = "Executing"
            self.remediation_progress = 0
            self.remediation_step = "Executing Rollback"
            
            self.add_chat_message("Operator", "Approve rollback")
            self.add_timeline_event("Rollback Approved by Operator", "INFO")
            self.add_chat_message("AI", "Rollback approved. Commencing rollback execution...")
            
        if self.demo_mode:
            asyncio.create_task(self.execute_rollback_flow())
        else:
            asyncio.create_task(self.resume_real_sre_agent("Approve"))

    async def resume_real_sre_agent(self, user_response: str):
        """Resumes the running ADK session with user input."""
        from google.genai import types
        
        async with self.lock:
            self.state = "Executing"
            self.remediation_progress = 25
            self.remediation_step = "Executing Rollback"
            
        try:
            async for event in self.active_adk_runner.run_async(
                user_id="operator",
                session_id=self.active_adk_session_id,
                new_message=types.Content(role="user", parts=[types.Part.from_text(text=user_response)])
            ):
                if event.is_final_response():
                    text_response = event.content.parts[0].text
                    self.add_chat_message("AI", text_response)
                    
            async with self.lock:
                self.state = "Verification"
                self.remediation_progress = 75
                self.remediation_step = "Health Verification"
                
            await asyncio.sleep(2)
            
            async with self.lock:
                self.state = "Recovered"
                self.remediation_progress = 100
                self.remediation_step = "Completed"
                self.deployment_status = "HEALTHY"
                
                # Query GCP to reset current_revision and previous_revision
                await self.initialize_revisions()
                
                recovery_time = int(time.time() - self.incident_start_time)
                self.generate_incident_report(recovery_time)
                
                self.add_timeline_event("Incident Closed: System fully recovered", "SUCCESS")
                self.state = "Closed"
                
        except Exception as e:
            logger.error(f"Error resuming SRE agent: {e}", exc_info=True)
            self.add_chat_message("System", f"Error during AI Agent execution: {e}")

    async def execute_rollback_flow(self):
        # Step 1: Executing Rollback
        await asyncio.sleep(2)
        async with self.lock:
            self.remediation_progress = 25
            self.remediation_step = "Updating Traffic"
            self.add_timeline_event("Rollback Started: Routing traffic to v14", "INFO")
            self.add_chat_message("AI", "Updating Cloud Run traffic configuration...")
            
        # Step 2: Update Split
        await asyncio.sleep(2)
        async with self.lock:
            self.remediation_progress = 50
            self.remediation_step = "Waiting for Deployment"
            os.environ["ENABLE_BAD_CONFIG"] = "false"
            self.current_revision = "sample-payment-service-v14"
            self.traffic_split = {"sample-payment-service-v14": 100, "sample-payment-service-v15": 0}
            self.add_timeline_event("Traffic routed: 100% traffic redirected to sample-payment-service-v14", "INFO")
            self.add_chat_message("AI", "Traffic redirected to v14. Waiting for routing stability...")
            
        # Step 3: Verify Health
        await asyncio.sleep(2.5)
        async with self.lock:
            self.state = "Verification"
            self.remediation_progress = 75
            self.remediation_step = "Health Verification"
            self.add_timeline_event("Verification Complete: HTTP status 200, Latency normal", "SUCCESS")
            self.add_chat_message("AI", "Verifying service health. Performing HTTP requests to health endpoints...")
            
        # Step 4: Complete
        await asyncio.sleep(2)
        async with self.lock:
            self.state = "Recovered"
            self.remediation_progress = 100
            self.remediation_step = "Completed"
            self.deployment_status = "HEALTHY"
            
            recovery_time = int(time.time() - self.incident_start_time)
            self.generate_incident_report(recovery_time)
            self.add_timeline_event("Incident Closed: System fully recovered", "SUCCESS")
            self.add_chat_message("AI", "Service verification successful. Latency: 98ms, Error Rate: 0.0%. Incident resolved.")
            self.add_chat_message("System", f"Incident {self.active_incident_id} Closed. Report generated.")
            self.state = "Closed"

    async def reject_rollback(self, feedback: str = "Rollback rejected by user"):
        """User rejects the rollback."""
        async with self.lock:
            if self.state != "Waiting Approval":
                return
            
            self.state = "Investigation"
            self.add_chat_message("Operator", f"Reject. {feedback}")
            self.add_timeline_event(f"Rollback Rejected: {feedback}", "ERROR")
            self.add_chat_message("AI", f"Rollback rejected. Awaiting alternative instructions. Feedback received: '{feedback}'. Please instruct me on how to proceed.")

    def generate_incident_report(self, recovery_time: int):
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
        start_str = datetime.fromtimestamp(self.incident_start_time).strftime("%Y-%m-%d %H:%M:%S UTC")
        
        md_report = f"""# Incident Post-Mortem: {self.active_incident_id}
**Service Affected:** `sample-payment-service`  
**Severity:** P0 - Critical  
**Status:** CLOSED  
**Incident Start:** {start_str}  
**Incident Resolved:** {now_str}  
**Total Recovery Time:** {recovery_time} seconds  

## 1. Executive Summary
On {start_str}, a Cloud Monitoring alert was triggered due to a massive spike in HTTP 500 errors (exceeding 90%) and a significant increase in average latency to over 450ms. An autonomous AI SRE agent (`IncidentResponseAgent`) was activated to triage and remediate the incident. The agent successfully identified the root cause as a configuration bug in the newly deployed revision and executed a rollback to the previous healthy revision after receiving operator approval.

## 2. Timeline of Events
- **{start_str}**: Cloud Monitoring alert triggered (HTTP 500 Error rate = 92.5%).
- **{start_str} + 2s**: `IncidentResponseAgent` initialized.
- **{start_str} + 4s**: Agent fetched error logs from Cloud Logging, identifying a `MISSING_PAYMENT_KEY` exception.
- **{start_str} + 6s**: Agent inspected revision specs and detected `ENABLE_BAD_CONFIG=true`.
- **{start_str} + 9s**: Agent formulated Root Cause Analysis (RCA) and requested operator approval for rollback.
- **{start_str} + 12s**: Operator approved the rollback.
- **{start_str} + 14s**: Rollback initiated.
- **{start_str} + 19s**: Health verification completed. HTTP Status 200 returned, latency normalized.
- **{start_str} + 21s**: Incident closed. Post-mortem report generated.

## 3. Root Cause Analysis
A faulty environment variable configuration key `ENABLE_BAD_CONFIG=true` was enabled on the active revision. This key forced the payment route to throw `500 Internal Server Error` with a `MISSING_PAYMENT_KEY` ValueError, disabling all payment processing.

## 4. Remediation Actions
1. **Traffic Shifting**: Transferred 100% of incoming HTTP traffic back to the previous stable revision.
2. **Verification**: Executed targeted curl validation against the `/health` and `/payment` endpoints to confirm stable HTTP 200 responses.

## 5. Recovery Metrics
- **Pre-Incident Latency:** 110ms
- **Peak Latency:** 520ms
- **Post-Incident Latency:** 98ms
- **Peak HTTP 500 Rate:** 92.5%
- **Post-Incident HTTP 500 Rate:** 0.0%

## 6. Recommendations & Lessons Learned
- **Config Validation**: Implement a pre-deploy schema validation check in the CI/CD pipeline to prevent deploying invalid config values.
- **Canary Deployments**: Transition from a 100% traffic shift model to a canary release strategy (e.g., routing 10% traffic to new revisions first).
- **Automated Rollbacks**: Enable automated rollbacks on critical alert metrics in staging environments.
"""
        
        self.incident_report = IncidentReport(
            incident_id=self.active_incident_id,
            title=f"High HTTP 500s on sample-payment-service",
            status="CLOSED",
            start_time=start_str,
            end_time=now_str,
            timeline=[
                f"Alert triggered: {start_str}",
                "Agent initialized",
                "RCA generated: Missing configuration key detected",
                "Operator approved rollback",
                "Rollback executed: 100% traffic to previous healthy revision",
                "Service health verified"
            ],
            root_cause="Faulty configuration key ENABLE_BAD_CONFIG enabled on revision, causing the code to raise MISSING_PAYMENT_KEY errors.",
            remediation_actions=["Rollback traffic to previous revision", "Execute verification scripts"],
            recovery_time_seconds=recovery_time,
            recommendations=["Add pre-deployment configuration checks", "Implement progressive canary rollouts"],
            lessons_learned=["Ensure critical variables are verified during service startup, not lazy loaded"],
            markdown_content=md_report
        )

    async def restore_service(self):
        """Force manual restore/reset of the state machine to Healthy."""
        async with self.lock:
            if self.demo_mode:
                os.environ["ENABLE_BAD_CONFIG"] = "false"
                self.current_revision = "sample-payment-service-v14"
                self.previous_revision = "sample-payment-service-v13"
                self.traffic_split = {self.current_revision: 100}
                self.deployment_status = "HEALTHY"
                self.state = "Healthy"
                self.remediation_progress = 0
                self.remediation_step = "Idle"
                self.ai_reasoning = None
                self.incident_report = None
                self.active_incident_id = None
                self.incident_start_time = None
                self.add_timeline_event("System returned to Healthy baseline", "SUCCESS")
                self.add_chat_message("System", "Service manually restored to healthy status.")
            else:
                logger.info("Manually restoring baseline in GCP by setting ENABLE_BAD_CONFIG=false")
                success = await self.update_cloud_run_env("sample-payment-service", {"ENABLE_BAD_CONFIG": "false"})
                if success:
                    await self.initialize_revisions()
                    self.deployment_status = "HEALTHY"
                    self.state = "Healthy"
                    self.remediation_progress = 0
                    self.remediation_step = "Idle"
                    self.ai_reasoning = None
                    self.incident_report = None
                    self.active_incident_id = None
                    self.incident_start_time = None
                    self.add_timeline_event("System returned to Healthy baseline in GCP", "SUCCESS")
                    self.add_chat_message("System", "Service manually restored to healthy baseline in GCP.")
                else:
                    self.add_timeline_event("Failed to manually restore baseline in GCP", "ERROR")
                    self.add_chat_message("System", "Error manually restoring baseline in GCP.")

# Global instance of IncidentManager
incident_manager = IncidentManager()
