#!/usr/bin/env bash
# Capture everything render_flight_promo.py reads.
#
# The rule this script exists to enforce is the same as the other two films':
# EVERYTHING ON SCREEN IS A REAL ARTEFACT. So the film is never re-rendered
# against numbers somebody typed -- it is re-rendered against the output of a
# run anyone can repeat.
#
# Needs a built workspace with the flight stack in it.
#
#   ./capture_flight_artifacts.sh [artifacts/flight]
set -euo pipefail

OUT="${1:-$(dirname "$0")/artifacts/flight}"
WS="${HIKO_WS:-$HOME/dev/hiko_ws}"
REPOS="${HIKO_REPO_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"

source /opt/ros/humble/setup.bash
source "$WS/install/setup.bash"
mkdir -p "$OUT/platforms"

# The catalogue itself, verbatim from what is installed -- the shipped
# definitions, not a copy somebody kept in step by hand.
cp "$WS/install/hiko_platform/share/hiko_platform/platforms/"*.yaml "$OUT/platforms/"

# All three airframes, closed-loop, in hikosim.
python3 "$REPOS/hiko-sim/tools/flight_check.py" --artifacts "$OUT"

# The same loop through Gazebo's solver, for the side-by-side.
python3 "$REPOS/hiko-sim/tools/gz_flight_check.py" --platform x500 --artifacts "$OUT"

echo "captured into $OUT"
