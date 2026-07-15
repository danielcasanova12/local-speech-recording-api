import json
from typing import Any

import sounddevice as sd

from app.config import AUDIO_SETTINGS_PATH, CHANNELS_DEFAULT, SAMPLE_RATE


class MicrophoneService:
    def __init__(self) -> None:
        self._selected: dict[str, Any] | None = None
        self._load_selected()

    def list_microphones(self) -> list[dict[str, Any]]:
        devices = sd.query_devices()
        host_apis = sd.query_hostapis()
        selected_id = self.selected_id
        microphones: list[dict[str, Any]] = []

        for device_id, device in enumerate(devices):
            max_input_channels = int(device.get("max_input_channels", 0))
            if max_input_channels <= 0:
                continue
            default_sample_rate = int(device.get("default_samplerate", 0))
            host_api = host_apis[int(device["hostapi"])]["name"]
            microphones.append(
                {
                    "id": device_id,
                    "name": device["name"],
                    "host_api": host_api,
                    "max_input_channels": max_input_channels,
                    "default_sample_rate": default_sample_rate,
                    "supports_48000_hz": self.supports_sample_rate(device_id),
                    "is_selected": device_id == selected_id,
                }
            )
        return microphones

    @property
    def selected_id(self) -> int | None:
        if self._selected is None:
            return None
        return int(self._selected["microphone_id"])

    @property
    def selected(self) -> dict[str, Any] | None:
        if self._selected is None:
            return None
        device_id = int(self._selected["microphone_id"])
        device = sd.query_devices(device_id, "input")
        return {
            "id": device_id,
            "name": device["name"],
            "channels": int(self._selected.get("channels", CHANNELS_DEFAULT)),
            "sample_rate": SAMPLE_RATE,
        }

    def select(self, microphone_id: int, channels: int) -> dict[str, Any]:
        device = sd.query_devices(microphone_id, "input")
        max_channels = int(device.get("max_input_channels", 0))
        if max_channels <= 0:
            raise ValueError("Dispositivo selecionado não possui canais de entrada.")
        if channels > max_channels:
            raise ValueError("Quantidade de canais maior que a suportada pelo microfone.")
        if not self.supports_sample_rate(microphone_id, channels):
            raise ValueError("Microfone selecionado não suporta 48000 Hz.")

        self._selected = {"microphone_id": microphone_id, "channels": channels}
        AUDIO_SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        AUDIO_SETTINGS_PATH.write_text(json.dumps(self._selected, indent=2), encoding="utf-8")
        return self.selected or {}

    def supports_sample_rate(self, microphone_id: int, channels: int = CHANNELS_DEFAULT) -> bool:
        try:
            sd.check_input_settings(
                device=microphone_id,
                channels=channels,
                samplerate=SAMPLE_RATE,
                dtype="float32",
            )
            return True
        except Exception:
            return False

    def _load_selected(self) -> None:
        if not AUDIO_SETTINGS_PATH.exists():
            return
        try:
            data = json.loads(AUDIO_SETTINGS_PATH.read_text(encoding="utf-8"))
            if "microphone_id" in data:
                self._selected = data
        except Exception:
            self._selected = None


microphone_service = MicrophoneService()

