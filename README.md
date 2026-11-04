# Steady

Garmin training dashboard for a Raspberry Pi. It answers "am I improving?" (pace at 140 bpm, strength,
weight toward your goal) and "am I overtraining?", with a written review by Claude whenever you ask for one.

## Install on the Pi

```sh
curl -fsSL https://raw.githubusercontent.com/ppconde/steady/main/install.sh | sh
```

It installs git and Docker if they're missing, puts Steady in `~/steady`, and asks for:

- your Anthropic API key (optional; without it the review is a plain written summary)
- your training goal, time zone and, optionally, a target weight (otherwise your Garmin Connect weight goal is used)
- your Garmin email, password and 2FA code, once. Only the login token is kept.

Then it starts everything and backfills 6 months of history in the background.
Run the same command again to update. Settings live in `~/steady/.env`.

Dashboard: `http://<pi-name>.local:8080`, from your home network or VPN only; no ports need opening.
Set a monthly spend limit for the API key in the Anthropic Console.

## Weight

Log weigh-ins in Garmin Connect (a scale or by hand) and set a weight goal there. Weight counts toward
"Are you improving?" when your 7-day average moves 0.3 kg toward the goal, or stays within 1 kg of it.
It needs 2 weigh-ins in the last 7 days and 2 in the 4 weeks before.
