#!/usr/bin/env bash
set -euo pipefail

cd /opt/ruiquant

if [ ! -x ./venv/bin/python ]; then
  echo "venv missing: /opt/ruiquant/venv"
  exit 1
fi

pkill -f "streamlit run app.py" 2>/dev/null || true
sleep 1

./venv/bin/python scripts/health_check.py

nohup ./venv/bin/streamlit run app.py \
  --server.headless true \
  --server.address 0.0.0.0 \
  --server.port 8501 \
  > /tmp/ae.log 2>&1 &

echo "PID: $!"
sleep 2

if ! ps -p "$!" >/dev/null 2>&1; then
  echo "Streamlit exited immediately. Last log:"
  tail -80 /tmp/ae.log || true
  exit 1
fi

echo "AlphaEye started: http://47.102.106.104:8501"
