# Contact Center automatizado con IA

Base operativa del backend para el prototipo académico de Contact Center. Este
proyecto incorpora ingesta de PDFs, recuperación semántica mediante embeddings
locales u OpenAI, un orquestador textual y un flujo de voz por archivo de audio
que transcribe, consulta el núcleo RAG y devuelve una respuesta sintetizada.
Desde Sprint 13 también incorpora un frontend web con login por roles.

## Requisitos

- Git
- Docker Desktop con Docker Compose
- Puertos `3000`, `8000`, `8001` y `11434` disponibles
- Conexión a internet durante el primer inicio para descargar imágenes y modelos

No es necesario instalar Python, Node.js, ChromaDB, Whisper ni Ollama en la
máquina host. Docker Compose administra el stack completo.

## Inicio rápido

1. Clonar el repositorio y entrar a su carpeta.

2. Crear el archivo local de configuración:

   ```powershell
   Copy-Item .env.example .env
   ```

3. Construir y levantar el sistema completo:

   ```powershell
   docker compose up --build --wait
   ```

La primera ejecución descarga `llama3.2:3b`, los embeddings multilingües y el
modelo de Whisper. Puede tardar varios minutos según la conexión y el equipo.
Las siguientes ejecuciones reutilizan los volúmenes persistentes.

4. Consultar el estado:

   ```powershell
   Invoke-RestMethod http://localhost:8000/health
   Invoke-RestMethod http://localhost:8000/healthcheck
   Invoke-RestMethod http://localhost:8000/version
   ```

La documentación interactiva queda disponible en
`http://localhost:8000/docs`.

Frontend web disponible en:
`http://localhost:3000`

Servicios incluidos en el stack:

- frontend web con Nginx
- API FastAPI
- ChromaDB
- Ollama con descarga automática del modelo
- embeddings y Whisper locales
- síntesis de voz local
- auditoría SQLite persistente

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
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://ollama:11434/api
OLLAMA_MODEL=llama3.2:3b
RAG_MIN_SIMILARITY=0.45
RAG_MIN_RESULTS=1
```

Ollama se ejecuta dentro de Docker. El servicio `ollama-init` descarga el modelo
configurado antes de iniciar la API, y el volumen `ollama-models` evita repetir
la descarga en cada reinicio. Desde la máquina host, la API de Ollama queda
disponible en `http://localhost:11434/api`.

Para cambiar de modelo, modifica `OLLAMA_MODEL` en `.env` y vuelve a ejecutar
`docker compose up --build --wait`. Compose descargará el nuevo modelo antes de
iniciar la API.

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
automatizados. La ejecución normal utiliza IA local real con:

```dotenv
EMBEDDING_PROVIDER=local
LLM_PROVIDER=ollama
STT_PROVIDER=local
TTS_PROVIDER=local
```

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
# Ver logs de todo el stack
docker compose logs -f

# Ver solamente API y Ollama
docker compose logs -f api ollama ollama-init

# Revisar contenedores y healthcheck
docker compose ps

# Ver los modelos instalados
docker compose exec ollama ollama list

# Reiniciar sin borrar datos ni modelos
docker compose restart

# Detener el entorno
docker compose down

# Detener y eliminar todos los datos y modelos persistentes
docker compose down --volumes
```

## Aceleración NVIDIA opcional

La configuración predeterminada usa CPU para maximizar compatibilidad. En un
equipo con GPU NVIDIA compatible, Docker Desktop con backend WSL2 y NVIDIA
Container Toolkit configurado, se puede iniciar con:

```powershell
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build --wait
```

El archivo `docker-compose.gpu.yml` asigna las GPU disponibles solamente al
servicio Ollama. Si Docker no reconoce la GPU, utiliza el comando normal sin el
archivo adicional.

## Solución de problemas

### Docker Desktop no está iniciado

Si aparece un error de conexión al daemon, inicia Docker Desktop, espera a que
el motor Linux esté disponible y vuelve a ejecutar `docker compose up`.

### La descarga del modelo falla

Revisa el inicializador:

```powershell
docker compose logs ollama-init
docker compose run --rm ollama-init
```

### Ollama no responde

```powershell
docker compose ps ollama
docker compose logs ollama
Invoke-RestMethod http://localhost:11434/api/tags
```

### Un puerto ya está ocupado

Los puertos publicados se pueden cambiar en `.env` mediante `APP_PORT`,
`CHROMA_HOST_PORT` y `OLLAMA_HOST_PORT`. Para cambiar el frontend, ajusta el
mapeo del servicio `frontend` en `docker-compose.yml`.

## Imagen de producción

El servicio `api` utiliza el target `production` del `Dockerfile`, sin recarga
automática. Para reconstruirlo junto con sus dependencias:

```powershell
docker compose build api
docker compose up --wait
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
Las evidencias del frontend con roles se organizan en `evidencia/sprint-frontend/`.
Las evidencias de pruebas integrales y validación E2E se organizan en `evidencia/sprint-13/`.
