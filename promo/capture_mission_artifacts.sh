#!/usr/bin/env bash
# Capture one mission, end to end, for render_mission_promo.py.
#
# Same rule as the other films: EVERYTHING ON SCREEN IS A REAL ARTEFACT. This
# one is the strictest case, because the film's whole claim is that the
# prediction made BEFORE the mission flew matched what happened when it did --
# so the order these run in is the order the film shows, and nothing is
# back-filled.
#
#   ./capture_mission_artifacts.sh [artifacts/mission]
set -eo pipefail

OUT="${1:-$(dirname "$0")/artifacts/mission}"
WS="${HIKO_WS:-$HOME/dev/hiko_ws}"
REPOS="${HIKO_REPO_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"

source /opt/ros/humble/setup.bash
source "$WS/install/setup.bash"
set -u
export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-57}"

mkdir -p "$OUT"
CORPUS="$WS/install/hiko_mission/lib/hiko_mission/hiko_mission_corpus"
ORACLE="$WS/install/hiko_mission_oracle/lib/hiko_mission_oracle/hiko_oracle"
TEMPLATES="$WS/install/hiko_mission/share/hiko_mission/trees/templates"

# The mission, as a plan. Takeoff, out to the first tower, inspect it, on to the
# second, home, land.
STEPS=(--step takeoff --step fly:1 --step inspect:2 --step fly:3 --step rtl --step land)
# Leaf reliabilities. Takeoff=0.0 is not a pessimistic guess: hikosim reports
# supports_takeoff=false and refuses every native takeoff request, which is why
# the shipped template has a ClimbTo fallback behind it.
LEAVES=(--leaf Arm=0.97 --leaf Takeoff=0.0 --leaf ClimbTo=0.93 --leaf SetMode=0.995
        --leaf GotoWaypoint=0.88 --leaf Land=0.94 --leaf TrackTarget=0.82)

echo "== v1: compose the plan and fly it 400 times =="
"$CORPUS" --templates "$TEMPLATES" "${STEPS[@]}" --mission-id tower_survey \
  --runs 400 --seed 11 --out "$OUT/history_v1.jsonl" --tree-json "$OUT/tree_v1.json" \
  "${LEAVES[@]}" --context wind_mps=6 | tee "$OUT/flown_v1.txt"
"$ORACLE" --history "$OUT/history_v1.jsonl" --tree "$OUT/tree_v1.json" > "$OUT/score_v1.txt"
"$ORACLE" --evidence "$OUT/history_v1.jsonl" --tree "$OUT/tree_v1.json" > "$OUT/evidence_v1.json"
cat "$OUT/score_v1.txt"

echo
echo "== v2: two edits, from what the ranking said =="
# -L, and it matters. A workspace built with `colcon build --symlink-install`
# installs the templates as SYMLINKS BACK INTO THE SOURCE TREE, so a plain
# `cp -r` copies the links rather than the files -- and writing the v2
# templates into the "copy" then overwrites the shipped ones in the repository.
# It did, once, and the capture silently scored v1 with v2's tree.
rm -rf "$OUT/templates_v2" && cp -rL "$TEMPLATES" "$OUT/templates_v2"
cat > "$OUT/templates_v2/fly.xml" <<'XML'
<?xml version="1.0"?>
<!-- v2: the leg is retried. A waypoint that was not reached is not a mission
     that has to end, and a leg is the cheapest thing in a mission to attempt
     twice. -->
<root>
  <BehaviorTree id="fly">
    <Retry num_attempts="3">
      <Timeout msec="180000">
        <GotoWaypoint target="{arg0}" acceptance_radius="1.0"/>
      </Timeout>
    </Retry>
  </BehaviorTree>
</root>
XML
cat > "$OUT/templates_v2/inspect.xml" <<'XML'
<?xml version="1.0"?>
<!-- v2: the track is retried, and losing it does not end the mission. An
     inspection that cannot be completed should cost the inspection, not the
     sortie. -->
<root>
  <BehaviorTree id="inspect">
    <Sequence name="inspect_step">
      <WaitFor seconds="2.0"/>
      <Fallback name="inspect_or_move_on">
        <Retry num_attempts="2">
          <TrackTarget track_id="{arg1}" timeout_lost_s="15.0"/>
        </Retry>
        <AlwaysSuccess/>
      </Fallback>
    </Sequence>
  </BehaviorTree>
</root>
XML

# Compose v2's shape WITHOUT flying it, so the prediction below is genuinely a
# prediction: one run, only to dump the tree.
"$CORPUS" --templates "$OUT/templates_v2" "${STEPS[@]}" --mission-id tower_survey_v2 \
  --runs 1 --out /dev/null --tree-json "$OUT/tree_v2.json" "${LEAVES[@]}" >/dev/null

echo "-- v2 predicted, from v1's evidence, before it has been flown --"
"$ORACLE" --history "$OUT/history_v1.jsonl" --tree "$OUT/tree_v2.json" \
  > "$OUT/predicted_v2.txt"
"$ORACLE" --evidence "$OUT/history_v1.jsonl" --tree "$OUT/tree_v2.json" \
  > "$OUT/predicted_v2.json"
head -1 "$OUT/predicted_v2.txt"

echo
echo "== then fly v2 400 times and see =="
"$CORPUS" --templates "$OUT/templates_v2" "${STEPS[@]}" --mission-id tower_survey_v2 \
  --runs 400 --seed 11 --out "$OUT/history_v2.jsonl" "${LEAVES[@]}" \
  --context wind_mps=6 | tee "$OUT/flown_v2.txt"
"$ORACLE" --history "$OUT/history_v2.jsonl" --tree "$OUT/tree_v2.json" > "$OUT/score_v2.txt"

echo
echo "== execution: the real thing, closed-loop, recorded =="
#
# REPEATS=4, and the film shows all four outcomes.
#
# This stage is not reproducible, and pretending otherwise would be the one
# dishonest frame in four films. On a clean ROS domain, with identical
# arguments, this mission produces 0.75 m of mean estimator error on one run
# and several hundred metres on the next: the magnetometer's innovation gate
# cascades, nothing else observes yaw, and once heading is thirty degrees wrong
# it stays wrong and the vehicle flies the error. See
# hiko-gnc/docs/estimator.md#the-magnetometer-cascade.
#
# So the capture flies it several times and keeps every outcome. The film uses
# a successful sortie for the trajectory and states the spread on screen.
rm -rf "$OUT/flight" "$OUT/attempts"
mkdir -p "$OUT/attempts"
REPEATS="${REPEATS:-4}"
for i in $(seq 1 "$REPEATS"); do
  python3 "$REPOS/hiko-sim/tools/mission_run.py" \
    --waypoints "0,0,-20; 40,0,-20; 40,30,-25; 0,0,-20" \
    --artifacts "$OUT/attempts/$i" --wind 4.0 --mission-id "tower_survey_$i" \
    > "$OUT/attempts/$i.txt" 2>&1 || true
  sleep 5
done
# The one the film flies, recorded properly, chosen as the first that held.
BEST=""
for i in $(seq 1 "$REPEATS"); do
  if grep -q '"outcome": "SUCCESS"' "$OUT/attempts/$i/mission_run.json" 2>/dev/null; then
    BEST="$i"; break
  fi
done
if [ -z "$BEST" ]; then
  echo "no attempt held; the film cannot show a successful sortie from this capture" >&2
  exit 1
fi
python3 "$REPOS/hiko-sim/tools/mission_run.py" \
  --waypoints "0,0,-20; 40,0,-20; 40,30,-25; 0,0,-20" \
  --artifacts "$OUT/flight" --wind 4.0 --record --mission-id tower_survey \
  | tee "$OUT/flight.txt" || true
if [ ! -f "$OUT/flight/mission_run.json" ] || \
   ! grep -q '"outcome": "SUCCESS"' "$OUT/flight/mission_run.json"; then
  echo "the recorded run did not hold; reusing attempt $BEST for the trajectory" >&2
  cp "$OUT/attempts/$BEST/mission_run.json" "$OUT/flight/mission_run.json"
  cp "$OUT/attempts/$BEST/mission_record.jsonl" "$OUT/flight/mission_record.jsonl"
fi
python3 - "$OUT" "$REPEATS" <<'PY2'
import json, os, sys
out, repeats = sys.argv[1], int(sys.argv[2])
rows = []
for i in range(1, repeats + 1):
    path = os.path.join(out, "attempts", str(i), "mission_run.json")
    if os.path.exists(path):
        r = json.load(open(path))
        rows.append({"run": i, "outcome": r["outcome"],
                     "legs_reached": r["metrics"]["legs_reached"],
                     "legs_total": r["metrics"]["legs_total"],
                     "estimator_error_mean_m": r["metrics"]["estimator_error_mean_m"]})
json.dump(rows, open(os.path.join(out, "attempts.json"), "w"), indent=1)
held = sum(1 for r in rows if r["outcome"] == "SUCCESS")
print(f"{held}/{len(rows)} attempts held")
PY2

# The session manifest, lifted out so the renderer does not have to guess a uuid.
python3 - "$OUT" <<'PY'
import json, os, sys
out = sys.argv[1]
root = os.path.join(out, "flight", "recordings")
sessions = sorted((os.path.join(root, d) for d in os.listdir(root)),
                  key=os.path.getmtime)
session = sessions[-1]
manifest = json.load(open(os.path.join(session, "manifest.json")))
manifest["_on_disk_bytes"] = sum(
    os.path.getsize(os.path.join(r, f))
    for r, _, files in os.walk(session) for f in files)
json.dump(manifest, open(os.path.join(out, "session.json"), "w"), indent=1)
print(f"session {manifest['session_id'][:8]}: "
      f"{len(manifest['topics'])} topics, {manifest['total_bytes'] / 1e6:.1f} MB serialized")
PY

echo
echo "== post-analysis: the flight becomes evidence =="
cp "$OUT/flight/mission_record.jsonl" "$OUT/mission_record.jsonl"
cat "$OUT/mission_record.jsonl"

echo "captured into $OUT"
