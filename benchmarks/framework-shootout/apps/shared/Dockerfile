FROM python:3.11-slim

ARG APP_DIR
COPY ${APP_DIR}/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY ${APP_DIR}/ /app/
COPY shared/ /app/shared/
WORKDIR /app

# Default: overridden per-service in docker-compose
CMD ["python", "app.py"]
