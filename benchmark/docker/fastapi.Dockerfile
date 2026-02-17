FROM python:3.11-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev curl && \
    rm -rf /var/lib/apt/lists/*

# Copy benchmark apps and payloads
COPY benchmark/ /app/benchmark/

# Install FastAPI + benchmark deps
RUN pip install --no-cache-dir \
    "fastapi>=0.110,<1.0" \
    "uvicorn[standard]>=0.27" \
    asyncpg orjson jinja2 python-multipart aiofiles

EXPOSE 8002

# Uvicorn with 4 workers, no access log
CMD ["uvicorn", "benchmark.apps.fastapi_app.main:app", \
     "--host", "0.0.0.0", "--port", "8002", "--workers", "4", \
     "--no-access-log", "--log-level", "warning"]
