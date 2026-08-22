#!/usr/bin/env bash
# Capture everything render_stack_promo.py reads.
#
# Same rule as the other films, and the reason all four capture scripts exist:
# EVERYTHING ON SCREEN IS A REAL ARTEFACT. The film is never re-rendered against
# numbers somebody typed -- it is re-rendered against the output of runs anyone
# can repeat, on this machine, from a built workspace.
#
#   ./capture_stack_artifacts.sh [artifacts/stack]
set -eo pipefail

OUT="${1:-$(dirname "$0")/artifacts/stack}"
WS="${HIKO_WS:-$HOME/dev/hiko_ws}"
REPOS="${HIKO_REPO_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"

source /opt/ros/humble/setup.bash
source "$WS/install/setup.bash"
set -u
export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-57}"

mkdir -p "$OUT"
ORACLE="$WS/install/hiko_mission_oracle/lib/hiko_mission_oracle/hiko_oracle"

# 1. The declarative statechart, verbatim from what is installed.
cp "$WS/install/hiko_hsm/share/hiko_hsm/charts/flight.xml" "$OUT/flight.xml"

# 2. Ten sorties through the real engine, and the oracle's verdict on them.
python3 "$REPOS/hiko-autonomy/tools/hsm_demo.py" --artifacts "$OUT/hsm" | tee "$OUT/hsm_demo.txt"
"$ORACLE" --states "$OUT/hsm/state_runs.jsonl" --json > "$OUT/state_oracle.json"

# 3. Twelve hundred missions through the real tree engine, and the table the
#    oracle exports from them.
bash "$REPOS/hiko-dashboard/tools/refresh_oracle_evidence.sh" > "$OUT/corpus.txt"
cp "$REPOS/hiko-dashboard/public/oracle/evidence.json" "$OUT/evidence.json"
cp "$REPOS/hiko-dashboard/public/oracle/trees.json" "$OUT/trees.json"

# 4. The closed loop the estimator could not fly until this month.
python3 "$REPOS/hiko-sim/tools/flight_check.py" --platform x500 --estimator \
  --artifacts "$OUT" --logdir "$OUT/logs"
mv "$OUT/x500.json" "$OUT/x500_estimator.json"

# 5. ... and the same loop swept to its edge through that estimator.
python3 "$REPOS/hiko-sim/tools/forge.py" "$REPOS/hiko-sim/forge/estimator_envelope.yaml" \
  --out "$OUT/estimator_envelope.json" | tee "$OUT/forge.txt"

# 6. What the whole workspace weighs.
( cd "$WS" && colcon test-result ) > "$OUT/tests.txt" 2>&1 || true
ls -d "$REPOS"/hiko-* > "$OUT/repos.txt"

echo "captured into $OUT"
