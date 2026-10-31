# Production Dockerfile for Report Navigator FastAPI Backend
FROM python:3.12-slim

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code & data
COPY . .

# Expose backend port
EXPOSE 8000

ENV HOST=0.0.0.0
ENV PORT=8000
ENV HF_HUB_OFFLINE=1
ENV TRANSFORMERS_OFFLINE=1

# Run API server
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
