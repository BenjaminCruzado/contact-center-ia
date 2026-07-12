import logging

from app.config.settings import Settings, settings
from app.prompts.templates import (
    OUT_OF_SCOPE_RESPONSE,
    build_system_prompt,
    build_user_prompt,
)
from app.schemas.orchestrator import (
    OrchestratorResponse,
    OrchestratorSource,
)
from app.schemas.search import SemanticSearchResult
from app.services.llm_service import LlmService, get_llm_service
from app.services.rag_service import RagService

logger = logging.getLogger("uvicorn.error")


class OrchestratorService:
    def __init__(
        self,
        rag_service: RagService | None = None,
        llm_service: LlmService | None = None,
        app_settings: Settings = settings,
    ) -> None:
        self.settings = app_settings
        self.rag_service = rag_service or RagService(app_settings=app_settings)
        self.llm_service = llm_service or get_llm_service(app_settings)

    def _normalize_sources(
        self,
        results: list[SemanticSearchResult],
    ) -> list[OrchestratorSource]:
        return [
            OrchestratorSource(
                position=result.position,
                chunk_id=result.chunk_id,
                document=result.document,
                content=result.content,
                similarity=result.similarity,
                similarity_percentage=result.similarity_percentage,
                chunk_index=result.chunk_index,
            )
            for result in results
        ]

    def _select_relevant_results(
        self,
        results: list[SemanticSearchResult],
    ) -> list[SemanticSearchResult]:
        return [
            result
            for result in results
            if result.similarity >= self.settings.rag_min_similarity
        ]

    def respond(self, query: str, top_k: int = 3) -> OrchestratorResponse:
        search_response = self.rag_service.search(query, top_k)
        relevant_results = self._select_relevant_results(search_response.results)
        sources = self._normalize_sources(relevant_results)

        if len(relevant_results) < self.settings.rag_min_results:
            logger.info(
                "Consulta fuera de contexto: consulta=%s resultados_validos=%s umbral=%.2f",
                query,
                len(relevant_results),
                self.settings.rag_min_similarity,
            )
            return OrchestratorResponse(
                query=query,
                status="out_of_scope",
                answer=OUT_OF_SCOPE_RESPONSE,
                collection=search_response.collection,
                llm_provider=self.llm_service.provider,
                llm_model=self.llm_service.model,
                llm_invoked=False,
                total_sources=len(sources),
                sources=sources,
            )

        system_prompt = build_system_prompt()
        user_prompt = build_user_prompt(query, relevant_results)
        answer = self.llm_service.generate_answer(
            query=query,
            context_results=relevant_results,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        logger.info(
            "Orquestación completada: consulta=%s proveedor_llm=%s fuentes=%s",
            query,
            self.llm_service.provider,
            len(sources),
        )
        return OrchestratorResponse(
            query=query,
            status="answered",
            answer=answer,
            collection=search_response.collection,
            llm_provider=self.llm_service.provider,
            llm_model=self.llm_service.model,
            llm_invoked=True,
            total_sources=len(sources),
            sources=sources,
        )
