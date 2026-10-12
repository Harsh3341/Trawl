FROM python:3.12-slim
WORKDIR /app
# Runtime deps (mirrors pyproject + the 'kafka' extra); python:3.12 guarantees wheels.
RUN pip install --no-cache-dir \
    "confluent-kafka>=2.3,<3" "httpx>=0.27" "psycopg[binary]>=3.1" "pgvector>=0.3"
COPY app ./app
ENV PYTHONPATH=/app
# Default role: embed-worker (continuous). Crawler overrides the command in compose.
CMD ["python", "-m", "app.embed_worker"]
