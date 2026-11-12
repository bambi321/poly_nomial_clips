#!/usr/bin/env python3
"""Post the next due clip from release-schedule.md to Instagram as a Reel.

Usage:
    python scripts/post_instagram.py              post the clip that's due (used by the 10am and 5pm jobs)
    python scripts/post_instagram.py --dry-run    show what would post and check everything, without posting
    python scripts/post_instagram.py --dry-run --as-of "2026-11-14 17:00"   same, pretending it's then
    python scripts/post_instagram.py --status     show the schedule, what's next, and recent log lines
    python scripts/post_instagram.py --test-alert send test start, finish and failure texts
    python scripts/post_instagram.py --test-tunnel <video>       share via tunnel, check it downloads (no Instagram)
    python scripts/post_instagram.py --test-ig-download <video>  Instagram downloads via tunnel; NOT published

Upload method (INSTAGRAM_UPLOAD_METHOD in .env, default "tunnel"):
    tunnel     share the clip at a temporary Cloudflare quick-tunnel link (scripts/tunnel.py)
               and let Instagram download it (video_url). Needs: brew install cloudflared
    resumable  push the file to Instagram's upload server

How it picks a clip:
    The earliest row in release-schedule.md that is `not-posted` and whose date and time have
    passed. At most one clip per run, so missed slots are caught up one clip per run.
    The slot times live in scripts/schedule.py (SLOTS).

Phone texts (iMessage to NOTIFY_IMESSAGE_TO in .env, plus a Mac notification):
    ▶️ when the job starts, ⏹ when it finishes (with what it posted), ⚠️ if it fails.

Success: the clip is marked `posted` in release-schedule.md, a line is added to the video's
posts.md and logs/post.log. Instagram itself also notifies followers who turned on post
notifications for the account.

Failure: the clip stays `not-posted` and the reason goes to logs/post.log.

Reads from .env: INSTAGRAM_ACCESS_TOKEN, INSTAGRAM_USER_ID, NOTIFY_IMESSAGE_TO (optional).
Uses only the Python standard library.
"""

import argparse
import fcntl
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

from schedule import CREDIT_PREFIX, SCHEDULE, SLOTS, caption_problems, fmt, read_schedule

ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT / "logs"
LOG = LOG_DIR / "post.log"
GRAPH = "https://graph.facebook.com/v23.0"


# ── Small helpers ────────────────────────────────────────────────────────────

def load_env():
    env = {}
    path = ROOT / ".env"
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env[key.strip()] = value.strip().strip("'\"")
    return env


ENV = load_env()
TOKEN = ENV.get("INSTAGRAM_ACCESS_TOKEN", "")


def redact(text):
    return str(text).replace(TOKEN, "<token>") if TOKEN else str(text)


def log(msg):
    LOG_DIR.mkdir(exist_ok=True)
    line = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  {redact(msg)}"
    with LOG.open("a") as f:
        f.write(line + "\n")
    print(line, flush=True)


def mac_notification(title, message):
    script = 'on run argv\ndisplay notification (item 2 of argv) with title (item 1 of argv)\nend run'
    subprocess.run(["osascript", "-e", script, title, message], capture_output=True)


def imessage(to, message):
    script = ('on run argv\n'
              'tell application "Messages"\n'
              'set svc to 1st account whose service type = iMessage\n'
              'send (item 1 of argv) to participant (item 2 of argv) of svc\n'
              'end tell\n'
              'end run')
    result = subprocess.run(["osascript", "-e", script, message, to], capture_output=True, text=True)
    return result.returncode == 0, result.stderr.strip()


def notify(icon, title, message):
    """Phone text (iMessage to NOTIFY_IMESSAGE_TO, if set) plus a Mac notification. Never raises."""
    mac_notification(title, message)
    to = ENV.get("NOTIFY_IMESSAGE_TO")
    if not to:
        log(f"notify: NOTIFY_IMESSAGE_TO not set in .env, Mac notification only ({title})")
        return
    try:
        ok, err = imessage(to, f"{icon} poly_nomial: {message}")
        log(f"notify: texted '{title}'" if ok else f"notify: iMessage failed ({err[:200]})")
    except Exception as e:
        log(f"notify: iMessage failed ({e})")


def alert(message):
    """Failure alert."""
    notify("⚠️", "poly_nomial post failed", message)


# ── Instagram Graph API ──────────────────────────────────────────────────────

class ApiError(Exception):
    pass


def api(method, path, timeout=60, **params):
    params["access_token"] = TOKEN
    data = urllib.parse.urlencode(params).encode()
    url = f"{GRAPH}/{path}"
    if method == "GET":
        req = urllib.request.Request(f"{url}?{data.decode()}")
    else:
        req = urllib.request.Request(url, data=data, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        try:
            err = json.load(e).get("error", {})
            raise ApiError(f"{e.code} {err.get('type', '')}: {err.get('message', '')}") from None
        except ApiError:
            raise
        except Exception:
            raise ApiError(f"HTTP {e.code} from {path}") from None
    except urllib.error.URLError as e:
        raise ApiError(f"network error: {e.reason}") from None


def upload_video(upload_uri, video):
    """Send the video bytes to Instagram's upload server.

    Uses /usr/bin/curl, matching Meta's documented example. The same request sent with
    Python's urllib was rejected with ProcessingFailedError. The token goes in a private
    temporary header file so it never appears in the process list.
    """
    size = video.stat().st_size
    fd, header_path = tempfile.mkstemp(prefix="ig-upload-", suffix=".txt")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(f"Authorization: OAuth {TOKEN}\noffset: 0\nfile_size: {size}\n")
        result = subprocess.run(
            ["/usr/bin/curl", "-sS", "--max-time", "900", "-X", "POST", upload_uri,
             "-H", f"@{header_path}", "--data-binary", f"@{video}", "-w", "\n%{http_code}"],
            capture_output=True, text=True)
    finally:
        os.unlink(header_path)
    if result.returncode != 0:
        raise ApiError(f"upload failed: network error: {redact(result.stderr.strip())[:300]}")
    body_text, _, status = result.stdout.rpartition("\n")
    try:
        body = json.loads(body_text)
    except json.JSONDecodeError:
        body = {}
    if status != "200" or not body.get("success"):
        raise ApiError(f"upload failed: HTTP {status} {redact(body_text)[:300]}")


def find_existing_post(user_id, caption):
    """Return the permalink of a recent post with this caption, if it's already up."""
    first_line = caption.strip().splitlines()[0][:80]
    try:
        recent = api("GET", f"{user_id}/media", fields="caption,permalink,timestamp", limit=10)
    except ApiError:
        return None
    for media in recent.get("data", []):
        if (media.get("caption") or "").startswith(first_line):
            return media.get("permalink")
    return None


def create_and_upload(user_id, video, caption):
    """Create an upload slot and send the video (one attempt)."""
    container = api("POST", f"{user_id}/media", media_type="REELS", upload_type="resumable",
                    caption=caption, share_to_feed="true")
    container_id, upload_uri = container.get("id"), container.get("uri")
    if not container_id or not upload_uri:
        raise ApiError(f"Instagram didn't return an upload slot: {redact(container)}")
    log(f"uploading {video.name} ({video.stat().st_size / 1e6:.1f} MB)")
    upload_video(upload_uri, video)
    return container_id


def wait_until_ready(container_id):
    deadline = time.time() + 15 * 60
    while True:
        state = api("GET", container_id, fields="status_code,status")
        code = state.get("status_code")
        if code == "FINISHED":
            return
        if code in ("ERROR", "EXPIRED"):
            raise ApiError(f"Instagram couldn't process the video: {state.get('status')}")
        if time.time() > deadline:
            raise ApiError("Instagram was still processing the video after 15 minutes")
        time.sleep(10)


def create_from_link(user_id, video, caption):
    """Share the clip through a temporary Cloudflare tunnel and let Instagram download it.

    The tunnel stays open until Instagram has finished processing, then closes.
    """
    from tunnel import share_file  # scripts/tunnel.py
    with share_file(video, log) as url:
        container = api("POST", f"{user_id}/media", media_type="REELS", video_url=url,
                        caption=caption, share_to_feed="true")
        container_id = container.get("id")
        if not container_id:
            raise ApiError(f"Instagram didn't accept the video link: {redact(container)}")
        log("Instagram is downloading and processing the clip")
        wait_until_ready(container_id)
    return container_id


def upload_method():
    method = ENV.get("INSTAGRAM_UPLOAD_METHOD", "tunnel").strip().lower()
    if method not in ("tunnel", "resumable"):
        raise ApiError(f"INSTAGRAM_UPLOAD_METHOD must be 'tunnel' or 'resumable', not '{method}'")
    return method


def publish_reel(user_id, video, caption):
    if upload_method() == "tunnel":
        container_id = create_from_link(user_id, video, caption)
    else:
        container_id = create_and_upload(user_id, video, caption)
        wait_until_ready(container_id)

    try:
        published = api("POST", f"{user_id}/media_publish", timeout=120, creation_id=container_id)
    except ApiError as e:
        # The publish call can fail after Instagram has actually posted. Check before giving up.
        link = find_existing_post(user_id, caption)
        if link:
            return link
        raise e
    media_id = published.get("id")
    try:
        return api("GET", media_id, fields="permalink").get("permalink") or f"media id {media_id}"
    except ApiError:
        return f"media id {media_id}"


# ── Schedule ─────────────────────────────────────────────────────────────────

def mark_posted(row):
    lines = SCHEDULE.read_text().splitlines()
    line = lines[row["line"]]
    lines[row["line"]] = re.sub(r"\|\s*not-posted\s*\|\s*$", "| posted |", line)
    SCHEDULE.write_text("\n".join(lines) + "\n")


def record_post(row, link):
    posts = ROOT / Path(row["video"]).parent.parent / "posts.md"
    if not posts.exists():
        posts.write_text("# Posts\n\n| Posted | Clip | Platform | Link |\n|--------|------|----------|------|\n")
    with posts.open("a") as f:
        f.write(f"| {datetime.now().strftime('%Y-%m-%d %H:%M')} | {row['clip']} | Instagram | {link} |\n")


def due_row(rows, now):
    pending = [r for r in rows if r["status"] == "not-posted" and r["when"] <= now]
    return min(pending, key=lambda r: r["when"]) if pending else None


def check_files(row):
    video = ROOT / (row["video"] or "")
    caption_path = ROOT / (row["caption"] or "")
    if not row["video"] or not video.exists():
        raise ApiError(f"{row['clip']}: video file is missing ({row['video']})")
    if not row["caption"] or not caption_path.exists():
        raise ApiError(f"{row['clip']}: caption file is missing ({row['caption']})")
    caption = caption_path.read_text().strip()
    problems = caption_problems(caption)
    if problems:  # e.g. Instagram rejects any caption containing "YouTube" (ProcessingFailedError)
        raise ApiError(f"{row['clip']}: caption {'; '.join(problems)}, refusing to post "
                       f"(see playbooks/captions.md)")
    return video, caption


# ── Commands ─────────────────────────────────────────────────────────────────

def cmd_status():
    rows = read_schedule()
    now = datetime.now()
    print(f"Now: {fmt(now)}. Posting slots: {', '.join(SLOTS)} daily.\n")
    pending = [r for r in rows if r["status"] == "not-posted"]
    upcoming = min((r["when"] for r in pending if r["when"] > now), default=None)
    for r in rows:
        flag = ""
        if r["status"] == "not-posted" and r["when"] <= now:
            flag = "  ← overdue (posts at the next run)"
        elif r["when"] == upcoming:
            flag = "  ← next"
        print(f"  {fmt(r['when'])}  {r['clip']:<6} {r['status']:<11} {r['title']}{flag}")
    print(f"\n{len(pending)} clip(s) left to post." + (" Queue runs out after "
          f"{fmt(max(r['when'] for r in pending))}." if pending else " Nothing scheduled."))
    if LOG.exists():
        print("\nRecent log:")
        for line in LOG.read_text().splitlines()[-10:]:
            print("  " + line)


def cmd_post(dry_run, now):
    if not TOKEN or not ENV.get("INSTAGRAM_USER_ID"):
        raise ApiError("INSTAGRAM_ACCESS_TOKEN or INSTAGRAM_USER_ID missing from .env")
    user_id = ENV["INSTAGRAM_USER_ID"]
    rows = read_schedule()
    row = due_row(rows, now)
    if not row:
        left = [r for r in rows if r["status"] == "not-posted"]
        if not left:
            msg = "no clips left in release-schedule.md, nothing posted. Queue more with /clip <url>."
            log(msg)
            if not dry_run:
                alert(msg)
            return None
        nxt = min(left, key=lambda r: r["when"])
        msg = f"nothing due right now (next: {nxt['clip']} at {fmt(nxt['when'])})"
        log(msg)
        return msg
    if (now - row["when"]).total_seconds() > 30 * 60:
        log(f"{row['clip']} was due {fmt(row['when'])} and missed; posting it now")
    video, caption = check_files(row)
    account = api("GET", user_id, fields="username")
    log(f"{'[dry run] would post' if dry_run else 'posting'} {row['clip']} "
        f"({row['title']}) to @{account.get('username')}")
    if dry_run:
        print("\nCaption:\n" + caption)
        limit = api("GET", f"{user_id}/content_publishing_limit", fields="quota_usage,config")
        quota = (limit.get("data") or [{}])[0]
        print(f"\nPublishing quota used: {quota.get('quota_usage')} of "
              f"{quota.get('config', {}).get('quota_total')} in 24h")
        return None

    existing = find_existing_post(user_id, caption)
    if existing:
        log(f"{row['clip']} is already on Instagram ({existing}); marking it posted")
        link = existing
    else:
        link = publish_reel(user_id, video, caption)
    mark_posted(row)
    record_post(row, link)
    log(f"posted {row['clip']}: {link}")
    left = sum(1 for r in read_schedule() if r["status"] == "not-posted")
    low = " Queue a new video with /clip." if left <= 2 else ""
    return f"posted {row['clip']} ({row['title']}): {link}. {left} clip(s) left.{low}"


def main():
    parser = argparse.ArgumentParser(description="Post the day's clip to Instagram.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--dry-run", action="store_true", help="check everything without posting")
    group.add_argument("--status", action="store_true", help="show the schedule and recent log")
    group.add_argument("--test-alert", action="store_true", help="send test start, finish and failure texts")
    group.add_argument("--test-tunnel", metavar="VIDEO", help="share a video through a tunnel and check it downloads (no Instagram)")
    group.add_argument("--test-ig-download", metavar="VIDEO",
                       help="have Instagram download and process a video via the tunnel, without publishing")
    parser.add_argument("--as-of", help='with --dry-run: pretend it is this time ("YYYY-MM-DD HH:MM", '
                        'or a date for the end of that day)')
    args = parser.parse_args()
    if args.as_of and not args.dry_run:
        parser.error("--as-of only works with --dry-run")
    if args.as_of:
        now = datetime.fromisoformat(args.as_of if " " in args.as_of or "T" in args.as_of
                                     else args.as_of + " 23:59")
    else:
        now = datetime.now()

    if args.status:
        cmd_status()
        return
    if args.test_tunnel:
        from tunnel import share_file
        with share_file(Path(args.test_tunnel), log):
            log("tunnel test passed (Instagram was not contacted)")
        return
    if args.test_ig_download:
        cid = create_from_link(ENV["INSTAGRAM_USER_ID"], Path(args.test_ig_download),
                               "Download test (poly_nomial). Not published.")
        log(f"Instagram download test passed: processed and ready, NOT published (container {cid})")
        return
    if args.test_alert:
        log("sending test notifications")
        notify("▶️", "poly_nomial job started", "TEST: daily post job started.")
        notify("⏹", "poly_nomial job finished", "TEST: daily post job finished.")
        alert("TEST: this is what a failure looks like. Nothing was posted.")
        return

    LOG_DIR.mkdir(exist_ok=True)
    with (LOG_DIR / "post.lock").open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            log("another post run is already in progress; exiting")
            return
        if not args.dry_run:
            log("job started")
            notify("▶️", "poly_nomial job started", "post job started.")
        try:
            result = cmd_post(args.dry_run, now)
        except Exception as e:  # any failure: log it and alert, leave the clip not-posted
            msg = redact(f"{type(e).__name__ if not isinstance(e, ApiError) else ''} {e}".strip())
            log(f"FAILED: {msg}")
            if not args.dry_run:
                alert(f"job finished with an error: {msg[:300]}. Nothing was posted. Run /post status in Claude.")
            sys.exit(1)
        if not args.dry_run:
            log("job finished")
            if result:
                notify("⏹", "poly_nomial job finished", f"job finished: {result}")


if __name__ == "__main__":
    main()
