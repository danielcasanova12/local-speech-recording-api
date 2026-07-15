from pydantic import BaseModel, Field


class SelectMicrophoneRequest(BaseModel):
    microphone_id: int = Field(..., ge=0)
    channels: int = Field(default=1, ge=1)

