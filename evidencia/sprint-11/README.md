# Evidencias - Sprint 11

Este directorio reúne la validación del flujo de voz de extremo a extremo.

Flujo validado:

```text
Audio entrada -> STT -> Orquestador -> TTS -> Audio salida
```

Archivos principales:

| Archivo | Demostración |
| --- | --- |
| `01-logs-flujo-audio.png` | Resumen del flujo completo de voz |
| `02-servicios-stt-tts.png` | Fragmento visual de los servicios STT y TTS |
| `audio-entrada.wav` | Audio de entrada usado para validar el sprint |
| `audio-respuesta.wav` | Audio generado por la respuesta del sistema |
| `transcripcion-respuesta.json` | Transcripción, respuesta textual y metadatos |
| `demo-local.mp4` | Micro-video local del flujo de audio |
| `logs/orquestacion-voz.log` | Logs del proceso extremo a extremo |
| `logs/pruebas.txt` | Resultado de las pruebas automatizadas |
