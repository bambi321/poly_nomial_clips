---
name: post
description: Check on or control the Instagram posting job (runs at 10am; clips go out at 10am, 1pm and 5pm). Shows what's posted, what's next and recent errors; can dry-run, post the due clip now, send test notifications, or pause and resume the scheduler. Use when the user runs /post, or asks about posting, the schedule, the scheduler, or why a post did or didn't go out.
argument-hint: [status | dry-run | now | api | test-alert | pause | resume]
allowed-tools: Bash(scripts/scheduler.sh:*), Bash(.venv/bin/python scripts/instagram.py:*), Bash(.venv/bin/python scripts/post_instagram.py:*), Bash(.venv/bin/python scripts/schedule.py:*), Bash(tail:*), Read, Edit
---

# /post

Arguments: $ARGUMENTS (default: `status`)

The job is a macOS LaunchAgent that runs `scripts/instagram.py run` once a day at 10:00 (the first of `SLOTS` in `scripts/schedule.py`). It starts Claude (Sonnet) with the Claude in Chrome extension, which follows `.claude/skills/instagram-web/SKILL.md` on instagram.com: the 10:00 clip is shared straight away and the 13:00 and 17:00 clips are scheduled with the composer's "Schedule content" switch. It also retries the previous day's `failed`/`not-posted` clips. Each clip's Status becomes `posted`, `scheduled` or `failed`, and a line goes in the video's `posts.md`. It runs before the YouTube (10:05) and TikTok (10:15) jobs, which wait for it to finish with Chrome. The old Graph API poster (`scripts/post_instagram.py`, via a Cloudflare tunnel) is kept as a manual fallback (`api` below). To see or change the queue, use `.venv/bin/python scripts/schedule.py list` (or `respace`), never a hand edit. It notifies the user when it's done (📸) or fails (⚠️). Logs are in `logs/instagram.log`, with Claude's report in `logs/instagram-claude-*.log`; the API fallback logs to `logs/post.log`.

Never print or read out `.env` values.

## status (default)

Run `scripts/scheduler.sh status`. Report in a few lines:
- whether the scheduler is ON, and the last run's exit code
- what posted most recently, and what's next (clip and date)
- anything overdue, or any `FAILED` lines in the recent log, with the likely fix (table below)
- if 6 or fewer clips are left (2 days at three posts a day), suggest running `/clip` on a new video

## dry-run

Run `.venv/bin/python scripts/instagram.py run --dry-run` (add `--date YYYY-MM-DD` to preview another day). Show which clips would be shared now or scheduled, and for when. Nothing is posted.

## now

Runs the day's Instagram job immediately (shares anything due, schedules the rest). **Ask the user to confirm first.** Then run `scripts/scheduler.sh run-now`; it takes a few minutes per clip. Read `logs/instagram.log` and the newest `logs/instagram-claude-*.log` when it's done.

## api

The fallback when the Chrome job can't run: posts the earliest due `not-posted` or `failed` clip through the Graph API. **Ask the user to confirm first.** Run `scripts/scheduler.sh run-api` and read `logs/post.log`. To bring the queue forward, run `schedule.py respace`, which moves every unposted clip to consecutive slots starting with the next one.

## test-alert

Run `scripts/scheduler.sh test-alert`. It sends the start, finish and failure texts from the job's own context. Tell the user to click **Allow** if macOS asks to let it control Messages. This needs `NOTIFY_IMESSAGE_TO` in `.env`; if the log says it's missing, give the user the command to add it themselves.

## pause / resume

- pause: `scripts/scheduler.sh uninstall`
- resume: `scripts/scheduler.sh install`

Pausing doesn't change the schedule, and reels already scheduled on Instagram still go out. A resumed job only picks up clips from the previous day onwards. Run `schedule.py respace` after resuming to put them back on evenly spaced slots.

## Common failures

The rows after the first two are from the API fallback (`logs/post.log`).

| Log says | Fix |
|---|---|
| `Instagram run incomplete` | Read the newest `logs/instagram-claude-*.log` for what Claude saw (sign-in, CAPTCHA, extension not connected). Fix that, then `now`, or `api` for a clip that's already due |
| `another Chrome run is in progress` | The YouTube or TikTok job had Chrome; the Instagram job waited and then ran. Nothing to do |
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
