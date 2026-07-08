#!/usr/bin/env bash
source /opt/ros/jazzy/setup.bash
set -Eeuo pipefail

export RMW_IMPLEMENTATION="${RMW_IMPLEMENTATION:-rmw_zenoh_cpp}"
export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-42}"
export ZENOH_ROUTER_IP="${ZENOH_ROUTER_IP:-127.0.0.1}"
export ZENOH_ROUTER_PORT="${ZENOH_ROUTER_PORT:-7447}"

cd /workspace

python -m pip install -e ".[dev]"

rmw_log="/tmp/rmw_zenohd.log"
ros2 run rmw_zenoh_cpp rmw_zenohd >"${rmw_log}" 2>&1 &
rmw_pid=$!

cleanup() {
    local status=$?
    if kill -0 "${rmw_pid}" >/dev/null 2>&1; then
        kill "${rmw_pid}" >/dev/null 2>&1 || true
        wait "${rmw_pid}" >/dev/null 2>&1 || true
    fi
    echo "----- rmw_zenohd log -----"
    cat "${rmw_log}" || true
    exit "${status}"
}
trap cleanup EXIT

python - <<'PY'
import os
import socket
import time

host = os.environ["ZENOH_ROUTER_IP"]
port = int(os.environ["ZENOH_ROUTER_PORT"])
deadline = time.time() + 15.0
last_error = None
while time.time() < deadline:
    try:
        with socket.create_connection((host, port), timeout=0.2):
            print(f"rmw_zenohd is accepting TCP connections on {host}:{port}")
            break
    except OSError as exc:
        last_error = exc
        time.sleep(0.2)
else:
    raise SystemExit(f"rmw_zenohd did not open {host}:{port}: {last_error}")
PY

echo "== SDK unit and non-ROS integration tests =="
python -m pytest tests -q

echo "== SDK Zenoh integration tests with rmw_zenohd router =="
ZENOH_TEST_INTEGRATION=1 python -m pytest \
    tests/test_integration.py \
    tests/test_integration_service_queue_mode.py \
    -q

echo "== ROS 2 Jazzy rmw_zenoh_cpp interop tests =="
ZENOH_ROS2_RMW_ZENOH_INTEROP=1 python -m pytest \
    tests/test_ros2_rmw_zenoh_interop.py \
    -q -s
