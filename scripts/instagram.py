#!/usr/bin/env python3
"""Post the day's clips to Instagram as Reels, through instagram.com in Chrome.

Works like the YouTube and TikTok jobs: once a day (10:00, scripts/scheduler.sh) it starts Claude
Code in the background with the Claude in Chrome extension, which follows
.claude/skills/instagram-web/SKILL.md to upload the day's clips on instagram.com: the 10:00 clip is
shared straight away, the 13:00 and 17:00 clips are uploaded and scheduled for their times
(the composer's "Schedule content" switch). It runs first; the YouTube (10:05) and TikTok (10:15)
jobs wait for it to finish with Chrome.

The Instagram cell is the schedule's Status column: not-posted · posted · scheduled · failed.
The old Graph API poster (scripts/post_instagram.py) is kept as a manual fallback.

Usage:
    python scripts/instagram.py plan [--date D] [--json]
                                                  the uploads a run on date D (default today) would do
    python scripts/instagram.py record <file> posted|scheduled|failed [url]
                                                  set a clip's Instagram status in release-schedule.md
                                                  (<file> is the clip's mp4 path as in the schedule)
    python scripts/instagram.py run [--date D] [--dry-run]
                                                  the daily job: plan, then upload with Claude in Chrome
"""

import argparse
import fcntl
import json
import shutil
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from schedule import ROOT, caption_problems, fmt, locked, read_schedule, write_schedule  # noqa: E402
from youtube import (CLAUDE_MODEL, CLAUDE_TIMEOUT, LOG_DIR, MAX_UPLOAD, chrome_turn, clip_paths,  # noqa: E402
                     make_small_copy, notify, upload_file)

ACCOUNT = "_poly_nomial_"      # the Instagram username the run must be signed in as
LOG = LOG_DIR / "instagram.log"
POST_NOW_WINDOW = 20 * 60      # a slot closer than this (or already past) is shared now, not scheduled
MAX_CAPTION = 2200             # Instagram's caption limit


def log(msg):
    LOG_DIR.mkdir(exist_ok=True)
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S}  {msg}"
    with LOG.open("a") as f:
        f.write(line + "\n")
    print(line, flush=True)


# ── What to upload ───────────────────────────────────────────────────────────

def prep_row(row):
    """The upload has to be under 10 MB (the extension's limit); the YouTube job usually made the small copy."""
    mp4, small, _ = clip_paths(row["video"])
    if not mp4.exists():
        raise RuntimeError(f"{row['video']} is missing")
    if mp4.stat().st_size > MAX_UPLOAD and not small.exists():
        make_small_copy(mp4, small)
        log(f"made {small.relative_to(ROOT)} ({small.stat().st_size / 1e6:.1f} MB)")


def instagram_caption(row):
    caption = (ROOT / row["caption"]).read_text().strip()
    problems = caption_problems(caption)
    if len(caption) > MAX_CAPTION:
        problems.append(f"is {len(caption)} characters (Instagram max is {MAX_CAPTION})")
    if problems:
        raise RuntimeError(f"{row['caption']}: {'; '.join(problems)} (see playbooks/captions.md)")
    return caption


def needs_instagram(row):
    return row["status"] in ("not-posted", "failed")


def plan(day, now):
    """Clips a run on `day` uploads: that day's clips, plus any from the day before that never made it."""
    out = []
    for row in sorted(read_schedule(), key=lambda r: r["when"]):
        if not needs_instagram(row) or not (day - timedelta(days=1) <= row["date"] <= day):
            continue
        post_now = (row["when"] - now).total_seconds() <= POST_NOW_WINDOW
        mp4 = ROOT / row["video"]
        out.append({
            "file": row["video"], "clip": row["clip"], "creator": row["creator"], "title": row["title"],
            "upload": str(upload_file(row["video"])) if mp4.exists() else None,
            "caption": instagram_caption(row),
            "mode": "post now" if post_now else "schedule",
            "date": f"{row['when']:%a, %-d %b %Y}",
            "hour": f"{row['when']:%H}", "minute": f"{row['when']:%M}",
            "slot": fmt(row["when"]),
        })
    return out


# ── Plan and record ──────────────────────────────────────────────────────────

def cmd_plan(day, as_json):
    items = plan(day, datetime.now())
    if as_json:
        print(json.dumps(items, indent=2, ensure_ascii=False))
        return
    if not items:
        print(f"Nothing to upload to Instagram for {day:%a %d %b}.")
    for it in items:
        when = "post now" if it["mode"] == "post now" else f"schedule for {it['date']} {it['hour']}:{it['minute']}"
        print(f"  {it['slot']}  {it['clip']:<6} {when:<36} {it['title']}")


def cmd_record(file, state, url):
    # Instagram shows no link for a scheduled reel, so the link is optional here.
    if url and not url.startswith("https://"):
        sys.exit("the link must start with https://")
    with locked():
        rows = read_schedule()
        row = next((r for r in rows if r["video"] == file), None)
        if not row:
            sys.exit(f"no clip with file {file} in release-schedule.md")
        row["status"] = state
        write_schedule(rows)
    if state in ("posted", "scheduled"):
        posts = ROOT / Path(file).parent.parent / "posts.md"
        if not posts.exists():
            posts.write_text("# Posts\n\n| Posted | Clip | Platform | Link |\n|--------|------|----------|------|\n")
        platform = "Instagram" if state == "posted" else f"Instagram (scheduled for {fmt(row['when'])})"
        with posts.open("a") as f:
            f.write(f"| {datetime.now():%Y-%m-%d %H:%M} | {row['clip']} | {platform} | {url or 'no link shown'} |\n")
    log(f"recorded {row['clip']} ({file}): Instagram {state} {url or ''}".rstrip())


# ── The daily run ────────────────────────────────────────────────────────────

PROMPT = """Run the poly_nomial Instagram upload. Read .claude/skills/instagram-web/SKILL.md and follow it exactly.

The Instagram account is {account}.

These are this run's uploads (JSON). Do them in this order:

{plan}
"""

ALLOWED_TOOLS = ["mcp__claude-in-chrome", "Read", "Bash(.venv/bin/python scripts/instagram.py record:*)"]


def cmd_run(day, dry_run):
    LOG_DIR.mkdir(exist_ok=True)
    with (LOG_DIR / "instagram.lock").open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            log("another Instagram run is in progress; exiting")
            return
        try:
            for row in read_schedule():
                if needs_instagram(row) and day - timedelta(days=1) <= row["date"] <= day:
                    prep_row(row)
        except Exception as e:
            log(f"FAILED before uploading: {e}")
            if not dry_run:
                notify("⚠️", "poly_nomial Instagram failed", f"Instagram run couldn't start: {str(e)[:250]}")
            sys.exit(1)

        claude = shutil.which("claude") or "/opt/homebrew/bin/claude"
        with chrome_turn(log):
            # Planned once Chrome is free, so a slot is never scheduled in the past.
            try:
                items = plan(day, datetime.now())
            except Exception as e:
                log(f"FAILED before uploading: {e}")
                if not dry_run:
                    notify("⚠️", "poly_nomial Instagram failed", f"Instagram run couldn't start: {str(e)[:250]}")
                sys.exit(1)
            if not items:
                log(f"nothing to upload to Instagram for {day:%a %d %b}")
                if not dry_run and not any(r["status"] == "not-posted" for r in read_schedule()):
                    notify("⚠️", "poly_nomial queue empty", "no clips left to post. Queue more with /clip <url>.")
                return
            prompt = PROMPT.format(account=ACCOUNT, plan=json.dumps(items, indent=2, ensure_ascii=False))
            cmd = [claude, "-p", prompt, "--model", CLAUDE_MODEL, "--chrome", "--output-format", "text", "--allowedTools", *ALLOWED_TOOLS]
            if dry_run:
                print(prompt)
                print("Would run:", " ".join(cmd[:2] + ["<prompt>"] + cmd[3:]))
                return

            log(f"Instagram run started: {', '.join(i['clip'] + ' (' + i['mode'] + ')' for i in items)}")
            transcript = LOG_DIR / f"instagram-claude-{datetime.now():%Y%m%d-%H%M}.log"
            try:
                with transcript.open("w") as out:
                    result = subprocess.run(cmd, cwd=ROOT, stdout=out, stderr=subprocess.STDOUT,
                                            stdin=subprocess.DEVNULL, timeout=CLAUDE_TIMEOUT)
                code = result.returncode
            except subprocess.TimeoutExpired:
                code = "timeout"
            log(f"Claude finished (exit {code}); transcript in {transcript.relative_to(ROOT)}")

    # What actually happened, from the schedule (the skill records each clip as it goes).
    rows = {r["video"]: r for r in read_schedule()}
    done, missing = [], []
    for it in items:
        state = rows[it["file"]]["status"]
        (done if state in ("posted", "scheduled") else missing).append(f"{it['clip']} {state}")
    left = sum(1 for r in rows.values() if r["status"] == "not-posted")
    low = f" Only {left} clip(s) left: queue a new video with /clip." if left <= 3 else ""
    if missing:
        log(f"Instagram run incomplete: {', '.join(missing)}")
        notify("⚠️", "poly_nomial Instagram failed",
               f"Instagram: {', '.join(done) or 'nothing'} done; {', '.join(missing)}. "
               f"See {transcript.relative_to(ROOT)}. Run /instagram-web in Claude, or "
               f"scripts/scheduler.sh run-api for the API fallback.{low}")
    else:
        log(f"Instagram run done: {', '.join(done)}")
        notify("📸", "poly_nomial Instagram done", f"Instagram: {', '.join(done)}.{low}")


def main():
    parser = argparse.ArgumentParser(description="Post the day's clips to Instagram via instagram.com.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan")
    p.add_argument("--date", type=date.fromisoformat, default=date.today())
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("record")
    p.add_argument("file")
    p.add_argument("state", choices=["posted", "scheduled", "failed"])
    p.add_argument("url", nargs="?")
    p = sub.add_parser("run")
    p.add_argument("--date", type=date.fromisoformat, default=date.today())
    p.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.cmd == "plan":
        cmd_plan(args.date, args.json)
    elif args.cmd == "record":
        cmd_record(args.file, args.state, args.url)
    elif args.cmd == "run":
        cmd_run(args.date, args.dry_run)


if __name__ == "__main__":
    main()
