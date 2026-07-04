import asyncio
import json
from fastapi import Request
from sse_starlette.sse import EventSourceResponse
from services.incident_manager import incident_manager

async def event_generator(request: Request):
    """Generates SSE events with the current system state, logs, metrics, and timeline."""
    # Keep track of last state we sent to prevent unnecessary heavy payload updates
    last_state = None
    
    while True:
        # Check if client closed connection
        if await request.is_disconnected():
            break
            
        # Update metrics and logs in the background simulation
        await incident_manager.update_metrics()
        
        # Serialize the status
        status_data = {
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
            "has_report": incident_manager.incident_report is not None,
            "has_reasoning": incident_manager.ai_reasoning is not None,
        }
        
        # We send structured updates
        yield {
            "event": "system_update",
            "id": str(time_update_id()),
            "retry": 2000, # Retry every 2s
            "data": json.dumps(status_data)
        }
        
        # Periodically send a full state payload or list updates
        # To avoid polling on frontend, the UI can listen to these events
        yield {
            "event": "timeline_update",
            "data": json.dumps([e.model_dump() for e in incident_manager.timeline])
        }
        
        yield {
            "event": "chat_update",
            "data": json.dumps([c.model_dump() for c in incident_manager.chat_history])
        }
        
        yield {
            "event": "metrics_update",
            "data": json.dumps([m.model_dump() for m in incident_manager.metrics_history])
        }
        
        # Sleep for 2 seconds
        await asyncio.sleep(2)

def time_update_id() -> int:
    import time
    return int(time.time() * 1000)
