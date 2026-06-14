# Cómo funciona el RAG internamente

## Conceptos clave

**RAG = Retrieval Augmented Generation**
- **Retrieval:** Buscar fragmentos relevantes
- **Augmented:** Enviar esos fragmentos como contexto
- **Generation:** El LLM genera una respuesta basada en ese contexto

---

## Flujo paso a paso

### 1️⃣ Inicialización (Primera pregunta)

**Qué pasa:**
```
Usuario hace: POST /ask {"question": "..."}
       ↓
La app detecta que el índice NO está listo
       ↓
Carga todos los .txt de /docs/
       ↓
Los parte en fragmentos de ~150 palabras
       ↓
Genera embeddings para cada fragmento (gemini-embedding-001)
       ↓
Guarda la matriz de embeddings en memoria (RAM)
       ↓
Marca: "Índice listo ✓"
```

**Por qué es lazy (perezoso):**
- El contenedor arranca de inmediato (`docker run` tarda ~2s)
- `/health` responde sin esperar el índice
- El primer `/ask` tarda más (~10-15s porque genera embeddings)
- Preguntas posteriores son rápidas (~1-2s)

---

### 2️⃣ Generación de Embeddings

**¿Qué es un embedding?**
Un embedding es un vector numérico (lista de números) que representa el "significado" del texto.

**Ejemplo ficticio:**
```
Texto: "La API key se pasa en runtime"
Embedding: [0.23, -0.45, 0.12, 0.88, ..., -0.67]
           ↑     ↑     ↑    ↑        ↑
           768 dimensiones (768 números)

Texto: "La clave se pasa en tiempo de ejecución"
Embedding: [0.22, -0.46, 0.11, 0.89, ..., -0.66]
           ↑ Similar al anterior (significan lo mismo)
```

**Cómo lo genera:**
```python
from google import genai

response = client.models.embed_content(
    model="gemini-embedding-001",
    contents=["Tu fragmento de texto aquí"],
    config=EmbedContentConfig(
        task_type="RETRIEVAL_DOCUMENT",
        output_dimensionality=768,
    ),
)
# Resultado: array de 768 números
```

---

### 3️⃣ Búsqueda (Similitud Coseno)

**Cuando llega una pregunta:**

```python
# Pregunta: "¿Dónde pongo la API key?"

# 1. Convierte la pregunta a embedding
q_vector = embed("¿Dónde pongo la API key?")
# Resultado: [0.24, -0.44, 0.13, 0.87, ...]

# 2. Compara con TODOS los embeddings guardados
matriz_docs = [
    [0.23, -0.45, 0.12, 0.88, ...],  # fragmento 1
    [0.10, 0.20, 0.30, -0.15, ...],  # fragmento 2
    [0.25, -0.43, 0.12, 0.86, ...],  # fragmento 3 ← MÁS SIMILAR
    ...
]

# 3. Calcula similitud coseno (qué tan parejos son los vectores)
similitudes = [
    0.87,   # fragmento 1
    0.45,   # fragmento 2
    0.95,   # fragmento 3 ← GANADOR
    ...
]

# 4. Ordena y toma los TOP 4
top_fragmentos = [fragmento_3, fragmento_1, ...]
```

**¿Por qué funciona?**
- Vectores similares = textos con significado parecido
- No busca palabras exactas (búsqueda semántica, no léxica)
- "¿Dónde pongo la API key?" encuentra "Se inyecta en runtime con -e GOOGLE_API_KEY=..."

---

### 4️⃣ Generación (LLM)

**Se construye el prompt:**

```
Eres un asistente preciso. Responde usando SOLO el contexto proporcionado.
Si no hay respuesta en el contexto, di que no tienes suficiente información.

Contexto:
---------
Se inyecta en runtime mediante -e GOOGLE_API_KEY=...

Nunca está dentro de la imagen ni en el código. La API key de Gemini 
debe regenerarse si se compromete.

---

Se pasa en tiempo de ejecución, no va en el repo. Ejemplo:
docker run -e GOOGLE_API_KEY=TU_KEY mlops-rag

---

Pregunta: ¿Dónde pongo la API key?

Respuesta:
```

**El LLM (Gemini 2.5 Flash) genera:**
```
La API key se pasa en tiempo de ejecución mediante la variable de entorno
GOOGLE_API_KEY, usando el flag -e de Docker. Ejemplo:
docker run -e GOOGLE_API_KEY=tu_key mlops-rag

Nunca debe estar dentro de la imagen ni en el código.
```

---

## Variables de Configuración

```python
DOCS_DIR = "docs"                           # Carpeta con .txt
CHAT_MODEL = "gemini-2.5-flash"             # Modelo generador
EMBED_MODEL = "gemini-embedding-001"        # Modelo de embeddings
EMBED_DIM = 768                             # Dimensión del embedding
TOP_K = 4                                   # Fragmentos a recuperar
CHUNK_WORDS = 150                           # Palabras por fragmento
CHUNK_OVERLAP = 30                          # Solapamiento entre fragmentos
```

**Qué hacer si:**
- ❌ Las respuestas son imprecisas → aumenta `TOP_K` (5 o 6)
- ❌ Es lento → reduce `EMBED_DIM` (512) o `CHUNK_WORDS` (100)
- ❌ Fragmentos muy pequeños → aumenta `CHUNK_WORDS` (200)

---

## Matriz de Embeddings en Memoria

```python
import numpy as np

# Ejemplo:
self._matrix = np.array([
    [0.23, -0.45, ..., -0.67],    # embedding del fragmento 1
    [0.10,  0.20, ..., 0.40],     # embedding del fragmento 2
    [0.25, -0.43, ..., -0.65],    # embedding del fragmento 3
    ...
])
# Forma: (n_fragmentos, 768)

# Búsqueda: q es el vector de la pregunta
scores = self._matrix @ q  # Producto punto con todos los fragmentos
top_indices = np.argsort(scores)[::-1][:TOP_K]  # Los 4 mejores
```

---

## Cuándo falla y por qué

| Situación | Código HTTP | Razón | Solución |
|-----------|-------------|-------|----------|
| Sin documentos en `/docs/` | 503 | `build()` lanza RuntimeError | Agrega al menos 1 `.txt` |
| API key inválida | 502 | Gemini rechaza la key | Verifica la key en https://aistudio.google.com/apikey |
| Pregunta no en documentos | 200 | LLM responde honestamente | Es el comportamiento correcto (no inventa) |
| `/health` antes de `/ask` | 200 | Index no está listo (`index_ready=false`) | Esto es normal; `/health` nunca falla |

---

## Flujo de seguridad

```
┌─────────────────────┐
│  docker run         │
│  -e GOOGLE_API_KEY  │  ← AQUÍ entra la clave
└──────────┬──────────┘
           ↓
   ┌───────────────────┐
   │  Contenedor       │
   │  (variables env)  │
   └─────────┬─────────┘
             ↓
        ┌────────────┐
        │ _get_api_key() ← Lee ENV, NUNCA del código
        └────────────┘
             ↓
        ┌────────────┐
        │ genai.Client(api_key=key)
        └────────────┘
             ↓
        ┌────────────┐
        │ Gemini API ← Solo en runtime
        └────────────┘

Notas:
- Dockerfile: SIN ENV GOOGLE_API_KEY
- main.py: SIN strings hardcodeadas
- Git: SIN secretos en historial
```

---

## Ejemplo real: conversación completa

```bash
# Usuario abre terminal
$ export GOOGLE_API_KEY="AIza..."
$ docker run -p 8000:8000 -e GOOGLE_API_KEY="$GOOGLE_API_KEY" mlops-rag

# Contenedor arranca → /health disponible inmediatamente

$ curl http://localhost:8000/health
{"status": "ok", "index_ready": false, "chunks": 0}

# Usuario hace la PRIMERA pregunta
$ curl -X POST http://localhost:8000/ask \
    -H "Content-Type: application/json" \
    -d '{"question": "¿Cuál es la rúbrica?"}'

# Internamente:
# 1. Detecta index no ready → build()
# 2. Carga docs/* → 3 fragmentos
# 3. Genera embeddings (Gemini API) → demora ~10s
# 4. Guarda matriz en RAM
# 5. Recupera TOP_4 para la pregunta
# 6. Envía a Gemini con contexto
# 7. Responde

{"answer": "La rúbrica vale 20 puntos: 6 para que arranche..."}

# Ahora /health dice:
$ curl http://localhost:8000/health
{"status": "ok", "index_ready": true, "chunks": 3}

# SEGUNDA pregunta (rápida, sin rebuild):
$ curl -X POST http://localhost:8000/ask \
    -H "Content-Type: application/json" \
    -d '{"question": "¿Quién es el instructor?"}'

# Solo busca + consulta Gemini → ~1s (sin generar embeddings)
{"answer": "..."}
```

---

## Limitaciones y trade-offs

| Aspecto | Limitación | Por qué | Alternativa |
|--------|-----------|--------|------------|
| **Índice en RAM** | Máx. ~10k fragmentos en una máquina normal | Numpy matrices caben en RAM | ChromaDB, Pinecone (más pesado) |
| **Sin persistencia** | Si reinicia el contenedor, se recalculan embeddings | Es lazy, no guarda en disco | Redis, Weaviate (más caro) |
| **Top-K fijo** | Siempre recupera 4 fragmentos | Simplifica el código | Búsqueda adaptativa (complejo) |
| **Embeddings recalculados** | Cada `docker run` nuevo genera desde cero | Optimiza para simplicidad | Cachés externos |

---

## Checklist técnico

- [ ] ¿Los `.txt` cargan sin errores?
- [ ] ¿El primer `/ask` tarda 10-15s? (es normal)
- [ ] ¿Respuestas posteriores son rápidas (~1s)?
- [ ] ¿Las respuestas usan solo contexto de los documentos?
- [ ] ¿Si cambio API key en runtime, funciona?
- [ ] ¿`/health` arranca al instante sin API key?
