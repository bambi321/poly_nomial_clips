# Post captions

Every clip gets a caption file next to it: `videos/<video>/clips/clipN-caption.txt`. That file is exactly what gets pasted (or posted) as the caption. It has three parts, in this order, separated by blank lines.

## 1. Insight (required)

A short, plain-English explanation of what the clip is about and why it's interesting.

- **No more than 3 sentences.**
- Simple words. Write for someone scrolling, not for a scientist.
- Only state what the clip itself says. Don't add facts or numbers the source doesn't make. Keep the source's hedges ("could", "up to", "may").
- If a claim in the clip is flagged in `highlights.md` (science check), attribute it to the video ("as the video explains…") instead of stating it as fact.

## 2. Credit (required, verbatim)

Always use this line exactly, filling in the creator's YouTube handle from `source.md`:

```
Full credits for the original video go to @<youtube-handle>
```

Never skip it, shorten it or reword it.

**Never write "YouTube" anywhere in a caption**, including links (`youtube.com/...`) and hashtags (`#youtube`). Instagram's API rejects any upload whose caption contains the word, with an unhelpful `ProcessingFailedError`. The posting script refuses such captions.

## 3. Hashtags (required)

Exactly **10** hashtags on one line, separated by spaces:

- 1–2 broad ones (`#science`, `#education`)
- 4–5 about the clip's topic
- 1 for the creator (e.g. `#kurzgesagt`)
- 1–2 discovery tags (`#sciencefacts`, `#didyouknow`)
- lowercase, no duplicates, no platform names (`#tiktok`, `#reels`, `#youtube`)

## Example

```
After a nuclear blast, burning cities create giant fire clouds called pyrocumulonimbus clouds. These push soot high into the stratosphere, above the weather. With no rain up there to wash it out, the soot can stay for years and block sunlight.

Full credits for the original video go to @kurzgesagt

#science #physics #weather #nuclearwinter #kurzgesagt #atmosphere #climatescience #clouds #sciencefacts #education
```
