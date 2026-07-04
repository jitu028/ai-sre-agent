# Troubleshooting Guide

This guide outlines common issues you might encounter while running the AI SRE Agent demo locally or in Google Cloud, along with steps to resolve them.

---

## 1. Local Run Issues

### Issue: Port 8000 or 8080 already in use
- **Symptoms**: Error message `[Errno 48] address already in use` when starting `app.py` or the payment service.
- **Solution**:
  1. Identify what process is holding the port:
     ```bash
     lsof -i :8000
     lsof -i :8080
     ```
  2. Kill the process:
     ```bash
     kill -9 <PID>
     ```
  3. Alternatively, run the dashboard on a different port:
     ```bash
     PORT=8001 python app.py
     ```

### Issue: SSE connection disconnects immediately
- **Symptoms**: Console log shows `SSE connection lost. Reconnecting...` repeatedly, and dashboard metrics don't update.
- **Solution**:
  1. Ensure the dashboard backend (`app.py`) is running.
  2. If using Docker Compose, check that both containers are attached to the `sre-network` and can ping each other.
  3. Ensure no local proxy or adblocker is intercepting Server-Sent Events requests.

### Issue: Python import errors or "App object not callable"
- **Symptoms**: `pytest` or `app.py` fails to launch due to namespace collisions.
- **Solution**:
  1. Ensure you have deleted the default-generated `app/` directory (created during `agents-cli init`). Having a folder named `app/` and a file named `app.py` at the root creates module conflicts.
  2. Make sure you are running in the correct virtual environment (`source .venv/bin/activate`).

---

## 2. Google Cloud Platform Issues

### Issue: `gcloud` returns authentication or quota errors
- **Symptoms**: `DefaultCredentialsError` or `PermissionDenied` when running GCP-based tool queries.
- **Solution**:
  1. Verify you are authenticated with Application Default Credentials:
     ```bash
     gcloud auth application-default login
     ```
  2. Ensure the active gcloud project matches the project you are using:
     ```bash
     gcloud config set project YOUR_PROJECT_ID
     ```
  3. Ensure the Service Account used by Cloud Run has the appropriate permissions:
     - `roles/monitoring.viewer`
     - `roles/logging.viewer`
     - `roles/run.developer`

### Issue: Eventarc trigger fails to invoke the Dashboard
- **Symptoms**: Alert triggered in Cloud Monitoring, but no incident appears on the dashboard.
- **Solution**:
  1. Verify the Eventarc trigger status:
     ```bash
     gcloud eventarc triggers describe sre-alert-trigger --location=us-central1
     ```
  2. Check Eventarc service account IAM policies. The service account executing the trigger needs `roles/run.invoker` on the dashboard Cloud Run service.
  3. Check the dashboard logs on Cloud Run to see if the `/api/trigger_incident` endpoint was reached and returned a 200 code.
