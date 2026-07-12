# version2 - Mejora de precisión del RAG

Esta versión incorpora una mejora interna del motor RAG para documentos normativos:

- chunking híbrido con prioridad por bloques semánticos y encabezados jurídicos
- metadata adicional por chunk (`page_start`, `page_end`, `section_title`)
- contexto agrupado por chunks vecinos del mismo documento antes de enviarlo al LLM
- configuración base más adecuada para PDFs normativos

Validación ejecutada:

- suite completa de pruebas automatizadas: `69 passed`
- pruebas específicas del núcleo RAG: `29 passed`

Archivos de evidencia incluidos:

- `logs/pruebas.txt`
- `chunks-ejemplo.json`
