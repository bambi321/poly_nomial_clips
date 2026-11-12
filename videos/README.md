# Videos

One folder per source video, created by `/clip <youtube-url>`, which also renders, captions and queues the clips in one sweep.

Folder names are `<creator>_<video-title>`, lowercase and hyphenated.

```
videos/kurzgesagt-in-a-nutshell_what-happens-after-nuclear-war/
├── source.md              # Link, creator, YouTube handle, publish date, length, chapters
├── transcript.md          # One sentence per line with timestamps, replay heat and scene cuts
├── highlights.md          # Claude's ranked clip picks: the plan /render follows
├── caption-fixes.txt      # Misheard words corrected in the on-screen captions
└── clips/
    ├── clip1.mp4          # Finished 9:16 clip (not in git)
    ├── clip1-caption.txt  # Its post caption: insight, creator credit, 10 hashtags
    ├── clip2.mp4
    ├── clip2-caption.txt
    └── …
```

Clips are numbered in score order: `clip1` is the strongest pick.

While a video is being worked on, it also has a `media/` folder holding the downloaded video, word timings and render check files. That folder is deleted once the clips are approved (`render.py --cleanup`), so a finished video folder holds only the files above.

Everything except the `.mp4` clips is committed. Caption rules live in `playbooks/captions.md`. To re-render a finished video, run `/render videos/<folder> --clips N`. It downloads and transcribes the source again first, because `media/` was cleaned up.
