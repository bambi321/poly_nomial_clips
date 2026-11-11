# Episodes

One folder per source video, created by `/clip <youtube-url>`.

Folder names are `YYYY-MM-DD_creator_video-slug`, using the video's upload date.

```
episodes/2026-11-04_example-channel_why-does-ice-float/
├── source.md        # Link, creator, publish date, length, chapters, description
├── transcript.md    # One sentence per line with timestamps, replay heat and scene cuts
├── highlights.md    # Claude's ranked clip picks (written by /clip)
├── posts.md         # What was posted, where and when, with links
├── media/           # Not in git
│   ├── source.mp4   #   the downloaded video (up to 1080p)
│   ├── info.json    #   full YouTube metadata
│   ├── words.json   #   a timestamp for every word, used for captions
│   └── scenes.json  #   times where the shot changes
└── renders/         # Not in git: finished 9:16 clips (Phase 2)
```

The `.md` files are committed. `media/` and `renders/` stay on this machine only, so a fresh clone has the notes but not the videos. Re-run `/clip` with the same link to download a video again.
