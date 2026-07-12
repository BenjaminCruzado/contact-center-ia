from pydantic import BaseModel, Field


class AudioInteractionMetadata(BaseModel):
    input_filename: str
    input_content_type: str
    output_filename: str
    output_content_type: str
    transcript: str
    answer: str
    stt_provider: str
    tts_provider: str
    llm_provider: str
    llm_model: str
    status: str
    audio_size_bytes: int = Field(ge=1)


class AudioInteractionDebugResponse(AudioInteractionMetadata):
    total_sources: int = Field(ge=0)
