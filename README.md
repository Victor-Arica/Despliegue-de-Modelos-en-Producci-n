# MLOps RAG API

API REST mínima de RAG (Retrieval Augmented Generation) sobre documentos `.txt` locales. Recibe una pregunta y responde usando Gemini. No usa frontend ni base de datos.

## Cómo funciona
- Carga los `.txt` de `docs/`, los parte en fragmentos y genera embeddings con `gemini-embedding-001`.
- Ante una pregunta, recupera los fragmentos más relevantes con similitud coseno y los pasa a `gemini-2.5-flash`.
- El índice se construye en memoria en la primera petición a `/ask`, por lo que el contenedor arranca de inmediato.

## Requisitos
- Docker.
- Una API key de Google Gemini desde https://aistudio.google.com/apikey.

## 1. Construir la imagen
```bash
docker build -t mlops-rag .
```

## 2. Ejecutar
```bash
docker run --rm -p 8000:8000 -e GOOGLE_API_KEY=TU_API_KEY mlops-rag
```

La API queda en http://localhost:8000 y la documentación interactiva en /docs.

## 3. Probar

Health check:
```bash
curl http://localhost:8000/health
```

Hacer una pregunta:
```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "¿De qué trata el documento?"}'
```

## Variables de entorno
| Variable | Por defecto | Descripción |
|---|---|---|
| `GOOGLE_API_KEY` | requerida | API key de Gemini. También acepta `GEMINI_API_KEY`. |
| `CHAT_MODEL` | `gemini-2.5-flash` | Modelo de generación. |
| `EMBED_MODEL` | `gemini-embedding-001` | Modelo de embeddings. |
| `TOP_K` | `4` | Número de fragmentos recuperados. |

## Desarrollo local
### macOS/Linux
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export GOOGLE_API_KEY=TU_API_KEY
uvicorn app.main:app --reload
```

### Windows PowerShell
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:GOOGLE_API_KEY="TU_API_KEY"
uvicorn app.main:app --reload
```

## Tests y lint
```bash
pip install pytest ruff
python -m pytest -q
ruff check .
```

## Estructura
```text
app/        código de FastAPI y motor RAG
docs/       documentos .txt indexados
tests/      tests sin API key
Dockerfile  imagen de producción slim y no-root
```
