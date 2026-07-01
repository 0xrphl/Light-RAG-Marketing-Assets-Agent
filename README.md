# 🖼️ Media Assets Marketing Agent

**AI-Powered Image Asset Library with Knowledge Graph Search**

Analyze 400+ marketing images with **Gemini Vision** → build a rich knowledge graph with **LightRAG** → query your asset library by objects, colors, emotions, settings, mood, and marketing use-cases.

> A [LightRAG](https://github.com/HKUDS/LightRAG) demo — GraphRAG for visual media assets.

---

## 🏗️ Architecture

![Pipeline](docs/architecture.svg)

---

## 📸 Screenshots

| Knowledge Graph | Node Detail | Documents |
|:---:|:---:|:---:|
| ![Graph](docs/graph-full-ingested.png) | ![Node](docs/graph-node-selected.png) | ![Docs](docs/document-management.png) |

| Graph Demo | Query RAG Demo |
|:---:|:---:|
| ![Graph Demo](docs/lightrag%20demo%20grtaph.png) | ![Query Demo](docs/query%20rag%20demo.png) |

---

## 🚀 Quick Start

```bash
# 1. Clone & configure
git clone https://github.com/0xrphl/Light-RAG-Marketing-Assets-Agent.git
cd Light-RAG-Marketing-Assets-Agent
cp .env.example .env   # add OPENAI_API_KEY + GEMINI_API_KEY

# 2. Install dependencies
pip install -r requirements.txt

# 3. Download pre-ingested data from HuggingFace (~513 MB)
python setup.py

# 4. Start LightRAG + Neo4j
docker compose up -d

# 5. Initialize Neo4j graph
python init_neo4j.py

# 6. Query — no ingestion needed, data is pre-loaded!
python query.py "sunset beach photos"

# 7. Explorer app (serve from project root)
python -m http.server 8899
# Open http://localhost:8899/app/
```

> **📦 Pre-ingested data on HuggingFace!** The vectors, KV stores, and knowledge graph
> from ~420 images (analyzed with Gemini Vision) are hosted on
> [🤗 HuggingFace](https://huggingface.co/datasets/0xrphl/Light-RAG-Marketing-Assets-Agent).
> Run `python setup.py` to download them — no re-ingestion needed!
>
> To re-ingest from scratch: `python ingest.py --clear`

---

## 📁 Project Structure

```
media_assets_marketing_agent/
├── ingest.py           # Image analysis + LightRAG ingestion
├── query.py            # CLI query tool (5 modes)
├── init_neo4j.py       # Import graph into Neo4j from graphml
├── docker-compose.yml  # LightRAG + Neo4j stack
├── requirements.txt
├── .env.example
├── app/                # Vue.js Explorer SPA
│   ├── index.html
│   ├── app.js
│   └── style.css
├── setup.py            # Download pre-ingested data from HuggingFace
├── data/               # Pre-ingested LightRAG storage (~513 MB, via setup.py)
│   └── lightrag/
│       ├── rag_storage/  # Vectors, KV stores, graphml
│       └── tiktoken/     # Tokenizer cache
├── docs/               # Screenshots & architecture
├── imgs/               # ~420 image assets
└── README.md
```

---

## 🔄 Ingestion Pipeline

Each image goes through a **3-step pipeline** producing **5 chunks per image**:

```
┌──────────┐     ┌──────────────┐     ┌──────────────┐
│  Image   │────▶│ Gemini Vision│────▶│   LightRAG   │
│  (file)  │     │  Analysis    │     │  (5 chunks)  │
└──────────┘     └──────────────┘     └──────────────┘
```

### Chunks per Image

| # | Chunk | Content |
|---|-------|---------|
| 1 | **Core** | Subject description, objects, elements |
| 2 | **Visual** | Colors, palette, photography style, lighting |
| 3 | **People & Setting** | Demographics, emotions, location, mood |
| 4 | **Marketing** | Industries, campaigns, audience, tags |
| 5 | **Full** | Complete analysis (holistic graph connections) |

### Extracted Metadata

- **Objects & Elements** — every visible item, prop, animal, vehicle, food, device
- **Colors & Palette** — primary/secondary colors, mood, harmony
- **People & Demographics** — count, age, gender, clothing, expressions, emotions
- **Setting & Place** — indoor/outdoor, specific location, architecture, time of day
- **Photography Style** — shot type, angle, lighting, focus, post-processing
- **Mood & Atmosphere** — emotional tone, energy level, mood descriptors
- **Marketing Use Cases** — industries, campaign types, target audience, themes
- **Tags** — 30-50 searchable keywords per image

---

## 🖥️ Explorer App

The `app/` folder contains a **Vue 3 single-page application**:

- **Query Tab** — Natural language search, 5 modes, markdown results, auto image gallery
- **Graph Tab** — Force-directed graph (1000 nodes), filter by community, node detail sidebar

```bash
python -m http.server 8899
# Open http://localhost:8899/app/
```

---

## 🔍 Query Examples

```bash
python query.py "images of people working in an office"
python query.py "warm golden hour photography"
python query.py "images suitable for healthcare campaigns"
python query.py "outdoor adventure sports" --all-modes
python query.py   # Interactive REPL
```

### Query Modes

| Mode | Description |
|------|-------------|
| `naive` | Simple vector similarity search |
| `local` | Entity-focused neighborhood search |
| `global` | High-level theme and community search |
| `hybrid` | Combined local + global (default) |
| `mix` | All strategies merged |

---

## ⚙️ CLI Options

### ingest.py

```bash
python ingest.py                    # Ingest all 420 images
python ingest.py --limit 10         # Process first 10 only
python ingest.py --resume           # Skip already-ingested images
python ingest.py --batch-size 20    # Batch size before pause
python ingest.py --dry-run          # Analyze without ingesting
python ingest.py --clear            # Clear graph before ingesting
python ingest.py --resume --limit 50  # Resume, process 50 more
```

### query.py

```bash
python query.py "your query"              # Default hybrid mode
python query.py "your query" --mode mix   # Specific mode
python query.py "your query" --all-modes  # All 5 modes compared
python query.py                           # Interactive REPL
```

---

## 🐳 Docker Services

| Container | Image | Port | Purpose |
|-----------|-------|------|---------|
| **lightrag** | ghcr.io/hkuds/lightrag | 9621 | Knowledge Graph (GraphRAG) |
| **neo4j** | neo4j:5.15.0 | 7474, 7687 | Graph Database |

```bash
docker compose up -d          # Start services
docker compose logs -f        # View logs
docker compose down           # Stop services
docker compose down -v        # Stop + remove data
```

---

## 🔑 Environment Variables

| Variable | Purpose | Required |
|----------|---------|----------|
| `OPENAI_API_KEY` | LightRAG entity extraction + embeddings (GPT-4o) | ✅ |
| `GEMINI_API_KEY` | Image vision analysis (Gemini Flash) | ✅ |
| `ANTHROPIC_API_KEY` | Optional advanced querying | ❌ |
| `LLM_MODEL` | LightRAG LLM model (default: gpt-4o) | ❌ |
| `EMBEDDING_MODEL` | Embedding model (default: text-embedding-3-small) | ❌ |
| `GEMINI_MODEL` | Vision model (default: gemini-3.5-flash) | ❌ |

---

## 🌐 Access Points

| Service | URL |
|---------|-----|
| Explorer App | http://localhost:8899/app/ |
| LightRAG WebUI | http://localhost:9621 |
| Neo4j Browser | http://localhost:7474 |

---

## 📝 License

MIT License
