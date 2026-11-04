# Design

Mid-century colour blocks: flat tiles of blue, mustard, pink, red, black and cream on a cream sheet with a white mat. Anton for numbers and headings (uppercase), Work Sans for text. No gradients, shadows or rounded corners; the only curves are the verdict discs and the gauge.

## Tokens
- `--blue #2347A8` · `--black #151515` · `--mustard #F2A922` · `--pink #F3A6B5` · `--red #E8502F` · `--cream #F4EEE1` · `--white #FBF8F2`
- Mustard means "good/now" (up ticks, today's sleep bar); red means "attention" (down marks, today underline, stale sync).

## Tiles
- **Verdict** (blue, 2 cols): big word + arrow, note, mustard/red discs at the bottom edge; right column is a scorecard of white cards, one per signal (running, strength, weight) with a mark: tick on mustard (up), cross on red (down), squiggle (flat), dashed circle (no call).
- **Gauge** (pink), **Running** (mustard), **Strength** (black, 2 cols), **Week** (white, 3 cols), **Weight** (pink).
- **Sleep** (black, 2 cols): last night's total and score, stage bar (deep blue, REM pink, light cream, awake red) with a key; each night this week as cream bars on a 10 h scale, today in mustard.
- **Claude's take** (cream, 3 cols).

Mobile (≤640px): one column; verdict discs move to the top-right corner.
