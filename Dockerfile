FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /root/.cache/huggingface /app/logs

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY ingest.py ingest_hf.py schema.sql ./

RUN mkdir -p /app/projects/content-engine /app/projects/lvyy /app/projects/rico /app/logs

ENV WATCHDOG_POLLING=true
ENV PYTHONUNBUFFERED=1
ENV HF_HOME=/root/.cache/huggingface

CMD ["python", "ingest_hf.py"]
