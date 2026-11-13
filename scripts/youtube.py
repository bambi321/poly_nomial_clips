#!/usr/bin/env python3
"""Post the day's clips to YouTube Shorts, through YouTube Studio in Chrome.

Until the Google Cloud project passes YouTube's API audit, API uploads are locked to private.
So once a day (10:05, scripts/scheduler.sh) this starts Claude Code in the background with the
Claude in Chrome extension, which follows .claude/skills/youtube/SKILL.md to upload the day's
clips in YouTube Studio: the 10:00 clip goes public straight away, the 13:00 and 17:00 clips are
uploaded and scheduled for their times. Instagram is unaffected and keeps its own job.

Usage:
    python scripts/youtube.py prep [<video>...]   make the YouTube files for every queued clip (or these videos):
                                                  clipN-yt.mp4 (under 10 MB, the extension's upload limit)
                                                  and clipN-youtube.txt (title, then the description)
    python scripts/youtube.py plan [--date D] [--json]
                                                  the uploads a run on date D (default today) would do
    python scripts/youtube.py record <file> live|scheduled|failed [url]
                                                  set a clip's YouTube cell in release-schedule.md
                                                  (<file> is the clip's mp4 path as in the schedule)
    python scripts/youtube.py run [--date D] [--dry-run]
                                                  the daily job: prep, plan, then upload with Claude in Chrome
    python scripts/youtube.py status              YouTube state of every clip in the schedule
"""

import argparse
import fcntl
import json
import re
import shutil
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from schedule import (NO_YOUTUBE, ROOT, fmt, locked, md_link, read_schedule,  # noqa: E402
                      video_info, write_schedule)

LOG_DIR = ROOT / "logs"
LOG = LOG_DIR / "youtube.log"
MAX_UPLOAD = 9_500_000          # Claude in Chrome's file upload limit is 10 MB per upload
TARGET_SIZE = 9_300_000         # what the compressed copy aims for
PUBLIC_NOW_WINDOW = 15 * 60     # a slot this close (or already past) is published now, not scheduled
CLAUDE_TIMEOUT = 50 * 60
CREDIT = "Full credits for the original video go to @"


def log(msg):
    LOG_DIR.mkdir(exist_ok=True)
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S}  {msg}"
    with LOG.open("a") as f:
        f.write(line + "\n")
    print(line, flush=True)


def notify(icon, title, message):
    from post_instagram import notify as send  # shares the Instagram job's texts and Mac notifications
    send(icon, title, message)


# ── YouTube files for each clip ──────────────────────────────────────────────

def clip_paths(mp4_rel):
    mp4 = ROOT / mp4_rel
    return mp4, mp4.with_name(mp4.stem + "-yt.mp4"), mp4.with_name(mp4.stem + "-youtube.txt")


def upload_file(mp4_rel):
    """The file to upload: the clip itself if it's small enough, otherwise its -yt.mp4 copy."""
    mp4, small, _ = clip_paths(mp4_rel)
    return mp4 if mp4.stat().st_size <= MAX_UPLOAD else small


def make_small_copy(mp4, out):
    """Two-pass H.264 at 30 fps, sized to just under the upload limit. Looks the same once YouTube re-encodes it."""
    duration = float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(mp4)],
        capture_output=True, text=True, check=True).stdout)
    video_kbps = int(TARGET_SIZE * 8 / 1000 / duration - 96)
    passlog = LOG_DIR / f"ffmpeg2pass-{mp4.stem}"
    common = ["ffmpeg", "-y", "-v", "error", "-i", str(mp4), "-vf", "fps=30", "-c:v", "libx264",
              "-preset", "slow", "-b:v", f"{video_kbps}k", "-passlogfile", str(passlog)]
    subprocess.run(common + ["-pass", "1", "-an", "-f", "mp4", "/dev/null"], check=True)
    subprocess.run(common + ["-pass", "2", "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart",
                             str(out)], check=True)
    for f in LOG_DIR.glob(f"ffmpeg2pass-{mp4.stem}*"):
        f.unlink()
    if out.stat().st_size > MAX_UPLOAD:
        raise RuntimeError(f"{out.name} came out at {out.stat().st_size / 1e6:.1f} MB, over the limit")


def youtube_text(row):
    """Title (from highlights.md) and description (the post caption plus a link to the original)."""
    video_dir = (ROOT / row["video"]).parent.parent
    clips, _ = video_info(video_dir)
    clip = next(c for c in clips if f"clip{c['id']}" == row["clip"])
    title = re.sub(r"[<>]", "", clip["title"]).strip()[:100]
    source = (video_dir / "source.md").read_text()
    m = re.search(r"\*\*url:\*\*\s*(\S+)", source)
    caption = (ROOT / row["caption"]).read_text().strip()
    lines = caption.splitlines()
    if m:
        at = next((i for i, l in enumerate(lines) if l.startswith(CREDIT)), None)
        link = f"Original video: {m.group(1)}"
        if at is None:
            lines += ["", link]
        else:
            lines.insert(at + 1, link)
    description = re.sub(r"[<>]", "", "\n".join(lines))
    return title, description


def read_youtube_text(path):
    title, _, description = path.read_text().partition("\n\n")
    return title.strip(), description.strip()


def prep_row(row, quiet=False):
    mp4, small, text = clip_paths(row["video"])
    if not mp4.exists():
        raise RuntimeError(f"{row['video']} is missing")
    if mp4.stat().st_size > MAX_UPLOAD and not small.exists():
        make_small_copy(mp4, small)
        if not quiet:
            log(f"made {small.relative_to(ROOT)} ({small.stat().st_size / 1e6:.1f} MB)")
    if not text.exists():
        title, description = youtube_text(row)
        text.write_text(f"{title}\n\n{description}\n")
        if not quiet:
            log(f"wrote {text.relative_to(ROOT)}")


def needs_youtube(row):
    return row["youtube"] in ("", NO_YOUTUBE) or row["youtube"].startswith("failed")


def cmd_prep(videos):
    rows = read_schedule()
    wanted = {(ROOT / v).resolve() for v in videos}
    for row in rows:
        if not needs_youtube(row):
            continue
        if wanted and (ROOT / row["video"]).parent.parent.resolve() not in wanted:
            continue
        prep_row(row)
    print("YouTube files ready.")


# ── Plan, record, status ─────────────────────────────────────────────────────

def plan(day, now):
    """Clips a run on `day` uploads: that day's clips, plus any from the day before that never made it."""
    out = []
    for row in sorted(read_schedule(), key=lambda r: r["when"]):
        if not needs_youtube(row) or not (day - timedelta(days=1) <= row["date"] <= day):
            continue
        public_now = (row["when"] - now).total_seconds() <= PUBLIC_NOW_WINDOW
        mp4, _, text = clip_paths(row["video"])
        title, description = read_youtube_text(text) if text.exists() else youtube_text(row)
        out.append({
            "file": row["video"], "clip": row["clip"], "creator": row["creator"],
            "upload": str(upload_file(row["video"])) if mp4.exists() else None,
            "title": title, "description": description,
            "mode": "public now" if public_now else "schedule",
            "date": f"{row['when']:%b} {row['when'].day}, {row['when']:%Y}",
            "time": row["when"].strftime("%-I:%M %p"),
            "slot": fmt(row["when"]),
        })
    return out


def cmd_plan(day, as_json):
    items = plan(day, datetime.now())
    if as_json:
        print(json.dumps(items, indent=2, ensure_ascii=False))
        return
    if not items:
        print(f"Nothing to upload to YouTube for {day:%a %d %b}.")
    for it in items:
        when = "publish now" if it["mode"] == "public now" else f"schedule for {it['date']} {it['time']}"
        print(f"  {it['slot']}  {it['clip']:<6} {when:<38} {it['title']}")


def cmd_record(file, state, url):
    if state in ("live", "scheduled") and not (url and url.startswith("https://")):
        sys.exit("live and scheduled need the video's https:// link")
    with locked():
        rows = read_schedule()
        row = next((r for r in rows if r["video"] == file), None)
        if not row:
            sys.exit(f"no clip with file {file} in release-schedule.md")
        row["youtube"] = f"[{state}]({url})" if url else state
        write_schedule(rows)
    if state in ("live", "scheduled"):
        posts = ROOT / Path(file).parent.parent / "posts.md"
        if not posts.exists():
            posts.write_text("# Posts\n\n| Posted | Clip | Platform | Link |\n|--------|------|----------|------|\n")
        platform = "YouTube" if state == "live" else f"YouTube (scheduled for {fmt(row['when'])})"
        with posts.open("a") as f:
            f.write(f"| {datetime.now():%Y-%m-%d %H:%M} | {row['clip']} | {platform} | {url} |\n")
    log(f"recorded {row['clip']} ({file}): YouTube {state} {url or ''}".rstrip())


def cmd_status():
    for r in read_schedule():
        yt = r["youtube"]
        link = md_link(yt)
        state = yt.split("]")[0].strip("[") if link else yt
        print(f"  {fmt(r['when'])}  {r['clip']:<6} IG {r['status']:<11} YT {state:<10} {r['title']}"
              + (f"\n{'':<20}{link}" if link else ""))


# ── The daily run ────────────────────────────────────────────────────────────

PROMPT = """Run the poly_nomial YouTube upload. Read .claude/skills/youtube/SKILL.md and follow it exactly.

These are this run's uploads (JSON). Do them in this order:

{plan}
"""

ALLOWED_TOOLS = ["mcp__claude-in-chrome", "Read", "Bash(.venv/bin/python scripts/youtube.py record:*)"]


def cmd_run(day, dry_run):
    LOG_DIR.mkdir(exist_ok=True)
    with (LOG_DIR / "youtube.lock").open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            log("another YouTube run is in progress; exiting")
            return
        try:
            for row in read_schedule():
                if needs_youtube(row) and day - timedelta(days=1) <= row["date"] <= day:
                    prep_row(row)
            items = plan(day, datetime.now())
        except Exception as e:
            log(f"FAILED before uploading: {e}")
            if not dry_run:
                notify("⚠️", "poly_nomial YouTube failed", f"YouTube run couldn't start: {str(e)[:250]}")
            sys.exit(1)
        if not items:
            log(f"nothing to upload to YouTube for {day:%a %d %b}")
            return
        prompt = PROMPT.format(plan=json.dumps(items, indent=2, ensure_ascii=False))
        claude = shutil.which("claude") or "/opt/homebrew/bin/claude"
        cmd = [claude, "-p", prompt, "--chrome", "--output-format", "text", "--allowedTools", *ALLOWED_TOOLS]
        if dry_run:
            print(prompt)
            print("Would run:", " ".join(cmd[:2] + ["<prompt>"] + cmd[3:]))
            return

        log(f"YouTube run started: {', '.join(i['clip'] + ' (' + i['mode'] + ')' for i in items)}")
        transcript = LOG_DIR / f"youtube-claude-{datetime.now():%Y%m%d-%H%M}.log"
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
        yt = rows[it["file"]]["youtube"]
        (done if yt.startswith(("[live]", "[scheduled]")) else missing).append(
            f"{it['clip']} {yt.split(']')[0].strip('[') if yt.startswith('[') else 'not uploaded'}")
    if missing:
        log(f"YouTube run incomplete: {', '.join(missing)}")
        notify("⚠️", "poly_nomial YouTube failed",
               f"YouTube: {', '.join(done) or 'nothing'} done; {', '.join(missing)}. "
               f"See {transcript.relative_to(ROOT)}. Upload by hand or run /youtube in Claude.")
    else:
        log(f"YouTube run done: {', '.join(done)}")
        notify("📺", "poly_nomial YouTube done", f"YouTube: {', '.join(done)}.")


def main():
    parser = argparse.ArgumentParser(description="Post the day's clips to YouTube Shorts via YouTube Studio.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prep")
    p.add_argument("videos", nargs="*")
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

    if args.cmd == "prep":
        cmd_prep(args.videos)
    elif args.cmd == "plan":
        cmd_plan(args.date, args.json)
    elif args.cmd == "record":
        cmd_record(args.file, args.state, args.url)
    elif args.cmd == "run":
        cmd_run(args.date, args.dry_run)
    elif args.cmd == "status":
        cmd_status()


if __name__ == "__main__":
    main()
