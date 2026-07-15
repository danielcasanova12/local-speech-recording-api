import threading
import wave
from pathlib import Path
from typing import Any

import sounddevice as sd
import soundfile as sf

from app.config import BIT_DEPTH, FORMAT, SAMPLE_RATE
from app.schemas.recording import RecordingStartRequest, RecordingStopRequest
from app.services import metadata_service
from app.services.microphone_service import microphone_service
from app.services.time_utils import utc_now_iso


class RecordingService:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._stream: sd.InputStream | None = None
        self._sound_file: sf.SoundFile | None = None
        self._active: dict[str, Any] | None = None
        self._frames_written = 0
        self._wav_path: Path | None = None

    @property
    def is_recording(self) -> bool:
        return self._active is not None

    def start(self, request: RecordingStartRequest) -> dict[str, Any]:
        with self._lock:
            if self._active is not None:
                return {
                    "success": False,
                    "message": "Já existe uma gravação em andamento.",
                    "active_recording": {
                        "user_id": self._active["user_id"],
                        "id_recordings": self._active["id_recordings"],
                        "session_id": self._active["session_id"],
                        "started_at": self._active["started_at"],
                    },
                }

            selected = microphone_service.selected
            if selected is None:
                return {
                    "success": False,
                    "message": "Nenhum microfone foi selecionado. Selecione um microfone antes de iniciar a gravação.",
                }

            if metadata_service.id_recordings_exists(request.id_recordings):
                return {
                    "success": False,
                    "message": "Já existe um áudio local associado ao id_recordings informado.",
                    "id_recordings": request.id_recordings,
                }

            target_wav = metadata_service.wav_path(
                request.user_id,
                request.session_id,
                request.id_recordings,
            )
            target_wav.parent.mkdir(parents=True, exist_ok=True)

            metadata = request.model_dump()
            metadata.update(
                {
                    "duration": None,
                    "format": FORMAT,
                    "sample_rate": SAMPLE_RATE,
                    "channels": selected["channels"],
                    "bit_depth": BIT_DEPTH,
                    "microphone_id": selected["id"],
                    "microphone_name": selected["name"],
                    "recording_status": "recording",
                    "status": "recording",
                    "filename": None,
                    "file_size_bytes": None,
                    "started_at": utc_now_iso(),
                    "stopped_at": None,
                }
            )

            sound_file = sf.SoundFile(
                target_wav,
                mode="w",
                samplerate=SAMPLE_RATE,
                channels=selected["channels"],
                subtype="PCM_24",
                format="WAV",
            )

            def callback(indata, frames, _time, status):
                if status:
                    metadata["last_stream_status"] = str(status)
                sound_file.write(indata.copy())
                self._frames_written += frames

            self._frames_written = 0
            stream = sd.InputStream(
                device=selected["id"],
                samplerate=SAMPLE_RATE,
                channels=selected["channels"],
                dtype="float32",
                callback=callback,
            )
            try:
                stream.start()
            except Exception:
                sound_file.close()
                if target_wav.exists():
                    target_wav.unlink()
                raise

            self._stream = stream
            self._sound_file = sound_file
            self._active = metadata
            self._wav_path = target_wav

            response_recording = metadata.copy()
            response_recording["microphone_id"] = selected["id"]
            return {
                "success": True,
                "message": "Gravação iniciada com sucesso.",
                "recording": response_recording,
            }

    def stop(self, request: RecordingStopRequest) -> dict[str, Any]:
        with self._lock:
            if self._active is None:
                return {"success": False, "message": "Não existe gravação em andamento."}

            for field in ("user_id", "id_recordings", "session_id"):
                if int(getattr(request, field)) != int(self._active[field]):
                    return {
                        "success": False,
                        "message": "A gravação ativa pertence a outro usuário, sessão ou id_recordings.",
                        "active_recording": {
                            "user_id": self._active["user_id"],
                            "id_recordings": self._active["id_recordings"],
                            "session_id": self._active["session_id"],
                        },
                    }

            stream = self._stream
            sound_file = self._sound_file
            wav = self._wav_path
            metadata = self._active

            self._stream = None
            self._sound_file = None
            self._active = None
            self._wav_path = None

            if stream is not None:
                stream.stop()
                stream.close()
            if sound_file is not None:
                sound_file.flush()
                sound_file.close()

            if wav is None:
                return {"success": False, "message": "Arquivo WAV não localizado no contexto ativo."}

            duration = self._duration_from_wav(wav)
            stopped_at = utc_now_iso()
            metadata.update(
                {
                    "duration": duration,
                    "filename": wav.name,
                    "file_size_bytes": wav.stat().st_size,
                    "stopped_at": stopped_at,
                    "recording_status": "completed",
                    "status": "completed",
                    "upload_status": "pending",
                }
            )
            metadata_service.save_metadata(metadata)

            return {
                "success": True,
                "message": "Gravação parada e arquivo salvo com sucesso.",
                "recording": self._response_metadata(metadata),
            }

    def status(self) -> dict[str, Any]:
        with self._lock:
            if self._active is None:
                return {
                    "success": True,
                    "is_recording": False,
                    "message": "Não existe gravação em andamento.",
                    "recording": None,
                }

            duration = self._frames_written / SAMPLE_RATE
            recording = {
                "user_id": self._active["user_id"],
                "id_recordings": self._active["id_recordings"],
                "session_id": self._active["session_id"],
                "dataset_id": self._active["dataset_id"],
                "bloco_id": self._active["bloco_id"],
                "frase_id": self._active["frase_id"],
                "frase_content": self._active["frase_content"],
                "duration": round(duration, 2),
                "sample_rate": SAMPLE_RATE,
                "format": FORMAT,
                "status": "recording",
            }
            return {
                "success": True,
                "is_recording": True,
                "message": "Existe uma gravação em andamento.",
                "recording": recording,
            }

    def active_summary(self) -> dict[str, Any] | None:
        if self._active is None:
            return None
        return {
            "user_id": self._active["user_id"],
            "id_recordings": self._active["id_recordings"],
            "session_id": self._active["session_id"],
            "started_at": self._active["started_at"],
        }

    def _duration_from_wav(self, path: Path) -> float:
        with wave.open(str(path), "rb") as wav_file:
            frames = wav_file.getnframes()
            sample_rate = wav_file.getframerate()
            sample_width = wav_file.getsampwidth()
        if sample_rate != SAMPLE_RATE:
            raise ValueError("Taxa de amostragem do WAV não corresponde a 48000 Hz.")
        if sample_width != 3:
            raise ValueError("Profundidade do WAV não corresponde a PCM 24 bits.")
        return frames / sample_rate

    def _response_metadata(self, metadata: dict[str, Any]) -> dict[str, Any]:
        response = metadata.copy()
        if isinstance(response.get("duration"), float):
            response["duration"] = round(response["duration"], 2)
        return response


recording_service = RecordingService()
