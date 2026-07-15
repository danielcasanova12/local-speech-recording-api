from fastapi import APIRouter, Header, Request
from fastapi.responses import FileResponse

from app.schemas.recording import RecordingStartRequest, RecordingStopRequest, UploadRecordingRequest
from app.services import metadata_service
from app.services.recording_service import recording_service
from app.services.remote_upload_service import remote_upload_service


router = APIRouter(prefix="/api/recordings", tags=["recordings"])


@router.post("/start")
def start_recording(request: RecordingStartRequest):
    return recording_service.start(request)


@router.post("/stop")
def stop_recording(request: RecordingStopRequest):
    return recording_service.stop(request)


@router.get("/status")
def recording_status():
    return recording_service.status()


@router.get("/latest/{user_id}")
def latest_recording(user_id: int, request: Request):
    found = metadata_service.find_latest_by_user(user_id)
    if found is None:
        return {
            "success": False,
            "message": "Nenhuma gravação foi encontrada para o usuário informado.",
            "user_id": user_id,
        }
    _, metadata = found
    metadata = _response_metadata(metadata)
    metadata["audio_url"] = str(request.url_for("latest_recording_audio", user_id=user_id))
    return {"success": True, "message": "Última gravação localizada.", "recording": metadata}


@router.get("/latest/{user_id}/audio", name="latest_recording_audio")
def latest_recording_audio(user_id: int):
    found = metadata_service.find_latest_by_user(user_id)
    if found is None:
        return {
            "success": False,
            "message": "Nenhuma gravação foi encontrada para o usuário informado.",
            "user_id": user_id,
        }
    _, metadata = found
    wav = metadata_service.wav_path(user_id, int(metadata["session_id"]), int(metadata["id_recordings"]))
    if not wav.exists():
        return {"success": False, "message": "Arquivo de áudio local não encontrado.", "user_id": user_id}
    return FileResponse(
        wav,
        media_type="audio/wav",
        filename=wav.name,
        headers={"Content-Disposition": f'inline; filename="{wav.name}"'},
    )


@router.get("/{id_recordings}")
def get_recording(id_recordings: int):
    found = metadata_service.find_by_id_recordings(id_recordings)
    if found is None:
        return {
            "success": False,
            "message": "Gravação não encontrada.",
            "id_recordings": id_recordings,
        }
    _, metadata = found
    return {"success": True, "message": "Gravação localizada.", "recording": _response_metadata(metadata)}


@router.get("/{id_recordings}/audio")
def get_recording_audio(id_recordings: int):
    found = metadata_service.find_by_id_recordings(id_recordings)
    if found is None:
        return {
            "success": False,
            "message": "Gravação não encontrada.",
            "id_recordings": id_recordings,
        }
    _, metadata = found
    wav = metadata_service.wav_path(
        int(metadata["user_id"]),
        int(metadata["session_id"]),
        int(metadata["id_recordings"]),
    )
    if not wav.exists():
        return {"success": False, "message": "Arquivo de áudio local não encontrado.", "id_recordings": id_recordings}
    return FileResponse(
        wav,
        media_type="audio/wav",
        filename=wav.name,
        headers={"Content-Disposition": f'inline; filename="{wav.name}"'},
    )


@router.post("/latest/{user_id}/upload")
async def upload_latest_recording(user_id: int, authorization: str | None = Header(default=None)):
    found = metadata_service.find_latest_by_user(user_id)
    if found is None:
        return {
            "success": False,
            "message": "Nenhuma gravação foi encontrada para o usuário informado.",
            "user_id": user_id,
        }
    path, metadata = found
    return await remote_upload_service.upload(path, metadata, authorization=authorization)


@router.post("/{id_recordings}/upload")
async def upload_recording(
    id_recordings: int,
    request: UploadRecordingRequest | None = None,
    authorization: str | None = Header(default=None),
):
    found = metadata_service.find_by_id_recordings(id_recordings)
    if found is None:
        return {
            "success": False,
            "message": "Gravação não encontrada.",
            "id_recordings": id_recordings,
        }
    path, metadata = found
    if request and request.user_id is not None and int(metadata["user_id"]) != request.user_id:
        return {
            "success": False,
            "message": "A gravação localizada não pertence ao usuário informado.",
            "user_id": request.user_id,
            "id_recordings": id_recordings,
        }
    return await remote_upload_service.upload(path, metadata, authorization=authorization)


def _response_metadata(metadata: dict):
    response = metadata.copy()
    if isinstance(response.get("duration"), float):
        response["duration"] = round(response["duration"], 2)
    return response
