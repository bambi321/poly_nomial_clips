---
name: post
description: Check on or control the Instagram posting job (10am, 1pm and 5pm daily). Shows what's posted, what's next and recent errors; can dry-run, post the due clip now, send test notifications, or pause and resume the scheduler. Use when the user runs /post, or asks about posting, the schedule, the scheduler, or why a post did or didn't go out.
argument-hint: [status | dry-run | now | test-alert | pause | resume]
allowed-tools: Bash(scripts/scheduler.sh:*), Bash(.venv/bin/python scripts/post_instagram.py:*), Bash(.venv/bin/python scripts/schedule.py:*), Bash(tail:*), Read, Edit
---

# /post

Arguments: $ARGUMENTS (default: `status`)

The job is a macOS LaunchAgent that runs `scripts/post_instagram.py` at each slot: 10:00, 13:00 and 17:00 Melbourne/Sydney time (`SLOTS` in `scripts/schedule.py`). Instagram downloads each clip from a temporary Cloudflare tunnel link (`scripts/tunnel.py`). Each run posts the earliest `not-posted` clip in `release-schedule.md` whose date and time have passed (one per run), marks it `posted`, and adds a line to the video's `posts.md`. To see or change the queue, use `.venv/bin/python scripts/schedule.py list` (or `respace`), never a hand edit. It texts the user when it starts (▶️), finishes (⏹) and fails (⚠️). Logs are in `logs/post.log`.

Never print or read out `.env` values.

## status (default)

Run `scripts/scheduler.sh status`. Report in a few lines:
- whether the scheduler is ON, and the last run's exit code
- what posted most recently, and what's next (clip and date)
- anything overdue, or any `FAILED` lines in the recent log, with the likely fix (table below)
- if 6 or fewer clips are left (2 days at three posts a day), suggest running `/clip` on a new video

## dry-run

Run `.venv/bin/python scripts/post_instagram.py --dry-run` (add `--as-of "YYYY-MM-DD HH:MM"` to preview a future slot). Show what would post and the caption. Nothing is posted.

## now

Posts the due clip immediately, the same as a scheduled run. **Ask the user to confirm first.** Then run `scripts/scheduler.sh run-now`, wait about a minute, and read `logs/post.log`. If nothing is due yet, say so. It won't post a future clip early. To bring the queue forward, run `schedule.py respace`, which moves every unposted clip to consecutive slots starting with the next one.

## test-alert

Run `scripts/scheduler.sh test-alert`. It sends the start, finish and failure texts from the job's own context. Tell the user to click **Allow** if macOS asks to let it control Messages. This needs `NOTIFY_IMESSAGE_TO` in `.env`; if the log says it's missing, give the user the command to add it themselves.

## pause / resume

- pause: `scripts/scheduler.sh uninstall`
- resume: `scripts/scheduler.sh install`

Pausing doesn't change the schedule. Clips due while paused post one per slot after resuming. Run `schedule.py respace` after resuming to put them back on evenly spaced slots.

## Common failures

| Log says | Fix |
|---|---|
| `video file is missing` | The `.mp4` was deleted or moved. Re-render with `/render`, or fix the path in `release-schedule.md` |
| `caption file is missing` / `no creator credit line` | Write or fix `clipN-caption.txt` per `playbooks/captions.md` |
| `OAuthException` / `Invalid OAuth access token` | The token was revoked or changed. Generate a new one in the Meta app and replace it in `.env` |
| `network error` | Mac was offline at the slot. Run `/post now` |
| `cloudflared is not installed` | `brew install cloudflared` |
| `cloudflared didn't open a tunnel` / `tunnel address never served the file` | Cloudflare's free quick tunnel had a hiccup. Run `/post now`, or test with `.venv/bin/python scripts/post_instagram.py --test-tunnel <clip>` |
| `ProcessingFailedError` | Only happens with `INSTAGRAM_UPLOAD_METHOD=resumable` (Instagram's upload server is unreliable). Use the default tunnel method |
| `couldn't process the video` | Instagram rejected the file. Check the clip plays, then re-render it |
| `NOTIFY_IMESSAGE_TO not set` | Add the number to `.env` (user does this) |
| `iMessage failed` | Messages isn't signed in, or permission was denied. Run `test-alert` and click Allow |
| no log line at all for a slot | The Mac was off or logged out. If it was only asleep, the job runs when it wakes. Otherwise the clip posts at the next slot |
