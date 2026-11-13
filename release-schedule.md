# Release schedule

Three posts a day, at **10:00, 13:00 and 17:00** Melbourne/Sydney time (the Mac's clock). Clips post in the order listed. (clip1 was a one-off trial at 8:35pm on Thu 12 Nov.)

**Status values:** `not-posted` · `posted`

The post job runs at each slot, posts the earliest clip whose time has passed, and marks it `posted`. `/clip <url>` queues new clips at the bottom, on the next free slots. Each clip's post caption (insight, creator credit and 10 hashtags) is in its caption file.

Edit the queue with `scripts/schedule.py` (`list`, `add`, `respace`) rather than by hand, so it never clashes with a post in progress. The slot times are `SLOTS` in that script.

| Date | Time | Clip | Title | Creator | File | Caption | Status |
|------|------|------|-------|---------|------|---------|--------|
| 2026-11-12 (Thu) | 20:35 | clip1 | Even a "small" nuclear war starves 250 million | Kurzgesagt – In a Nutshell | [clip1.mp4](videos/kurzgesagt-in-a-nutshell_what-happens-after-nuclear-war/clips/clip1.mp4) | [caption](videos/kurzgesagt-in-a-nutshell_what-happens-after-nuclear-war/clips/clip1-caption.txt) | posted |
| 2026-11-13 (Fri) | 10:00 | clip2 | 4,400 bombs: the worst case, by the numbers | Kurzgesagt – In a Nutshell | [clip2.mp4](videos/kurzgesagt-in-a-nutshell_what-happens-after-nuclear-war/clips/clip2.mp4) | [caption](videos/kurzgesagt-in-a-nutshell_what-happens-after-nuclear-war/clips/clip2-caption.txt) | posted |
| 2026-11-13 (Fri) | 13:00 | clip3 | The brutal maths of how many people Earth can feed | Kurzgesagt – In a Nutshell | [clip3.mp4](videos/kurzgesagt-in-a-nutshell_what-happens-after-nuclear-war/clips/clip3.mp4) | [caption](videos/kurzgesagt-in-a-nutshell_what-happens-after-nuclear-war/clips/clip3-caption.txt) | posted |
| 2026-11-13 (Fri) | 17:35 | clip4 | Why the world's bread baskets would go empty | Kurzgesagt – In a Nutshell | [clip4.mp4](videos/kurzgesagt-in-a-nutshell_what-happens-after-nuclear-war/clips/clip4.mp4) | [caption](videos/kurzgesagt-in-a-nutshell_what-happens-after-nuclear-war/clips/clip4-caption.txt) | posted |
| 2026-11-14 (Sat) | 10:00 | clip5 | The countries that might survive a nuclear winter | Kurzgesagt – In a Nutshell | [clip5.mp4](videos/kurzgesagt-in-a-nutshell_what-happens-after-nuclear-war/clips/clip5.mp4) | [caption](videos/kurzgesagt-in-a-nutshell_what-happens-after-nuclear-war/clips/clip5-caption.txt) | not-posted |
| 2026-11-14 (Sat) | 13:00 | clip6 | The fire cloud that's deadlier than the mushroom cloud | Kurzgesagt – In a Nutshell | [clip6.mp4](videos/kurzgesagt-in-a-nutshell_what-happens-after-nuclear-war/clips/clip6.mp4) | [caption](videos/kurzgesagt-in-a-nutshell_what-happens-after-nuclear-war/clips/clip6-caption.txt) | not-posted |
| 2026-11-14 (Sat) | 17:00 | clip1 | You're a tiny antimatter factory (thanks, bananas) | Veritasium | [clip1.mp4](videos/veritasium_what-happens-if-you-drop-0-125-grams-of-antimatt/clips/clip1.mp4) | [caption](videos/veritasium_what-happens-if-you-drop-0-125-grams-of-antimatt/clips/clip1-caption.txt) | not-posted |
| 2026-11-15 (Sun) | 10:00 | clip2 | Everything you see survived a one-in-a-billion accident | Veritasium | [clip2.mp4](videos/veritasium_what-happens-if-you-drop-0-125-grams-of-antimatt/clips/clip2.mp4) | [caption](videos/veritasium_what-happens-if-you-drop-0-125-grams-of-antimatt/clips/clip2-caption.txt) | not-posted |
| 2026-11-15 (Sun) | 13:00 | clip3 | Could you really steal antimatter from CERN? | Veritasium | [clip3.mp4](videos/veritasium_what-happens-if-you-drop-0-125-grams-of-antimatt/clips/clip3.mp4) | [caption](videos/veritasium_what-happens-if-you-drop-0-125-grams-of-antimatt/clips/clip3-caption.txt) | not-posted |
| 2026-11-15 (Sun) | 17:00 | clip4 | "If you enter while it's running, you die in 10 seconds" | Veritasium | [clip4.mp4](videos/veritasium_what-happens-if-you-drop-0-125-grams-of-antimatt/clips/clip4.mp4) | [caption](videos/veritasium_what-happens-if-you-drop-0-125-grams-of-antimatt/clips/clip4-caption.txt) | not-posted |
| 2026-11-16 (Mon) | 10:00 | clip5 | The most violent process physics allows | Veritasium | [clip5.mp4](videos/veritasium_what-happens-if-you-drop-0-125-grams-of-antimatt/clips/clip5.mp4) | [caption](videos/veritasium_what-happens-if-you-drop-0-125-grams-of-antimatt/clips/clip5-caption.txt) | not-posted |
| 2026-11-16 (Mon) | 13:00 | clip6 | How much does a gram of antimatter cost? | Veritasium | [clip6.mp4](videos/veritasium_what-happens-if-you-drop-0-125-grams-of-antimatt/clips/clip6.mp4) | [caption](videos/veritasium_what-happens-if-you-drop-0-125-grams-of-antimatt/clips/clip6-caption.txt) | not-posted |
| 2026-11-16 (Mon) | 17:00 | clip7 | The physicist robbed of a Nobel Prize | Veritasium | [clip7.mp4](videos/veritasium_what-happens-if-you-drop-0-125-grams-of-antimatt/clips/clip7.mp4) | [caption](videos/veritasium_what-happens-if-you-drop-0-125-grams-of-antimatt/clips/clip7-caption.txt) | not-posted |
