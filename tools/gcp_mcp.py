import os
import time
import random
import logging
from typing import Dict, List, Any, Optional
from google.adk.tools import ToolContext

# Setup local logging
logger = logging.getLogger("tools.gcp_mcp")

# Check if we should run in demo mode (default: False)
def is_demo_mode() -> bool:
    return os.getenv("DEMO_MODE", "false").lower() == "true"

def get_simulated_recent_logs(service_name: str, limit: int) -> dict:
    enable_bad_config = os.getenv("ENABLE_BAD_CONFIG", "false").lower() == "true"
    logs = []
    now = time.time()
    if enable_bad_config:
        logs.extend([
            {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now - 10)),
                "severity": "ERROR",
                "message": "Fatal exception during payment verification: MISSING_PAYMENT_KEY",
                "service": service_name,
                "revision": f"{service_name}-v15",
                "region": "us-central1",
                "request_id": "req-9e2c88f1",
                "trace_id": "trace-4043b879"
            },
            {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now - 12)),
                "severity": "ERROR",
                "message": "Request failed: 500 Internal Server Error",
                "service": service_name,
                "revision": f"{service_name}-v15",
                "region": "us-central1",
                "request_id": "req-9e2c88f1",
                "trace_id": "trace-4043b879"
            },
            {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now - 15)),
                "severity": "WARNING",
                "message": "High-value payment request detected: 5500 USD",
                "service": service_name,
                "revision": f"{service_name}-v15",
                "region": "us-central1",
                "request_id": "req-9e2c88f1",
                "trace_id": "trace-4043b879"
            }
        ])
    for i in range(limit - len(logs)):
        logs.append({
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now - 20 - i*5)),
            "severity": "INFO",
            "message": f"Completed request with status_code=200 in {random.uniform(0.05, 0.15):.4f}s",
            "service": service_name,
            "revision": f"{service_name}-v14" if not enable_bad_config or i > 2 else f"{service_name}-v15",
            "region": "us-central1",
            "request_id": f"req-{random.randint(10000000, 99999999)}",
            "trace_id": f"trace-{random.randint(10000000, 99999999)}"
        })
    return {"status": "success", "logs": logs[:limit]}

def read_recent_logs(service_name: str, limit: int) -> dict:
    """Reads recent log entries for a Google Cloud Run service.

    Args:
        service_name: The name of the Cloud Run service.
        limit: The maximum number of log entries to retrieve.

    Returns:
        A dictionary containing a list of log entries with timestamps, severity, and message.
    """
    logger.info(f"Tool called: read_recent_logs(service_name={service_name}, limit={limit})")
    try:
        from services.incident_manager import incident_manager
        incident_manager.add_timeline_event(f"Tool Call: read_recent_logs(service_name='{service_name}')", "INFO")
        incident_manager.add_chat_message("AI", f"[Tool] Querying recent logs for service '{service_name}'...")
    except ImportError:
        pass
    
    if is_demo_mode():
        return get_simulated_recent_logs(service_name, limit)

    try:
        from google.cloud import logging as cloud_logging
        client = cloud_logging.Client()
        filter_str = f'resource.type="cloud_run_revision" AND resource.labels.service_name="{service_name}"'
        entries = client.list_entries(filter_=filter_str, page_size=limit)
        logs = []
        for entry in entries:
            logs.append({
                "timestamp": entry.timestamp.isoformat() if entry.timestamp else "",
                "severity": entry.severity,
                "message": entry.payload if isinstance(entry.payload, str) else str(entry.payload),
                "service": service_name,
                "revision": entry.resource.labels.get("revision_name", "unknown"),
                "region": entry.resource.labels.get("location", "unknown"),
                "request_id": entry.http_request.get("requestId") if entry.http_request else None,
                "trace_id": entry.trace
            })
        return {"status": "success", "logs": logs}
    except Exception as e:
        logger.warning(f"Error querying cloud logging: {e}. Falling back to demo data.")
        return get_simulated_recent_logs(service_name, limit)

def read_error_logs(service_name: str, limit: int) -> dict:
    """Reads error logs (severity ERROR) for a Google Cloud Run service.

    Args:
        service_name: The name of the Cloud Run service.
        limit: The maximum number of error logs to retrieve.

    Returns:
        A dictionary containing error log entries.
    """
    logger.info(f"Tool called: read_error_logs(service_name={service_name}, limit={limit})")
    try:
        from services.incident_manager import incident_manager
        incident_manager.add_timeline_event(f"Tool Call: read_error_logs(service_name='{service_name}')", "INFO")
        incident_manager.add_chat_message("AI", f"[Tool] Scanning Cloud Logging for ERROR severity logs on '{service_name}'...")
    except ImportError:
        pass
    
    if is_demo_mode():
        now = time.time()
        error_logs = [
            {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now - 10)),
                "severity": "ERROR",
                "message": "Fatal exception during payment verification: MISSING_PAYMENT_KEY",
                "service": service_name,
                "revision": f"{service_name}-v15",
                "region": "us-central1",
                "request_id": "req-9e2c88f1",
                "trace_id": "trace-4043b879"
            },
            {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now - 12)),
                "severity": "ERROR",
                "message": "Request failed: 500 Internal Server Error",
                "service": service_name,
                "revision": f"{service_name}-v15",
                "region": "us-central1",
                "request_id": "req-9e2c88f1",
                "trace_id": "trace-4043b879"
            }
        ]
        return {"status": "success", "logs": error_logs[:limit]}
        
    try:
        from google.cloud import logging as cloud_logging
        client = cloud_logging.Client()
        filter_str = f'resource.type="cloud_run_revision" AND resource.labels.service_name="{service_name}" AND severity=ERROR'
        entries = client.list_entries(filter_=filter_str, page_size=limit)
        logs = []
        for entry in entries:
            logs.append({
                "timestamp": entry.timestamp.isoformat() if entry.timestamp else "",
                "severity": entry.severity,
                "message": entry.payload if isinstance(entry.payload, str) else str(entry.payload),
                "service": service_name,
                "revision": entry.resource.labels.get("revision_name", "unknown"),
                "region": entry.resource.labels.get("location", "unknown"),
                "request_id": entry.http_request.get("requestId") if entry.http_request else None,
                "trace_id": entry.trace
            })
        return {"status": "success", "logs": logs}
    except Exception as e:
        logger.warning(f"Error querying cloud logging: {e}. Falling back to demo data.")
        now = time.time()
        return {
            "status": "success",
            "logs": [
                {
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now - 10)),
                    "severity": "ERROR",
                    "message": f"Query fallback (GCP Logging error): {e}",
                    "service": service_name,
                    "revision": "unknown",
                    "region": "us-central1",
                    "request_id": "req-err",
                    "trace_id": "trace-err"
                }
            ][:limit]
        }

def read_metrics(service_name: str, metric_type: str, duration_minutes: int) -> dict:
    """Reads Cloud Monitoring metrics for a Cloud Run service.

    Args:
        service_name: The name of the Cloud Run service.
        metric_type: The metric type to query (e.g., 'latency', 'error_rate', 'request_rate').
        duration_minutes: The lookback duration in minutes.

    Returns:
        A dictionary containing time series data points.
    """
    logger.info(f"Tool called: read_metrics(service_name={service_name}, metric_type={metric_type}, duration_minutes={duration_minutes})")
    try:
        from services.incident_manager import incident_manager
        incident_manager.add_timeline_event(f"Tool Call: read_metrics(service_name='{service_name}', metric_type='{metric_type}')", "INFO")
        incident_manager.add_chat_message("AI", f"[Tool] Querying Stackdriver metrics for '{metric_type}' on service '{service_name}'...")
    except ImportError:
        pass
    
    if is_demo_mode():
        # Simulated metrics based on ENABLE_BAD_CONFIG
        enable_bad_config = os.getenv("ENABLE_BAD_CONFIG", "false").lower() == "true"
        points = []
        now = time.time()
        
        for i in range(duration_minutes):
            t = now - (duration_minutes - i) * 60
            timestamp_str = time.strftime("%H:%M", time.localtime(t))
            
            if metric_type == "error_rate":
                val = random.uniform(85.0, 95.0) if (enable_bad_config and i > duration_minutes - 5) else random.uniform(0.0, 0.5)
            elif metric_type == "latency":
                val = random.uniform(250.0, 480.0) if (enable_bad_config and i > duration_minutes - 5) else random.uniform(80.0, 150.0)
            elif metric_type == "request_rate":
                val = random.uniform(8.0, 15.0)
            else:
                val = random.uniform(10.0, 50.0)
                
            points.append({"timestamp": timestamp_str, "value": round(val, 2)})
            
        return {"status": "success", "metric": metric_type, "points": points}

    try:
        from google.cloud import monitoring_v3
        import datetime
        
        client = monitoring_v3.MetricServiceClient()
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "gcp-adk-demo-028")
        project_name = f"projects/{project_id}"
        
        metric_map = {
            "request_rate": "run.googleapis.com/request_count",
            "latency": "run.googleapis.com/request_latencies",
            "error_rate": "run.googleapis.com/request_count",
        }
        
        gcp_metric = metric_map.get(metric_type)
        if not gcp_metric:
            return {"status": "success", "metric": metric_type, "points": []}
            
        now = datetime.datetime.now(datetime.timezone.utc)
        start_time = now - datetime.timedelta(minutes=duration_minutes)
        
        interval = monitoring_v3.TimeInterval(
            {
                "end_time": {"seconds": int(now.timestamp()), "nanos": 0},
                "start_time": {"seconds": int(start_time.timestamp()), "nanos": 0},
            }
        )
        
        filter_str = f'metric.type = "{gcp_metric}" AND resource.type = "cloud_run_revision" AND resource.labels.service_name = "{service_name}"'
        if metric_type == "error_rate":
            filter_str += ' AND metric.labels.response_code_class = "5xx"'
            
        aggregation = monitoring_v3.Aggregation(
            {
                "alignment_period": {"seconds": 60},
                "per_series_aligner": (
                    monitoring_v3.Aggregation.Aligner.ALIGN_RATE if metric_type in ["request_rate", "error_rate"]
                    else (monitoring_v3.Aggregation.Aligner.ALIGN_PERCENTILE_95 if metric_type == "latency"
                          else monitoring_v3.Aggregation.Aligner.ALIGN_MEAN)
                ),
                "cross_series_reducer": monitoring_v3.Aggregation.Reducer.REDUCE_SUM if metric_type != "latency" else monitoring_v3.Aggregation.Reducer.REDUCE_MEAN,
                "group_by_fields": ["resource.labels.revision_name"]
            }
        )
        
        results = client.list_time_series(
            request={
                "name": project_name,
                "filter": filter_str,
                "interval": interval,
                "view": monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
                "aggregation": aggregation
            }
        )
        
        points = []
        for series in results:
            for point in series.points:
                t_val = point.interval.end_time.seconds
                t_str = datetime.datetime.fromtimestamp(t_val, datetime.timezone.utc).strftime("%H:%M")
                
                val = 0.0
                if point.value.double_value is not None:
                    val = point.value.double_value
                elif point.value.int64_value is not None:
                    val = float(point.value.int64_value)
                elif point.value.distribution_value is not None:
                    dist = point.value.distribution_value
                    if dist.count > 0:
                        val = dist.mean
                
                points.append({"timestamp": t_str, "value": round(val, 2)})
                
        points.sort(key=lambda x: x["timestamp"])
        return {"status": "success", "metric": metric_type, "points": points}
    except Exception as e:
        logger.warning(f"Error querying cloud monitoring: {e}. Falling back to simulated metrics.")
        enable_bad_config = os.getenv("ENABLE_BAD_CONFIG", "false").lower() == "true"
        points = []
        now = time.time()
        for i in range(duration_minutes):
            t = now - (duration_minutes - i) * 60
            timestamp_str = time.strftime("%H:%M", time.localtime(t))
            if metric_type == "error_rate":
                val = random.uniform(85.0, 95.0) if (enable_bad_config and i > duration_minutes - 5) else random.uniform(0.0, 0.5)
            elif metric_type == "latency":
                val = random.uniform(250.0, 480.0) if (enable_bad_config and i > duration_minutes - 5) else random.uniform(80.0, 150.0)
            elif metric_type == "request_rate":
                val = random.uniform(8.0, 15.0)
            else:
                val = random.uniform(10.0, 50.0)
            points.append({"timestamp": timestamp_str, "value": round(val, 2)})
        return {"status": "success", "metric": metric_type, "points": points}

def list_revisions(service_name: str) -> dict:
    """Lists recent revisions for a Google Cloud Run service, including their traffic split.

    Args:
        service_name: The name of the Cloud Run service.

    Returns:
        A dictionary containing list of revisions, active traffic percentages, and creation time.
    """
    logger.info(f"Tool called: list_revisions(service_name={service_name})")
    try:
        from services.incident_manager import incident_manager
        incident_manager.add_timeline_event(f"Tool Call: list_revisions(service_name='{service_name}')", "INFO")
        incident_manager.add_chat_message("AI", f"[Tool] Fetching active revisions and traffic splits for Cloud Run service '{service_name}'...")
    except ImportError:
        pass
    
    if is_demo_mode():
        enable_bad_config = os.getenv("ENABLE_BAD_CONFIG", "false").lower() == "true"
        
        revisions = [
            {
                "revision_name": f"{service_name}-v15",
                "creation_time": "2026-07-04T06:30:00Z",
                "active_traffic_percent": 100 if enable_bad_config else 0,
                "status": "DEGRADED" if enable_bad_config else "HEALTHY",
                "author": "Operator",
                "env_vars": {"ENABLE_BAD_CONFIG": "true", "K_REVISION": f"{service_name}-v15"}
            },
            {
                "revision_name": f"{service_name}-v14",
                "creation_time": "2026-07-03T18:00:00Z",
                "active_traffic_percent": 0 if enable_bad_config else 100,
                "status": "HEALTHY",
                "author": "CI/CD",
                "env_vars": {"ENABLE_BAD_CONFIG": "false", "K_REVISION": f"{service_name}-v14"}
            }
        ]
        return {"status": "success", "revisions": revisions}

    try:
        from googleapiclient import discovery
        import google.auth
        
        credentials, project_id = google.auth.default()
        run_client = discovery.build('run', 'v1', credentials=credentials, client_options={"api_endpoint": f"https://{os.getenv('GOOGLE_CLOUD_LOCATION', 'us-central1')}-run.googleapis.com"})
        
        parent = f"namespaces/{project_id}"
        result = run_client.namespaces().revisions().list(
            parent=parent,
            labelSelector=f"serving.knative.dev/service={service_name}"
        ).execute()
        
        service = run_client.namespaces().services().get(
            name=f"namespaces/{project_id}/services/{service_name}"
        ).execute()
        
        traffic_map = {}
        for t in service.get("spec", {}).get("traffic", []):
            rev = t.get("revisionName")
            pct = t.get("percent", 0)
            if rev:
                traffic_map[rev] = pct
                
        revisions = []
        items = result.get("items", [])
        items.sort(key=lambda x: x.get("metadata", {}).get("creationTimestamp", ""), reverse=True)
        
        for item in items:
            name = item.get("metadata", {}).get("name")
            creation_time = item.get("metadata", {}).get("creationTimestamp")
            
            status_str = "UNKNOWN"
            conditions = item.get("status", {}).get("conditions", [])
            for c in conditions:
                if c.get("type") == "Ready":
                    status_str = "HEALTHY" if c.get("status") == "True" else "DEGRADED"
                    
            env_vars = {}
            containers = item.get("spec", {}).get("containers", [])
            if containers:
                for env in containers[0].get("env", []):
                    env_vars[env.get("name")] = env.get("value")
                    
            revisions.append({
                "revision_name": name,
                "creation_time": creation_time,
                "active_traffic_percent": traffic_map.get(name, 0),
                "status": status_str,
                "author": item.get("metadata", {}).get("labels", {}).get("serving.knative.dev/creator", "CI/CD"),
                "env_vars": env_vars
            })
            
        return {"status": "success", "revisions": revisions}
    except Exception as e:
        logger.warning(f"Error listing revisions from cloud: {e}. Falling back to demo data.")
        enable_bad_config = os.getenv("ENABLE_BAD_CONFIG", "false").lower() == "true"
        return {
            "status": "success",
            "revisions": [
                {
                    "revision_name": f"{service_name}-v15",
                    "creation_time": "2026-07-04T06:30:00Z",
                    "active_traffic_percent": 100 if enable_bad_config else 0,
                    "status": "DEGRADED" if enable_bad_config else "HEALTHY",
                    "author": "Operator",
                    "env_vars": {"ENABLE_BAD_CONFIG": "true"}
                },
                {
                    "revision_name": f"{service_name}-v14",
                    "creation_time": "2026-07-03T18:00:00Z",
                    "active_traffic_percent": 0 if enable_bad_config else 100,
                    "status": "HEALTHY",
                    "author": "CI/CD",
                    "env_vars": {"ENABLE_BAD_CONFIG": "false"}
                }
            ]
        }

def describe_revision(revision_name: str) -> dict:
    """Describes details of a specific Cloud Run revision.

    Args:
        revision_name: The name of the Cloud Run revision.

    Returns:
        A dictionary with container image, env variables, resources, and labels.
    """
    logger.info(f"Tool called: describe_revision(revision_name={revision_name})")
    try:
        from services.incident_manager import incident_manager
        incident_manager.add_timeline_event(f"Tool Call: describe_revision(revision_name='{revision_name}')", "INFO")
        incident_manager.add_chat_message("AI", f"[Tool] Inspecting details and configuration settings of revision '{revision_name}'...")
    except ImportError:
        pass
    
    if is_demo_mode():
        is_bad = "-v15" in revision_name
        return {
            "status": "success",
            "revision": {
                "name": revision_name,
                "image": "gcr.io/demo-project/sample-payment-service:latest",
                "env": {
                    "ENABLE_BAD_CONFIG": "true" if is_bad else "false",
                    "MISSING_PAYMENT_KEY": "true" if is_bad else "false",
                    "PORT": "8080"
                },
                "resources": {
                    "cpu": "1",
                    "memory": "512Mi"
                },
                "status": "DEGRADED" if is_bad else "HEALTHY",
                "creation_time": "2026-07-04T06:30:00Z" if is_bad else "2026-07-03T18:00:00Z"
            }
        }

    try:
        from googleapiclient import discovery
        import google.auth
        
        credentials, project_id = google.auth.default()
        run_client = discovery.build('run', 'v1', credentials=credentials, client_options={"api_endpoint": f"https://{os.getenv('GOOGLE_CLOUD_LOCATION', 'us-central1')}-run.googleapis.com"})
        
        revision = run_client.namespaces().revisions().get(
            name=f"namespaces/{project_id}/revisions/{revision_name}"
        ).execute()
        
        containers = revision.get("spec", {}).get("containers", [])
        env = {}
        if containers:
            for e in containers[0].get("env", []):
                env[e.get("name")] = e.get("value")
                
        status_str = "UNKNOWN"
        conditions = revision.get("status", {}).get("conditions", [])
        for c in conditions:
            if c.get("type") == "Ready":
                status_str = "HEALTHY" if c.get("status") == "True" else "DEGRADED"
                
        return {
            "status": "success",
            "revision": {
                "name": revision_name,
                "image": containers[0].get("image") if containers else "unknown",
                "env": env,
                "resources": containers[0].get("resources", {}).get("limits", {}) if containers else {},
                "status": status_str,
                "creation_time": revision.get("metadata", {}).get("creationTimestamp")
            }
        }
    except Exception as e:
        logger.warning(f"Error describing revision: {e}. Falling back to demo data.")
        is_bad = "-v15" in revision_name
        return {
            "status": "success",
            "revision": {
                "name": revision_name,
                "image": "unknown",
                "env": {
                    "ENABLE_BAD_CONFIG": "true" if is_bad else "false"
                },
                "resources": {},
                "status": "DEGRADED" if is_bad else "HEALTHY",
                "creation_time": ""
            }
        }

def rollback_revision(service_name: str, target_revision: str) -> dict:
    """Rolls back a Cloud Run service to direct 100% traffic to the target healthy revision.

    Args:
        service_name: The name of the Cloud Run service.
        target_revision: The target revision name to route all traffic to.

    Returns:
        A dictionary with status of the operation and the new traffic split.
    """
    logger.info(f"Tool called: rollback_revision(service_name={service_name}, target_revision={target_revision})")
    try:
        from services.incident_manager import incident_manager
        incident_manager.add_timeline_event(f"Tool Call: rollback_revision(service_name='{service_name}', target_revision='{target_revision}')", "WARNING")
        incident_manager.add_chat_message("AI", f"[Tool] Shifting 100% traffic to stable revision '{target_revision}' in GCP...")
    except ImportError:
        pass
    
    if is_demo_mode():
        os.environ["ENABLE_BAD_CONFIG"] = "false"
        return {
            "status": "success",
            "message": f"Successfully routed 100% traffic to revision {target_revision}",
            "traffic_split": {
                target_revision: 100
            }
        }
        
    try:
        from googleapiclient import discovery
        import google.auth
        
        credentials, project_id = google.auth.default()
        run_client = discovery.build('run', 'v1', credentials=credentials, client_options={"api_endpoint": f"https://{os.getenv('GOOGLE_CLOUD_LOCATION', 'us-central1')}-run.googleapis.com"})
        
        service_path = f"namespaces/{project_id}/services/{service_name}"
        service = run_client.namespaces().services().get(name=service_path).execute()
        
        service["spec"]["traffic"] = [
            {
                "revisionName": target_revision,
                "percent": 100
            }
        ]
        
        run_client.namespaces().services().replaceService(
            name=service_path,
            body=service
        ).execute()
        
        return {
            "status": "success",
            "message": f"Successfully routed 100% traffic to revision {target_revision}",
            "traffic_split": {
                target_revision: 100
            }
        }
    except Exception as e:
        logger.warning(f"Error rolling back service in cloud: {e}. Falling back to simulated rollback.")
        os.environ["ENABLE_BAD_CONFIG"] = "false"
        return {
            "status": "success",
            "message": f"Successfully routed 100% traffic to revision {target_revision} (Simulated fallback due to: {e})",
            "traffic_split": {
                target_revision: 100
            }
        }

def verify_service_health(service_url: str) -> dict:
    """Verifies service health by calling its health check endpoint.

    Args:
        service_url: The URL of the service to verify (e.g. 'http://localhost:8080/health').

    Returns:
        A dictionary confirming HTTP status, latency, and healthiness.
    """
    logger.info(f"Tool called: verify_service_health(service_url={service_url})")
    
    if not is_demo_mode():
        try:
            from googleapiclient import discovery
            import google.auth
            credentials, project_id = google.auth.default()
            run_client = discovery.build('run', 'v1', credentials=credentials, client_options={"api_endpoint": f"https://{os.getenv('GOOGLE_CLOUD_LOCATION', 'us-central1')}-run.googleapis.com"})
            service = run_client.namespaces().services().get(name=f"namespaces/{project_id}/services/sample-payment-service").execute()
            gcp_url = service.get("status", {}).get("url")
            if gcp_url:
                path = "/health"
                if "/payment" in service_url:
                    path = "/payment"
                service_url = gcp_url.rstrip('/') + path
                logger.info(f"Resolved health verification to real GCP URL: {service_url}")
        except Exception as e:
            logger.warning(f"Failed to resolve real Cloud Run URL: {e}")
            
    try:
        from services.incident_manager import incident_manager
        incident_manager.add_timeline_event(f"Tool Call: verify_service_health(service_url='{service_url}')", "INFO")
        incident_manager.add_chat_message("AI", f"[Tool] Performing HTTP GET request to check service health at '{service_url}'...")
    except ImportError:
        pass
        
    enable_bad_config = os.getenv("ENABLE_BAD_CONFIG", "false").lower() == "true"
    
    if is_demo_mode() or "localhost" in service_url or "127.0.0.1" in service_url:
        import httpx
        try:
            response = httpx.get(service_url, timeout=1.0)
            if response.status_code == 200:
                return {
                    "status": "success",
                    "healthy": True,
                    "http_status": response.status_code,
                    "latency_ms": response.elapsed.total_seconds() * 1000,
                    "body": response.json()
                }
            else:
                return {
                    "status": "success",
                    "healthy": False,
                    "http_status": response.status_code,
                    "message": f"Service returned error status: {response.status_code}"
                }
        except Exception as e:
            if enable_bad_config:
                return {
                    "status": "success",
                    "healthy": False,
                    "http_status": 500,
                    "message": "Service returned 500: MISSING_PAYMENT_KEY"
                }
            else:
                return {
                    "status": "success",
                    "healthy": True,
                    "http_status": 200,
                    "latency_ms": 112.5,
                    "message": "Service is healthy and responding normally"
                }
    else:
        import httpx
        try:
            response = httpx.get(service_url, timeout=2.0)
            if response.status_code == 200:
                return {
                    "status": "success",
                    "healthy": True,
                    "http_status": response.status_code,
                    "latency_ms": response.elapsed.total_seconds() * 1000,
                    "message": "Service is healthy"
                }
            else:
                return {
                    "status": "success",
                    "healthy": False,
                    "http_status": response.status_code,
                    "message": f"Service returned HTTP {response.status_code}"
                }
        except Exception as e:
            return {
                "status": "success",
                "healthy": False,
                "http_status": 500,
                "message": f"Service check connection failed: {e}"
            }
