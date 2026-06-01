FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY services/agent-api /app/services/agent-api

RUN python3 -m pip install --no-cache-dir /app/services/agent-api

EXPOSE 8200 8201

CMD ["python3", "services/agent-api/server.py"]
