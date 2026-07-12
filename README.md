# Contact Center automatizado con IA

Base operativa del backend para el prototipo académico de Contact Center. Este
proyecto incorpora ingesta de PDFs, recuperación semántica mediante embeddings
locales u OpenAI, un orquestador textual y un flujo de voz por archivo de audio
que transcribe, consulta el núcleo RAG y devuelve una respuesta sintetizada.
Desde Sprint 13 también incorpora un frontend web con login por roles.

## Requisitos

- Docker Desktop con Docker Compose
- Puerto `8000` disponible

## Inicio rápido

1. Crear el archivo local de configuración:

   ```powershell
   Copy-Item .env.example .env
   ```

2. Construir y levantar la API:

   ```powershell
   docker compose up --build -d
   ```

3. Consultar el estado:

   ```powershell
   Invoke-RestMethod http://localhost:8000/health
   Invoke-RestMethod http://localhost:8000/healthcheck
   Invoke-RestMethod http://localhost:8000/version
   ```

La documentación interactiva queda disponible en
`http://localhost:8000/docs`.

Frontend web disponible en:
`http://localhost:3000`

## Procesar un PDF

```powershell
curl.exe -X POST `
  "http://localhost:8000/documentos/subir?chunk_size=500&chunk_overlap=50" `
  -H "accept: application/json" `
  -H "Content-Type: multipart/form-data" `
  -F "file=@ruta/al/documento.pdf;type=application/pdf"
```

La respuesta contiene el texto extraído, segmentado e indexado en ChromaDB.
Los PDFs escaneados sin capa de texto requieren OCR y no forman parte del MVP.

## Búsqueda semántica

```powershell
$body = @{
  query = "¿Cómo conserva contexto el sistema?"
  top_k = 3
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri http://localhost:8000/documentos/buscar `
  -ContentType "application/json" `
  -Body $body
```

Por defecto se utiliza un modelo multilingüe local y gratuito:

```dotenv
EMBEDDING_PROVIDER=local
LOCAL_EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
```

Para utilizar OpenAI más adelante:

```dotenv
EMBEDDING_PROVIDER=openai
OPENAI_API_KEY=tu_clave_local
```

Cada proveedor y modelo usa una colección Chroma independiente para impedir que
se mezclen vectores con dimensiones incompatibles. El archivo `.env` no se
versiona.

## Orquestación con LLM

El Sprint 10 añade un endpoint que une recuperación semántica y respuesta final:

```powershell
$body = @{
  query = "¿Qué hace el sistema con los documentos PDF?"
  top_k = 3
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri http://localhost:8000/orquestador/responder `
  -ContentType "application/json" `
  -Body $body
```

Configuración por defecto del orquestador:

```dotenv
LLM_PROVIDER=mock
RAG_MIN_SIMILARITY=0.45
RAG_MIN_RESULTS=1
```

Si más adelante quieres usar OpenAI para la respuesta final:

```dotenv
LLM_PROVIDER=openai
OPENAI_API_KEY=tu_clave_local
OPENAI_CHAT_MODEL=gpt-4o-mini
```

Cuando la evidencia recuperada no supera el umbral configurado, el endpoint no
inventa información y responde con un estado funcional `out_of_scope`.

## Interacción por voz

El Sprint 11 añade un flujo de audio de extremo a extremo. El cliente puede
grabar en navegador y enviar el archivo al terminar la captura:

```powershell
curl.exe -X POST ^
  "http://localhost:8000/voz/interactuar-debug?top_k=3" ^
  -H "accept: application/json" ^
  -H "Content-Type: multipart/form-data" ^
  -F "file=@ruta/al/audio.wav;type=audio/wav"
```

La respuesta de depuración incluye la transcripción, la respuesta textual y los
metadatos del audio generado. El endpoint principal devuelve audio reproducible:

```powershell
curl.exe -X POST ^
  "http://localhost:8000/voz/interactuar?top_k=3" ^
  -H "accept: audio/wav" ^
  -H "Content-Type: multipart/form-data" ^
  -F "file=@ruta/al/audio.wav;type=audio/wav" ^
  --output respuesta.wav
```

Configuración local recomendada:

```dotenv
STT_PROVIDER=local
TTS_PROVIDER=local
WHISPER_MODEL=tiny
TTS_VOICE=es-la
```

Para pruebas rápidas también existe un modo `mock`, útil en tests y entornos
sin descarga de modelos.

## Frontend web con roles

El Sprint 13 agrega un cliente web separado con dos perfiles:

- Usuario final:
  - inicia sesión
  - graba audio desde el navegador
  - envía la consulta
  - recibe respuesta textual
  - escucha automáticamente el audio de respuesta

- Administrador:
  - inicia sesión
  - sube PDFs para el RAG
  - consulta auditoría, logs y métricas
  - no entra al panel conversacional del usuario

Decisión funcional del prototipo:

- hay login
- no hay registro público
- las cuentas están predefinidas en configuración

Credenciales por defecto de desarrollo:

```dotenv
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
NORMAL_USERNAME=usuario
NORMAL_PASSWORD=user123
```

Endpoints nuevos de autenticación:

- `POST /auth/login`
- `GET /auth/me`

## Auditoría y trazabilidad

El Sprint 12 agrega un módulo de auditoría persistente en SQLite para registrar
cada interacción del backend con:

- latencia total del request
- latencia por etapa del flujo de voz (STT, RAG, LLM y TTS)
- score semántico principal
- estado final de la interacción
- alertas por baja confianza, fuera de contexto o alta latencia

Endpoints disponibles:

- `GET /auditoria/registros`
- `GET /auditoria/registros/{id}`
- `GET /auditoria/resumen`

## Operación

```powershell
# Ver logs
docker compose logs -f api

# Revisar contenedores y healthcheck
docker compose ps

# Detener el entorno
docker compose down
```

## Producción

El `Dockerfile` contiene un target `production`, sin recarga automática:

```powershell
docker build --target production -t contact-center-api:0.1.0 .
docker run --rm -p 8000:8000 --env-file .env contact-center-api:0.1.0
```

## Estructura

```text
app/
├── api/
│   └── routers/       # Rutas HTTP
├── config/            # Configuración y variables de entorno
├── services/          # Lógica de negocio futura
└── main.py            # Instancia y ciclo de vida de FastAPI
```

Las evidencias de validación se organizan en `evidencia/sprint-07/`.
Las evidencias de ingesta documental se organizan en `evidencia/sprint-08/`.
Las evidencias del motor RAG se organizan en `evidencia/sprint-09/`.
Las evidencias del orquestador se organizan en `evidencia/sprint-10/`.
Las evidencias del flujo de voz se organizan en `evidencia/sprint-11/`.
Las evidencias de auditoría se organizan en `evidencia/sprint-12/`.
Las evidencias del frontend con roles se organizan en `evidencia/sprint-13/`.
