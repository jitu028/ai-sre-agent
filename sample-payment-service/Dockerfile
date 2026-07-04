FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

EXPOSE 8080

ENV PORT=8080
ENV K_SERVICE=sample-payment-service
ENV K_REVISION=sample-payment-service-v1
ENV GCP_REGION=us-central1
ENV ENABLE_BAD_CONFIG=false

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
