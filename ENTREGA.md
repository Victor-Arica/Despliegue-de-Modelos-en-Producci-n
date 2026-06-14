# Entrega — MLOps RAG API

## 📋 Checklist de Validación Local

Antes de entregar, ejecuta en tu máquina:

```bash
# 1. Tests sin API key (deben pasar 4)
python -m pytest -q

# 2. Lint (debe estar limpio)
ruff check .

# 3. Build de imagen
docker build -t mlops-rag .

# 4. Ejecutar (con TU API KEY de Gemini)
docker run --rm -p 8000:8000 -e GOOGLE_API_KEY=TU_KEY mlops-rag

# 5. En otra terminal: probar
curl http://localhost:8000/health
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "¿Cuál es el objetivo?"}'
```

---

## 🎯 Qué hace la app

Es un **RAG (Retrieval Augmented Generation)** que:

1. **Carga documentos** de `/docs/*.txt`
2. **Genera embeddings** (convierte texto en vectores numéricos)
3. **Busca fragmentos relevantes** usando similitud coseno
4. **Consulta Gemini** con el contexto más pertinente
5. **Responde** solo con lo que está en los documentos

**Ventaja:** Las respuestas se anclan en tus propios documentos, no inventa.

---

## 🚀 Para el profesor: Dos opciones de entrega

### Opción A: Archivo `.tar` (Sin necesidad de clonar ni buildear)

```bash
# El profesor recibe mlops-rag.tar y ejecuta:
docker load -i mlops-rag.tar
docker run --rm -p 8000:8000 -e GOOGLE_API_KEY=<TU_KEY> mlops-rag:latest

# Accede a http://localhost:8000/docs (Swagger interactivo)
```

✅ **Ventaja:** La imagen ya está lista, no hay que compilar. Más rápido.

### Opción B: Repositorio GitHub

```bash
# El profesor clona y construye:
git clone https://github.com/TU_USER/mlops-rag-app.git
cd mlops-rag-app
docker build -t mlops-rag .
docker run --rm -p 8000:8000 -e GOOGLE_API_KEY=<TU_KEY> mlops-rag
```

✅ **Ventaja:** El profesor ve el código y puede auditar el build.

---

## 📁 Dónde poner tus documentos

Todos los `.txt` en `/docs/` se indexan automáticamente:

```
docs/
├── mamiferos.txt       ← Ya está (ejemplo)
├── aves.txt            ← Ya está (ejemplo)
├── reptiles.txt        ← Ya está (ejemplo)
└── otros-temas.txt     ← Si agregas más textos del mismo tema
```

**Para agregar documentos:**
1. Crea o pega el contenido en un archivo `.txt` dentro de `docs/`.
2. Mantén el tema relacionado con biología o fauna para que el RAG siga siendo coherente.
3. Reconstruye la imagen: `docker build -t mlops-rag .`

---

## 🔐 API Key: Dónde NO va, dónde SÍ va

❌ **NUNCA en:**
- `requirements.txt`
- `Dockerfile` (ENV)
- Código (hardcoded)
- `.env` (si sube a git)
- Git history

✅ **SÍ en:**
- **Runtime solo:** `-e GOOGLE_API_KEY=...`
- Ejemplo: `docker run -e GOOGLE_API_KEY=sk_*** mlops-rag`

---

## 📊 Flujo de una pregunta

```
Usuario pregunta: "¿Qué es el RAG?"
        ↓
App genera embedding de la pregunta (vector numérico)
        ↓
Busca fragmentos similares en /docs/ (similitud coseno)
        ↓
Toma los 4 fragmentos más relevantes
        ↓
Los envía a Gemini: "Contexto: [fragmentos]. Pregunta: ¿Qué es el RAG?"
        ↓
Gemini responde usando SOLO esos fragmentos
        ↓
Respuesta: "Es una técnica que..."
```

---

## 📞 Endpoints

| Método | Path | Descripción | Requiere API Key |
|--------|------|-------------|------------------|
| GET | `/health` | Verifica que el servicio arrancó | ❌ No |
| POST | `/ask` | Pregunta sobre los documentos | ✅ Sí |
| GET | `/docs` | Documentación Swagger interactiva | ❌ No |

**Ejemplo `/ask`:**
```json
{
  "question": "¿Cuál es la fecha límite?"
}
```

**Respuesta:**
```json
{
  "answer": "La fecha límite es el 13 de junio de 2026."
}
```

---

## 🐳 Tamaño de la imagen

- **Sin documentos grandes:** ~850 MB
- **Con más textos temáticos:** el tamaño casi no cambia; solo aumenta si agregas muchos archivos grandes

Se entrega como: `mlops-rag.tar` (83.84 MB comprimido)

---

## ✅ Rúbrica cubierta

| Criterio | Puntos | Verificación |
|----------|--------|--------------|
| Arranca con `docker run` | 6 | ✓ Sin API key en build; `-e GOOGLE_API_KEY=...` en runtime |
| IA funciona y responde pertinente | 6 | ✓ RAG real: embeddings + recuperación coseno + Gemini |
| README claro | 3 | ✓ Construcción, ejecución, ejemplo `/ask` |
| Extras (Git, Dockerfile slim, tests, lint, CI) | 5 | ✓ `.gitignore`, user no-root, pytest, ruff, GitHub Actions |
| **Total** | **20** | ✓ Listo |
