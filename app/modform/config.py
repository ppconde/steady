"""Every setting and threshold, read once from the environment."""
import os
from zoneinfo import ZoneInfo

INFLUX_URL = os.getenv("INFLUX_URL", "http://influxdb:8086")
INFLUX_USER = os.getenv("INFLUX_USER", "")
INFLUX_PASSWORD = os.getenv("INFLUX_PASSWORD", "")
INFLUX_DB = "GarminStats"
TZ = ZoneInfo(os.getenv("TZ") or "Europe/Lisbon")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5")
GOAL = os.getenv("GOAL", "General health; improve running and strength")
DB_PATH = os.getenv("DB_PATH", "/data/modform.db")
REVIEW_TIMES = tuple(os.getenv("REVIEW_TIMES", "07:30,21:30").split(","))

# Analysis thresholds
EFFORT_LOAD_MODERATE = 50
EFFORT_LOAD_HARD = 120
HR_LO, HR_HI = 135, 145  # pace-at-140 band
HR_MIN_S = 300  # seconds in band for a run to count
AFTER_STRENGTH_H = 2
BASELINE_MIN_NIGHTS = 14
BASELINE_DAYS = 42
LOAD_HIGH_FACTOR = 1.25
