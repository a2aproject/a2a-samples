#!/usr/bin/env bash
# Records the fleet demo: opencode agents serve a crowd of users while a
# server crashes, a server joins and a server drains. Writes demo/demo.cast
# and, with agg installed, demo/demo.gif.
#
# Needs Docker, tmux, asciinema 3, agg and GEMINI_API_KEY. Run from anywhere:
#   GEMINI_API_KEY=... demo/record.sh [--no-record] [--users N]

set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$DIR/demo"
COLS=150
ROWS=50
USERS=8
RECORD=1
while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-record) RECORD=""; shift ;;
    --users) USERS="$2"; shift 2 ;;
    *) echo "usage: demo/record.sh [--no-record] [--users N]" >&2; exit 2 ;;
  esac
done

: "${GEMINI_API_KEY:?set GEMINI_API_KEY}"
tools=(docker tmux make)
[[ -z "$RECORD" ]] || tools+=(asciinema agg)
for tool in "${tools[@]}"; do
  command -v "$tool" >/dev/null || { echo "error: $tool is not installed" >&2; exit 1; }
done
if [[ -n "$RECORD" ]] && ! asciinema --version | grep -q '^asciinema 3'; then
  echo "error: asciinema 3 is needed to record without a terminal" >&2
  exit 1
fi

SOCKET=acp-fleet-demo
COMPOSE=(docker compose -f "$DIR/infra/docker-compose.yaml")
WORK="$(mktemp -d)"
t() { tmux -L "$SOCKET" "$@"; }
log() { printf '\033[2m[demo] %s\033[0m\n' "$*" >&2; }
die() { printf '[demo] error: %s\n' "$*" >&2; exit 1; }

cleanup() {
  local rc=$?
  set +e
  if [[ $rc -ne 0 ]]; then
    for p in watch crowd ops; do
      echo "--- pane $p ---" >&2
      t capture-pane -p -t "$(pane "$p")" 2>/dev/null | grep -v '^$' | tail -n 20 >&2
    done
  fi
  t kill-server 2>/dev/null
  rm -rf "$WORK"
  exit $rc
}
trap cleanup EXIT

cat >"$WORK/bashrc" <<EOF
PS1='\[\e[1;34m\]acp-fleet\[\e[0m\] \$ '
HISTFILE=
PROMPT_COMMAND='tmux -L $SOCKET wait-for -S "ready-\$DEMO_PANE"'
cd "$DIR"
EOF

shell() { printf 'DEMO_PANE=%s exec bash --noprofile --rcfile %q -i' "$1" "$WORK/bashrc"; }

# pane prints the tmux target of a pane: watch on top, crowd and ops below.
pane() {
  case "$1" in
    watch) echo demo:main.0 ;;
    crowd) echo demo:main.1 ;;
    ops) echo demo:main.2 ;;
  esac
}

wait_ready() {
  timeout "${2:-600}" tmux -L "$SOCKET" wait-for "ready-$1" || die "pane $1: no prompt"
}

type_keys() {
  local i
  for ((i = 0; i < ${#2}; i++)); do
    t send-keys -t "$(pane "$1")" -l -- "${2:i:1}"
    sleep 0.03
  done
  sleep 0.3
  t send-keys -t "$(pane "$1")" Enter
}

run() { type_keys "$1" "$2"; wait_ready "$1" "${3:-600}"; sleep 1; }
start() { type_keys "$1" "$2"; }
say() { run "$1" "# $2"; }

wait_text() {
  local deadline=$(($(date +%s) + ${3:-120}))
  until t capture-pane -p -t "$(pane "$1")" | grep -Eq -- "$2"; do
    (($(date +%s) < deadline)) || die "pane $1: no match for /$2/"
    sleep 0.5
  done
}

# busiest prints the live server with the most conversations, skipping $1.
busiest() {
  "${COMPOSE[@]}" --progress quiet run --rm --no-deps -T tools status |
    awk -v skip="${1:-}" 'NR > 1 && $3 == "live" && $1 != skip { print $5, $1 }' | sort -rn | head -n 1 | cut -d' ' -f2
}

log "starting the fleet with opencode (off camera)"
make -C "$DIR" clean >/dev/null 2>&1 || true
make -C "$DIR" up-opencode >/dev/null 2>&1 || die "make up-opencode failed"
"${COMPOSE[@]}" --profile tools build tools >/dev/null 2>&1
deadline=$(($(date +%s) + 60))
until [[ "$("${COMPOSE[@]}" --progress quiet run --rm --no-deps -T tools status 2>/dev/null | grep -c ' live ')" == 3 ]]; do
  (($(date +%s) < deadline)) || die "the fleet didn't start"
  sleep 2
done

t new-session -d -s demo -x "$COLS" -y "$ROWS" -n main "$(shell watch)"
t set-option -g status off
t set-option -g pane-border-status top
t set-option -g pane-border-format ' #{@title} '
t set-option -p -t demo:main.0 @title "make watch: what the fleet does"
wait_ready watch 30
t split-window -v -l 36% -t demo:main.0 "$(shell crowd)"
t set-option -p -t demo:main.1 @title "make crowd: $USERS users of opencode agents, behind nginx"
wait_ready crowd 30
t split-window -h -l 45% -t demo:main.1 "$(shell ops)"
t set-option -p -t demo:main.2 @title "you: operate the fleet"
wait_ready ops 30
ASCIINEMA_PID=""
if [[ -n "$RECORD" ]]; then
  TERM=xterm-256color asciinema rec --headless --window-size "${COLS}x${ROWS}" -f asciicast-v2 \
    --overwrite -q -i 2 -t "acp-fleet" -c "tmux -L $SOCKET attach -t demo" "$OUT/demo.cast" </dev/null >/dev/null 2>&1 &
  ASCIINEMA_PID=$!
  until t list-clients -t demo 2>/dev/null | grep -q .; do sleep 0.2; done
  log "recording (watch: tmux -L $SOCKET attach -r)"
fi
sleep 1

start watch "make watch"
sleep 2
start crowd "make crowd N=$USERS"
say ops "Users chat with their agents through nginx."
say ops "Each conversation's shard has one owner server."
wait_text watch "[1-9][0-9] memory checks" 300

victim="$(busiest)"
say ops "Crash the busiest server."
run ops "make kill S=$victim"
wait_text watch "took [0-9]+ shards from $victim \\(crashed\\)" 60
wait_text watch "remembers the .* after moving from $victim" 180
sleep 8

say ops "Add a server."
run ops "make join"
wait_text watch "server-4 took [0-9]+ shards from .* \\(rebalanced\\)" 60
sleep 20

drained="$(busiest server-4)"
say ops "Drain a server: turns finish, then shards move."
run ops "make drain S=$drained" 180
wait_text watch "from $drained \\(drained\\)" 30
sleep 25
run ops "make status"
sleep 6

if [[ -n "$ASCIINEMA_PID" ]]; then
  # End on the last frame of the fleet: drop what tmux prints when it detaches.
  cutoff="$(tail -n 1 "$OUT/demo.cast" | awk -F'[[,]' '{ print $2 }')"
  t detach-client -s demo
  wait "$ASCIINEMA_PID"
  awk -v cut="$cutoff" 'NR == 1 { print; next } { split($0, f, /[[,]/) } f[2] + 0 <= cut + 0' "$OUT/demo.cast" >"$WORK/demo.cast"
  mv "$WORK/demo.cast" "$OUT/demo.cast"
  grep -qF -- "$GEMINI_API_KEY" "$OUT/demo.cast" && { rm -f "$OUT/demo.cast"; die "the recording showed GEMINI_API_KEY"; }
  agg --speed 2 --idle-time-limit 2 --font-size 14 "$OUT/demo.cast" "$OUT/demo.gif"
  log "wrote $OUT/demo.cast and $OUT/demo.gif"
fi
