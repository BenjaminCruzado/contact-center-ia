# Evidencias - Sprint 10

Este directorio reúne la validación del orquestador central del MVP.

Flujo validado:

```text
consulta -> RAG -> contexto -> prompt -> LLM -> respuesta
```

Archivos principales:

| Archivo | Demostración |
| --- | --- |
| `01-request-response.png` | Respuesta exitosa del endpoint `/orquestador/responder` |
| `02-prompt-template.png` | Prompt del sistema y la inyección de contexto |
| `respuesta-ejemplo.json` | JSON real del orquestador con fuentes utilizadas |
| `prompt-ejemplo.txt` | Prompt generado con restricciones y contexto |
| `logs/orquestacion.log` | Resultado resumido del flujo orquestado |
| `logs/pruebas.txt` | Resultado de las pruebas automatizadas del sprint |
