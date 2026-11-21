#!/bin/sh

set -eu

PROJECT_DIR="/home/aza/Codigos_aza/App-aza/APP-AZA"
PYTHON="/home/aza/miniconda3/envs/neoapi/bin/python"
BAUMER_DIR="/opt/baumer-camera-explorer"
LOCK_FILE="/tmp/aza-analyzer.lock"

export GENICAM_GENTL64_PATH="$BAUMER_DIR/lib"
export LD_LIBRARY_PATH="$BAUMER_DIR/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

exec 9>"$LOCK_FILE"
if ! flock -n 9; then
    if command -v notify-send >/dev/null 2>&1; then
        notify-send "AZA Analyzer" "La aplicacion ya esta abierta."
    fi
    exit 0
fi

cd "$PROJECT_DIR"

# Warm up GigE discovery after boot without opening the camera stream.
# --no-rp-filter helps GigE Vision on Linux when the command has permission.
"$BAUMER_DIR/bin/gevipconfig" --no-rp-filter >/tmp/aza-gevipconfig.log 2>&1 || true

exec "$PYTHON" -m src.main
