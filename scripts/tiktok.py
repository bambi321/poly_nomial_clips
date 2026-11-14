#!/usr/bin/env python3
"""Post the day's clips to TikTok, through TikTok Studio in Chrome.

TikTok's Content Posting API only posts privately until the app passes TikTok's audit, so this
works like the YouTube job: once a day (10:15, scripts/scheduler.sh) it starts Claude Code in the
background with the Claude in Chrome extension, which follows .claude/skills/tiktok/SKILL.md to
upload the day's clips in TikTok Studio: the 10:00 clip is posted straight away, the 13:00 and
17:00 clips are uploaded and scheduled for their times. If the YouTube run is still using Chrome,
this waits for it. Instagram and YouTube are unaffected.

The job does nothing until ACCOUNT below is set to the TikTok handle.

Usage:
    python scripts/tiktok.py plan [--date D] [--json]
                                                  the uploads a run on date D (default today) would do
    python scripts/tiktok.py record <file> live|scheduled|failed [url]
                                                  set a clip's TikTok cell in release-schedule.md
                                                  (<file> is the clip's mp4 path as in the schedule)
    python scripts/tiktok.py run [--date D] [--dry-run]
                                                  the daily job: plan, then upload with Claude in Chrome
    python scripts/tiktok.py status               TikTok state of every clip in the schedule
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
from schedule import NO_TIKTOK, ROOT, fmt, locked, md_link, read_schedule, write_schedule  # noqa: E402
from youtube import (CLAUDE_TIMEOUT, LOG_DIR, MAX_UPLOAD, chrome_turn, clip_paths,  # noqa: E402
                     make_small_copy, notify, upload_file)

ACCOUNT = "@_poly_nomial_"      # the TikTok handle; the job does nothing if this is empty
LOG = LOG_DIR / "tiktok.log"
POST_NOW_WINDOW = 20 * 60      # TikTok only schedules 15+ minutes ahead; a slot closer than this is posted now
MAX_CAPTION = 4000             # TikTok's caption limit


def log(msg):
    LOG_DIR.mkdir(exist_ok=True)
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S}  {msg}"
    with LOG.open("a") as f:
        f.write(line + "\n")
    print(line, flush=True)


# ── What to upload ───────────────────────────────────────────────────────────

def prep_row(row):
    """The upload has to be under 10 MB; the YouTube job usually made the small copy already."""
    mp4, small, _ = clip_paths(row["video"])
    if not mp4.exists():
        raise RuntimeError(f"{row['video']} is missing")
    if mp4.stat().st_size > MAX_UPLOAD and not small.exists():
        make_small_copy(mp4, small)
        log(f"made {small.relative_to(ROOT)} ({small.stat().st_size / 1e6:.1f} MB)")


def tiktok_caption(row):
    """The Instagram caption as it is: insight, creator credit, 10 hashtags."""
    caption = (ROOT / row["caption"]).read_text().strip()
    if len(caption) > MAX_CAPTION:
        raise RuntimeError(f"{row['caption']} is {len(caption)} characters (TikTok max is {MAX_CAPTION})")
    return caption


def needs_tiktok(row):
    return row["tiktok"] in ("", NO_TIKTOK) or row["tiktok"].startswith("failed")


def plan(day, now):
    """Clips a run on `day` uploads: that day's clips, plus any from the day before that never made it."""
    out = []
    for row in sorted(read_schedule(), key=lambda r: r["when"]):
        if not needs_tiktok(row) or not (day - timedelta(days=1) <= row["date"] <= day):
            continue
        post_now = (row["when"] - now).total_seconds() <= POST_NOW_WINDOW
        mp4 = ROOT / row["video"]
        out.append({
            "file": row["video"], "clip": row["clip"], "creator": row["creator"], "title": row["title"],
            "upload": str(upload_file(row["video"])) if mp4.exists() else None,
            "caption": tiktok_caption(row),
            "mode": "post now" if post_now else "schedule",
            "date": f"{row['when']:%Y-%m-%d}",
            "time": f"{row['when']:%H:%M}",
            "slot": fmt(row["when"]),
        })
    return out


# ── Plan, record, status ─────────────────────────────────────────────────────

def cmd_plan(day, as_json):
    items = plan(day, datetime.now())
    if as_json:
        print(json.dumps(items, indent=2, ensure_ascii=False))
        return
    if not items:
        print(f"Nothing to upload to TikTok for {day:%a %d %b}.")
    for it in items:
        when = "post now" if it["mode"] == "post now" else f"schedule for {it['date']} {it['time']}"
        print(f"  {it['slot']}  {it['clip']:<6} {when:<30} {it['title']}")


def cmd_record(file, state, url):
    # TikTok doesn't always show a link for a scheduled post, so the link is optional here.
    if url and not url.startswith("https://"):
        sys.exit("the link must start with https://")
    with locked():
        rows = read_schedule()
        row = next((r for r in rows if r["video"] == file), None)
        if not row:
            sys.exit(f"no clip with file {file} in release-schedule.md")
        row["tiktok"] = f"[{state}]({url})" if url else state
        write_schedule(rows)
    if state in ("live", "scheduled"):
        posts = ROOT / Path(file).parent.parent / "posts.md"
        if not posts.exists():
            posts.write_text("# Posts\n\n| Posted | Clip | Platform | Link |\n|--------|------|----------|------|\n")
        platform = "TikTok" if state == "live" else f"TikTok (scheduled for {fmt(row['when'])})"
        with posts.open("a") as f:
            f.write(f"| {datetime.now():%Y-%m-%d %H:%M} | {row['clip']} | {platform} | {url or 'no link shown'} |\n")
    log(f"recorded {row['clip']} ({file}): TikTok {state} {url or ''}".rstrip())


def cmd_status():
    for r in read_schedule():
        tt = r["tiktok"]
        link = md_link(tt)
        state = tt.split("]")[0].strip("[") if link else tt
        print(f"  {fmt(r['when'])}  {r['clip']:<6} IG {r['status']:<11} TT {state:<10} {r['title']}"
              + (f"\n{'':<20}{link}" if link else ""))


# ── The daily run ────────────────────────────────────────────────────────────

PROMPT = """Run the poly_nomial TikTok upload. Read .claude/skills/tiktok/SKILL.md and follow it exactly.

The TikTok account is {account}.

These are this run's uploads (JSON). Do them in this order:

{plan}
"""

ALLOWED_TOOLS = ["mcp__claude-in-chrome", "Read", "Bash(.venv/bin/python scripts/tiktok.py record:*)"]


def cmd_run(day, dry_run):
    if not ACCOUNT and not dry_run:
        log("ACCOUNT isn't set in scripts/tiktok.py yet; nothing uploaded")
        return
    LOG_DIR.mkdir(exist_ok=True)
    with (LOG_DIR / "tiktok.lock").open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            log("another TikTok run is in progress; exiting")
            return
        try:
            for row in read_schedule():
                if needs_tiktok(row) and day - timedelta(days=1) <= row["date"] <= day:
                    prep_row(row)
        except Exception as e:
            log(f"FAILED before uploading: {e}")
            if not dry_run:
                notify("⚠️", "poly_nomial TikTok failed", f"TikTok run couldn't start: {str(e)[:250]}")
            sys.exit(1)

        claude = shutil.which("claude") or "/opt/homebrew/bin/claude"
        with chrome_turn(log):
            # Planned once Chrome is free, so a long YouTube run doesn't leave a slot scheduled in the past.
            try:
                items = plan(day, datetime.now())
            except Exception as e:
                log(f"FAILED before uploading: {e}")
                if not dry_run:
                    notify("⚠️", "poly_nomial TikTok failed", f"TikTok run couldn't start: {str(e)[:250]}")
                sys.exit(1)
            if not items:
                log(f"nothing to upload to TikTok for {day:%a %d %b}")
                return
            prompt = PROMPT.format(account=ACCOUNT or "(ACCOUNT not set yet)", plan=json.dumps(items, indent=2, ensure_ascii=False))
            cmd = [claude, "-p", prompt, "--chrome", "--output-format", "text", "--allowedTools", *ALLOWED_TOOLS]
            if dry_run:
                print(prompt)
                print("Would run:", " ".join(cmd[:2] + ["<prompt>"] + cmd[3:]))
                return

            log(f"TikTok run started: {', '.join(i['clip'] + ' (' + i['mode'] + ')' for i in items)}")
            transcript = LOG_DIR / f"tiktok-claude-{datetime.now():%Y%m%d-%H%M}.log"
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
        tt = rows[it["file"]]["tiktok"]
        state = tt.split("]")[0].strip("[") if tt.startswith("[") else tt
        (done if state in ("live", "scheduled") else missing).append(
            f"{it['clip']} {state if state != NO_TIKTOK else 'not uploaded'}")
    if missing:
        log(f"TikTok run incomplete: {', '.join(missing)}")
        notify("⚠️", "poly_nomial TikTok failed",
               f"TikTok: {', '.join(done) or 'nothing'} done; {', '.join(missing)}. "
               f"See {transcript.relative_to(ROOT)}. Upload by hand or run /tiktok in Claude.")
    else:
        log(f"TikTok run done: {', '.join(done)}")
        notify("🎵", "poly_nomial TikTok done", f"TikTok: {', '.join(done)}.")


def main():
    parser = argparse.ArgumentParser(description="Post the day's clips to TikTok via TikTok Studio.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan")
    p.add_argument("--date", type=date.fromisoformat, default=date.today())
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("record")
    p.add_argument("file")
    p.add_argument("state", choices=["live", "scheduled", "failed"])
    p.add_argument("url", nargs="?")
    p = sub.add_parser("run")
    p.add_argument("--date", type=date.fromisoformat, default=date.today())
    p.add_argument("--dry-run", action="store_true")
    sub.add_parser("status")
    args = parser.parse_args()

    if args.cmd == "plan":
        cmd_plan(args.date, args.json)
    elif args.cmd == "record":
        cmd_record(args.file, args.state, args.url)
    elif args.cmd == "run":
        cmd_run(args.date, args.dry_run)
    elif args.cmd == "status":
        cmd_status()


if __name__ == "__main__":
    main()
