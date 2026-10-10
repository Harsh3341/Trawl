#!/usr/bin/env bash
# End-to-end walking-skeleton check: ingest a real GitHub repo's releases through
# the embedding service into Postgres, then ask a question via the secured gateway.
# Offline + deterministic: the embedding service runs in hash mode so no model
# download is needed and ingestion/gateway share identical vectors.
set -euo pipefail
cd "$(dirname "$0")/.."

REPO="${1:-pallets/flask}"
export DATABASE_URL="postgresql://trawl:trawl@localhost:5432/trawl"
export EMBEDDING_URL="http://localhost:8000"
export GATEWAY_DB="Host=localhost;Username=trawl;Password=trawl;Database=trawl"
export JWT_SECRET="dev-only-change-me-00000000000000000000000000000000"

EMB_PID=""; GW_PID=""
cleanup() { [ -n "$EMB_PID" ] && kill "$EMB_PID" 2>/dev/null || true;
            [ -n "$GW_PID" ] && kill "$GW_PID" 2>/dev/null || true; }
trap cleanup EXIT

wait_for() {  # wait_for <url> <label>
  for _ in $(seq 1 60); do
    curl -fsS "$1" >/dev/null 2>&1 && return 0
    sleep 1
  done
  echo "timed out waiting for $2 ($1)" >&2; exit 1
}

echo "1/4 starting embedding service (hash mode)..."
( cd services/embedding && . .venv/bin/activate && EMBEDDER=hash exec uvicorn app.main:app --port 8000 ) &
EMB_PID=$!
wait_for "$EMBEDDING_URL/health" "embedding service"

echo "2/4 ingesting $REPO ..."
( cd services/ingestion && . .venv/bin/activate && python -m app.pipeline "$REPO" )

echo "3/4 starting gateway..."
( cd gateway && exec dotnet run --project Trawl.Gateway --urls http://localhost:8080 ) &
GW_PID=$!
wait_for "http://localhost:8080/health" "gateway"

echo "4/4 asking a question..."
TOKEN=$(curl -fsS -X POST localhost:8080/token | python3 -c "import sys,json;print(json.load(sys.stdin)['token'])")
curl -fsS -X POST localhost:8080/ask \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"question":"what changed recently?","k":5}' | python3 -m json.tool
