FROM python:3.11-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev curl && \
    rm -rf /var/lib/apt/lists/*

# Copy benchmark apps and payloads
COPY benchmark/ /app/benchmark/

# Install Sanic + benchmark deps
RUN pip install --no-cache-dir \
    "sanic>=23.12,<24.0" \
    asyncpg orjson jinja2

EXPOSE 8001

# Sanic built-in server, 4 workers, no access log
CMD ["sanic", "benchmark.apps.sanic_app.main:app", \
     "--host", "0.0.0.0", "--port", "8001", "--workers", "4", \
     "--no-access-log"]
