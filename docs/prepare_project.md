# How-To: Prepare GCP Project gcp-adk-demo-028 for the Demo

This guide explains how to prepare the Google Cloud Platform (GCP) project `gcp-adk-demo-028` for the live SRE Agent demo.

---

## Step 1: Authenticate and Set Project
Run the following commands in your local terminal to log in to Google Cloud and point your environment to the project:

```bash
# 1. Log in to gcloud CLI
gcloud auth login

# 2. Authenticate Application Default Credentials (ADC) for Python/ADK SDK tools
gcloud auth application-default login

# 3. Set the active project to gcp-adk-demo-028
gcloud config set project gcp-adk-demo-028
```

---

## Step 2: Enable Required GCP APIs
Enable all API services required for Eventarc, Cloud Run, Pub/Sub, and monitoring telemetry:

```bash
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  eventarc.googleapis.com \
  pubsub.googleapis.com \
  logging.googleapis.com \
  monitoring.googleapis.com \
  cloudbuild.googleapis.com
```

---

## Step 3: Provision Resources via Terraform
We have pre-configured `terraform/terraform.tfvars` with the project ID `gcp-adk-demo-028`.

1. Navigate to the terraform directory:
   ```bash
   cd terraform
   ```
2. Initialize Terraform:
   ```bash
   terraform init
   ```
3. Apply the configuration to create the Artifact Registry repo, Pub/Sub channels, eventarc triggers, service accounts, and alert rules:
   ```bash
   terraform apply -auto-approve
   ```

---

## Step 4: Build & Deploy Container Images

### 1. Authenticate Docker with the new registry
```bash
gcloud auth configure-docker us-central1-docker.pkg.dev --quiet
```

### 2. Build and Deploy Payment Service (Target)
```bash
# Build and Push
docker build --platform linux/amd64 -t us-central1-docker.pkg.dev/gcp-adk-demo-028/ai-sre-demo-repo/sample-payment-service:v1 ./sample-payment-service
docker push us-central1-docker.pkg.dev/gcp-adk-demo-028/ai-sre-demo-repo/sample-payment-service:v1

# Deploy to Cloud Run
gcloud run deploy sample-payment-service \
  --image=us-central1-docker.pkg.dev/gcp-adk-demo-028/ai-sre-demo-repo/sample-payment-service:v1 \
  --region=us-central1 \
  --allow-unauthenticated
```

### 3. Build and Deploy SRE Agent Dashboard
```bash
# Build and Push
docker build --platform linux/amd64 -t us-central1-docker.pkg.dev/gcp-adk-demo-028/ai-sre-demo-repo/ai-sre-agent-dashboard:latest .
docker push us-central1-docker.pkg.dev/gcp-adk-demo-028/ai-sre-demo-repo/ai-sre-agent-dashboard:latest

# Deploy to Cloud Run
gcloud run deploy ai-sre-agent-dashboard \
  --image=us-central1-docker.pkg.dev/gcp-adk-demo-028/ai-sre-demo-repo/ai-sre-agent-dashboard:latest \
  --region=us-central1 \
  --allow-unauthenticated \
  --set-env-vars="DEMO_MODE=false,GOOGLE_CLOUD_PROJECT=gcp-adk-demo-028,GEMINI_MODEL=gemini-3.5-flash"
```

Once deployed, the `ai-sre-agent-dashboard` URL is printed in the terminal. Open this URL to load the live Operations Center!

---

## Step 5: Verification & Setup Checks
- **Alert Ingestion**: Verify the alert policy is active by visiting the Cloud Monitoring Alerting console.
- **Log Routing**: Trigger a 500 error manually using `/payment` on the payment service and confirm the structured JSON log reaches Cloud Logging.
