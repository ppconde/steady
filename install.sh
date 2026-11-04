#!/bin/sh
# Steady installer for a Raspberry Pi (or any Debian-like Linux box).
#
#   curl -fsSL https://raw.githubusercontent.com/ppconde/steady/main/install.sh | sh
#
# Installs git and Docker if missing, clones Steady to ~/steady (STEADY_DIR to change),
# asks for your keys, logs in to Garmin once (only the login token is kept), starts
# everything and backfills 6 months of history. Run it again any time to update.
set -eu

REPO=https://github.com/ppconde/steady.git
DIR=${STEADY_DIR:-$HOME/steady}

say() { printf '\n\033[1m==> %s\033[0m\n' "$*"; }
die() { printf '\n\033[31m%s\033[0m\n' "$*" >&2; exit 1; }

# ask VAR "Prompt" [default] [secret]: reads from the terminal even when piped from curl
ask() {
  printf '%s' "$2${3:+ [$3]}: " > /dev/tty
  if [ "${4:-}" = secret ]; then
    stty -echo < /dev/tty; IFS= read -r _a < /dev/tty || _a=; stty echo < /dev/tty; printf '\n' > /dev/tty
  else
    IFS= read -r _a < /dev/tty || _a=
  fi
  [ -n "$_a" ] || _a=${3:-}
  eval "$1=\$_a"
}

main() {
  [ -r /dev/tty ] || die "Run this from a terminal: it needs to ask you a few questions."
  if [ "$(id -u)" -eq 0 ]; then SUDO=; else SUDO=sudo; fi

  if ! command -v git >/dev/null 2>&1; then
    say "Installing git"
    command -v apt-get >/dev/null 2>&1 || die "Please install git, then run this again."
    $SUDO apt-get update -qq && $SUDO apt-get install -y -qq git
  fi

  if ! command -v docker >/dev/null 2>&1; then
    say "Installing Docker (official get.docker.com script)"
    curl -fsSL https://get.docker.com | $SUDO sh
    [ -z "$SUDO" ] || $SUDO usermod -aG docker "$(id -un)"  # docker without sudo from your next login
  fi
  if docker info >/dev/null 2>&1; then DOCKER=docker; else DOCKER="$SUDO docker"; fi

  if [ -d "$DIR/.git" ]; then
    say "Updating $DIR"
    git -C "$DIR" pull --ff-only -q
  else
    say "Downloading Steady to $DIR"
    git clone -q "$REPO" "$DIR"
  fi
  cd "$DIR"

  if [ -f .env ]; then
    say "Keeping your settings in $DIR/.env"
  else
    say "A few questions (Enter keeps the [default])"
    ask KEY "Anthropic API key for Claude's take (empty: plain written review)" "" secret
    ask GOAL "Your training goal, in a few words" "General health; improve running and strength"
    TZ_GUESS=$(cat /etc/timezone 2>/dev/null || timedatectl show -p Timezone --value 2>/dev/null || echo Europe/Lisbon)
    ask TZONE "Time zone" "$TZ_GUESS"
    PASS=$(od -An -N24 -tx1 /dev/urandom | tr -d ' \n')
    # shellcheck disable=SC1003  # strip characters .env quoting can't hold
    GOAL=$(printf '%s' "$GOAL" | tr -d '"$`\\')
    (umask 077 && cat > .env <<EOF
INFLUXDB_USER=steady
INFLUXDB_PASSWORD=$PASS
TZ=$TZONE
ANTHROPIC_API_KEY=$KEY
GOAL="$GOAL"
EOF
    )
    echo "Saved to $DIR/.env (only you can read it). Edit it later and re-run this script to apply."
  fi

  mkdir -p data/garminconnect-tokens data/app data/influxdb
  $SUDO chown 1000:1000 data/garminconnect-tokens data/app
  $SUDO chmod 700 data/garminconnect-tokens

  say "Building (a few minutes the first time)"
  $DOCKER compose build -q

  if [ -z "$($SUDO ls -A data/garminconnect-tokens)" ]; then
    say "Garmin login"
    echo "Steady asks for your Garmin email, password and 2FA code once. Only the login token is saved."
    $DOCKER compose up -d influxdb
    i=0
    until $DOCKER compose exec -T influxdb curl -sf http://localhost:8086/ping >/dev/null 2>&1; do
      i=$((i + 1)); [ $i -lt 30 ] || die "InfluxDB didn't start. See: $DOCKER compose logs influxdb"; sleep 2
    done
    $DOCKER compose run --rm -e MANUAL_START_DATE="$(date +%F)" fetch < /dev/tty \
      || die "Garmin login failed. Run this script again to retry."
  fi

  say "Starting Steady"
  $DOCKER compose up -d

  if [ ! -f data/.backfilled ]; then
    say "Backfilling 6 months of Garmin history in the background"
    $DOCKER compose run -d --rm -e MANUAL_START_DATE="$(date -d '6 months ago' +%F)" fetch >/dev/null
    touch data/.backfilled
    echo "This takes a while; the dashboard fills in as it goes."
  fi

  IP=$(hostname -I 2>/dev/null | awk '{print $1}'); HOST=$(hostname); HOST=${HOST%.local}
  say "Done. Open http://$HOST.local:8080${IP:+ or http://$IP:8080} (home network or VPN only)."
  [ -n "$(grep '^ANTHROPIC_API_KEY=.' .env || true)" ] && echo "Tip: set a monthly spend limit for your API key in the Anthropic Console."
  return 0
}

main "$@"  # everything above is read before anything runs, so `curl | sh` is safe
