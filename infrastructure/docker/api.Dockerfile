FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/packages/llm_sdk:/app/apps/api

WORKDIR /app

COPY packages/llm_sdk /app/packages/llm_sdk
COPY apps/api /app/apps/api

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -e /app/packages/llm_sdk -r /app/apps/api/requirements.txt

WORKDIR /app/apps/api

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
