# Evidencias — Sprint 09

Este directorio reúne la validación del motor de recuperación semántica:

```text
PDF → chunks → embeddings → ChromaDB → búsqueda top 3
```

## Evidencias comprometidas

| Archivo | Demostración |
| --- | --- |
| `01-chromadb-registros.png` | Colección vectorial, índice coseno y registros persistidos |
| `02-busqueda-semantica.png` | Tres fragmentos ordenados por similitud |
| `03-logs-similitud.png` | Logs con los scores porcentuales |
| `estado-vector-store.json` | Estado y cantidad de registros de ChromaDB |
| `busqueda-ejemplo.json` | Respuesta estructurada del motor RAG |
| `logs/chromadb.log` | Inicio y persistencia del contenedor vectorial |
| `logs/busqueda-semantica.log` | Resultado textual de la búsqueda |
| `logs/pruebas.txt` | Resultado de las pruebas automatizadas |

La clave `OPENAI_API_KEY` se mantiene exclusivamente en `.env`, archivo que no
se versiona. Las pruebas automatizadas utilizan clientes simulados y no
consumen créditos.

