#!/usr/bin/env bash
# Keep WARP/SOCKS :40000 and one secretary watch up. Do not change default route.
# Real WARP proxy only. A dummy local SOCKS on :40000 looks "up" while MTProto still fails.
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/out"
LOG="$OUT/supervisor.log"
WATCH_LOG="$OUT/watch.log"
SOCKS_LOG="$OUT/socks.log"
PIDFILE="$OUT/supervisor.pid"
WATCH_PIDFILE="$ROOT/watch.pid"
SOCK="$ROOT/watch.sock"
VENV="$ROOT/.venv/bin/python"
export TG_HARNESS_ROLE=secretary
mkdir -p "$OUT"
echo $$ > "$PIDFILE"
log() { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $*" >> "$LOG"; }

socks_up() {
  ss -lnt 2>/dev/null | grep -q '127.0.0.1:40000' && return 0
  ss -lnt 2>/dev/null | grep -qE ':40000\b' && return 0
  return 1
}

ensure_socks() {
  if socks_up; then
    return 0
  fi
  log "socks 40000 down; restoring warp proxy"
  if command -v warp-cli >/dev/null 2>&1; then
    if ! pgrep -x warp-svc >/dev/null 2>&1; then
      if command -v sudo >/dev/null 2>&1; then
        sudo -n warp-svc >>"$SOCKS_LOG" 2>&1 &
        sleep 2
      fi
    fi
    warp-cli --accept-tos mode proxy >>"$SOCKS_LOG" 2>&1 || true
    warp-cli --accept-tos connect >>"$SOCKS_LOG" 2>&1 || true
    sleep 2
  fi
  if socks_up; then
    log "socks restored via warp-cli proxy"
    return 0
  fi
  log "FAILED to restore socks 40000 (need real WARP proxy, not a dummy local SOCKS)"
  return 1
}

python_watch_pids() {
  local f pid comm cmd
  for f in /proc/[0-9]*/cmdline; do
    cmd="$(tr '\0' ' ' < "$f" 2>/dev/null || true)"
    case "$cmd" in
      *"/tg-harness/.venv/bin/python -m tg_harness.cli watch"*|*" -m tg_harness.cli watch"*) ;;
      *) continue ;;
    esac
    pid="${f#/proc/}"; pid="${pid%/cmdline}"
    comm="$(cat "/proc/$pid/comm" 2>/dev/null || true)"
    case "$comm" in
      python*) echo "$pid" ;;
    esac
  done
}

watch_alive() {
  local pid=""
  if [[ -f "$WATCH_PIDFILE" ]]; then
    pid="$(cat "$WATCH_PIDFILE" 2>/dev/null || true)"
  fi
  if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
    comm="$(cat /proc/$pid/comm 2>/dev/null || true)"
    case "$comm" in
      python*)
        if [[ -S "$SOCK" ]]; then
          return 0
        fi
        ;;
    esac
  fi
  if [[ -n "$(python_watch_pids)" ]] && [[ -S "$SOCK" ]]; then
    return 0
  fi
  return 1
}

ensure_watch() {
  if watch_alive; then
    return 0
  fi
  if [[ -n "$(python_watch_pids)" ]]; then
    log "watch process exists but sock/pid unhealthy; not starting a second client"
    return 1
  fi
  if [[ -S "$SOCK" ]]; then
    rm -f "$SOCK" || true
  fi
  log "starting secretary watch"
  cd "$ROOT"
  nohup env TG_HARNESS_ROLE=secretary "$VENV" -m tg_harness.cli watch >>"$WATCH_LOG" 2>&1 &
  echo $! > "$WATCH_PIDFILE"
  sleep 2
  if watch_alive; then
    log "watch up pid=$(cat "$WATCH_PIDFILE")"
    return 0
  fi
  log "FAILED to start watch"
  return 1
}

log "supervisor start pid=$$ root=$ROOT"
while true; do
  ensure_socks || true
  ensure_watch || true
  sleep 15
done
