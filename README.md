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
│   ├── editing-style.md       # Pacing, captions, fonts, colours, music, branding
│   ├── clip-workflow.md       # Source video → shortlist → edit → review → publish
│   └── fair-use.md            # Attribution, transformation and takedown policy
│
├── episodes/                  # Everything for each source video, one folder per video
│   └── YYYY-MM-DD_creator_video-slug/
│       ├── source.md          # Link, title, creator, publish date, length, chapters
│       ├── transcript.md      # Timed transcript with replay heat
│       ├── highlights.md      # Ranked clip picks with timestamps and why they work
│       ├── posts.md           # What was posted, where, captions, links
│       ├── media/             # Downloaded video, metadata, word timings (not in git)
│       └── renders/           # Finished vertical clips (not in git)
│
├── templates/                 # Blank versions of the files above to copy from
│
├── scripts/                   # Pipeline scripts (e.g. ingest.py: download + transcribe)
├── requirements.txt           # Python packages for the pipeline
│
├── docs/                      # Diagrams and pages (e.g. the pipeline walkthrough)
│
└── analytics/                 # Notes on performance: what hooked, what flopped, lessons learned
```

Folders get created as we need them, so not all of these exist yet.

---

## Automation pipeline

**Interactive walkthrough:** [Clip Pipeline](https://claude.ai/artifact/9Gka2iJTwiBGYYFyRnyENW) (source: `docs/clip-pipeline.html`)

YouTube URL → download (yt-dlp) → transcribe (WhisperX) → find highlights (Claude) → cut & reframe to 9:16 (ffmpeg + MediaPipe) → captions & branding (ffmpeg / Remotion) → **review & approve (you)** → publish (YouTube / Instagram / TikTok APIs) → learn from analytics.

### Using `/clip`

In Claude Code, from this repo:

```
/clip https://www.youtube.com/watch?v=<id>
```

This downloads the video, transcribes it with word timings, reads YouTube's most-replayed heatmap, and has Claude write ranked picks to `episodes/<folder>/highlights.md`. The video itself is saved in `episodes/<folder>/media/` and stays out of git. It runs on your Claude subscription, so no API key is needed. Automatic cutting (Phase 2) is next.

### One-time setup

```
brew install yt-dlp deno uv ffmpeg-full
uv python install 3.12
uv venv --python 3.12
source .venv/bin/activate
uv pip install -r requirements.txt
```

---

## Workflow at a glance

1. **Pick a source.** A new or classic video from a creator in `knowledge/creators/`.
2. **Log it.** `/clip <url>` creates `episodes/YYYY-MM-DD_creator_video-slug/` with `source.md` and `transcript.md`, and saves the video in its `media/` folder.
3. **Find highlights.** The same `/clip` run has Claude write ranked picks to `highlights.md`.
4. **Edit.** Cut clips following `playbooks/editing-style.md` into the episode's `renders/` folder. Media stays out of git.
5. **Caption and post.** Write hooks and captions, publish, and record everything in `posts.md`.
6. **Learn.** Add what worked (or didn't) to `analytics/` and update the playbooks.

---

## Conventions

- **Everything is Markdown.** Plain `.md` files so they're readable by people and easy for Claude to search and edit.
- **Folder names:** lowercase, hyphenated (`video-slug`), dates as `YYYY-MM-DD`.
- **Timestamps:** `HH:MM:SS` against the original upload, so anyone can jump to the moment.
- **Always credit the creator.** Every clip links back to the source video and channel.
- **No media in git.** Each episode keeps its video and data in `media/` and finished clips in `renders/`. Those folders, plus video, audio, project files and large images anywhere, are ignored by `.gitignore`.
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
