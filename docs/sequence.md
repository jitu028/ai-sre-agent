# System Workflow Sequence

This document describes the execution sequence of an incident response workflow.

```mermaid
sequenceDiagram
    autonumber
    actor Operator as SRE Operator
    participant Target as Payment Service
    participant Mon as Cloud Monitoring
    participant Dash as SRE Dashboard (FastAPI)
    participant Agent as IncidentResponseAgent (ADK)
    participant Log as Cloud Logging
    participant Run as Cloud Run API

    %% Phase 1: Triggering the Incident
    Note over Target: Service degraded via bad config (v15)
    Target->>Mon: 500 Internal Server Errors logged
    Mon->>Mon: Evaluate Alert Rules (5xx > Threshold)
    Mon->>Dash: Trigger HTTP alert callback / Eventarc event

    %% Phase 2: Autonomous Investigation
    Dash->>Agent: Spawn/Run Agent for Triage
    Note over Agent: Triage Phase Started
    Agent->>Mon: read_metrics(service_name, 'error_rate')
    Mon-->>Agent: Returns 92.5% error rate metrics
    Agent->>Log: read_error_logs(service_name)
    Log-->>Agent: Returns ValueError: MISSING_PAYMENT_KEY tracebacks
    Agent->>Run: list_revisions(service_name)
    Run-->>Agent: Returns active revision: v15, previous revision: v14
    Agent->>Run: describe_revision(revision_name='v15')
    Run-->>Agent: Returns specification showing ENABLE_BAD_CONFIG=true

    %% Phase 3: Reasoning and Human-in-the-Loop Approval
    Agent->>Agent: Formulate RCA & Remediation Plan
    Agent->>Dash: Update Reasoning Panel (Evidence, Cause, Plan)
    Agent->>Dash: Post Chat Message: "v15 is degraded. Approve rollback to v14?"
    Dash->>Operator: Present Chat & Action Buttons
    Note over Operator: Operator reviews symptoms & evidence
    Operator->>Dash: Click "Approve Rollback" button
    Dash->>Agent: Resume Agent Run (Approve)

    %% Phase 4: Remediation
    Agent->>Run: rollback_revision(target_revision='v14')
    Run->>Run: Route 100% traffic to v14
    Run-->>Agent: Update Traffic split complete
    Agent->>Target: verify_service_health(http://.../health)
    Target-->>Agent: Returns HTTP 200 OK (Healthy)
    Agent->>Mon: read_metrics(service_name, 'error_rate')
    Mon-->>Agent: Returns 0% error rate (Normalized)

    %% Phase 5: Closing
    Agent->>Agent: Compile Post-Mortem Markdown Report
    Agent->>Dash: Close incident state & Save Report
    Dash->>Operator: Display complete Incident Report (Download available)
```

## Detailed Stage Analysis

1. **Triggering**: A deployment of a bad revision (represented by `sample-payment-service-v15` containing `ENABLE_BAD_CONFIG=true`) causes payment calls to fail. High rates of 500 errors trigger a Cloud Monitoring Alert policy.
2. **Alert Ingestion**: In production, the alert is sent to a Pub/Sub topic and then routed via Eventarc as a webhook call to `/api/trigger_incident` on the dashboard.
3. **Automated Triage**: The ADK agent executes a series of parallelized/sequential tool calls to collect telemetry. It reasons about this telemetry, discovering the `MISSING_PAYMENT_KEY` environment configuration problem.
4. **Human Gate**: The dashboard locks into the `Waiting Approval` state, displaying the operator chat message and the reasoning panel. The agent halts tool execution until input is provided.
5. **Remediation**: The operator clicks approve, releasing the agent to perform the update. It routes traffic back to `v14` and tests the health endpoint.
6. **Report Compilation**: The agent compiles the post-mortem document and pushes it to the dashboard. The dashboard saves the report, transitions to `Closed`, and updates the UI.
