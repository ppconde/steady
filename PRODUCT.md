# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

One person, the owner, checking their own Garmin data on a phone or laptop, at home on the LAN or over PiVPN.

## Product Purpose

Steady answers two questions from the owner's Garmin data: "Am I improving?" (pace at 140 bpm, strength best-set per exercise, weight toward the Garmin Connect weight goal) and "Am I overtraining?" (fresh / normal / strained, from HRV, resting HR, sleep and training load). A written review from Claude is produced on demand, with a plain template fallback.

## Operating Context

- Runs on a Raspberry Pi 4: garmin-grafana sync → InfluxDB 1.11 → Python stdlib app serving one page on port 8080.
- The page is a weekly view with week navigation, a review panel (this week / last 4 weeks / custom range), and past reviews.
- Installed with `install.sh` (`curl | sh`).

## Capabilities and Constraints

- Static HTML/CSS/JS served by the app; no build step, no frontend framework, fonts self-hosted.
- Private: LAN/VPN only, no published ports besides 8080, no credentials stored besides the Garmin token.
- Only findings and the report summary go to Claude, never credentials or per-second data.

## Brand Commitments

- Name: Steady.

## Evidence on Hand

- Real data comes from the owner's Garmin account; `python -m steady --demo` serves plausible demo data. No testimonials or users beyond the owner.

## Product Principles

- Honest verdicts over flattery: say "mixed" or "not enough data" when that is the truth.
- No medical, diet, calorie or training-plan advice.
- Every number shown or written stays traceable to the owner's data.
- Private by default.
