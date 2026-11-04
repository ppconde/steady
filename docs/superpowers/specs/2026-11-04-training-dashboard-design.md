# modform — Garmin training dashboard on a Raspberry Pi — design

Date: 2026-11-04 · Status: draft for review · Project name: **modform** ("mod" for mid-century modern, "form" for training form)

## Intent

A self-hosted dashboard on the owner's Raspberry Pi that answers two questions about their training,
looking back over the last week and month:

1. **Am I improving?** Running: faster pace at the same heart rate. Strength: more reps, time or weight
   on the same exercises.
2. **Am I overtraining?** Judged from recovery (HRV, resting heart rate, sleep) against the owner's own
   normal, and from how hard the recent weeks were.

The owner's goal is general health. They train with a Garmin Forerunner 965 and do HIIT/strength,
running and volleyball, with 1–2 rest days a week. Their days are already decided, so the dashboard is
a **review of what happened**, not a planner or a daily "train hard today" coach.

Everything runs on the Pi. Nothing leaves it except the Garmin Connect sync. It costs nothing to run.

## Who and how it's used

- One person, the owner. Opened in a browser on the home network, on laptop or phone.
- Read once or twice a day, after the morning and evening reviews have been written.
- Sometimes the owner asks for a review of a different period (last month, custom dates) and is happy
  to wait 1–2 minutes for it.

## Goals

- One screen that answers "improving?" and "overtraining?" at a glance, with the numbers behind them.
- A short written review ("Claude's take") produced automatically twice a day, plus on demand.
- History: step back through past weeks and read the review written at the time.
- Works with whatever the owner records, including sports outside the usual three.
- Mid-century poster look (see Visual design).

## Non-goals

- No planning, no future sessions, no workout suggestions, nothing sent to the watch.
- No Grafana. garmin-grafana is used only for sync and storage.
- No accounts, no login, no multi-user.
- No access from outside the home network, except through the owner's existing PiVPN (no ports opened for this project).
- No MCP server.
- No paid services except the Claude API for writing the review (owner's decision, 2026-11-04:
  reversed the earlier local-model choice). Expected cost under $1/month.

## Anti-goals (would make it a failure even if it works)

- Numbers or verdicts invented by the language model. The model never decides anything; it only words
  findings the code has already computed.
- Flagging the owner's normal routine as a problem (e.g. "two hard days in a row" every Thursday–Friday
  when that's their usual pattern and they recover from it).
- Treating planned or guessed sessions as data. Only recorded activities count.
- An empty or broken review panel because the model failed.
- Weakening the Pi's security posture (open database ports, default passwords).

## Constraints

- **Hardware:** Raspberry Pi 4 Model B, **4 GB RAM**, boots from / stores on an SSD.
- **Language:** Python everywhere (owner's decision).
- **Data source:** Garmin Connect via the unofficial `python-garminconnect` library, **≥ 0.3.20**
  (older versions predate fixes to Garmin's 2026 login changes and debug logging of API responses).
  Garmin offers no push/webhooks for personal use, so data arrives by polling.
- **Memory budget:** sync + InfluxDB + dashboard app ≈ 0.5–1 GB. No model runs on the Pi.
- **Data leaving the Pi:** only the review input (computed findings + the week's summary, see below)
  goes to Anthropic's API. No Garmin credentials, raw GPS or per-second data.
- **Network:** local network only, served at `http://raspberry.local:<port>`. Port 80 is taken by Pi-hole's
  web UI, so the dashboard uses another port (e.g. 8080). Reachable from outside via the owner's PiVPN.
- **Other services on the Pi:** Pi-hole and PiVPN (light, always on). An occasional Minecraft server
  (currently off for a while) uses GB of RAM; with no local model this no longer matters.
- **Fresh install:** nothing Garmin-related is on the Pi yet. Install garmin-grafana's sync + InfluxDB
  from scratch and run its historical backfill once at setup.

## How it's built (decided)

All services in one **Docker Compose** file on the Pi:

| Service | What | Notes |
|---|---|---|
| `garmin-fetch-data` | garmin-grafana's sync container | Pinned image/version, not `:latest`. Patched as below. |
| `influxdb` | InfluxDB 1.11 | **No published port** (internal network only). Non-default password. |
| `dashboard` | New Python app: analysis + web page + scheduler | Serves one HTML page with plain JS/CSS. No frontend build step. |

Security fixes carried over from the review of garmin-grafana's example setup:
- Remove InfluxDB's published port and change its password.
- Pin every image version.
- Garmin token folder owned by uid 1000, `chmod 700` (the upstream easy-install script uses `777`;
  don't use that script).
- Don't store the Garmin password (not even base64). Log in once interactively; only the token is kept.
- Enable 2FA on the Garmin account.

### Patch to garmin-grafana's sync

garmin-grafana only fetches per-exercise sets (exercise, reps, duration, weight) for activities whose
type contains `strength`. The owner records most gym sessions as **HIIT**, which in Garmin Connect
lists exercises with reps and times but no weights. Extend that filter so HIIT activities also get
their exercise sets fetched (`garmin_fetch.py`, the `'strength' in activity_type_key` check).
Verify with a real HIIT activity that reps/durations come through; if Garmin returns nothing for HIIT,
the strength tile falls back to "not enough data" (see Edge cases).

## What the analysis computes (decided)

All in Python, from InfluxDB. The language model sees none of the raw data.

### Improving — running
- Metric: **pace at a fixed heart rate** (default 140 bpm; band e.g. 135–145 bpm), per run, trended
  over the last 6 weeks.
- Computed from the **per-second activity samples** garmin-grafana already stores for GPS activities
  (it fetches them by default for its GPS track panels): average pace over the samples where HR is in
  the band. If a run has fewer than ~5 minutes in the band, it's skipped. Runs without samples
  (e.g. treadmill without GPS) fall back to whole-run average pace and HR only if the average HR is in
  the band. (Claude's call.)
- **Exclude runs that start within 2 hours after a HIIT or strength session** from this trend (the owner
  usually runs straight after Thursday HIIT; those runs start tired with raised HR). They still count
  in weekly load and appear in the week row.
- Shown as: current value, change over 6 weeks, small trend line.

### Improving — strength
- Per exercise, compare the **best set this month vs last month**, using whatever was recorded:
  reps, duration, or weight. An exercise is only compared with itself.
- Skip exercises that don't appear in both periods (new or rare ones).
- Shown as: "N of M exercises up vs last month", plus the 3–4 biggest changes up or down.
- Works for both HIIT and Strength activity types.

### Improving — verdict
- **Yes / No / Mixed**, with one line of why. Derived from the running and strength results by a simple
  rule in code (e.g. both up → Yes, both down → No, otherwise Mixed; "not enough data" when neither
  has data).

### Overtraining — gauge
- Three positions: **fresh / normal / strained**.
- Inputs: overnight HRV, resting HR and sleep, each compared with the owner's own baseline
  (rolling window, e.g. 4–8 weeks), plus how hard the last 7 days were compared with their usual week.
- Garmin's own readiness and training-status values may be used as extra inputs, not displayed as the
  answer.
- **How they combine (Claude's call):** recovery decides, load only adds weight.
  - A recovery signal is "off" when that night's value is outside the owner's baseline band
    (HRV below, resting HR above, sleep well below).
  - **Strained:** 2+ recovery signals off on 2+ of the last 3 nights, **or** last-7-days load clearly
    above the usual week **and** at least 1 recovery signal off.
  - **Fresh:** no recovery signals off in the last 3 nights and last-7-days load at or below the usual week.
  - **Normal:** everything else.
  - A heavy week that matches the usual pattern is not, by itself, a reason for "strained". Load alone,
    with recovery fine, never gives "strained".

### Usual pattern
- Learned from the last ~8 weeks of recorded activities: typical hard days, typical weekly load,
  typical back-to-back hard days. Used so the review says "your usual hard stretch, recovered fine"
  instead of raising a warning about the normal routine. Adapts automatically when the routine
  changes. No schedule is written down anywhere.

### Effort per day
- Each recorded activity gets an effort level (**Easy / Moderate / Hard**) from Garmin's training load
  and/or heart-rate data, not from its sport. Any sport works.

## The review text ("Claude's take")

- The code produces a short list of findings (the numbers above, in plain sentences).
- **Template path (always available):** the code turns findings into a paragraph using sentence
  templates. Instant, no model.
- **Claude path (on by default):** the findings plus a compact JSON summary of the period (the same
  report the dashboard shows: days, sessions, effort, nightly HRV/RHR/sleep, pace trend, exercise
  changes) go to the Claude API (`claude-sonnet-5-5`, low effort). Claude writes one paragraph
  (≤150 words) and may point out patterns it sees in that summary, but the verdicts and gauge stay
  the code's. Takes a few seconds.
- **Number check:** every number in Claude's text must appear in what it was sent; otherwise the
  template text is used. Cheap guard against invented figures.
- If the API key is missing, the call fails, times out, refuses, or fails the number check, the panel
  shows the template version. Never empty.
- The owner's goal is written once in a small config (e.g. "general health; improve running and
  strength") and included in Claude's instruction.
- Labelled **"Claude's take"**; a small "template" note shows when the fallback text was used.
- API key in `.env` (`ANTHROPIC_API_KEY`, file mode `600`). Owner should set a monthly spend limit
  in the Anthropic Console.

### When reviews are written
- **Automatically at ~07:30** (after overnight sleep/HRV has synced) and **~21:30** (after the day's
  activities have synced). Times configurable.
- **Skip a run if nothing new has synced** since the last review.
- Each review covers **the current week so far plus the trend over the last 4–6 weeks**.
- **Review button** on the dashboard: pick this week, last month, or a custom date range. Shows a
  "writing your review…" state and the text appears (streamed word by word if practical) when done.
- Every review is stored with its timestamp and period, so past weeks show the review written at
  the time.

### Periods (Claude's call)
- **"Month" means rolling 4 weeks**, not a calendar month, so "this month vs last month" is always
  4 weeks vs the 4 weeks before.
- Every analysis function takes a **period end date** (and length where relevant), so the same code
  serves the current week, past weeks and custom ranges.
- **Custom range or "last month" review:** strength compares the range with the same-length period
  right before it; the running trend covers the range, extended back to at least 6 weeks if the range
  is shorter; the gauge uses the last 3 nights of the range.

### Past weeks (Claude's call)
- Stepping back with ‹ › recalculates **every tile as of that week's end** (Sunday), using the
  baselines and usual pattern as they were then.
- The Claude's take shown for a past week is **the last scheduled review written during that week**.
- Custom-range reviews are kept in a separate "Past reviews" list (date written + period), not mixed
  into the week view.

## The screen (decided)

One page, style **B "color-block grid"** from the brainstorm. Reference mockup:
`.superpowers/brainstorm/91066-1793818998/content/blocks-v3.html` (fake data; the layout and look are
what's agreed, the numbers aren't).

Top to bottom:
1. **Header (black):** week number and dates, **‹ ›** arrows to step through past weeks, **Review** button.
2. **"Are you improving?"** (blue, wide): big Yes / No / Mixed and one line of why.
3. **"Overtraining?"** (pink): half-circle gauge fresh / normal / strained, with HRV and resting HR.
4. **Running** (mustard): pace at 140 bpm, 6-week trend line, change in s/km.
5. **Strength** (black, wide): "N/M exercises up vs last month" plus biggest changes.
6. **This week** (full width): one column per day, Mon–Sun. Each shows day, date, a block per recorded
   activity (sport + duration or distance), a 3-step effort bar and the effort in words. Days with two
   sessions stack. Rest days show "Rest". Days still to come in the current week are empty.
   Running, HIIT/strength and volleyball have fixed colors; any other sport shows its name in a
   neutral block.
7. **Claude's take** (full width): the latest review for the week shown, with when it was written.

### Visual design
- Inspired by mid-century poster design, specifically bold flat color blocks with strong symmetry and
  huge condensed type (owner's chosen reference: the second poster, "Different is Beautiful" style).
- Palette: cobalt blue `#2347A8`, black `#151515`, mustard `#F2A922`, pink `#F3A6B5`,
  red `#E8502F`, cream `#F4EEE1`, off-white `#FBF8F2`.
- Type: a heavy condensed display face for headlines and big numbers (mockup uses Anton) and a clean
  sans for text (mockup uses Work Sans). Uppercase only for short labels.
- Charts are geometric: half-circles, flat bars, thick single lines.
- Text must meet WCAG AA contrast (the mockup was checked; black text on the red needs the brighter
  `#E8502F`).
- Must work at phone width.

## Edge cases

- **Not enough history yet** (first weeks after setup): show "building your baseline" instead of a
  verdict; garmin-grafana can backfill history, so run a backfill at install.
- **No runs without prior HIIT in the period:** running tile shows "no comparable runs this period".
- **No exercise data for HIIT** (if Garmin doesn't return it): strength tile shows "not enough data".
- **Garmin login breaks** (it happens when Garmin changes its login): dashboard shows "last sync"
  time prominently so stale data is obvious; reviews skip because nothing new synced.
- **Missing sleep/HRV for a night** (watch not worn): gauge uses the data it has and says so.

## Left to the builder

- Python web framework (or stdlib), the dashboard app's internal structure, how the scheduler runs.
- Exact thresholds and baseline windows (sensible defaults, kept in one config).
- How fonts are served (self-host them so the page doesn't call Google from the LAN — preferred).
- Chart rendering approach (inline SVG suggested; no heavy chart library needed).
- Tests: at least one runnable check for the analysis rules (the 2-hour exclusion, the per-exercise
  comparison, the verdict rule).

## Calls made by Claude (not explicitly decided by the owner)

- Morning/evening times 07:30 and 21:30.
- Fixed heart rate 140 bpm for the running trend; 6-week window.
- 2-hour window for "run after HIIT".
- Best set month vs month for strength; skipping exercises not in both months.
- Week row Mon–Sun; ‹ › history arrows.
- Model `claude-sonnet-5-5` at low effort; Claude sees findings + period summary, not raw data.
- Number check on Claude's text.
- Self-hosting fonts.
- Template text as the always-available fallback.
- How the overtraining gauge combines its inputs (recovery decides, load only adds weight).
- Pace at 140 bpm from per-second samples, with a whole-run fallback.
- "Month" = rolling 4 weeks; custom ranges compared with the same-length period before.
- Past weeks recalculated as of their Sunday; custom reviews in a separate list.
- Project name "modform".
- Dashboard on port 8080 (Pi-hole has 80).
- Server-side refusal fallback (`fallbacks: "default"`) enabled on the API call.
