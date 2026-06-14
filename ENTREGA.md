# Entrega Rápida

Checklist para entregar este repo:

1. Confirmar que `python -m pytest -q` y `ruff check .` pasan.
2. Confirmar que `docker build -t mlops-rag .` termina sin errores.
3. Ejecutar el contenedor con `-e GOOGLE_API_KEY=...` en runtime.
4. Probar `GET /health` y `POST /ask`.
5. Subir el repo o generar un `.tar` con `docker save` si ese es el canal de entrega.

Comandos de referencia:

```bash
docker build -t mlops-rag .
docker run --rm -p 8000:8000 -e GOOGLE_API_KEY=TU_API_KEY mlops-rag
```
