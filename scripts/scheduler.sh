#!/bin/bash
# Manage the daily 10am Instagram post job (a macOS LaunchAgent).
#
#   scripts/scheduler.sh install      turn on: post the due clip every day at 10:00
#   scripts/scheduler.sh uninstall    turn off (nothing else changes; install again to resume)
#   scripts/scheduler.sh status       is it on, when did it last run, what's next
#   scripts/scheduler.sh run-now      run the real 10am job immediately (posts if a clip is due)
#   scripts/scheduler.sh test-alert   send test start, finish and failure texts from the job's context,
#                                     so macOS asks for any permission while you're watching
#
# The job runs while you're logged in (a locked screen is fine). It does not need Claude
# or a terminal open. Output goes to logs/post.log and logs/launchd.log.

set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
LABEL="com.polynomial.clips.post"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
PYTHON="$REPO/.venv/bin/python"
DOMAIN="gui/$(id -u)"
HOUR=10
MINUTE=0

write_plist() {  # $1 = plist path, $2 = label, $3.. = extra script args
  local path="$1" label="$2"; shift 2
  local args=""
  for a in "$@"; do args+="    <string>$a</string>"$'\n'; done
  local schedule=""
  if [ "$label" = "$LABEL" ]; then
    schedule="  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key><integer>$HOUR</integer>
    <key>Minute</key><integer>$MINUTE</integer>
  </dict>"
  fi
  mkdir -p "$(dirname "$path")" "$REPO/logs"
  cat > "$path" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$label</string>
  <key>ProgramArguments</key>
  <array>
    <string>$PYTHON</string>
    <string>$REPO/scripts/post_instagram.py</string>
$args  </array>
  <key>WorkingDirectory</key><string>$REPO</string>
$schedule
  <key>StandardOutPath</key><string>$REPO/logs/launchd.log</string>
  <key>StandardErrorPath</key><string>$REPO/logs/launchd.log</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key><string>/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin</string>
  </dict>
</dict>
</plist>
EOF
}

is_loaded() { launchctl print "$DOMAIN/$1" >/dev/null 2>&1; }

case "${1:-status}" in
  install)
    [ -x "$PYTHON" ] || { echo "Missing $PYTHON. Set up the Python environment first (see README)."; exit 1; }
    write_plist "$PLIST" "$LABEL"
    is_loaded "$LABEL" && launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null || true
    launchctl bootstrap "$DOMAIN" "$PLIST"
    echo "Scheduler on: posts the due clip every day at $(printf '%02d:%02d' $HOUR $MINUTE)."
    ;;
  uninstall)
    is_loaded "$LABEL" && launchctl bootout "$DOMAIN/$LABEL" || true
    rm -f "$PLIST"
    echo "Scheduler off. Nothing will post until you run: scripts/scheduler.sh install"
    ;;
  status)
    if is_loaded "$LABEL"; then
      echo "Scheduler: ON (daily at $(printf '%02d:%02d' $HOUR $MINUTE))"
      launchctl print "$DOMAIN/$LABEL" | grep -E "last exit code|runs =" | sed 's/^[[:space:]]*/  /' || true
    else
      echo "Scheduler: OFF"
    fi
    echo
    "$PYTHON" "$REPO/scripts/post_instagram.py" --status
    ;;
  run-now)
    is_loaded "$LABEL" || { echo "Scheduler is off. Run: scripts/scheduler.sh install"; exit 1; }
    launchctl kickstart "$DOMAIN/$LABEL"
    echo "Started. Follow along with: tail -f $REPO/logs/post.log"
    ;;
  test-alert)
    TEST_LABEL="$LABEL.test-alert"
    TEST_PLIST="$(mktemp -d)/$TEST_LABEL.plist"
    write_plist "$TEST_PLIST" "$TEST_LABEL" "--test-alert"
    is_loaded "$TEST_LABEL" && launchctl bootout "$DOMAIN/$TEST_LABEL" 2>/dev/null || true
    launchctl bootstrap "$DOMAIN" "$TEST_PLIST"
    launchctl kickstart "$DOMAIN/$TEST_LABEL"
    echo "Test texts sent from the job's context. If macOS asks to let it control Messages, click Allow."
    sleep 20
    launchctl bootout "$DOMAIN/$TEST_LABEL" 2>/dev/null || true
    tail -n 3 "$REPO/logs/post.log"
    ;;
  *)
    echo "Usage: scripts/scheduler.sh install|uninstall|status|run-now|test-alert"; exit 1 ;;
esac
