# syntax=docker/dockerfile:1

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN addgroup --system appgroup \
    && adduser --system --ingroup appgroup appuser

COPY requirements.txt .
RUN pip install --no-cache-dir --requirement requirements.txt

COPY --chown=appuser:appgroup app ./app

USER appuser

EXPOSE 8000

FROM base AS development

USER root

COPY requirements-dev.txt .
RUN pip install --no-cache-dir --requirement requirements-dev.txt

COPY --chown=appuser:appgroup tests ./tests
COPY --chown=appuser:appgroup pytest.ini .

USER appuser

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

FROM base AS production

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
