import logging

from app.config.settings import Settings, settings
from app.schemas.search import SemanticSearchResult
from app.services.embedding_service import EmbeddingService, get_embedding_service
from app.services.llm_service import LlmService, get_llm_service
from app.services.stt_service import SttService, get_stt_service

logger = logging.getLogger("uvicorn.error")


class WarmupService:
    def __init__(
        self,
        stt_service: SttService | None = None,
        embedding_service: EmbeddingService | None = None,
        llm_service: LlmService | None = None,
        app_settings: Settings = settings,
    ) -> None:
        self.settings = app_settings
        self.stt_service = stt_service or get_stt_service(app_settings)
        self.embedding_service = embedding_service or get_embedding_service(app_settings)
        self.llm_service = llm_service or get_llm_service(app_settings)

    def warm_up(self) -> None:
        self._warm_up_stt()
        self._warm_up_embeddings()
        self._warm_up_llm()

    def _warm_up_stt(self) -> None:
        warm_method = getattr(self.stt_service, "_get_model", None)
        if callable(warm_method):
            warm_method()
            logger.info("Warmup completado: STT proveedor=%s", self.stt_service.provider)

    def _warm_up_embeddings(self) -> None:
        warm_method = getattr(self.embedding_service, "_get_model", None)
        if callable(warm_method):
            warm_method()
            logger.info(
                "Warmup completado: embeddings proveedor=%s modelo=%s",
                self.embedding_service.provider,
                self.embedding_service.model,
            )

    def _warm_up_llm(self) -> None:
        if self.llm_service.provider == "ollama":
            self.llm_service.generate_answer(
                query="warmup",
                context_results=[
                    SemanticSearchResult(
                        position=1,
                        chunk_id="warmup-1",
                        document="warmup.txt",
                        content="Respuesta de precalentamiento.",
                        similarity=1.0,
                        similarity_percentage=100.0,
                        chunk_index=0,
                    )
                ],
                system_prompt="Responde brevemente para precalentar el modelo.",
                user_prompt="Responde solo: ok",
            )
            logger.info("Warmup completado: LLM proveedor=%s modelo=%s", self.llm_service.provider, self.llm_service.model)
            return

        client_loader = getattr(self.llm_service, "_get_client", None)
        if callable(client_loader):
            client_loader()
            logger.info("Warmup completado: LLM proveedor=%s modelo=%s", self.llm_service.provider, self.llm_service.model)
