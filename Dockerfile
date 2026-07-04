FROM python:3.11-slim

WORKDIR /app

# Install uv to manage dependencies quickly
RUN pip install --no-cache-dir uv

# Copy dependency definitions
COPY pyproject.toml .
# Sync dependencies without compiling wheels locally if we can avoid it, or just use uv to install
RUN uv pip install --system .

# Copy agent and dashboard source code
COPY app.py .
COPY agents/ agents/
COPY tools/ tools/
COPY services/ services/
COPY models/ models/
COPY dashboard/ dashboard/

EXPOSE 8080

ENV PORT=8080
ENV DEMO_MODE=true
ENV GEMINI_MODEL=gemini-3.5-flash

CMD ["python", "app.py"]
