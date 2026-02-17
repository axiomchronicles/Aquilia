FROM python:3.11-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev curl && \
    rm -rf /var/lib/apt/lists/*

# Copy project
COPY . /app/

# Install Aquilia + benchmark deps
RUN pip install --no-cache-dir -e . && \
    pip install --no-cache-dir asyncpg uvicorn[standard] orjson jinja2 aiofiles

EXPOSE 8000

# Default: 4 workers, no access log
CMD ["uvicorn", "benchmark.apps.aquilia_app.main:app", \
     "--host", "0.0.0.0", "--port", "8000", "--workers", "4", \
     "--no-access-log", "--log-level", "warning"]
