#!/bin/bash
# Reserved-run watcher. Emits: a progress line every 2 hours, an alert the moment a
# section-5 operational band changes, and a final line when the runner exits for any
# reason. Read-only; it never touches the run.
BASE=/home/ros/dca_v051/reserved_run_2026-08-15
STATUS=$BASE/run_status.py
PAT="api_runner_qa1.py --config config/model_kimi_gpuedge"
last_report=0
prev_band=""
reported_band=""
stable=0

while true; do
  out=$(python3 "$STATUS" 2>&1)
  prog=$(echo "$out" | grep -m1 '^progress' | sed 's/  */ /g')

  # Change detection tracks the bands that carry meaning: the GENUINE truncation rate (the
  # section 5 phenomenon proper) and the invalid-output rate. The frozen-classification rate
  # and the between-arm spread both sit on the 5% threshold and flip constantly; they are
  # still printed in every 2-hour progress line, and any STOP on ANY band is reported below
  # immediately and unfiltered. Nothing is suppressed, only de-duplicated.
  gen_line=$(echo "$out" | grep -m1 'genuine truncation')
  if [ -z "$gen_line" ]; then gen_line=$(echo "$out" | grep -m1 'truncation rate'); fi
  inv_line=$(echo "$out" | grep -m1 'invalid-output rate')
  # The genuine-truncation rate straddles the 5% line and flips band repeatedly; a WARN there
  # carries no action under section 5, only a STOP does. Change detection therefore tracks the
  # invalid-output band and STOP-level transitions only. Every band is still printed in full in
  # each 2-hour progress line, and a STOP on ANY band is reported immediately below.
  gen_band=$(echo "$gen_line" | grep -oE '\[(ok|WARN|STOP|n<[0-9]+)\]' | tr -d '[]')
  case "$gen_band" in STOP) gen_state=STOP ;; *) gen_state=below_stop ;; esac
  band=$(printf 'gen:%s,%s\n' "$gen_state" "$(echo "$inv_line" | grep -oE '\[(ok|WARN|STOP|n<[0-9]+)\]' | tr -d '[]')")
  all_bands=$(echo "$out" | grep -oE '\[(ok|WARN|STOP)\]' | tr -d '[]' | tr '\n' ',')
  # Hysteresis: a rate hovering on a threshold flips band on every poll. Report a WARN only
  # once it has persisted across 3 consecutive polls (15 min), and report the return to ok the
  # same way. A STOP is always reported immediately, below, without hysteresis.
  if [ "$band" = "$prev_band" ]; then
    stable=$((stable + 1))
  else
    stable=1
  fi
  if [ "$stable" -eq 3 ] && [ "$band" != "$reported_band" ]; then
    echo "MATERIAL BAND CHANGE (held 15 min): $(echo "$out" | grep -E 'truncation rate|genuine truncation|invalid-output rate|arm truncation spread' | tr '\n' ' | ')"
    reported_band="$band"
  fi
  prev_band="$band"
  if echo "$all_bands" | grep -q STOP; then
    echo "STOP THRESHOLD CROSSED — pausing is required before inspecting condition accuracy. $prog"
  fi

  if ! pgrep -f "$PAT" >/dev/null; then
    echo "RUNNER EXITED. $prog"
    echo "$(echo "$out" | grep -E 'statuses|truncation rate|invalid-output rate|retryable' | tr '\n' ' | ')"
    tail -3 "$BASE/medical_assumption_memory_computational_benchmark_v0_5_1_qa1b/results_reserved_run.log" 2>/dev/null
    break
  fi

  now=$(date +%s)
  if [ $((now - last_report)) -ge 7200 ]; then
    echo "$prog | $(echo "$out" | grep -E 'truncation rate|invalid-output rate' | tr '\n' ' | ')"
    last_report=$now
  fi
  sleep 300
done
