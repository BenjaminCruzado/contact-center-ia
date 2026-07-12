# Evidencias - Sprint 09

Este directorio reúne la validación final del motor RAG del Sprint 09 con el
proveedor local de embeddings como opción por defecto y OpenAI como alternativa
configurable.

Flujo validado:

```text
PDF -> chunks -> embeddings -> ChromaDB -> busqueda top 3
```

Archivos principales:

| Archivo | Demostración |
| --- | --- |
| `01-chromadb-registros.png` | Estado del índice vectorial local con 6 registros y dimensión 384 |
| `02-busqueda-semantica.png` | Respuesta real del endpoint `/documentos/buscar` con top 3 ordenado por similitud |
| `03-logs-similitud.png` | Log final con los scores porcentuales de similitud |
| `estado-vector-store.json` | Estado de la colección activa y cantidad de registros |
| `busqueda-ejemplo.json` | Respuesta JSON estructurada del motor RAG |
| `logs/chromadb.log` | Resumen del índice local persistido en ChromaDB |
| `logs/busqueda-semantica.log` | Scores devueltos por la búsqueda semántica |
| `logs/pruebas.txt` | Resultado de la suite automatizada: 26 pruebas exitosas |

Notas:

- La colección validada es `contact-center-documents-local-sentence-transformers-paraphrase-multilingual-minilm-l12-v2`.
- La dimensión efectiva de embeddings es `384`.
- `OPENAI_API_KEY` sigue siendo opcional y se carga solo desde `.env`.
