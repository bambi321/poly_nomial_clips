#!/usr/bin/env python3
"""Manage release-schedule.md: the daily posting slots and the queue of clips.

Posting slots are the times in SLOTS, every day, in the Mac's local time (Melbourne/Sydney).
scripts/scheduler.sh reads them from here, so this is the only place to change them.
After changing SLOTS, run `scripts/scheduler.sh install` and then `respace`.

Usage:
    python scripts/schedule.py list                       show the queue
    python scripts/schedule.py add <video> [--clips 1,3] [--notify]
                                                          queue a video's clips at the next free slots;
                                                          --notify texts/notifies a summary (used by /clip)
    python scripts/schedule.py respace                    put every not-posted clip on consecutive slots,
                                                          starting at the next slot from now (order kept)
    python scripts/schedule.py slots                      print the slot times (used by scheduler.sh)

Change the schedule through this script rather than by hand: it waits for any post that's
running (same lock as the posting job) so the two never edit the file at once.
"""

import argparse
import contextlib
import fcntl
import json
import os
import re
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEDULE = ROOT / "release-schedule.md"
LOCK = ROOT / "logs" / "post.lock"
SLOTS = ["10:00", "17:00"]

CREDIT_PREFIX = "Full credits for the original video go to @"
HEADER = "| Date | Time | Clip | Title | Creator | File | Caption | Status |"
SEPARATOR = "|------|------|------|-------|---------|------|---------|--------|"
ROW_START = re.compile(r"^\|\s*\d{4}-\d{2}-\d{2}")


# ── Reading and writing the table ────────────────────────────────────────────

def md_link(cell):
    m = re.search(r"\]\(([^)]+)\)", cell)
    return m.group(1) if m else None


def parse_row(line):
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    if len(cells) == 7:  # older format without a Time column
        cells.insert(1, SLOTS[0])
    if len(cells) < 8:
        return None
    when = datetime.combine(date.fromisoformat(cells[0][:10]), time.fromisoformat(cells[1]))
    return {
        "when": when, "date": when.date(), "clip": cells[2], "title": cells[3], "creator": cells[4],
        "file_cell": cells[5], "caption_cell": cells[6],
        "video": md_link(cells[5]), "caption": md_link(cells[6]), "status": cells[7],
    }


def read_schedule():
    """All rows, in file order. Each row's "line" is its line number in the file."""
    rows = []
    for i, line in enumerate(SCHEDULE.read_text().splitlines()):
        if ROW_START.match(line):
            row = parse_row(line)
            if row:
                row["line"] = i
                rows.append(row)
    return rows


def format_row(r):
    return (f"| {r['when']:%Y-%m-%d (%a)} | {r['when']:%H:%M} | {r['clip']} | {r['title']} | "
            f"{r['creator']} | {r['file_cell']} | {r['caption_cell']} | {r['status']} |")


def write_schedule(rows):
    lines = SCHEDULE.read_text().splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("| Date |"))
    end = start + 1
    while end < len(lines) and lines[end].startswith("|"):
        end += 1
    lines[start:end] = [HEADER, SEPARATOR] + [format_row(r) for r in rows]
    tmp = SCHEDULE.with_suffix(".md.tmp")
    tmp.write_text("\n".join(lines) + "\n")
    os.replace(tmp, SCHEDULE)


@contextlib.contextmanager
def locked():
    """Wait for any running post job, then hold its lock while we edit the schedule."""
    LOCK.parent.mkdir(exist_ok=True)
    with LOCK.open("w") as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("A post is running; waiting for it to finish…", file=sys.stderr)
            fcntl.flock(f, fcntl.LOCK_EX)
        yield


# ── Slots ────────────────────────────────────────────────────────────────────

def slots_after(moment):
    """Every posting slot strictly after `moment`, in order, forever."""
    day = moment.date()
    times = sorted(time.fromisoformat(s) for s in SLOTS)
    while True:
        for t in times:
            slot = datetime.combine(day, t)
            if slot > moment:
                yield slot
        day += timedelta(days=1)


def fmt(moment):
    return moment.strftime("%a %d %b %H:%M")


# ── Caption checks (shared with post_instagram.py) ───────────────────────────

def caption_problems(text, strict=False):
    """Reasons a caption can't be posted. strict=True also checks the playbook's style rules."""
    problems = []
    if CREDIT_PREFIX not in text:
        problems.append("no creator credit line")
    if "youtube" in text.lower():
        problems.append("mentions YouTube, which Instagram rejects")
    if len(text) > 2200:
        problems.append(f"{len(text)} characters (Instagram max is 2200)")
    if strict:
        tags = re.findall(r"#\w+", text)
        if len(tags) != 10 or len(set(t.lower() for t in tags)) != 10:
            problems.append(f"needs exactly 10 unique hashtags, found {len(tags)}")
    return problems


# ── Commands ─────────────────────────────────────────────────────────────────

def cmd_list():
    rows = read_schedule()
    now = datetime.now()
    pending = [r for r in rows if r["status"] == "not-posted"]
    upcoming = min((r["when"] for r in pending if r["when"] > now), default=None)
    for r in rows:
        flag = ""
        if r["status"] == "not-posted" and r["when"] <= now:
            flag = "  ← due now (overdue)"
        elif r["when"] == upcoming:
            flag = "  ← next"
        print(f"  {fmt(r['when'])}  {r['clip']:<6} {r['status']:<11} {r['title']}{flag}")
    print(f"\nPosting slots: {', '.join(SLOTS)} daily. {len(pending)} clip(s) left to post." +
          (f" Queue runs out after {fmt(max(r['when'] for r in pending))}." if pending else ""))


def video_info(video_dir):
    highlights = (video_dir / "highlights.md").read_text()
    m = re.search(r"```json\s*(\{.*?\})\s*```", highlights, re.S)
    if not m:
        sys.exit(f"{video_dir}/highlights.md has no machine-readable JSON block")
    clips = json.loads(m.group(1))["clips"]
    source = (video_dir / "source.md").read_text()
    cm = re.search(r"\*\*creator:\*\*\s*\[([^\]]+)\]", source) or re.search(r"\*\*creator:\*\*\s*(.+)", source)
    return clips, (cm.group(1).strip() if cm else video_dir.name.split("_")[0])


def cmd_add(video, only, notify=False):
    video_dir = (ROOT / video).resolve()
    if not (video_dir / "highlights.md").exists():
        sys.exit(f"not a video folder (no highlights.md): {video}")
    rel = video_dir.relative_to(ROOT).as_posix()
    clips, creator = video_info(video_dir)
    clips = sorted(clips, key=lambda c: int(c["id"]))
    if only:
        clips = [c for c in clips if c["id"] in only]

    with locked():
        rows = read_schedule()
        scheduled = {r["video"] for r in rows}
        last = max([r["when"] for r in rows] + [datetime.now()])
        free = slots_after(last)
        added, skipped = [], []
        for c in clips:
            name = f"clip{c['id']}"
            mp4, cap = f"{rel}/clips/{name}.mp4", f"{rel}/clips/{name}-caption.txt"
            if mp4 in scheduled:
                skipped.append(f"{name}: already in the schedule")
                continue
            if not (ROOT / mp4).exists():
                skipped.append(f"{name}: {mp4} is missing")
                continue
            if not (ROOT / cap).exists():
                skipped.append(f"{name}: {cap} is missing")
                continue
            problems = caption_problems((ROOT / cap).read_text().strip(), strict=True)
            if problems:
                skipped.append(f"{name}: caption {'; '.join(problems)}")
                continue
            when = next(free)
            row = {"when": when, "clip": name, "title": c["title"].replace("|", "–"), "creator": creator,
                   "file_cell": f"[{name}.mp4]({mp4})", "caption_cell": f"[caption]({cap})",
                   "status": "not-posted"}
            rows.append(row)
            added.append(row)
        if added:
            write_schedule(rows)

    for r in added:
        print(f"queued {r['clip']} for {fmt(r['when'])}: {r['title']}")
    for s in skipped:
        print(f"skipped {s}")
    if not added:
        print("nothing added")
    if notify:
        from post_instagram import notify as send  # imported here to avoid a circular import
        if added:
            send("🎬", "poly_nomial clips queued",
                 f"{len(added)} new clip(s) from {creator} queued: {fmt(added[0]['when'])} to "
                 f"{fmt(added[-1]['when'])}." + (f" {len(skipped)} skipped." if skipped else ""))
        else:
            send("⚠️", "poly_nomial clips not queued", f"no clips from {video_dir.name} were queued.")
    sys.exit(1 if skipped and not added else 0)


def cmd_respace():
    with locked():
        rows = read_schedule()
        pending = sorted((r for r in rows if r["status"] == "not-posted"), key=lambda r: r["when"])
        free = slots_after(datetime.now())
        for r in pending:
            r["when"] = next(free)
        posted = [r for r in rows if r["status"] != "not-posted"]
        write_schedule(sorted(posted, key=lambda r: r["when"]) + pending)
    for r in pending:
        print(f"{r['clip']} → {fmt(r['when'])}: {r['title']}")


def main():
    parser = argparse.ArgumentParser(description="Manage release-schedule.md")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    sub.add_parser("slots")
    sub.add_parser("respace")
    add = sub.add_parser("add")
    add.add_argument("video", help="video folder, e.g. videos/<creator>_<video>")
    add.add_argument("--clips", help="only these clip numbers, comma-separated")
    add.add_argument("--notify", action="store_true", help="send a Mac notification and text with the result")
    args = parser.parse_args()

    if args.cmd == "slots":
        print(" ".join(SLOTS))
    elif args.cmd == "list":
        cmd_list()
    elif args.cmd == "respace":
        cmd_respace()
    elif args.cmd == "add":
        cmd_add(args.video, set(args.clips.split(",")) if args.clips else None, args.notify)


if __name__ == "__main__":
    main()
