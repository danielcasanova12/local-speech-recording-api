from fastapi import APIRouter

from app.schemas.microphone import SelectMicrophoneRequest
from app.services.microphone_service import microphone_service
from app.services.recording_service import recording_service


router = APIRouter(prefix="/api/microphones", tags=["microphones"])


@router.get("")
def list_microphones():
    microphones = microphone_service.list_microphones()
    return {
        "success": True,
        "message": "Microfones conectados encontrados.",
        "selected_microphone_id": microphone_service.selected_id,
        "microphones": microphones,
    }


@router.get("/selected")
def selected_microphone():
    selected = microphone_service.selected
    if selected is None:
        return {"success": False, "message": "Nenhum microfone selecionado.", "microphone": None}
    return {"success": True, "message": "Microfone selecionado.", "microphone": selected}


@router.put("/selected")
def select_microphone(request: SelectMicrophoneRequest):
    if recording_service.is_recording:
        return {
            "success": False,
            "message": "Não é permitido trocar o microfone durante uma gravação.",
            "active_recording": recording_service.active_summary(),
        }
    try:
        selected = microphone_service.select(request.microphone_id, request.channels)
    except Exception as exc:
        return {"success": False, "message": str(exc)}
    return {
        "success": True,
        "message": "Microfone selecionado com sucesso.",
        "microphone": selected,
    }

