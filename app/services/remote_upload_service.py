import json
from pathlib import Path
from typing import Any

import httpx

from app.config import REMOTE_RECORDINGS_URL
from app.services import metadata_service
from app.services.time_utils import utc_now_iso


REMOTE_METADATA_FIELDS = (
    "session_id",
    "dataset_id",
    "bloco_id",
    "frase_id",
    "is_test",
    "duration",
    "format",
    "sample_rate",
    "frase_content",
    "room_tone_start",
    "room_tone_end",
    "extra_info",
)


class RemoteUploadService:
    async def upload(
        self,
        metadata_path: Path,
        metadata: dict[str, Any],
        authorization: str | None = None,
    ) -> dict[str, Any]:
        user_id = str(metadata["user_id"])
        session_id = int(metadata["session_id"])
        id_recordings = int(metadata["id_recordings"])
        wav = metadata_service.wav_path(user_id, session_id, id_recordings)
        if not wav.exists():
            return {
                "success": False,
                "message": "Arquivo WAV local não encontrado para envio.",
                "recording": self._recording_summary(metadata),
            }

        metadata["upload_status"] = "uploading"
        metadata["last_upload_attempt"] = utc_now_iso()
        metadata_service.save_metadata(metadata)

        data = self._remote_data(metadata)
        headers = self._remote_headers(authorization)
        try:
            with wav.open("rb") as audio_file:
                files = {"audio_file": (wav.name, audio_file, "audio/wav")}
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        REMOTE_RECORDINGS_URL,
                        data=data,
                        files=files,
                        headers=headers,
                        timeout=60,
                    )
        except Exception as exc:
            metadata.update(
                {
                    "upload_status": "failed",
                    "remote_error": str(exc),
                    "last_upload_attempt": utc_now_iso(),
                }
            )
            metadata_service.save_metadata(metadata)
            return {
                "success": False,
                "message": "A gravação foi salva localmente, mas não foi possível enviá-la para a API remota.",
                "recording": self._recording_summary(metadata),
                "remote_status_code": None,
                "remote_response": {"error": str(exc)},
            }

        remote_response = self._parse_response(response)
        if 200 <= response.status_code < 300:
            metadata.update(
                {
                    "upload_status": "uploaded",
                    "uploaded_at": utc_now_iso(),
                    "remote_status_code": response.status_code,
                    "remote_error": None,
                }
            )
            metadata_service.save_metadata(metadata)
            return {
                "success": True,
                "message": "Áudio e metadados enviados com sucesso para a API remota.",
                "recording": self._recording_summary(metadata),
                "remote_status_code": response.status_code,
                "remote_response": remote_response,
            }

        metadata.update(
            {
                "upload_status": "failed",
                "last_upload_attempt": utc_now_iso(),
                "remote_status_code": response.status_code,
                "remote_error": response.text,
            }
        )
        metadata_service.save_metadata(metadata)
        return {
            "success": False,
            "message": "A gravação foi salva localmente, mas não foi possível enviá-la para a API remota.",
            "recording": self._recording_summary(metadata),
            "remote_status_code": response.status_code,
            "remote_response": remote_response,
        }

    def _remote_data(self, metadata: dict[str, Any]) -> dict[str, str]:
        data: dict[str, str] = {}
        for field in REMOTE_METADATA_FIELDS:
            value = metadata.get(field)
            if value is None:
                continue
            elif isinstance(value, bool):
                data[field] = str(value).lower()
            elif isinstance(value, (dict, list)):
                data[field] = json.dumps(value, ensure_ascii=False)
            else:
                data[field] = str(value)
        return data

    def _remote_headers(self, authorization: str | None) -> dict[str, str]:
        if not authorization:
            return {}
        return {"Authorization": authorization}

    def _recording_summary(self, metadata: dict[str, Any]) -> dict[str, Any]:
        return {
            "user_id": metadata.get("user_id"),
            "id_recordings": metadata.get("id_recordings"),
            "session_id": metadata.get("session_id"),
            "filename": metadata.get("filename"),
            "duration": round(metadata["duration"], 2) if isinstance(metadata.get("duration"), float) else metadata.get("duration"),
            "format": metadata.get("format"),
            "sample_rate": metadata.get("sample_rate"),
            "upload_status": metadata.get("upload_status"),
        }

    def _parse_response(self, response: httpx.Response) -> Any:
        try:
            return response.json()
        except Exception:
            return {"text": response.text}


remote_upload_service = RemoteUploadService()
