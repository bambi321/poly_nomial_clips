# poly_nomial_clips

Clipping science and research videos into short-form highlights for Instagram Reels, TikTok and YouTube Shorts.

This repo is the **brain of the channel**, not the media store. It holds the skills, knowledge bases and working docs that help us (and Claude) find good moments in long-form science videos, edit them well, and keep track of what's been posted.

> Raw footage, renders and exports live outside git (local drive / cloud storage). Only text, metadata and small reference files belong here.

---

## Repo layout

```
poly_nomial_clips/
├── README.md
├── CLAUDE.md                  # Instructions Claude reads at the start of every session
│
├── .claude/
│   └── skills/                # Claude Code skills (one folder per skill, each with SKILL.md)
│       ├── find-highlights/   #   e.g. scan a transcript and rank clip-worthy moments
│       ├── write-captions/    #   e.g. hooks, on-screen text, post captions, hashtags
│       └── ...
│
├── knowledge/                 # Long-lived reference material
│   ├── creators/              # One file per YouTuber: style, topics, recurring segments, licensing notes
│   ├── topics/                # Science explainers we keep needing (so captions are accurate)
│   └── platforms/             # Instagram / TikTok / YouTube Shorts specs, limits, best practices
│
├── playbooks/                 # How we do things, step by step
│   ├── captions.md            # Post caption rules: insight, verbatim credit, 10 hashtags
│   ├── editing-style.md       # Pacing, captions, fonts, colours, music, branding
│   ├── clip-workflow.md       # Source video → shortlist → edit → review → publish
│   └── fair-use.md            # Attribution, transformation and takedown policy
│
├── videos/                    # Everything for each source video, one folder per video
│   └── creator_video-slug/
│       ├── source.md          # Link, title, creator, YouTube handle, publish date, chapters
│       ├── transcript.md      # Timed transcript with replay heat
│       ├── highlights.md      # Ranked clip picks with timestamps and why they work
│       ├── caption-fixes.txt  # Misheard words to correct in captions (wrong => right)
│       ├── media/             # Working files while editing; deleted when done (not in git)
│       └── clips/
│           ├── clip1.mp4          # Finished vertical clip (not in git)
│           └── clip1-caption.txt  # Its post caption
│
├── templates/                 # Blank versions of the files above to copy from
│
├── scripts/                   # ingest.py, render.py, schedule.py, post_instagram.py, tunnel.py, scheduler.sh
├── requirements.txt           # Python packages for the pipeline
├── release-schedule.md        # Which clip posts in which slot (10:00 / 13:00 / 17:00), and whether it's posted
├── logs/                      # Posting job logs (not in git)
│
├── docs/                      # Diagrams and pages (e.g. the pipeline walkthrough)
│
└── analytics/                 # Notes on performance: what hooked, what flopped, lessons learned
```

Folders get created as we need them, so not all of these exist yet.

---

## Automation pipeline

**Interactive walkthrough:** [Clip Pipeline](https://claude.ai/artifact/9Gka2iJTwiBGYYFyRnyENW) (source: `docs/clip-pipeline.html`)

```
/clip <url>      one unattended sweep:
                 download (yt-dlp) → transcribe (WhisperX) → highlights.md (Claude)
                 → cut + 9:16 framing + word-by-word captions (ffmpeg, MediaPipe) → clipN.mp4 + clipN-caption.txt
                 → self-check → queue at the next free slots in release-schedule.md → clean up → notify you
10:00 · 13:00 · 17:00    scheduler (launchd) → Cloudflare quick tunnel → Instagram downloads the clip → Reel published
```

| Stage | Status |
|---|---|
| Find highlights (`/clip`) | ✅ built |
| Cut, caption and write post captions (`/render`, also run by `/clip`) | ✅ built |
| One-sweep `/clip`: link in, clips queued | ✅ built |
| Posting to Instagram three times a day (scheduler + tunnel) | ✅ built, first post 12 Nov 2026 |
| TikTok and YouTube Shorts | not started |
| Performance tracking (`analytics/`) | not started |

### Using `/clip`

In Claude Code, from this repo:

```
/clip https://www.youtube.com/watch?v=<id>
```

That's the whole job. One sweep with no questions, about 10–20 minutes:

1. Downloads the video, transcribes it with word timings and reads YouTube's most-replayed heatmap.
2. Claude picks the highlights (only clips scoring 7/10 or more) and writes them to `videos/<folder>/highlights.md`.
3. Renders each clip and writes its post caption (the `/render` steps below), then checks the contact sheet, cut points and captions. Fixes are re-rendered once, and any clip that still has a problem is left out of the queue.
4. Queues the good clips at the next free 10:00/13:00/17:00 slots after the last scheduled clip (`scripts/schedule.py add`), and sends you a notification with the dates.
5. Deletes the working files (`media/`) and reports what it queued.

Add `--review` to stop after step 2 and approve the picks yourself, then run `/render`. It runs on your Claude subscription, so no API key is needed.

To leave it running unattended, start Claude with fewer prompts (for example in auto mode). The skill pre-approves the scripts it runs. Also add the [permissions below](#permissions-for-unattended-runs) so its file edits don't stop at a prompt.

### Using `/render`

```
/render videos/<folder>
/render videos/<folder> --clips 1,3
```

This turns each pick in `highlights.md` into a finished 1080×1920 clip, `videos/<folder>/clips/clip1.mp4`, `clip2.mp4` and so on, numbered in score order. Next to each clip it writes `clipN-caption.txt`, the post caption: a short insight, the verbatim creator credit and 10 hashtags (rules in `playbooks/captions.md`). Each clip is just the footage plus word-by-word captions with the current word highlighted. There's no hook title, credit or other text on screen; credits go in the post caption. Animated or diagram clips use blur-fill framing, and `speaker` clips are cropped around the face. Claude first writes any misheard words to `caption-fixes.txt` (`wrong => right`), then checks the result. Run on its own (to fix a clip, or after `/clip --review`), it asks you to approve. Then it deletes the working files and queues any clips not yet scheduled. A re-rendered clip that's already queued keeps its slot.

### Posting to Instagram (10am, 1pm and 5pm)

A background job on this Mac posts at **10:00, 13:00 and 17:00** every day, Melbourne/Sydney time (the Mac's clock). Each run posts the earliest `not-posted` clip in `release-schedule.md` whose slot has passed. It's published as a Reel with `clipN-caption.txt` as the caption, then marked `posted`, with the link logged in the video's `posts.md` and `logs/post.log`. No Claude session or terminal needs to be open.

#### How a post works

```
10:00 / 13:00 / 17:00  launchd starts scripts/post_instagram.py
         │
         ├─ picks the due clip from release-schedule.md, checks the video + caption files
         │
         ├─ scripts/tunnel.py
         │    copies clipN.mp4 to an empty temp folder under a random name
         │    serves ONLY that file on 127.0.0.1 (everything else → 404)
         │    cloudflared opens a free quick tunnel → https://<random>.trycloudflare.com/<random>.mp4
         │    downloads the file back through the tunnel and checks it matches (≈90s while DNS comes up)
         │
         ├─ Instagram Graph API (graph.facebook.com)
         │    POST /{ig-user-id}/media   media_type=REELS, video_url=<tunnel link>, caption=…
         │    Instagram downloads the clip from the tunnel; poll status until FINISHED (≈1 min)
         │
         ├─ tunnel closed, temp copy deleted (always, even on failure)
         │
         └─ POST /{ig-user-id}/media_publish → Reel is live → mark posted, log link, text ⏹
```

**Why a tunnel:** Instagram can take a video two ways. We could push the file to its upload server (`rupload.facebook.com`), but that rejected about half of our uploads, and every scheduled one, with an unexplained `ProcessingFailedError`. The other way is to give Instagram a link and let it download the file. That worked first time, so it's the default. The tunnel gives the clip a temporary public link without any cloud storage or account: it exists only for the 2–3 minutes of the job, the link is random, and nothing but that one file is reachable. Your Instagram token never goes through it. The push method is still available with `INSTAGRAM_UPLOAD_METHOD=resumable` in `.env`, but isn't recommended.

**Testing without posting:**

```
.venv/bin/python scripts/post_instagram.py --dry-run [--as-of "2026-11-14 17:00"]   # what would post, and the caption
.venv/bin/python scripts/post_instagram.py --test-tunnel <clip.mp4>         # tunnel only; Instagram not contacted
.venv/bin/python scripts/post_instagram.py --test-ig-download <clip.mp4>    # Instagram downloads + processes; NOT published
```

Each run makes one attempt. If it fails, the clip stays `not-posted` and the next run tries again.

**Phone texts** (iMessage to `NOTIFY_IMESSAGE_TO` in `.env`): ▶️ when the job starts, ⏹ when it finishes (with what it posted), ⚠️ if it fails. Following the account on your personal Instagram with post notifications on also gives a native push when each Reel goes live.

```
scripts/scheduler.sh status       # on/off, what's posted, what's next, recent log
scripts/scheduler.sh install      # turn on (or resume)
scripts/scheduler.sh uninstall    # turn off (pause)
scripts/scheduler.sh run-now      # run the job now (posts only if a clip is due)
scripts/scheduler.sh test-alert   # send test texts; click Allow if macOS asks about Messages
```

In Claude, `/post` does the same: `status` (default), `dry-run`, `now`, `test-alert`, `pause`, `resume`.

**The queue** (`scripts/schedule.py`). Use it instead of hand-editing `release-schedule.md`: it waits for a post that's running, so the two never edit the file at once.

```
.venv/bin/python scripts/schedule.py list                 # the queue, with the next slot marked
.venv/bin/python scripts/schedule.py add videos/<folder>  # queue a video's clips at the next free slots
.venv/bin/python scripts/schedule.py respace              # move all unposted clips onto consecutive slots from now
```

To change the posting times, edit `SLOTS` in `scripts/schedule.py`, then run `scripts/scheduler.sh install` and `schedule.py respace`.

**`.env` needs:** `INSTAGRAM_ACCESS_TOKEN` (never-expiring system-user token from the Meta app), `INSTAGRAM_USER_ID` and `NOTIFY_IMESSAGE_TO`. Optional: `INSTAGRAM_UPLOAD_METHOD` (`tunnel`, the default, or `resumable`).

**Also needs:** `cloudflared` (`brew install cloudflared`). It runs only during the job, not as a background service.

**For it to keep running:**
- The Mac is on, online and you're logged in at 10:00, 13:00 and 17:00. A locked screen is fine. If it's asleep, the post goes out when it wakes. To wake it automatically, run `sudo pmset repeat wakeorpoweron MTWRFSU 09:58:00` (macOS allows only one repeating wake time, so 17:00 relies on the Mac being awake or woken).
- The repo stays at this path.
- The `.mp4` clips aren't deleted before they're posted. They only exist on this Mac.

Missed slots are caught up one clip per run, never two at once.

### Permissions for unattended runs

So `/clip` can write its files without asking, add this to `.claude/settings.json` (you add it yourself: Claude isn't allowed to change its own permissions):

```json
{
  "permissions": {
    "allow": [
      "Bash(.venv/bin/python scripts/ingest.py:*)",
      "Bash(.venv/bin/python scripts/render.py:*)",
      "Bash(.venv/bin/python scripts/schedule.py:*)",
      "Edit(./videos/**)",
      "Edit(./knowledge/**)"
    ],
    "deny": ["Read(./.env)", "Edit(./.env)"]
  }
}
```

### One-time setup

```
brew install yt-dlp deno uv ffmpeg-full cloudflared
uv python install 3.12
uv venv --python 3.12
source .venv/bin/activate
uv pip install -r requirements.txt
```

---

## Workflow at a glance

1. **Pick a source.** A new or classic video from a creator in `knowledge/creators/`.
2. **Run `/clip <url>`.** One sweep creates `videos/creator_video-slug/` (`source.md`, `transcript.md`, `highlights.md`), renders the clips and their captions into `clips/`, checks them, and queues them in `release-schedule.md`. Media stays out of git.
3. **Post.** The 10:00, 13:00 and 17:00 job posts the queue to Instagram in order, with each clip's caption file. Queue a new video before the schedule runs out (three clips a day).
4. **Learn.** Add what worked (or didn't) to `analytics/` and update the playbooks.

---

## Conventions

- **Everything is Markdown.** Plain `.md` files so they're readable by people and easy for Claude to search and edit.
- **Folder names:** lowercase, hyphenated. Video folders are `creator_video-slug`; clips are `clip1`, `clip2`…
- **Timestamps:** `HH:MM:SS` against the original upload, so anyone can jump to the moment.
- **Always credit the creator.** Every post caption names the creator and links the source video. Credits are not burned into the video.
- **No media in git.** Each video keeps finished clips in `clips/`, plus working files in `media/` until the clips are approved. Those folders, plus video, audio, project files and large images anywhere, are ignored by `.gitignore`.
- **Keep facts checked.** If a caption makes a science claim, it should match the source or a note in `knowledge/topics/`.

---

## Working with Claude

- `CLAUDE.md` holds the standing instructions: channel voice, editing rules, where things live.
- Skills in `.claude/skills/` are reusable workflows Claude can run on request (for example "find highlights in this transcript").
- Knowledge base files are written so Claude can pull from them when drafting captions, choosing clips or checking facts.

---

## Respecting creators

We clip other people's work, so we:

- credit the creator and link the original in every post,
- add commentary, context or editing that transforms the clip rather than reposting it,
- honour any takedown or opt-out request promptly, and log it in the creator's file in `knowledge/creators/`.
