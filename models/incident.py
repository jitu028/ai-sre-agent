from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class TimelineEvent(BaseModel):
    timestamp: str
    message: str
    severity: str = "INFO" # INFO, WARNING, ERROR, SUCCESS

class LogEntry(BaseModel):
    timestamp: str
    severity: str # INFO, WARNING, ERROR
    message: str
    service: str
    revision: str
    region: str
    request_id: Optional[str] = None
    trace_id: Optional[str] = None

class SystemMetrics(BaseModel):
    timestamp: str
    request_rate: float # req/sec
    latency: float # ms
    cpu: float # %
    memory: float # %
    http_500_rate: float # %

class ChatMessage(BaseModel):
    id: str
    sender: str # AI, Operator, System
    text: str
    timestamp: str
    options: Optional[List[str]] = None # Approved, Rejected, etc.

class AIReasoning(BaseModel):
    observed_symptoms: str
    evidence: str
    reasoning: str
    confidence_score: float
    root_cause: str
    recommended_action: str
    estimated_recovery_time: str

class CloudRunInfo(BaseModel):
    current_revision: str
    previous_revision: str
    traffic_split: Dict[str, int]
    deployment_status: str # HEALTHY, DEGRADED, DEPLOYING

class IncidentReport(BaseModel):
    incident_id: str
    title: str
    status: str
    start_time: str
    end_time: Optional[str] = None
    timeline: List[str]
    root_cause: str
    remediation_actions: List[str]
    recovery_time_seconds: int
    recommendations: List[str]
    lessons_learned: List[str]
    markdown_content: str

class SystemStatus(BaseModel):
    availability: float # e.g. 99.9
    latency: float # ms
    error_rate: float # %
    revision: str
    status_label: str # HEALTHY, DEGRADED, INCIDENT_DETECTED, waiting_approval, rollback_executing, etc.
    status_severity: str # green, yellow, red
