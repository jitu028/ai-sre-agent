import os
from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from services.incident_manager import incident_manager

router = APIRouter(prefix="/api")

class ChatInput(BaseModel):
    text: str

class RejectInput(BaseModel):
    feedback: str

@router.get("/status")
async def get_status() -> Dict[str, Any]:
    return {
        "state": incident_manager.state,
        "availability": incident_manager.availability,
        "latency": incident_manager.latency,
        "error_rate": incident_manager.error_rate,
        "current_revision": incident_manager.current_revision,
        "previous_revision": incident_manager.previous_revision,
        "traffic_split": incident_manager.traffic_split,
        "deployment_status": incident_manager.deployment_status,
        "remediation_progress": incident_manager.remediation_progress,
        "remediation_step": incident_manager.remediation_step,
        "active_incident_id": incident_manager.active_incident_id,
    }

@router.get("/logs")
async def get_logs(severity: Optional[str] = None) -> List[Dict[str, Any]]:
    filtered_logs = []
    for log in incident_manager.logs:
        if severity:
            if log.severity.upper() == severity.upper():
                filtered_logs.append(log.model_dump())
        else:
            filtered_logs.append(log.model_dump())
    return filtered_logs

@router.get("/metrics")
async def get_metrics() -> List[Dict[str, Any]]:
    return [m.model_dump() for m in incident_manager.metrics_history]

@router.get("/chat")
async def get_chat() -> List[Dict[str, Any]]:
    return [c.model_dump() for c in incident_manager.chat_history]

@router.post("/chat")
async def send_chat_message(user_input: ChatInput) -> Dict[str, Any]:
    text = user_input.text.strip()
    incident_manager.add_chat_message("Operator", text)
    
    # Process inputs if we are waiting for approval and user typed Approve/Reject
    if incident_manager.state == "Waiting Approval":
        if "approve" in text.lower() or "yes" in text.lower() or "y" == text.lower():
            await incident_manager.approve_rollback()
        elif "reject" in text.lower() or "no" in text.lower() or "n" == text.lower():
            await incident_manager.reject_rollback(feedback="Rejected via chat input")
        else:
            incident_manager.add_chat_message("AI", "I am currently waiting for your approval to rollback. Please type 'Approve' or 'Reject', or use the buttons below.")
    else:
        # Simple agent routing simulation/integration
        # If incident is active but not waiting for approval
        if incident_manager.state in ["Incident Detected", "Investigation"]:
            if any(word in text.lower() for word in ["fix", "rollback", "remediate", "approve", "go ahead"]):
                incident_manager.state = "Executing"
                incident_manager.remediation_progress = 0
                incident_manager.remediation_step = "Executing Rollback"
                incident_manager.add_timeline_event("Remediation Triggered via Chat", "INFO")
                incident_manager.add_chat_message("AI", "Understood! Since you've instructed me to fix it, I am commencing the automated remediation rollback flow now...")
                import asyncio
                asyncio.create_task(incident_manager.execute_rollback_flow())
            else:
                incident_manager.add_chat_message("AI", "Understood. I am investigating the current logs and metrics to pinpoint the root cause.")
        else:
            incident_manager.add_chat_message("AI", "I am monitoring the system. No active incident detected. You can trigger one using the 'Trigger Incident' button.")
            
    return {"status": "success"}

@router.get("/incident")
async def get_incident() -> Dict[str, Any]:
    if not incident_manager.active_incident_id:
        return {"active": False}
        
    reasoning_data = None
    if incident_manager.ai_reasoning:
        reasoning_data = incident_manager.ai_reasoning.model_dump()
        
    return {
        "active": True,
        "incident_id": incident_manager.active_incident_id,
        "state": incident_manager.state,
        "ai_reasoning": reasoning_data
    }

@router.get("/report")
async def get_report() -> Dict[str, Any]:
    if not incident_manager.incident_report:
        return {"report_available": False, "message": "No incident report generated yet."}
    return {
        "report_available": True,
        "report": incident_manager.incident_report.model_dump()
    }

@router.post("/approve")
async def approve_incident() -> Dict[str, Any]:
    if incident_manager.state != "Waiting Approval":
        raise HTTPException(status_code=400, detail="No pending incident approval.")
    await incident_manager.approve_rollback()
    return {"status": "success", "message": "Rollback approved and execution initiated."}

@router.post("/reject")
async def reject_incident(reject_data: Optional[RejectInput] = None) -> Dict[str, Any]:
    if incident_manager.state != "Waiting Approval":
        raise HTTPException(status_code=400, detail="No pending incident approval.")
    feedback = reject_data.feedback if reject_data else "Rollback rejected by operator."
    await incident_manager.reject_rollback(feedback=feedback)
    return {"status": "success", "message": "Rollback rejected."}

@router.post("/rollback")
async def trigger_manual_rollback() -> Dict[str, Any]:
    # Force manual rollback (skips approval if operator triggers it manually)
    incident_manager.state = "Executing"
    incident_manager.remediation_progress = 0
    incident_manager.remediation_step = "Executing Rollback"
    incident_manager.add_timeline_event("Manual Rollback Triggered by Operator", "WARNING")
    incident_manager.add_chat_message("System", "Manual rollback initiated by Operator.")
    
    # Run the restoration flow
    import asyncio
    asyncio.create_task(incident_manager.execute_rollback_flow())
    return {"status": "success"}

@router.post("/trigger_incident")
async def trigger_simulation_incident() -> Dict[str, Any]:
    if incident_manager.state != "Healthy":
        return {"status": "ignored", "message": "System is already in incident state."}
    await incident_manager.trigger_incident()
    return {"status": "success", "message": "Incident simulation triggered."}

@router.post("/restore")
async def restore_service() -> Dict[str, Any]:
    await incident_manager.restore_service()
    return {"status": "success", "message": "System restored to Healthy."}
