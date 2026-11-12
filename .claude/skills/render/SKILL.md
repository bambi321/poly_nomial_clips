---
name: render
description: Cut the picks in a video's highlights.md into finished, numbered 9:16 clips (clip1.mp4, clip2.mp4…) with word-by-word captions and no other on-screen text, write each clip's post caption, then check them. Use when the user runs /render, or asks to cut, render or export the clips for a video.
argument-hint: [video-folder] [--clips 1,3]
allowed-tools: Bash(.venv/bin/python scripts/render.py:*), Bash(.venv/bin/python scripts/ingest.py:*), Bash(ls:*), Read, Write, Edit, Glob
---

# /render

Arguments: $ARGUMENTS

## 1. Pick the video

- If a video folder was given, use it.
- If not, use the most recently changed folder in `videos/` that has a `highlights.md`. Name it in your first message so the user can correct you.
- Pass `--clips 1,3` through if the user named specific clips.
- If `<video>/media/source.mp4` or `<video>/media/words.json` is missing (the video was already cleaned up), first re-run `.venv/bin/python scripts/ingest.py "<url>"` in the background, using the url from `<video>/source.md`. Tell the user this re-downloads and re-transcribes the video, which takes several minutes.

## 2. Fix misheard words before rendering

On-screen captions come straight from the transcript, so mistakes end up burned into the video.

1. Read `<video>/highlights.md`, then read the transcript lines inside each clip's time range in `<video>/transcript.md`.
2. Look for words the transcriber got wrong: science terms, names, numbers, and anything the highlights file flags.
3. Write each fix to `<video>/caption-fixes.txt`, one per line, in the form `wrong => right`. `wrong` can be several words. Matching ignores case and punctuation. Keep existing lines and add to them.

```
# caption fixes for this video
canneries => calories
nuclear wind => nuclear winter
```

Only fix what is clearly a mishearing. Don't reword what the creator said.

## 3. Render

Run this from the repo root **in the background** (it takes roughly 10–30 seconds per clip):

```
.venv/bin/python scripts/render.py <video> [--clips 1,3]
```

Wait for it to finish. Don't poll it. It prints `CONTACT_SHEET=` and `CLIPS_DIR=` at the end. Clips are saved as `<video>/clips/clip1.mp4`, `clip2.mp4`… matching the ids in `highlights.md`.

Framing comes from each clip's `framing` field in `highlights.md`:
- `speaker`: crops to 9:16 around the speaker's face
- anything else: blur-fill, with the whole frame in the middle over a blurred copy

## 4. Write the post captions

For each rendered clip, write `<video>/clips/clipN-caption.txt` following `playbooks/captions.md` exactly:

1. **Insight:** at most 3 simple sentences on what the clip teaches. Only claims the clip makes; respect the science check in `highlights.md`.
2. **Credit, verbatim:** `Full credits for the original video go to @<youtube-handle>`, using the handle from `<video>/source.md`. Never write "YouTube" anywhere in a caption: Instagram rejects the upload.
3. **Hashtags:** exactly 10, unique, lowercase, on one line.

Then set the clip's `- **Caption:**` line in `highlights.md` to `see clips/clipN-caption.txt`.

## 5. Check the output

1. Look at `<video>/media/contact-sheet.jpg`. The top row is each clip at 1.2s, and the bottom row is the middle of each clip. Check that:
   - the captions are readable and inside the frame
   - there's no extra text burned into the video: no hook title, credit or source text. Only the captions.
   - on `speaker` clips, the face is in frame
2. Read `<video>/media/manifest.json`. For each clip, check:
   - `first_words` starts on a clean sentence start, and `last_words` ends on a finished thought
   - `captions` has no remaining mishearings (if it does, add them to `caption-fixes.txt` and re-render just those clips)
   - `faces_found` isn't 0 on `speaker` clips
3. Re-read each `clipN-caption.txt`: 3 parts, ≤3 sentences, exact credit line, 10 hashtags.

Fix and re-render at most once. Then report.

## 6. Report back

Keep it short:
- one line: how many clips were rendered, and where
- a table: clip, length, framing, anything you fixed or noticed
- ask the user to watch the clips and read the captions, then say whether they're happy or want changes

## 7. Clean up and schedule once the clips are approved

When the user says the clips are good:

1. Delete the video's working files:

   ```
   .venv/bin/python scripts/render.py <video> --cleanup
   ```

   This removes `media/` (the source video, word timings, contact sheet and manifest) and anything in `clips/` that isn't a clip or caption. The video folder keeps `source.md`, `transcript.md`, `highlights.md`, `caption-fixes.txt` and `clips/`.

2. Add the clips to `release-schedule.md`, one per day after the last scheduled date, in clip order, with status `not-posted`. Follow the existing table format, including the File and Caption links.

Don't clean up before the user approves. Re-rendering after cleanup means downloading and transcribing the video again.
