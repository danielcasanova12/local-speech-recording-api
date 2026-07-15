from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.config import FORMAT, SAMPLE_RATE


class RecordingStartRequest(BaseModel):
    user_id: int = Field(..., gt=0)
    id_recordings: int = Field(..., gt=0)
    session_id: int = Field(..., gt=0)
    dataset_id: int
    bloco_id: int
    frase_id: int | None = None
    is_test: bool = False
    duration: float | None = None
    format: str | None = FORMAT
    sample_rate: int | None = SAMPLE_RATE
    frase_content: str
    room_tone_start: float | None = 0.0
    room_tone_end: float | None = 0.0
    created_at: str
    extra_info: Any | None = None

    @field_validator("format")
    @classmethod
    def validate_format(cls, value: str | None) -> str:
        if value is None:
            return FORMAT
        if value.lower() != FORMAT:
            raise ValueError("format deve ser wav")
        return FORMAT

    @field_validator("sample_rate")
    @classmethod
    def validate_sample_rate(cls, value: int | None) -> int:
        if value is None:
            return SAMPLE_RATE
        if value != SAMPLE_RATE:
            raise ValueError("sample_rate deve ser 48000")
        return SAMPLE_RATE


class RecordingStopRequest(BaseModel):
    user_id: int = Field(..., gt=0)
    id_recordings: int = Field(..., gt=0)
    session_id: int = Field(..., gt=0)


class UploadRecordingRequest(BaseModel):
    user_id: int | None = Field(default=None, gt=0)

