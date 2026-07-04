# Deployment Guide

This guide describes how to run this demo locally for testing and deploy it to a production Google Cloud Platform environment.

---

## 1. Prerequisites

Before starting, ensure you have the following installed:
- **Python**: Version 3.10 to 3.13 (Python 3.11 is recommended).
- **UV**: Astral's package manager (recommended for fast installation: `curl -LsSf https://astral.sh/uv/install.sh | sh`).
- **Docker & Docker Compose**: For containerized local development.
- **Google Cloud SDK (gcloud)**: Required for deploying to GCP.
- **Terraform**: Version 1.3+ (only if deploying infrastructure to GCP).

---

## 2. Local Deployment (Recommended for Quick Demos)

You can run the entire operations center and microservice locally using two methods.

### Method A: Docker Compose (Easiest)
This launches both containers inside a bridged network.

1. **Set your API Key** (optional, for real agent runs):
   ```bash
   export GOOGLE_API_KEY="your-api-key-from-ai-studio"
   ```
2. **Launch Services**:
   ```bash
   docker-compose up --build
   ```
3. **Access Services**:
   - Dashboard (Operations Center): [http://localhost:8000](http://localhost:8000)
   - Payment Service: [http://localhost:8080](http://localhost:8080)

### Method B: Native Running (Fastest iteration)
Runs python scripts directly on your local system using separate shell terminals.

1. **Sync dependencies**:
   ```bash
   uv sync
   ```
2. **Start the Payment Service** (Terminal 1):
   ```bash
   cd sample-payment-service
   # Activate local virtual environment
   source ../.venv/bin/activate
   uvicorn app:app --port 8080 --reload
   ```
3. **Start the SRE Agent Dashboard** (Terminal 2):
   ```bash
   # In workspace root
   source .venv/bin/activate
   export DEMO_MODE=true
   python app.py
   ```
4. **Access Dashboard**:
   Open [http://localhost:8000](http://localhost:8000) in your browser.

---

## 3. Google Cloud Platform Deployment

To deploy this demo to Google Cloud Run, follow these steps.

### Step 1: GCP Authentication
Log in to your GCP account and set active project:
```bash
gcloud auth login --update-adc
gcloud config set project YOUR_PROJECT_ID
```

### Step 2: Infrastructure Provisioning with Terraform
1. **Initialize Terraform**:
   ```bash
   cd terraform
   terraform init
   ```
2. **Preview and Apply changes**:
   ```bash
   terraform apply -var="project_id=YOUR_PROJECT_ID" -var="region=us-central1"
   ```
   *Note: This will provision the Artifact Registry, service accounts, Pub/Sub topic, monitoring channels, alert policy, and placeholder Cloud Run configurations.*

### Step 3: Build & Push Docker Images
We will build the container images locally and push them to the new Artifact Registry repository:

1. **Authenticate Docker with GCP**:
   ```bash
   gcloud auth configure-docker us-central1-docker.pkg.dev --quiet
   ```
2. **Build and Push the Payment Service**:
   ```bash
   docker build --platform linux/amd64 -t us-central1-docker.pkg.dev/YOUR_PROJECT_ID/ai-sre-demo-repo/sample-payment-service:v1 ./sample-payment-service
   docker push us-central1-docker.pkg.dev/YOUR_PROJECT_ID/ai-sre-demo-repo/sample-payment-service:v1
   ```
3. **Build and Push the Agent Dashboard**:
   ```bash
   docker build --platform linux/amd64 -t us-central1-docker.pkg.dev/YOUR_PROJECT_ID/ai-sre-demo-repo/ai-sre-agent-dashboard:latest .
   docker push us-central1-docker.pkg.dev/YOUR_PROJECT_ID/ai-sre-demo-repo/ai-sre-agent-dashboard:latest
   ```

### Step 4: Trigger Initial Deployments on Cloud Run
To update Cloud Run services with the pushed images:
```bash
# Deploy Payment Service
gcloud run deploy sample-payment-service \
  --image=us-central1-docker.pkg.dev/YOUR_PROJECT_ID/ai-sre-demo-repo/sample-payment-service:v1 \
  --region=us-central1 \
  --allow-unauthenticated

# Deploy Dashboard UI
gcloud run deploy ai-sre-agent-dashboard \
  --image=us-central1-docker.pkg.dev/YOUR_PROJECT_ID/ai-sre-demo-repo/ai-sre-agent-dashboard:latest \
  --region=us-central1 \
  --allow-unauthenticated \
  --set-env-vars="DEMO_MODE=false,GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID"
```

Once completed, the dashboard URL is printed by `gcloud` and can be accessed securely.
