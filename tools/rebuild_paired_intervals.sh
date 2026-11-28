#!/usr/bin/env bash
# Run from the repository root. Output files must be new.
set -eu
out=${1:?usage: bash tools/rebuild_paired_intervals.sh OUTPUT_DIRECTORY}
rebuild() {
  local name=$1 first=$2
  shift 2
  local args=()
  for report in "$@"; do
    args+=(--additional-report "results/$report.json")
  done
  python tools/paired_primary_intervals.py --report "results/$first.json" "${args[@]}" --output "$out/$name.json"
  diff --strip-trailing-cr -u "results/$name.json" "$out/$name.json"
}
rebuild hunyuan_i2v_intervals47 hunyuan_i2v_primary40 hunyuan_i2v_primary_040_043 hunyuan_i2v_primary_044_045 hunyuan_i2v_primary_slice291
rebuild hunyuan_t2v_intervals16 hunyuan_t2v_primary14 hunyuan_t2v_primary_slice014 hunyuan_t2v_paired_primary_015
rebuild wan22_i2v_intervals15 wan22_i2v_primary14 wan22_i2v_paired_primary_014
rebuild wan22_t2v_intervals15 wan22_t2v_primary14 wan22_t2v_paired_primary_014
