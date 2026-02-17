FROM python:3.11-slim

# Install Aquilia from local source first
COPY . /aquilia-src
RUN pip install --no-cache-dir /aquilia-src

# Install benchmark app deps
COPY benchmarks/framework-shootout/apps/aquilia_app/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY benchmarks/framework-shootout/apps/aquilia_app/ /app/
WORKDIR /app
RUN mkdir -p /app/.aquilia

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "4", "--loop", "uvloop", "--no-access-log"]
