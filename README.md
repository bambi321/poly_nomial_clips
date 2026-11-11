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
├── clips/                     # One folder per source video we've worked on
│   └── YYYY-MM-DD_creator_video-slug/
│       ├── source.md          # Link, title, creator, publish date, length
│       ├── transcript.md      # Transcript (or a link to it)
│       ├── highlights.md      # Candidate moments with timestamps and why they work
│       └── posts.md           # What was cut, where it was posted, captions, links
│
├── templates/                 # Blank versions of the files above to copy from
│
└── analytics/                 # Notes on performance: what hooked, what flopped, lessons learned
```

Folders get created as we need them, so not all of these exist yet.

---

## Workflow at a glance

1. **Pick a source.** A new or classic video from a creator in `knowledge/creators/`.
2. **Log it.** Create `clips/YYYY-MM-DD_creator_video-slug/` from `templates/` and fill in `source.md`.
3. **Find highlights.** Pull the transcript and run the highlight-finding skill to produce `highlights.md`.
4. **Edit.** Cut clips following `playbooks/editing-style.md`. Media stays out of git.
5. **Caption and post.** Write hooks and captions, publish, and record everything in `posts.md`.
6. **Learn.** Add what worked (or didn't) to `analytics/` and update the playbooks.

---

## Conventions

- **Everything is Markdown.** Plain `.md` files so they're readable by people and easy for Claude to search and edit.
- **Folder names:** lowercase, hyphenated (`video-slug`), dates as `YYYY-MM-DD`.
- **Timestamps:** `HH:MM:SS` against the original upload, so anyone can jump to the moment.
- **Always credit the creator.** Every clip links back to the source video and channel.
- **No media in git.** Video, audio, project files and large images are ignored by `.gitignore`.
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
