import asyncio
import math

import numpy as np
import sounddevice as sd
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.config import SAMPLE_RATE
from app.services.microphone_service import microphone_service


router = APIRouter(tags=["audio"])


@router.websocket("/api/audio/stream")
async def audio_level_stream(websocket: WebSocket):
    await websocket.accept()
    selected = microphone_service.selected
    if selected is None:
        await websocket.send_json(
            {
                "type": "error",
                "message": "Nenhum microfone foi selecionado. Selecione um microfone antes de iniciar o monitoramento.",
            }
        )
        await websocket.close()
        return

    queue: asyncio.Queue[dict] = asyncio.Queue(maxsize=10)
    loop = asyncio.get_running_loop()

    def callback(indata, _frames, _time, status):
        samples = indata.astype("float32", copy=False)
        rms = float(np.sqrt(np.mean(np.square(samples)))) if samples.size else 0.0
        peak = float(np.max(np.abs(samples))) if samples.size else 0.0
        decibels = 20 * math.log10(max(rms, 1e-12))
        payload = {
            "type": "audio_level",
            "rms": round(rms, 4),
            "peak": round(peak, 4),
            "decibels": round(decibels, 1),
            "is_clipping": peak >= 0.99,
        }
        if status:
            payload["stream_status"] = str(status)
        loop.call_soon_threadsafe(_put_latest, queue, payload)

    stream = sd.InputStream(
        device=selected["id"],
        samplerate=SAMPLE_RATE,
        channels=selected["channels"],
        dtype="float32",
        callback=callback,
    )

    try:
        stream.start()
        await websocket.send_json(
            {
                "type": "stream_started",
                "message": "Monitoramento do microfone iniciado.",
                "microphone_id": selected["id"],
                "microphone_name": selected["name"],
                "sample_rate": SAMPLE_RATE,
                "channels": selected["channels"],
            }
        )
        while True:
            payload = await queue.get()
            await websocket.send_json(payload)
    except WebSocketDisconnect:
        pass
    finally:
        stream.stop()
        stream.close()


def _put_latest(queue: asyncio.Queue, payload: dict) -> None:
    if queue.full():
        try:
            queue.get_nowait()
        except asyncio.QueueEmpty:
            pass
    queue.put_nowait(payload)

