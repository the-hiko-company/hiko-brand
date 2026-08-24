#!/usr/bin/env bash
# Capture everything render_operator_promo.py reads.
#
# Same rule as the other films: EVERYTHING ON SCREEN IS A REAL ARTEFACT, so the
# film is never re-rendered against numbers somebody typed -- it is re-rendered
# against the output of a run anyone can repeat.
#
# Two runs, and the second one matters as much as the first: the control arm
# flies the identical sequence with NOTHING pushed, which is the only way the
# film can say whether the climb belonged to the operator.
#
# Needs a built workspace with the flight stack in it.
set -euo pipefail

REPO="${REPO:-$HOME/dev/the-hiko-company}"
WS="${WS:-$HOME/dev/hiko_ws}"
OUT="$(cd "$(dirname "$0")" && pwd)/artifacts/operator"
DEMO="$REPO/hiko-gcs/tools/operator_flight_demo.py"

mkdir -p "$OUT"
# shellcheck disable=SC1091
source /opt/ros/humble/setup.bash
# shellcheck disable=SC1091
source "$WS/install/setup.bash"
export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-57}"

cleanup() {
  pkill -9 -f "[s]imulator_node"  2>/dev/null || true
  pkill -9 -f "[s]cenario.launch" 2>/dev/null || true
  sleep 2
}

echo "== the run =="
cleanup
HIKO_DEMO_ARTIFACTS="$OUT" timeout 300 python3 "$DEMO" || true

echo
echo "== the control arm, nothing pushed =="
cleanup
HIKO_DEMO_ARTIFACTS="$OUT" HIKO_DEMO_NO_PUSH=1 timeout 300 python3 "$DEMO" || true
cleanup

echo
ls -la "$OUT"
echo "now: python3 render_operator_promo.py --out hiko-operator.mp4"
