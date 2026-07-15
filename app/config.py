import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
RECORDINGS_DIR = BASE_DIR / "recordings"
CONFIG_DIR = BASE_DIR / "config"
AUDIO_SETTINGS_PATH = CONFIG_DIR / "audio_settings.json"

REMOTE_RECORDINGS_URL = os.getenv(
    "REMOTE_RECORDINGS_URL",
    "https://akcitapi.duckdns.org/api/v1/recordings",
)

SAMPLE_RATE = 48_000
BIT_DEPTH = 24
CHANNELS_DEFAULT = 1
FORMAT = "wav"
