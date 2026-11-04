# Design: Conceptual Sketch

Steady's dashboard reads as a designer's working sketch sheet: hand-ruled ink boxes on grainy paper, graphite notes, crosshatching, and one printed green that only marks meaning.

## Tokens (`app/steady/static/style.css` `:root`)

| Token | Value | Job |
|---|---|---|
| `--paper` | `#ECEAE3` + SVG grain | page ground, label chips on hatching |
| `--ink` | `#1D1C1A` | text, box strokes, buttons, crosshatch |
| `--graphite` | `#55524C` | secondary text (≥4.5:1 on paper), second box stroke, hatch |
| `--pencil` | `#A39F95` | rules, future days, inactive marks. Never text |
| `--green` | `#18693F` | meaning only: verdict yes, improving rows, fresh, today, hover, focus |

## Type
- **Cabin Sketch 700**: display lettering and big numbers (verdict, week, pace, kg, headings).
- **Kalam 400/700**: handwritten labels, notes, the review text.
- **Work Sans 400–700**: tabular data and inputs.
All self-hosted from `static/fonts` (OFL texts beside them).

## Marks
- **Ruled box** (`.rule`): two pseudo-element strokes, wobbled by the inline SVG filters `#rough-a` and `#rough-b`. Text is never filtered.
- **Hatching encodes data**: run = diagonal graphite hatch, strength/HIIT = ink crosshatch, other = dots, rest = dashed outline, future = faint pencil outline. Effort is shown as 1–3 tally marks.
- **Gauge**: hatched zones that get denser from fresh to strained, with an ink needle. Don't filter the needle: a vertical line has a zero-width box, and the filter erases it.
- **Verdict scribble**: a loose ellipse in `--mark` (green when the verdict is yes).
- **Controls**: ink-filled buttons with uneven radii; hover turns them green with a slight tilt; focus shows a dashed green outline.

## Layout
3-column grid with 22px gaps, max-width 1000px. Below 640px it becomes one column, and day rows become horizontal rows.
