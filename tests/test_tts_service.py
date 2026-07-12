import wave

from app.services.tts_service import MockTtsService


def test_mock_tts_generates_valid_wav_bytes() -> None:
    service = MockTtsService()

    audio_bytes = service.synthesize("respuesta breve")

    assert len(audio_bytes) > 44
    with wave.open(__import__("io").BytesIO(audio_bytes), "rb") as wav_file:
        assert wav_file.getnchannels() == 1
        assert wav_file.getframerate() == 16000
