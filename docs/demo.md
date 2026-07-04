# Live Demo Walkthrough

Use this guide to run a successful, live demonstration of the AI SRE Agent at conferences or team demos.

---

## 1. Prerequisites and Setup
1. Open the **Operations Center Dashboard** at [http://localhost:8000](http://localhost:8000).
2. Ensure both the Dashboard and the Payment Service are running (e.g. via `docker-compose up`).
3. Set your browser to **Light Theme** (default) or **Dark Theme** using the toggle button in the top right header depending on the projector contrast.
4. Verify the system shows `Healthy` baseline metrics:
   - Availability: **100%**
   - Latency: **~110ms**
   - HTTP Error Rate: **0%**
   - Active revision: **payment-service-v14**
   - Overall status badge: **Healthy** (pulsing green indicator)

---

## 2. Walkthrough Script

### Step 1: Deploy healthy service
*Explain to the audience:*
> "Here is our SRE Operations Center. Our microservice (`sample-payment-service`) is currently running revision `v14` in production. It is performing at 100% availability, serving payment requests within normal latencies (~110ms) and without any errors."

### Step 2: Deploy a faulty revision (Trigger the Incident)
*Action:* Click the red **"Trigger Incident"** button on the top right header, or run `python trigger_incident.py` from a terminal.
*Explain to the audience:*
> "We've just pushed a new version of our payment service, revision `v15`. However, there's a misconfigured environment flag `ENABLE_BAD_CONFIG=true` that was accidentally enabled. Let's see how our monitoring system and AI agent respond."

*Observe:*
- The status badge transitions to **Incident Detected** (pulsing red indicator).
- The Availability drops, Latency spikes, and HTTP Error Rate rises to >90%.
- Error log tracebacks (`ValueError: MISSING_PAYMENT_KEY`) start flooding the **Cloud Run Live Logs** console.
- The **Live Timeline** logs: `Cloud Monitoring Alert Triggered: High HTTP 500 Error Rate`.

### Step 3: Run the AI SRE Agent
*Observe:*
- The timeline shows: `AI Agent Started: IncidentResponseAgent initialized`.
- In the **ADK Chat Window**, the agent posts: `Incident detected on sample-payment-service. Commencing automated triage...`
- The timeline records the agent's actions: `Reading Logs`, `Analyzing Metrics`.
- The chat window updates as the agent reports:
  - "Querying Cloud Logging. Found multiple 500 error logs with message 'MISSING_PAYMENT_KEY'."
  - "Checking Cloud Run Revisions... Active revision is sample-payment-service-v15."

### Step 4: Show AI reasoning
*Observe:*
- The **Gemini SRE Reasoning** card appears, displaying the agent's real-time diagnostic output:
  - **Observed Symptoms**: Spiking errors, high latency.
  - **Evidence**: Environment variable `ENABLE_BAD_CONFIG=true` on v15.
  - **Root Cause**: Faulty configuration key enabled on v15, disabling payments.
  - **Recommended Action**: Rollback to revision v14.
  - **Confidence Score**: **98.5%**

*Explain to the audience:*
> "The SRE agent didn't just notice the error—it investigated it. It connected to Cloud Logging, identified the exception, checked the Cloud Run API to inspect the revision variables, and reasoned that rolling back to the previous healthy revision (`v14`) is the optimal way to restore service."

### Step 5: Operator Approval (Human-in-the-Loop)
*Observe:*
- The status transitions to **Waiting Approval**.
- The chat posts: `Recommendation: Rollback 100% traffic to previous healthy revision sample-payment-service-v14. Do you approve?`
- Action buttons **Approve Rollback** and **Reject Action** appear under the chat.

*Action:* Click **Approve Rollback**.
*Explain to the audience:*
> "To prevent accidental actions, our agent operates under a human-in-the-loop governance model. It presents its reasoning and awaits operator consent. I will now approve the rollback."

### Step 6: Rollback and Verification
*Observe:*
- The state transitions to **Executing** (rollback).
- The **Remediation Status** progress bar updates (0% -> 25% -> 50% -> 75% -> 100%).
- The current revision on the bottom panel shifts back to `payment-service-v14` (100% traffic).
- The logs show recovery as HTTP status returns to 200.
- State transitions to **Verification** and then **Recovered**.
- The agent posts in chat: `Service verification successful. Latency: 98ms, Error Rate: 0.0%. Incident resolved.`

### Step 7: Incident Report Generation (Post-Mortem)
*Observe:*
- The **Incident Post-Mortem** card appears containing a markdown report.
- The state badge changes to **Closed** (green).

*Action:* Click the **Copy** icon or **Download** icon on the post-mortem header.
*Explain to the audience:*
> "Once recovery is confirmed, the agent writes a complete Post-Mortem report documenting the timeline, root cause, metrics, and long-term recommendations. The incident is now officially Closed. The entire lifecycle—from alert to recovery—took less than a minute, with full auditability."

---

## 3. Demo Reset
To run the demo again for another session, simply click the **"Restore Baseline"** button in the header, or run `python restore_service.py`. The dashboard will immediately reset to the healthy `v14` state.
