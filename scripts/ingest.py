#!/usr/bin/env python3
"""Stages 1-2 of the clip pipeline: download a YouTube video, transcribe it,
and write the files Claude reads to pick highlights.

Usage:
    .venv/bin/python scripts/ingest.py <youtube-url> [--model small] [--language en] [--force]

Writes (committed to git):
    clips/<YYYY-MM-DD>_<creator>_<video-slug>/source.md      video details, chapters, description
    clips/<YYYY-MM-DD>_<creator>_<video-slug>/transcript.md  sentence-level transcript with replay heat

Writes (local only, ignored by git):
    media/<same-name>/source.mp4    the video
    media/<same-name>/info.json     full yt-dlp metadata
    media/<same-name>/words.json    word-level timings (used later for captions)
    media/<same-name>/scenes.json   scene cut times in seconds

Re-running is safe: finished steps are skipped unless --force is passed.
The last line on stdout is `CLIP_DIR=<path>` so callers can find the output.
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
import unicodedata
import warnings
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BARS = "▁▂▃▄▅▆▇█"
VIDEO_FORMAT = (
    "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/"
    "b[height<=1080][ext=mp4]/"
    "bv*[height<=1080]+ba/b"
)


def log(msg):
    print(f"[ingest] {msg}", file=sys.stderr, flush=True)


def slugify(text, max_len):
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text[:max_len].rstrip("-") or "untitled"


def tc(sec, decimals=True):
    """Seconds -> HH:MM:SS(.s)"""
    sec = max(0.0, float(sec))
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    if decimals:
        return f"{int(h):02d}:{int(m):02d}:{s:04.1f}"
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d}"


# ── Stage 1: download ────────────────────────────────────────────────────────

def fetch_info(url):
    out = subprocess.run(
        ["yt-dlp", "--no-playlist", "--skip-download", "-J", url],
        capture_output=True, text=True,
    )
    if out.returncode != 0:
        sys.exit(f"yt-dlp could not read that link:\n{out.stderr.strip()[-1000:]}")
    return json.loads(out.stdout)


def download(url, dest):
    cmd = ["yt-dlp", "--no-playlist", "-f", VIDEO_FORMAT,
           "--merge-output-format", "mp4", "-o", str(dest), url]
    # Send yt-dlp's progress to stderr so stdout stays clean for CLIP_DIR=
    result = subprocess.run(cmd, stdout=sys.stderr)
    if result.returncode != 0 or not dest.exists():
        sys.exit("Video download failed (see yt-dlp output above).")


# ── Stage 2: transcribe + analyse ────────────────────────────────────────────

def transcribe(video, model_name, language):
    warnings.filterwarnings("ignore")
    import whisperx  # slow import, so only load it when needed

    audio = whisperx.load_audio(str(video))
    model = whisperx.load_model(model_name, "cpu", compute_type="int8", language=language)
    result = model.transcribe(audio, batch_size=8)
    lang = result["language"]
    align_model, meta = whisperx.load_align_model(language_code=lang, device="cpu")
    aligned = whisperx.align(result["segments"], align_model, meta, audio, "cpu",
                             return_char_alignments=False)
    segments = []
    for s in aligned["segments"]:
        text = s.get("text", "").strip()
        if not text:
            continue
        words = [{k: w[k] for k in ("word", "start", "end", "score") if k in w}
                 for w in s.get("words", [])]
        segments.append({"start": float(s["start"]), "end": float(s["end"]),
                         "text": text, "words": words})
    return {"language": lang, "model": model_name, "segments": segments}


def detect_scenes(video):
    from scenedetect import ContentDetector, detect
    scene_list = detect(str(video), ContentDetector())
    # Each scene is (start, end); the cut times are every start except the first.
    return [round(start.get_seconds(), 2) for start, _ in scene_list[1:]]


def heat_between(heatmap, start, end):
    vals = [h["value"] for h in heatmap if h["end_time"] > start and h["start_time"] < end]
    return sum(vals) / len(vals) if vals else None


def heat_peaks(heatmap, count=6):
    """Group the top 20% of heatmap bins into ranges, strongest first."""
    if not heatmap:
        return []
    values = sorted(h["value"] for h in heatmap)
    threshold = values[int(len(values) * 0.8)]
    ranges, current = [], None
    for h in heatmap:
        if h["value"] >= threshold:
            if current and h["start_time"] <= current["end"] + 0.01:
                current["end"] = h["end_time"]
                current["peak"] = max(current["peak"], h["value"])
            else:
                current = {"start": h["start_time"], "end": h["end_time"], "peak": h["value"]}
                ranges.append(current)
        else:
            current = None
    return sorted(ranges, key=lambda r: -r["peak"])[:count]


# ── Writing the Markdown files ───────────────────────────────────────────────

def write_source_md(path, info, media_dir):
    upload = info.get("upload_date") or ""
    published = f"{upload[:4]}-{upload[4:6]}-{upload[6:]}" if len(upload) == 8 else "unknown"
    lines = [
        f"# {info.get('title', 'Untitled')}",
        "",
        f"- **url:** {info.get('webpage_url')}",
        f"- **video id:** {info.get('id')}",
        f"- **creator:** [{info.get('channel') or info.get('uploader')}]({info.get('channel_url') or info.get('uploader_url') or ''})",
        f"- **published:** {published}",
        f"- **length:** {tc(info.get('duration') or 0, decimals=False)}",
        f"- **views at ingest:** {info.get('view_count', 'unknown'):,}" if isinstance(info.get("view_count"), int)
        else "- **views at ingest:** unknown",
        f"- **ingested:** {date.today().isoformat()}",
        f"- **local media:** `{media_dir.relative_to(ROOT)}/source.mp4` (not in git)",
        "",
    ]
    chapters = info.get("chapters") or []
    if chapters:
        lines += ["## Chapters", ""]
        lines += [f"- {tc(c['start_time'], decimals=False)} {c.get('title', '')}" for c in chapters]
        lines.append("")
    description = (info.get("description") or "").strip()
    if description:
        trimmed = description[:1500] + ("…" if len(description) > 1500 else "")
        lines += ["## Description (from YouTube, first 1,500 characters)", "", "```text", trimmed, "```", ""]
    path.write_text("\n".join(lines))


def write_transcript_md(path, info, transcript, heatmap, scenes):
    max_heat = max((h["value"] for h in heatmap), default=0) or 1
    chapters = list(info.get("chapters") or [])
    scene_iter = iter(scenes)
    next_cut = next(scene_iter, None)

    out = [
        f"# Transcript: {info.get('title', 'Untitled')}",
        "",
        f"{info.get('webpage_url')} · language `{transcript['language']}` · "
        f"WhisperX `{transcript['model']}` · generated {date.today().isoformat()}",
        "",
        "Each line is one sentence: `[start → end] heat ✂ text`.",
        "",
        "- **heat** is how much viewers rewatched that moment, from YouTube's most-replayed data "
        "(`▁` low to `█` highest). `·` means no heat data.",
        "- **✂** means the picture cuts to a new shot during or just before that sentence.",
        "- `###` lines are the creator's chapters.",
        "",
    ]

    peaks = heat_peaks(heatmap)
    out += ["## Most-replayed moments", ""]
    if peaks:
        for i, p in enumerate(peaks, 1):
            out.append(f"{i}. {tc(p['start'], False)} – {tc(p['end'], False)} "
                       f"(peak {p['peak'] / max_heat:.2f})")
    else:
        out.append("No heatmap available (new or low-view video). Judge from the transcript alone.")
    out += ["", "## Transcript", ""]

    for seg in transcript["segments"]:
        while chapters and chapters[0]["start_time"] <= seg["start"] + 0.5:
            c = chapters.pop(0)
            out += ["", f"### {tc(c['start_time'], False)} {c.get('title', '')}", ""]
        cut = False
        while next_cut is not None and next_cut <= seg["end"]:
            if next_cut >= seg["start"] - 1.0:
                cut = True
            next_cut = next(scene_iter, None)
        heat = heat_between(heatmap, seg["start"], seg["end"]) if heatmap else None
        bar = BARS[min(7, int(heat / max_heat * 8))] if heat is not None else "·"
        out.append(f"[{tc(seg['start'])} → {tc(seg['end'])}] {bar} {'✂ ' if cut else ''}{seg['text']}")

    path.write_text("\n".join(out) + "\n")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Download and transcribe a YouTube video for /clip.")
    parser.add_argument("url")
    parser.add_argument("--model", default="small",
                        help="WhisperX model: tiny, base, small (default), medium, large-v3")
    parser.add_argument("--language", default=None, help="Force a language code, e.g. en")
    parser.add_argument("--force", action="store_true", help="Redo every step even if files exist")
    args = parser.parse_args()

    for tool in ("yt-dlp", "deno", "ffmpeg"):
        if not shutil.which(tool):
            sys.exit(f"`{tool}` is not installed. Run: brew install {tool}")

    log("Reading video details…")
    info = fetch_info(args.url)
    if info.get("is_live") or info.get("live_status") in ("is_live", "is_upcoming"):
        sys.exit("That's a live or upcoming stream. Wait until it has finished and been uploaded.")

    upload = info.get("upload_date") or date.today().strftime("%Y%m%d")
    name = (f"{upload[:4]}-{upload[4:6]}-{upload[6:]}_"
            f"{slugify(info.get('channel') or info.get('uploader'), 24)}_"
            f"{slugify(info.get('title'), 48)}")
    clip_dir = ROOT / "clips" / name
    media_dir = ROOT / "media" / name
    clip_dir.mkdir(parents=True, exist_ok=True)
    media_dir.mkdir(parents=True, exist_ok=True)
    (media_dir / "info.json").write_text(json.dumps(info))
    log(f"{info.get('title')} · {tc(info.get('duration') or 0, False)} · {info.get('channel')}")

    video = media_dir / "source.mp4"
    if args.force or not video.exists():
        log("Downloading video (up to 1080p)…")
        download(args.url, video)
    else:
        log("Video already downloaded, skipping.")

    words_path = media_dir / "words.json"
    if args.force or not words_path.exists():
        log(f"Transcribing with WhisperX `{args.model}` on CPU. This takes a while for long videos…")
        transcript = transcribe(video, args.model, args.language)
        words_path.write_text(json.dumps(transcript))
    else:
        log("Transcript already exists, skipping.")
        transcript = json.loads(words_path.read_text())

    scenes_path = media_dir / "scenes.json"
    if args.force or not scenes_path.exists():
        log("Detecting scene cuts…")
        scenes = detect_scenes(video)
        scenes_path.write_text(json.dumps(scenes))
    else:
        scenes = json.loads(scenes_path.read_text())

    heatmap = info.get("heatmap") or []
    write_source_md(clip_dir / "source.md", info, media_dir)
    write_transcript_md(clip_dir / "transcript.md", info, transcript, heatmap, scenes)

    log(f"Done: {len(transcript['segments'])} sentences, {len(scenes)} scene cuts, "
        f"{'heatmap found' if heatmap else 'no heatmap'}.")
    print(f"CLIP_DIR={clip_dir.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
