import logging
import time

from app.config.settings import Settings, settings
from app.prompts.templates import (
    OUT_OF_SCOPE_RESPONSE,
    build_system_prompt,
    build_user_prompt,
)
from app.schemas.orchestrator import (
    OrchestratorResponse,
    OrchestratorSource,
    OrchestratorTrace,
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
        return self.respond_with_trace(query, top_k).response

    def respond_with_trace(self, query: str, top_k: int = 3) -> OrchestratorTrace:
        total_started_at = time.perf_counter()
        rag_started_at = time.perf_counter()
        search_response = self.rag_service.search(query, top_k)
        rag_latency_ms = (time.perf_counter() - rag_started_at) * 1000
        relevant_results = self._select_relevant_results(search_response.results)
        sources = self._normalize_sources(relevant_results)
        top_score = max(
            (result.similarity for result in search_response.results),
            default=None,
        )

        if len(relevant_results) < self.settings.rag_min_results:
            logger.info(
                "Consulta fuera de contexto: consulta=%s resultados_validos=%s umbral=%.2f",
                query,
                len(relevant_results),
                self.settings.rag_min_similarity,
            )
            response = OrchestratorResponse(
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
            total_latency_ms = (time.perf_counter() - total_started_at) * 1000
            return OrchestratorTrace(
                response=response,
                rag_latency_ms=round(rag_latency_ms, 2),
                llm_latency_ms=0.0,
                total_latency_ms=round(total_latency_ms, 2),
                top_score=round(top_score, 6) if top_score is not None else None,
            )

        system_prompt = build_system_prompt()
        user_prompt = build_user_prompt(query, relevant_results)
        llm_started_at = time.perf_counter()
        answer = self.llm_service.generate_answer(
            query=query,
            context_results=relevant_results,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
        llm_latency_ms = (time.perf_counter() - llm_started_at) * 1000
        total_latency_ms = (time.perf_counter() - total_started_at) * 1000

        logger.info(
            "Orquestación completada: consulta=%s proveedor_llm=%s fuentes=%s",
            query,
            self.llm_service.provider,
            len(sources),
        )
        response = OrchestratorResponse(
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
        return OrchestratorTrace(
            response=response,
            rag_latency_ms=round(rag_latency_ms, 2),
            llm_latency_ms=round(llm_latency_ms, 2),
            total_latency_ms=round(total_latency_ms, 2),
            top_score=round(top_score, 6) if top_score is not None else None,
        )
