# Evidencias — Sprint 08

Este directorio contiene la validación del flujo funcional mínimo:

```text
PDF → extracción de texto → normalización → chunking → JSON en memoria
```

## Evidencias comprometidas

| Archivo | Demostración |
| --- | --- |
| `01-logs-extraccion.png` | Consola con extracción, creación de chunks y respuestas HTTP |
| `02-codigo-text-splitter.png` | Implementación del algoritmo divisor de texto |
| `03-respuesta-endpoint.png` | JSON retornado por `POST /documentos/subir` |
| `chunks-ejemplo.json` | Resultado real de procesar el PDF de prueba |
| `logs/procesamiento-pdf.log` | Logs textuales del flujo |
| `logs/pruebas.txt` | Resultado de las pruebas automatizadas |

El procesamiento de este sprint es transitorio y ocurre solo en memoria. No se
utilizan embeddings, OCR ni una base de datos vectorial.

