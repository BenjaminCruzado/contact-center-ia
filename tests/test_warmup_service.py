from app.services.warmup_service import WarmupService


class FakeSttService:
    provider = "local"

    def __init__(self) -> None:
        self.loaded = False

    def _get_model(self) -> object:
        self.loaded = True
        return object()


class FakeEmbeddingService:
    provider = "local"
    model = "test-embedding"

    def __init__(self) -> None:
        self.loaded = False

    def _get_model(self) -> object:
        self.loaded = True
        return object()


class FakeLlmService:
    provider = "ollama"
    model = "test-llm"

    def __init__(self) -> None:
        self.warmed = False

    def generate_answer(
        self,
        query: str,
        context_results: list[object],
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        assert query == "warmup"
        assert context_results
        assert system_prompt
        assert user_prompt
        self.warmed = True
        return "ok"


def test_warmup_service_loads_stt_embeddings_and_llm() -> None:
    stt_service = FakeSttService()
    embedding_service = FakeEmbeddingService()
    llm_service = FakeLlmService()

    service = WarmupService(
        stt_service=stt_service,
        embedding_service=embedding_service,
        llm_service=llm_service,
    )

    service.warm_up()

    assert stt_service.loaded is True
    assert embedding_service.loaded is True
    assert llm_service.warmed is True
