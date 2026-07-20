from typing import Any
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse, JSONResponse

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
def latest_recording(user_id: UUID, request: Request):
    found = metadata_service.find_latest_by_user(user_id)
    if found is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nenhuma gravação foi encontrada para o usuário informado.",
        )
    _, metadata = found
    metadata = _response_metadata(metadata)
    metadata["audio_url"] = str(request.url_for("latest_recording_audio", user_id=user_id))
    return {"success": True, "message": "Última gravação localizada.", "recording": metadata}


@router.get("/latest/{user_id}/audio", name="latest_recording_audio")
def latest_recording_audio(user_id: UUID):
    found = metadata_service.find_latest_by_user(user_id)
    if found is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nenhuma gravação foi encontrada para o usuário informado.",
        )
    _, metadata = found
    wav = metadata_service.wav_path(str(user_id), int(metadata["session_id"]), int(metadata["id_recordings"]))
    if not wav.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Arquivo de áudio local não encontrado.")
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gravação não encontrada.")
    _, metadata = found
    return {"success": True, "message": "Gravação localizada.", "recording": _response_metadata(metadata)}


@router.get("/{id_recordings}/audio")
def get_recording_audio(id_recordings: int):
    found = metadata_service.find_by_id_recordings(id_recordings)
    if found is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gravação não encontrada.")
    _, metadata = found
    wav = metadata_service.wav_path(
        str(metadata["user_id"]),
        int(metadata["session_id"]),
        int(metadata["id_recordings"]),
    )
    if not wav.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Arquivo de áudio local não encontrado.")
    return FileResponse(
        wav,
        media_type="audio/wav",
        filename=wav.name,
        headers={"Content-Disposition": f'inline; filename="{wav.name}"'},
    )


@router.post("/latest/{user_id}/upload")
async def upload_latest_recording(user_id: UUID, authorization: str | None = Header(default=None)):
    authorization = _require_bearer_token(authorization)
    found = metadata_service.find_latest_by_user(user_id)
    if found is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nenhuma gravação foi encontrada para o usuário informado.",
        )
    path, metadata = found
    result = await remote_upload_service.upload(path, metadata, authorization=authorization)
    return _upload_http_response(result)


@router.post("/{id_recordings}/upload")
async def upload_recording(
    id_recordings: int,
    request: UploadRecordingRequest | None = None,
    authorization: str | None = Header(default=None),
):
    authorization = _require_bearer_token(authorization)
    found = metadata_service.find_by_id_recordings(id_recordings)
    if found is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gravação não encontrada.")
    path, metadata = found
    metadata_user_id = str(metadata["user_id"])
    if (
        request
        and request.user_id is not None
        and metadata_user_id != str(request.user_id)
        and not metadata_user_id.isdigit()
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="A gravação localizada não pertence ao usuário informado.",
        )
    result = await remote_upload_service.upload(path, metadata, authorization=authorization)
    return _upload_http_response(result)


def _require_bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer ") or not authorization[7:].strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Envie o token de acesso no header Authorization: Bearer <token>.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return authorization


def _upload_http_response(result: dict[str, Any]):
    if result.get("success"):
        return result

    remote_status = result.get("remote_status_code")
    response_status = remote_status if isinstance(remote_status, int) and 400 <= remote_status <= 599 else 502
    return JSONResponse(status_code=response_status, content=jsonable_encoder(result))


def _response_metadata(metadata: dict):
    response = metadata.copy()
    if isinstance(response.get("duration"), float):
        response["duration"] = round(response["duration"], 2)
    return response
