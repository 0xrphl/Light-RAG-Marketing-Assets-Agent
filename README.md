# 🖼️ Media Assets Marketing Agent

**AI-Powered Image Asset Library with Knowledge Graph Search**

Analyze 420 marketing images with **Gemini Vision** → build a rich knowledge graph with **LightRAG** → query your asset library by objects, colors, emotions, settings, mood, and marketing use-cases.

> A [LightRAG](https://github.com/HKUDS/LightRAG) demo — GraphRAG for visual media assets.

<p align="center">
  <a href="https://huggingface.co/datasets/0xrphl/Light-RAG-Marketing-Assets-Agent">
    <img src="docs/HuggingFace.svg" alt="HuggingFace" width="28" style="vertical-align:middle"/>
    <strong>Pre-ingested dataset on HuggingFace</strong>
  </a>
  &nbsp;·&nbsp;
  <a href="https://huggingface.co/datasets/0xrphl/Light-RAG-Marketing-Assets-Agent">
    <img alt="HF Dataset" src="https://img.shields.io/badge/🤗_Dataset-Light--RAG--Marketing--Assets-yellow"/>
  </a>
</p>

---

## 🏗️ Architecture

<p align="center">
  <img src="docs/architecture.svg" alt="End-to-End GraphRAG Pipeline" width="100%"/>
</p>

---

## 📊 Dataset Statistics

| Metric | Value |
|--------|-------|
| **Source images** | 420 (JPG / PNG / WebP) |
| **Text chunks** | 2,095 (5 per image) |
| **Graph nodes** | 13,604 entities |
| **Graph edges** | 22,958 relationships |
| **Unique entities** | 2,094 (deduplicated) |
| **Unique relations** | 2,039 (deduplicated) |
| **Embedding model** | `text-embedding-3-small` (OpenAI) |
| **Embedding dimensions** | **1,536** |
| **Total vectors** | 38,657 |
| **Pre-ingested data** | ~513 MB ([🤗 HuggingFace](https://huggingface.co/datasets/0xrphl/Light-RAG-Marketing-Assets-Agent)) |

---

## 📸 Screenshots

<table>
  <tr>
    <td align="center"><strong>Knowledge Graph (Full)</strong></td>
    <td align="center"><strong>Graph Demo</strong></td>
  </tr>
  <tr>
    <td><img src="docs/graph-full-ingested.png" alt="Knowledge Graph" width="500"/></td>
    <td><img src="docs/lightrag%20demo%20grtaph.png" alt="Graph Demo" width="500"/></td>
  </tr>
  <tr>
    <td align="center"><strong>Query RAG Demo</strong></td>
    <td align="center"><strong>Node Detail</strong></td>
  </tr>
  <tr>
    <td><img src="docs/query%20rag%20demo.png" alt="Query Demo" width="500"/></td>
    <td><img src="docs/graph-node-selected.png" alt="Node Detail" width="500"/></td>
  </tr>
  <tr>
    <td align="center" colspan="2"><strong>Document Management</strong></td>
  </tr>
  <tr>
    <td colspan="2" align="center"><img src="docs/document-management.png" alt="Documents" width="700"/></td>
  </tr>
</table>

---

## 🚀 Quick Start

### Option A: Run with pre-ingested demo data (recommended)

No ingestion needed — download the pre-built knowledge graph from [🤗 HuggingFace](https://huggingface.co/datasets/0xrphl/Light-RAG-Marketing-Assets-Agent) and start querying immediately.

```bash
# 1. Clone & configure
git clone https://github.com/0xrphl/Light-RAG-Marketing-Assets-Agent.git
cd Light-RAG-Marketing-Assets-Agent
cp .env.example .env   # add OPENAI_API_KEY (for queries)

# 2. Install dependencies
pip install -r requirements.txt

# 3. Download pre-ingested data from HuggingFace (~513 MB)
python setup.py

# 4. Start LightRAG + Neo4j
docker compose up -d

# 5. Initialize Neo4j graph from GraphML
python init_neo4j.py

# 6. Query!
python query.py "sunset beach photos"
python query.py "professional headshots" --mode mix
python query.py "images with warm golden light" --all-modes
```

### Option B: Run empty — ingest your own images

Start with a clean LightRAG instance, bring your own images, and build the knowledge graph from scratch.

```bash
# 1. Clone & configure
git clone https://github.com/0xrphl/Light-RAG-Marketing-Assets-Agent.git
cd Light-RAG-Marketing-Assets-Agent
cp .env.example .env   # add OPENAI_API_KEY + GEMINI_API_KEY

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start LightRAG + Neo4j (empty graph)
docker compose up -d

# 4. Add your images to imgs/ folder, then ingest
python ingest.py --limit 10        # start with a few to test
python ingest.py --resume          # continue ingesting remaining

# 5. Query your custom library
python query.py "your search query"
```

---

## 📁 Project Structure

```
Light-RAG-Marketing-Assets-Agent/
├── ingest.py           # Image analysis + LightRAG ingestion pipeline
├── query.py            # CLI query tool (5 modes: naive/local/global/hybrid/mix)
├── setup.py            # Download pre-ingested data from HuggingFace
├── init_neo4j.py       # Import GraphML knowledge graph into Neo4j
├── docker-compose.yml  # LightRAG + Neo4j Docker stack
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variable template
├── app/                # Vue.js Explorer SPA
│   ├── index.html
│   ├── app.js
│   └── style.css
├── data/               # Pre-ingested LightRAG storage (~513 MB, via setup.py)
│   └── lightrag/
│       ├── rag_storage/  # Vectors (466 MB), KV stores, GraphML (20 MB)
│       └── tiktoken/     # Tokenizer cache
├── docs/               # Screenshots, architecture SVG, generator script
│   ├── architecture.svg
│   ├── generate_architecture_svg.py
│   └── *.png
└── imgs/               # ~420 source image assets
```

---

## 🔄 Ingestion Pipeline

Each image goes through a **multi-stage pipeline** producing **5 chunks per image**:

```
420 Images ──→ Gemini Vision (2.5-flash) ──→ 5 Chunks/Image ──→ LightRAG (GPT-4o) ──→ Embeddings (1536-d)
                                                                       │                       │
                                                                       ▼                       ▼
                                                                  Neo4j Graph            NanoVectorDB
                                                              13,604 nodes            466 MB vectors
                                                              22,958 edges            3 separate indexes
```

### Chunks per Image

| # | Chunk | Content |
|---|-------|---------|
| 1 | **Core** | Subject description, objects, elements |
| 2 | **Visual** | Colors, palette, photography style, lighting |
| 3 | **People & Setting** | Demographics, emotions, location, mood |
| 4 | **Marketing** | Industries, campaigns, audience, tags |
| 5 | **Full** | Complete analysis (holistic graph connections) |

### Gemini Vision Prompt Sections

1. Core Description · 2. Objects & Elements · 3. Colors & Palette · 4. People & Demographics
5. Setting & Place · 6. Photography & Style · 7. Mood & Atmosphere · 8. Marketing Use Cases + Tags

---

## 🔍 Query Modes

| Mode | Strategy | Use Case | Speed |
|------|----------|----------|-------|
| `naive` | Pure vector similarity over chunks | Quick similarity search | ⚡ Fastest |
| `local` | Entity-centric 1-hop graph expansion | Find specific objects/people | 🔍 Precise |
| `global` | Community-level Leiden cluster summaries | Broad theme exploration | 🌐 Broad |
| `hybrid` | local + global combined **(default)** | Balanced search | ⚖️ Balanced |
| `mix` | naive + local + global fused & reranked | Maximum coverage | 🧬 Thorough |

### Query Examples

```bash
python query.py "images of people working in an office"
python query.py "warm golden hour photography" --mode local
python query.py "images suitable for healthcare campaigns" --mode global
python query.py "outdoor adventure sports" --all-modes
python query.py   # Interactive REPL mode
```

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

## ⚙️ CLI Options

### ingest.py

```bash
python ingest.py                      # Ingest all images
python ingest.py --limit 10           # Process first 10 only
python ingest.py --resume             # Skip already-ingested images
python ingest.py --batch-size 20      # Batch size before pause
python ingest.py --dry-run            # Analyze without ingesting
python ingest.py --clear              # Clear graph before ingesting
python ingest.py --resume --limit 50  # Resume, process 50 more
```

### query.py

```bash
python query.py "your query"              # Default hybrid mode
python query.py "your query" --mode mix   # Specific mode
python query.py "your query" --all-modes  # All 5 modes compared
python query.py                           # Interactive REPL
```

### setup.py

```bash
python setup.py           # Download pre-ingested data from HuggingFace
python setup.py --force   # Re-download even if data exists
```

### init_neo4j.py

```bash
python init_neo4j.py          # Import GraphML into Neo4j (skips if already populated)
python init_neo4j.py --force  # Clear Neo4j and reimport
```

---

## 🐳 Docker Services

| Container | Image | Port | Purpose |
|-----------|-------|------|---------|
| **lightrag** | `ghcr.io/hkuds/lightrag` | 9621 | LightRAG server (GraphRAG + WebUI) |
| **neo4j** | `neo4j:5.15.0` | 7474, 7687 | Graph database (Bolt + Browser) |

```bash
docker compose up -d          # Start services
docker compose logs -f        # View logs
docker compose down           # Stop services
docker compose down -v        # Stop + remove volumes
```

---

## 🔑 Environment Variables

| Variable | Purpose | Required |
|----------|---------|----------|
| `OPENAI_API_KEY` | LightRAG entity extraction + embeddings (GPT-4o) | ✅ |
| `GEMINI_API_KEY` | Image vision analysis (Gemini Flash) | ✅ for ingestion |
| `LLM_MODEL` | LightRAG LLM model (default: `gpt-4o`) | ❌ |
| `EMBEDDING_MODEL` | Embedding model (default: `text-embedding-3-small`) | ❌ |
| `GEMINI_MODEL` | Vision model (default: `gemini-3.5-flash`) | ❌ |

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
