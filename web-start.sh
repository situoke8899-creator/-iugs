#!/bin/sh
set -eu
: "${QUANT_ADMIN_TOKEN:?Set QUANT_ADMIN_TOKEN in deployment environment}"
mkdir -p /data
export QUANT_DB="${QUANT_DB:-/data/quantlab.db}"
export QUANT_WORKER=1
export QUANT_API_URL=http://127.0.0.1:8000
python -m uvicorn backend.api:app --host 127.0.0.1 --port 8000 &
API_PID=$!
trap 'kill "$API_PID" 2>/dev/null || true' EXIT INT TERM
exec streamlit run dashboard.py --server.address 0.0.0.0 --server.port "${PORT:-8501}" --server.headless true --browser.gatherUsageStats false
