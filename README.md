# Contact Center automatizado con IA

Base operativa del backend para el prototipo académico de Contact Center. Este
proyecto incorpora ingesta de PDFs y recuperación semántica mediante OpenAI
Embeddings y ChromaDB. Todavía no incorpora generación final con LLM, STT, TTS
ni telefonía.

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

Antes de levantar Docker, agrega una clave válida exclusivamente en `.env`:

```dotenv
OPENAI_API_KEY=tu_clave_local
```

El archivo `.env` no se versiona.

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
