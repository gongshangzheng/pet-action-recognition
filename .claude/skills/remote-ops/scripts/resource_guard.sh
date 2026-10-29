#!/bin/bash
# Resource guard for anything we run on the remote server.
#
# Two jobs, both mandatory before/while executing code on pet:
#   preflight  -- is the machine free enough for this work to run alone?
#   run        -- run a command under a watchdog that kills it if it starts to
#                 eat the machine (CPU, RSS, GPU memory, wall time).
#
# The point is not politeness: a runaway job that pins every core or fills the
# GPU makes its own measurements meaningless and can take down someone else's
# session. Checking is therefore part of running the code, not an optional step.
#
# Runs on Linux only (reads /proc). Invoke from the remote checkout, e.g.
#   bash .agents/skills/remote-ops/scripts/preflight.sh
#   bash .agents/skills/remote-ops/scripts/remote_run.sh -- python3 bench.py
#
# Exit codes: 0 ok / 1 unusable environment / 2 gpu busy / 3 cpu, memory or disk pressure
#             / 4 watchdog killed the command / 5 command failed on its own

set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]:-$PWD}")" 2>/dev/null && pwd || pwd)"

usage() {
  cat <<'EOF'
usage:
  resource_guard.sh preflight [options]
  resource_guard.sh snapshot
  resource_guard.sh run [options] -- <command...>

preflight options:
  --gpu-index N        only consider this GPU (default: all)
  --gpu-mem-pct P      GPU memory percent that counts as busy (default 80)
  --gpu-util P         GPU utilisation percent that counts as busy (default 50)
  --max-load-per-core F  refuse when 1-minute load/core exceeds this (default 0.7)
  --min-free-mem-mb M  refuse when available memory is below this (default 8000)
  --min-free-disk-gb G refuse when free disk on the checkout is below this (default 5)
  --allow-busy-gpu     downgrade a busy GPU to a warning (only for our own idle server)
  --ignore-load        skip the load average check (for deliberate parallel runs)

run options:
  --gpu-index N        GPU whose memory is watched (default 1)
  --max-gpu-mem-pct P  kill above this GPU memory percent (default 90)
  --max-cpu-pct C      kill when the process tree exceeds this CPU percent (default 350)
  --max-rss-mb M       kill when the process tree RSS exceeds this (default 24000)
  --timeout-s T        kill after T seconds (default 3600)
  --interval S         sampling interval in seconds (default 5)
  --threads N          cap OMP/MKL/OpenMP threads (default 8)
  --log FILE           append samples here (default .run/guard/<timestamp>.log)
  --nice N             niceness for the command (default 10)
EOF
}

log() { printf '[guard %s] %s\n' "$(date +%H:%M:%S)" "$*"; }
die() { log "ABORT: $*"; exit "${2:-1}"; }

cpu_count() {
  getconf _NPROCESSORS_ONLN 2>/dev/null || nproc
}

mem_available_mb() {
  awk '/MemAvailable/ {print int($2/1024)}' /proc/meminfo
}

load_1m() {
  awk '{print $1}' /proc/loadavg
}

gpu_rows() {
  nvidia-smi --query-gpu=index,utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits 2>/dev/null
}

# Processes that actually hold device memory, per GPU index. Utilisation alone is
# not enough: a job can sit at 20% util while holding 8 GB, and a sampling window
# can catch it at 0%.
gpu_compute_apps() {
  local index=${1:-}
  local query="pid,process_name,used_memory"
  if [[ -n "$index" ]]; then
    nvidia-smi --id="$index" --query-compute-apps="$query" --format=csv,noheader,nounits 2>/dev/null
  else
    nvidia-smi --query-compute-apps="$query" --format=csv,noheader,nounits 2>/dev/null
  fi
}

# Total device memory (MiB) held by compute processes, for the given GPU or all.
gpu_compute_mib() {
  gpu_compute_apps "${1:-}" | awk -F, '{gsub(/ /,"",$3); if ($3 ~ /^[0-9]+$/) s+=$3} END{print s+0}'
}

snapshot() {
  echo "### GPU"
  gpu_rows | awk -F, '{printf "  GPU %s: util %s%%, mem %s/%s MiB (%.0f%%)\n", $1, $2, $3, $4, ($3*100)/$4}'
  echo "### GPU compute apps"
  local apps
  apps=$(nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader 2>/dev/null)
  if [[ -n "$apps" ]]; then echo "$apps" | sed 's/^/  /'; else echo "  none"; fi
  echo "### CPU / memory"
  printf '  load %s over %s cores; mem available %s MiB; swap used %s MiB\n' \
    "$(load_1m)" "$(cpu_count)" "$(mem_available_mb)" \
    "$(awk '/SwapTotal/{t=$2} /SwapFree/{f=$2} END{print int((t-f)/1024)}' /proc/meminfo)"
  echo "### disk (checkout)"
  df -h "$HERE/../../../.." | tail -1 | sed 's/^/  /'
  echo "### top CPU processes"
  ps -eo pid,pcpu,pmem,rss,comm --sort=-pcpu | head -6 | sed 's/^/  /'
}

preflight() {
  local gpu_index="" gpu_mem_pct=80 gpu_util=50 load_per_core=0.7 min_free_mem=8000
  local min_free_disk=5 allow_busy=0 ignore_load=0
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --gpu-index) gpu_index="$2"; shift 2 ;;
      --gpu-mem-pct) gpu_mem_pct="$2"; shift 2 ;;
      --gpu-util) gpu_util="$2"; shift 2 ;;
      --max-load-per-core) load_per_core="$2"; shift 2 ;;
      --min-free-mem-mb) min_free_mem="$2"; shift 2 ;;
      --min-free-disk-gb) min_free_disk="$2"; shift 2 ;;
      --allow-busy-gpu) allow_busy=1; shift ;;
      --ignore-load) ignore_load=1; shift ;;
      --help|-h) usage; exit 0 ;;
      *) die "unknown option $1" ;;
    esac
  done

  local rc=0
  snapshot

  echo "### verdict"
  local rows
  rows=$(gpu_rows)
  [[ -n "$rows" ]] || die "nvidia-smi unavailable: cannot confirm the GPU is free"

  local busy=0
  while IFS=, read -r idx util used total; do
    idx=$(echo "$idx" | tr -d ' '); util=$(echo "$util" | tr -d ' ')
    used=$(echo "$used" | tr -d ' '); total=$(echo "$total" | tr -d ' ')
    [[ -n "$gpu_index" && "$idx" != "$gpu_index" ]] && continue
    (( total > 0 )) || continue
    local mem_pct=$(( used * 100 / total ))
    local held
    held=$(gpu_compute_mib "$idx")
    if (( held >= 500 )); then
      log "  GPU $idx busy: ${held} MiB held by compute processes (util ${util}%, mem ${mem_pct}%)"
      busy=1
    elif (( util >= gpu_util || mem_pct >= gpu_mem_pct )); then
      log "  GPU $idx busy: util ${util}%, mem ${mem_pct}%"
      busy=1
    else
      log "  GPU $idx free: util ${util}%, mem ${mem_pct}%, held ${held} MiB"
    fi
  done <<< "$rows"

  if (( busy )); then
    if (( allow_busy )); then
      log "  busy GPU allowed by --allow-busy-gpu (confirm it is our own idle service)"
    else
      rc=2
    fi
  fi

  local cores load load_limit
  cores=$(cpu_count); load=$(load_1m)
  load_limit=$(awk -v c="$cores" -v f="$load_per_core" 'BEGIN{printf "%.2f", c*f}')
  if (( ignore_load )); then
    log "  load check skipped (--ignore-load)"
  elif awk -v l="$load" -v m="$load_limit" 'BEGIN{exit !(l > m)}'; then
    log "  CPU pressure: load $load > $load_limit (${load_per_core}/core); someone else is computing"
    rc=3
  else
    log "  load ok: $load <= $load_limit"
  fi

  local mem
  mem=$(mem_available_mb)
  if (( mem < min_free_mem )); then
    log "  memory pressure: ${mem} MiB available < ${min_free_mem} MiB"
    rc=3
  else
    log "  memory ok: ${mem} MiB available"
  fi

  local disk_gb
  disk_gb=$(df -Pk "$HERE/../../../.." | awk 'NR==2{int($4/1048576)}' )
  if [[ -n "$disk_gb" ]] && (( disk_gb < min_free_disk )); then
    log "  disk pressure: ${disk_gb} GB free < ${min_free_disk} GB"
    rc=3
  fi

  (( rc == 0 )) && log "PREFLIGHT OK"
  return $rc
}

tree_pids() {
  local root=$1
  echo "$root"
  ps -eo pid=,ppid= 2>/dev/null | awk -v root="$root" '
    { parent[$1]=$2 }
    END {
      changed=1
      while (changed) {
        changed=0
        for (p in parent) {
          if (!(p in seen) && (p == root || parent[p] in seen)) { seen[p]=1; print p; changed=1 }
        }
      }
    }'
}

tree_cpu_jiffies() {
  local total=0 pid stat
  for pid in $(tree_pids "$1"); do
    [[ -r /proc/$pid/stat ]] || continue
    stat=$(awk '{print $14+$15}' "/proc/$pid/stat" 2>/dev/null) || continue
    total=$(( total + ${stat:-0} ))
  done
  echo "$total"
}

tree_rss_mb() {
  local total=0 pid kb
  for pid in $(tree_pids "$1"); do
    [[ -r /proc/$pid/status ]] || continue
    kb=$(awk '/VmRSS/{print $2}' "/proc/$pid/status" 2>/dev/null)
    total=$(( total + ${kb:-0} ))
  done
  echo $(( total / 1024 ))
}

gpu_mem_pct() {
  local index=$1
  nvidia-smi --query-gpu=index,memory.used,memory.total --format=csv,noheader,nounits 2>/dev/null |
    awk -F, -v want="$index" '{gsub(/ /,"",$1); if ($1 == want) printf "%d", ($2*100)/$3}'
}

guard_run() {
  local gpu_index=0 max_gpu_pct=90 max_cpu_pct=350 max_rss_mb=24000 timeout_s=3600
  local interval=5 threads=8 log_file="" nice_level=10
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --gpu-index) gpu_index="$2"; shift 2 ;;
      --max-gpu-mem-pct) max_gpu_pct="$2"; shift 2 ;;
      --max-cpu-pct) max_cpu_pct="$2"; shift 2 ;;
      --max-rss-mb) max_rss_mb="$2"; shift 2 ;;
      --timeout-s) timeout_s="$2"; shift 2 ;;
      --interval) interval="$2"; shift 2 ;;
      --threads) threads="$2"; shift 2 ;;
      --log) log_file="$2"; shift 2 ;;
      --nice) nice_level="$2"; shift 2 ;;
      --help|-h) usage; exit 0 ;;
      --) shift; break ;;
      *) die "run: unknown option $1 (did you forget -- ?)" ;;
    esac
  done
  [[ $# -gt 0 ]] || die "run: no command given"

  local stamp
  stamp=$(date +%Y%m%d-%H%M%S)
  log_file=${log_file:-.run/guard/run-$stamp.log}
  mkdir -p "$(dirname "$log_file")"
  {
    echo "# guard run $stamp"
    echo "# command: $*"
    echo "# caps: gpu${gpu_index}<=${max_gpu_pct}% cpu<=${max_cpu_pct}% rss<=${max_rss_mb}MB timeout=${timeout_s}s threads=${threads}"
  } >> "$log_file"

  # Bounded threads and low priority: a benchmark must not take the machine down
  # even when it is the only thing running.
  export OMP_NUM_THREADS="$threads" MKL_NUM_THREADS="$threads" OPENBLAS_NUM_THREADS="$threads" \
         NUMEXPR_NUM_THREADS="$threads" TOKENIZERS_PARALLELISM=false
  export PYTORCH_CUDA_ALLOC_CONF="${PYTORCH_CUDA_ALLOC_CONF:-expandable_segments:True}"

  local start_s
  start_s=$(date +%s)
  nice -n "$nice_level" "$@" &
  local child=$!
  log "started pid $child (log $log_file)"

  local prev_jiffies prev_t now_jiffies cpu_pct rss gpu_pct elapsed
  prev_jiffies=$(tree_cpu_jiffies "$child"); prev_t=$(date +%s)
  local verdict=0 reason=""

  while kill -0 "$child" 2>/dev/null; do
    sleep "$interval"
    kill -0 "$child" 2>/dev/null || break
    now_jiffies=$(tree_cpu_jiffies "$child"); t=$(date +%s)
    local hz=100
    [[ -r /proc/self/stat ]] && hz=$(getconf CLK_TCK 2>/dev/null || echo 100)
    local dj=$(( now_jiffies - prev_jiffies )) dt=$(( t - prev_t ))
    (( dt > 0 )) || dt=1
    cpu_pct=$(( dj * 100 / (dt * hz) ))
    rss=$(tree_rss_mb "$child")
    gpu_pct=$(gpu_mem_pct "$gpu_index")
    elapsed=$(( t - start_s ))
    printf '%s pid=%s cpu=%s%% rss=%sMB gpu%s=%s%% elapsed=%ss\n' \
      "$(date +%H:%M:%S)" "$child" "$cpu_pct" "$rss" "$gpu_index" "${gpu_pct:-?}" "$elapsed" >> "$log_file"
    printf '[guard %s] cpu=%s%% rss=%sMB gpu%s=%s%% %ss\n' \
      "$(date +%H:%M:%S)" "$cpu_pct" "$rss" "$gpu_index" "${gpu_pct:-?}" "$elapsed"

    if (( cpu_pct > max_cpu_pct )); then verdict=4; reason="cpu ${cpu_pct}% > ${max_cpu_pct}%"; fi
    if (( rss > max_rss_mb )); then verdict=4; reason="rss ${rss}MB > ${max_rss_mb}MB"; fi
    if [[ -n "$gpu_pct" ]] && (( gpu_pct > max_gpu_pct )); then
      verdict=4; reason="gpu$gpu_index ${gpu_pct}% > ${max_gpu_pct}%"
    fi
    if (( elapsed > timeout_s )); then verdict=4; reason="timeout ${elapsed}s > ${timeout_s}s"; fi
    (( verdict == 0 )) || break

    prev_jiffies=$now_jiffies; prev_t=$t
  done

  if (( verdict == 4 )); then
    log "CAP BREACH ($reason): terminating $child"
    echo "CAP BREACH ($reason)" >> "$log_file"
    kill -TERM "$child" 2>/dev/null
    for _ in 1 2 3 4 5 6; do kill -0 "$child" 2>/dev/null || break; sleep 2; done
    if kill -0 "$child" 2>/dev/null; then
      log "still alive after TERM, sending KILL"
      pkill -KILL -P "$child" 2>/dev/null
      kill -KILL "$child" 2>/dev/null
    fi
    wait "$child" 2>/dev/null
    log "ended by guard; samples in $log_file"
    return 4
  fi

  wait "$child"
  local rc=$?
  log "command finished rc=$rc in $(( $(date +%s) - start_s ))s; samples in $log_file"
  (( rc == 0 )) && return 0 || return 5
}

case "${1:-}" in
  preflight) shift; preflight "$@" ;;
  snapshot) snapshot ;;
  run) shift; guard_run "$@" ;;
  --help|-h|"") usage; exit 0 ;;
  *) die "unknown subcommand ${1}" ;;
esac
