FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml ./
COPY jacred-proxy/ ./jacred-proxy/

RUN pip install --no-cache-dir ".[production]"

EXPOSE 5002

# --- gunicorn (listen) ---
ENV HOST=0.0.0.0
ENV PORT=5002
ENV GUNICORN_WORKERS=2
ENV GUNICORN_TIMEOUT=30

# --- backend (override JACRED_BASE_URL in Docker; 127.0.0.1 is only the container itself) ---
# JACRED_APIKEY: set at runtime only (docker run -e / compose), not in the image
ENV JACRED_BASE_URL=http://127.0.0.1:9117
ENV JACRED_TIMEOUT=20
ENV JACRED_MERGE_V1=true
ENV JACRED_STRIP_YEAR=false
ENV JACRED_ENRICH_TITLES=true

# --- logging ---
ENV LOG_LEVEL=INFO
ENV LOG_FILE=/tmp/jacred_proxy.log

CMD ["sh", "-c", "exec gunicorn -b ${HOST}:${PORT} -w ${GUNICORN_WORKERS} --timeout ${GUNICORN_TIMEOUT} jacred_proxy.wsgi:app"]
