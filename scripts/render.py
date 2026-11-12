#!/usr/bin/env python3
"""Stages 4-5 of the clip pipeline: turn the picks in highlights.md into finished
9:16 clips with word-by-word captions. No other text is added to the video.
Creator credits go in the post caption, not in the video.

Usage:
    .venv/bin/python scripts/render.py videos/<folder> [--clips 1,3] [--handle @name]
    .venv/bin/python scripts/render.py videos/<folder> --cleanup

Reads:
    <video>/highlights.md           clip times from the ```json block
    <video>/caption-fixes.txt       optional: "wrong => right" lines for misheard words
    <video>/media/source.mp4        the source video
    <video>/media/words.json        word timings from ingest.py

Writes (ignored by git):
    <video>/clips/clip<id>.mp4          finished 1080x1920 clips (kept, next to clip<id>-caption.txt)
    <video>/media/clip<id>.ass            caption file used (working file)
    <video>/media/contact-sheet.jpg   two stills per clip, for checking (working file)
    <video>/media/manifest.json       exact cut times and caption text per clip (working file)

--cleanup deletes the video's media/ folder (source video, word timings and the
working files above) once the clips are approved. Re-rendering after that means
running ingest.py on the video again first.

Framing (from each clip's "framing" field):
    speaker              crop to 9:16 around the speaker's face (MediaPipe)
    diagram/screen/mixed blur-fill: the whole frame in the middle over a blurred copy
"""

import argparse
import json
import re
import shutil
import statistics
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
W, H = 1080, 1920
FONT_DIR = "/System/Library/Fonts/Supplemental"
FONT = "Arial Black"
# ASS colours are &HAABBGGRR
YELLOW = "&H0000D7FF&"
WHITE = "&H00FFFFFF&"
FACE_MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/face_detector/"
                  "blaze_face_short_range/float16/1/blaze_face_short_range.tflite")
FACE_MODEL = Path.home() / ".cache" / "poly_nomial_clips" / "blaze_face_short_range.tflite"


def log(msg):
    print(f"[render] {msg}", file=sys.stderr, flush=True)


# ── Loading inputs ───────────────────────────────────────────────────────────

def load_clips(ep):
    path = ep / "highlights.md"
    if not path.exists():
        sys.exit(f"No highlights.md in {ep}. Run /clip first.")
    m = re.search(r"```json\s*\n(.*?)```", path.read_text(), re.S)
    if not m:
        sys.exit("highlights.md has no ```json block under '## Machine-readable'.")
    return json.loads(m.group(1))["clips"]


def load_words(ep):
    data = json.loads((ep / "media" / "words.json").read_text())
    words = [dict(w) for s in data["segments"] for w in s.get("words", [])
             if w.get("word", "").strip()]
    # WhisperX can't time some tokens (often numbers like "4,400"). Spread them
    # evenly between the neighbouring timed words.
    i, n = 0, len(words)
    while i < n:
        if "start" in words[i] and "end" in words[i]:
            i += 1
            continue
        j = i
        while j < n and not ("start" in words[j] and "end" in words[j]):
            j += 1
        lo = words[i - 1]["end"] if i > 0 else (words[j]["start"] - 0.3 * (j - i) if j < n else 0.0)
        hi = words[j]["start"] if j < n else lo + 0.3 * (j - i)
        step = (hi - lo) / (j - i) if hi > lo else 0.3
        for k in range(i, j):
            words[k]["start"] = lo + step * (k - i)
            words[k]["end"] = lo + step * (k - i + 1)
        i = j
    return words


def norm(word):
    return re.sub(r"[^\w']", "", word.lower())


def apply_fixes(ep, words):
    """caption-fixes.txt: one 'wrong => right' per line. 'wrong' can be several words."""
    path = ep / "caption-fixes.txt"
    if not path.exists():
        return words, 0
    count = 0
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=>" not in line:
            continue
        wrong, right = (x.strip() for x in line.split("=>", 1))
        target = [norm(x) for x in wrong.split()]
        k = len(target)
        i = 0
        while i + k <= len(words):
            if [norm(words[i + j]["word"]) for j in range(k)] == target:
                trailing = re.search(r"[^\w']*$", words[i + k - 1]["word"]).group(0)
                start, end = words[i]["start"], words[i + k - 1]["end"]
                parts = right.split()
                step = (end - start) / len(parts)
                # One entry per replacement word, sharing the original time span,
                # so captions still group and wrap normally.
                new = [{"word": p, "start": start + step * n, "end": start + step * (n + 1)}
                       for n, p in enumerate(parts)]
                new[-1]["word"] += trailing
                words[i:i + k] = new
                count += 1
                i += len(new)
            else:
                i += 1
    return words, count


# ── Cut points ───────────────────────────────────────────────────────────────

def cut_points(words, start, end):
    """Snap the clip to whole words and add a little breathing room either side."""
    idx = [i for i, w in enumerate(words) if start - 0.25 <= (w["start"] + w["end"]) / 2 <= end + 0.25]
    if not idx:
        sys.exit(f"No transcript words between {start}s and {end}s. Check the clip times.")
    i0, i1 = idx[0], idx[-1]
    first, last = words[i0], words[i1]
    prev_end = words[i0 - 1]["end"] if i0 > 0 else 0.0
    next_start = words[i1 + 1]["start"] if i1 + 1 < len(words) else last["end"] + 1.0
    t0 = max(0.0, min(first["start"], max(first["start"] - 0.25, prev_end + 0.05)))
    t1 = max(last["end"] + 0.05, min(last["end"] + 0.5, next_start - 0.05))
    return t0, t1, words[i0:i1 + 1]


# ── Captions (ASS) ───────────────────────────────────────────────────────────

def ass_time(t):
    t = max(0.0, t)
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


def ass_text(text):
    return text.replace("\\", "").replace("{", "(").replace("}", ")")


def caption_word(word):
    return ass_text(re.sub(r"[.,;:]+$", "", word.strip()).upper())


def group_words(words):
    groups, current = [], []
    for w in words:
        if current:
            joined = " ".join(x["word"].strip() for x in current + [w])
            gap = w["start"] - current[-1]["end"]
            ends_phrase = re.search(r"[.,?!;:]$", current[-1]["word"].strip())
            if len(current) >= 3 or len(joined) > 18 or gap > 0.6 or ends_phrase:
                groups.append(current)
                current = []
        current.append(w)
    if current:
        groups.append(current)
    return groups


def build_ass(words, t0, duration, handle, layout):
    if layout == "speaker":
        cap_pos = r"\an2\pos(540,1450)"
    else:  # blur-fill: the source frame sits between y=656 and y=1264
        cap_pos = r"\an8\pos(540,1320)"

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,{FONT},84,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,7,3,5,40,40,0,1
Style: Small,Arial,36,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,1,2,40,40,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    if handle:
        events.append(f"Dialogue: 1,{ass_time(0)},{ass_time(duration)},Small,,0,0,0,,"
                      f"{{\\an8\\pos(540,90)}}{ass_text(handle)}")

    lines = []
    groups = group_words(words)
    for g_i, group in enumerate(groups):
        next_group_start = groups[g_i + 1][0]["start"] if g_i + 1 < len(groups) else None
        for w_i, w in enumerate(group):
            start = w["start"] - t0
            if w_i + 1 < len(group):
                end = group[w_i + 1]["start"] - t0
            else:
                end = w["end"] + 0.35
                if next_group_start is not None:
                    end = min(end, next_group_start)
                end -= t0
            end = min(max(end, start + 0.05), duration)
            if start >= duration:
                continue
            text = " ".join(
                f"{{\\c{YELLOW}}}{caption_word(x['word'])}{{\\c{WHITE}}}" if x is w else caption_word(x["word"])
                for x in group
            )
            events.append(f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Caption,,0,0,0,,{{{cap_pos}}}{text}")
        lines.append(" ".join(caption_word(x["word"]) for x in group))
    return header + "\n".join(events) + "\n", lines


# ── Framing ──────────────────────────────────────────────────────────────────

def face_crop_x(video, t0, t1):
    """Median horizontal face position across the clip, as a crop x offset in pixels."""
    import cv2
    import mediapipe as mp
    from mediapipe.tasks.python import BaseOptions, vision

    if not FACE_MODEL.exists():
        FACE_MODEL.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(FACE_MODEL_URL, FACE_MODEL)
    detector = vision.FaceDetector.create_from_options(
        vision.FaceDetectorOptions(base_options=BaseOptions(model_asset_path=str(FACE_MODEL))))
    cap = cv2.VideoCapture(str(video))
    src_w, src_h = cap.get(cv2.CAP_PROP_FRAME_WIDTH), cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    centres, t = [], t0
    while t < t1:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, frame = cap.read()
        if ok:
            image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            faces = detector.detect(image).detections
            if faces:
                box = max(faces, key=lambda d: d.bounding_box.width * d.bounding_box.height).bounding_box
                centres.append(box.origin_x + box.width / 2)
        t += 0.5
    cap.release()
    detector.close()
    crop_w = int(src_h * 9 / 16) // 2 * 2
    centre = statistics.median(centres) if centres else src_w / 2
    x = int(min(max(centre - crop_w / 2, 0), src_w - crop_w)) // 2 * 2
    return x, crop_w, len(centres)


def video_filter(layout, ass_path, crop=None):
    subs = f"subtitles=filename='{ass_path}':fontsdir='{FONT_DIR}'"
    if layout == "speaker":
        x, crop_w = crop
        return f"[0:v]crop={crop_w}:ih:{x}:0,scale={W}:{H},setsar=1,{subs}[v]"
    return (f"[0:v]split=2[a][b];"
            f"[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
            f"gblur=sigma=40,eq=brightness=-0.12[bg];"
            f"[b]scale={W}:-2[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1,{subs}[v]")


# ── Main ─────────────────────────────────────────────────────────────────────

def render_clip(ep, video, clip, words, handle, out_dir, work_dir):
    t0, t1, clip_words = cut_points(words, clip["start"], clip["end"])
    duration = t1 - t0
    framing = clip.get("framing", "diagram")
    layout = "speaker" if framing == "speaker" else "blur"
    crop, faces = None, None
    if layout == "speaker":
        x, crop_w, faces = face_crop_x(video, t0, t1)
        crop = (x, crop_w)
        if faces == 0:
            log(f"{clip['id']}: no face found, using a centre crop.")

    ass, caption_lines = build_ass(clip_words, t0, duration, handle, layout)
    name = f"clip{clip['id']}"
    ass_path = work_dir / f"{name}.ass"
    ass_path.write_text(ass)
    out = out_dir / f"{name}.mp4"
    fade_out = max(duration - 0.12, 0)
    graph = (video_filter(layout, ass_path, crop) + ";"
             f"[0:a]afade=t=in:d=0.04,afade=t=out:st={fade_out:.2f}:d=0.12,"
             f"loudnorm=I=-14:TP=-1.5:LRA=11[a]")
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
           "-ss", f"{t0:.3f}", "-t", f"{duration:.3f}", "-i", str(video),
           "-filter_complex", graph, "-map", "[v]", "-map", "[a]",
           "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", str(out)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f"ffmpeg failed on clip {clip['id']}:\n{result.stderr[-1500:]}")
    log(f"{name}: {duration:.1f}s, {layout} framing → {out.relative_to(ROOT)}")
    return {"id": clip["id"], "file": out.name, "cut_start": round(t0, 2), "cut_end": round(t1, 2),
            "duration": round(duration, 2), "layout": layout, "faces_found": faces,
            "first_words": " ".join(w["word"] for w in clip_words[:6]),
            "last_words": " ".join(w["word"] for w in clip_words[-6:]),
            "captions": caption_lines}


def contact_sheet(out_dir, results, work_dir):
    """Two rows of stills: near the start (1.2s) and at the middle of each clip."""
    if not results:
        return None
    inputs, filters, top, bottom = [], [], [], []
    for i, r in enumerate(results):
        path = str(out_dir / r["file"])
        inputs += ["-ss", "1.2", "-i", path, "-ss", f"{r['duration'] / 2:.2f}", "-i", path]
        filters.append(f"[{2 * i}:v]scale=360:640,setsar=1[t{i}]")
        filters.append(f"[{2 * i + 1}:v]scale=360:640,setsar=1[b{i}]")
        top.append(f"[t{i}]")
        bottom.append(f"[b{i}]")
    n = len(results)
    if n == 1:
        filters.append("[t0][b0]vstack=inputs=2[out]")
    else:
        filters.append(f"{''.join(top)}hstack=inputs={n}[top]")
        filters.append(f"{''.join(bottom)}hstack=inputs={n}[bot]")
        filters.append("[top][bot]vstack=inputs=2[out]")
    sheet = work_dir / "contact-sheet.jpg"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *inputs,
                    "-filter_complex", ";".join(filters), "-map", "[out]", "-frames:v", "1",
                    "-q:v", "3", str(sheet)], check=True)
    return sheet


def cleanup(ep):
    removed = 0
    media = ep / "media"
    if media.exists():
        removed += sum(1 for f in media.rglob("*") if f.is_file())
        shutil.rmtree(media)
    clips_dir = ep / "clips"
    if clips_dir.exists():
        for f in clips_dir.iterdir():
            if f.is_file() and not (f.suffix == ".mp4" or f.name.endswith("-caption.txt")):
                f.unlink()
                removed += 1
    clips = sorted(f.name for f in clips_dir.glob("*.mp4")) if clips_dir.exists() else []
    log(f"Removed {removed} working files. Kept: {', '.join(clips) or 'no clips'}.")


def main():
    parser = argparse.ArgumentParser(description="Render the clips in highlights.md as 9:16 videos.")
    parser.add_argument("video", help="Path to the video folder, e.g. videos/<creator>_<video>")
    parser.add_argument("--clips", help="Only these clip numbers, comma-separated (e.g. 1,3)")
    parser.add_argument("--handle", default="", help="Optional channel handle shown at the top")
    parser.add_argument("--cleanup", action="store_true",
                        help="Delete media/ and anything in clips/ that isn't a clip or caption, then exit")
    args = parser.parse_args()

    ep = (ROOT / args.video).resolve() if not Path(args.video).is_absolute() else Path(args.video)
    if not (ep / "highlights.md").exists():
        sys.exit(f"{args.video} doesn't look like a video folder (no highlights.md).")
    if args.cleanup:
        cleanup(ep)
        return
    video = ep / "media" / "source.mp4"
    for needed in (video, ep / "media" / "words.json"):
        if not needed.exists():
            sys.exit(f"Missing {needed.relative_to(ROOT)}. Run /clip on this video first.")

    clips = load_clips(ep)
    if args.clips:
        wanted = {c.strip().lower().removeprefix("clip") for c in args.clips.split(",")}
        clips = [c for c in clips if str(c["id"]).lower() in wanted]
        if not clips:
            sys.exit(f"None of {sorted(wanted)} are in highlights.md.")

    words, fixed = apply_fixes(ep, load_words(ep))
    if fixed:
        log(f"Applied {fixed} caption fixes from caption-fixes.txt.")
    out_dir = ep / "clips"
    out_dir.mkdir(exist_ok=True)
    work_dir = ep / "media"

    results = [render_clip(ep, video, c, words, args.handle, out_dir, work_dir) for c in clips]
    sheet = contact_sheet(out_dir, results, work_dir)
    manifest_path = work_dir / "manifest.json"
    existing = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    existing.update({r["id"]: r for r in results})
    manifest_path.write_text(json.dumps(existing, indent=2))
    log(f"Done: {len(results)} clips.")
    if sheet:
        print(f"CONTACT_SHEET={sheet.relative_to(ROOT)}")
    print(f"CLIPS_DIR={out_dir.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
