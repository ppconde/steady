# modform

Garmin training dashboard for a Raspberry Pi: "am I improving?" and "am I overtraining?",
with a twice-daily review written by Claude.

## Setup on the Pi

```sh
cp .env.example .env && chmod 600 .env        # then set INFLUXDB_PASSWORD and ANTHROPIC_API_KEY
mkdir -p data/garminconnect-tokens data/app
sudo chown 1000:1000 data/garminconnect-tokens data/app && chmod 700 data/garminconnect-tokens
docker compose run --rm fetch                  # one-time interactive Garmin login (2FA); only the token is kept
docker compose up -d --build
docker compose run --rm -e MANUAL_START_DATE=$(date -d '6 months ago' +%F) fetch   # one-off backfill
```

Dashboard: `http://raspberry.local:8080` (LAN or PiVPN only). Set a monthly spend limit for the API key in the Anthropic Console.
