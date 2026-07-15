import json
from pathlib import Path
from typing import Any

from app.config import RECORDINGS_DIR


def recording_dir(user_id: int, session_id: int) -> Path:
    return RECORDINGS_DIR / str(user_id) / f"session_{session_id}"


def wav_path(user_id: int, session_id: int, id_recordings: int) -> Path:
    return recording_dir(user_id, session_id) / f"recording_{id_recordings}.wav"


def json_path(user_id: int, session_id: int, id_recordings: int) -> Path:
    return recording_dir(user_id, session_id) / f"recording_{id_recordings}.json"


def save_metadata(metadata: dict[str, Any]) -> Path:
    path = json_path(
        int(metadata["user_id"]),
        int(metadata["session_id"]),
        int(metadata["id_recordings"]),
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def load_metadata(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def find_by_id_recordings(id_recordings: int) -> tuple[Path, dict[str, Any]] | None:
    if not RECORDINGS_DIR.exists():
        return None
    for path in RECORDINGS_DIR.rglob(f"recording_{id_recordings}.json"):
        metadata = load_metadata(path)
        if int(metadata.get("id_recordings", -1)) == id_recordings:
            return path, metadata
    return None


def id_recordings_exists(id_recordings: int) -> bool:
    found = find_by_id_recordings(id_recordings)
    if found is not None:
        return True
    if not RECORDINGS_DIR.exists():
        return False
    return any(RECORDINGS_DIR.rglob(f"recording_{id_recordings}.wav"))


def find_latest_by_user(user_id: int) -> tuple[Path, dict[str, Any]] | None:
    user_dir = RECORDINGS_DIR / str(user_id)
    if not user_dir.exists():
        return None

    candidates: list[tuple[float, Path, dict[str, Any]]] = []
    for path in user_dir.rglob("recording_*.json"):
        metadata = load_metadata(path)
        if int(metadata.get("user_id", -1)) != user_id:
            continue
        wav = wav_path(user_id, int(metadata["session_id"]), int(metadata["id_recordings"]))
        timestamp = wav.stat().st_mtime if wav.exists() else path.stat().st_mtime
        candidates.append((timestamp, path, metadata))

    if not candidates:
        return None
    _, path, metadata = max(candidates, key=lambda item: item[0])
    return path, metadata

