# From Alerts to Actions: Autonomous Incident Response Agents on Google Cloud

This repository contains a complete, production-ready demo showcase for a conference session titled **"From Alerts to Actions: Building Autonomous Incident Response Agents on Google Cloud"**. It demonstrates an AI-powered Site Reliability Engineer (SRE) Agent built using the **Google Agent Development Kit (ADK)** and Gemini, capable of autonomously triaging and remediating Cloud Run service incidents.

---

## 📖 Table of Contents
1. [Project Overview](#-project-overview)
2. [Module Explanations](#-module-explanations)
3. [Quick Start (Local Dev)](#-quick-start-local-dev)
4. [Simulation Scripts](#-simulation-scripts)
5. [Documentation Index](#-documentation-index)

---

## 🚀 Project Overview

The project models a modern event-driven SRE troubleshooting workflow:
1. **Incident Trigger**: A faulty revision (`sample-payment-service-v15`) is deployed with a config bug. It throws HTTP 500 errors.
2. **Alerting**: Cloud Monitoring detects the spike in errors and fires an alert.
3. **Agent Activation**: The alert is received by the SRE Dashboard, spawning our ADK agent (`IncidentResponseAgent`).
4. **Triage & Diagnosis**: The agent inspects metrics and logs, identifies the root cause (`MISSING_PAYMENT_KEY`), and presents a diagnosis.
5. **Human Gate**: The agent pauses and asks the operator for approval to rollback via the dashboard chat window.
6. **Remediation & Report**: Upon approval, the agent executes the rollback to `v14`, verifies service recovery, and writes a post-mortem post.

---

## 📁 Module Explanations

Here is a breakdown of the codebase architecture:

- **`app.py`**: The entrypoint launcher. Starts a FastAPI server serving the dashboard page and the real-time Server-Sent Events (SSE) stream.
- **`agents/`**: Contains `incident_agent.py` which defines the Google ADK `IncidentResponseAgent` instructions, reasoning steps, and tool integrations.
- **`tools/`**: Contains `gcp_mcp.py` exposing Python tool wrappers for Cloud Logging, Cloud Monitoring, and Cloud Run APIs (or telemetry simulation fallbacks when run locally).
- **`services/`**: Contains `incident_manager.py` managing the incident state machine transitions, telemetry history generation, log streams, and chat history.
- **`models/`**: Contains `incident.py` declaring the Pydantic data models for status metrics, log frames, timelines, and chat items.
- **`dashboard/`**:
  - `templates/dashboard.html`: The Google Cloud Console-themed UI using HTMX, Tailwind, and Chart.js.
  - `api/dashboard.py`: Rest API endpoints managing approvals, rollbacks, and simulation inputs.
  - `websocket/events.py`: Serves the SSE stream pushing state updates every 2 seconds.
- **`sample-payment-service/`**: The target FastAPI microservice with a toggleable bug controlled via `ENABLE_BAD_CONFIG=true`.
- **`terraform/`**: Infrastructure-as-code files to deploy Artifact Registry, Cloud Run, Pub/Sub, and Cloud Monitoring alert policies in GCP.
- **`.github/workflows/`**: Continuous Integration and Deployment configurations to automate testing and Cloud Run deployments.

---

## ⚡ Quick Start (Local Dev)

You can run the entire session demo locally in a single command using Docker.

### Step 1: Clone and Set Env
Ensure Docker is running and set your Gemini API key (optional, default simulation mode runs without it):
```bash
export GOOGLE_API_KEY="your-api-key"
```

### Step 2: Spin Up Containers
```bash
docker-compose up --build
```

### Step 3: Open the Dashboard
Open your browser and navigate to:
👉 **[http://localhost:8000](http://localhost:8000)** (SRE Dashboard)

*The sample payment microservice is exposed at: [http://localhost:8080](http://localhost:8080)*

---

## 🛠️ Simulation Scripts

Several scripts are provided to simulate SRE operations locally:
- **`trigger_incident.py`**: Simulates a Cloud Monitoring alert trigger by transitioning the dashboard to `Incident Detected`.
- **`restore_service.py`**: Manual cleanup tool returning the dashboard to the `Healthy` baseline.
- **`simulate_http500.py`**: Sends continuous traffic transactions to the payment service, displaying successes or exception tracebacks.
- **`simulate_high_latency.py`**: Generates concurrent requests to stress-test the service response metrics.

---

## 📚 Documentation Index

To explore the architecture, sequence flows, and guides in detail, check the files in the `docs/` folder:

- **[System Architecture Diagram](file:///Users/jitendragupta/Documents/github-repo/ai-sre-agent/docs/architecture.md)**: Visualizes component interactions, alert channels, and data flow.
- **[Incident Execution Sequence](file:///Users/jitendragupta/Documents/github-repo/ai-sre-agent/docs/sequence.md)**: Standard time-sequence chart mapping operations from alert trigger to report generation.
- **[GCP Deployment & CI/CD Guide](file:///Users/jitendragupta/Documents/github-repo/ai-sre-agent/docs/deployment.md)**: Setup and deployment workflow for production GCP environments.
- **[GCP Project Setup Guide](file:///Users/jitendragupta/Documents/github-repo/ai-sre-agent/docs/prepare_project.md)**: Dynamic step-by-step walk-through for preparing your demo project `YOUR_GCP_PROJECT_ID`.
- **[Live Presenter Script](file:///Users/jitendragupta/Documents/github-repo/ai-sre-agent/docs/demo.md)**: Step-by-step walkthrough script for presenting this demo live on stage.
- **[Troubleshooting Reference](file:///Users/jitendragupta/Documents/github-repo/ai-sre-agent/docs/troubleshooting.md)**: Resolving port issues, import errors, or connection losses.
