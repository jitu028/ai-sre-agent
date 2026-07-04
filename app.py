import os
import uvicorn
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from dashboard.api.dashboard import router as api_router
from dashboard.websocket.events import event_generator
from sse_starlette.sse import EventSourceResponse

# Initialize app
app = FastAPI(
    title="AI SRE Agent Operations Center",
    description="Powered by Google ADK, Gemini, and MCP",
    version="1.0.0"
)

# Setup templates
templates = Jinja2Templates(directory="dashboard/templates")

# Include API Router
app.include_router(api_router)

@app.get("/", response_class=HTMLResponse)
async def get_dashboard(request: Request):
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "gcp-adk-demo-028")
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    gemini_model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
    return templates.TemplateResponse(
        "dashboard.html", 
        {
            "request": request,
            "project_id": project_id,
            "location": location,
            "gemini_model": gemini_model
        }
    )

@app.get("/api/events")
async def sse_events(request: Request):
    """Real-time Server-Sent Events stream for status, metrics, logs, and timelines."""
    return EventSourceResponse(event_generator(request))

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    # In production/demo, we run uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)
