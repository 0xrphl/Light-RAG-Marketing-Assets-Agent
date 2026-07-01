#!/usr/bin/env python3
"""
Generate docs/architecture.svg — a detailed, expert-level diagram of the
Media Assets Marketing Agent GraphRAG pipeline.

Usage:
    python docs/generate_architecture_svg.py

Regenerate any time the pipeline stats change (image count, chunk count,
entity/relationship counts, embedding dimensions, etc). Stats can be pulled
automatically from the local data/ folder with --stats-from-data.
"""

import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_PATH = SCRIPT_DIR / "architecture.svg"
DATA_DIR = SCRIPT_DIR.parent / "data" / "lightrag" / "rag_storage"
IMGS_DIR = SCRIPT_DIR.parent / "imgs"

DEFAULT_STATS = {
    "images": 420,
    "documents": 2095,
    "entities_raw": 13604,
    "relationships_raw": 22958,
    "entities_unique": 2094,
    "relationships_unique": 2039,
    "embedding_dim": 1536,
    "embedding_model": "text-embedding-3-small",
    "vdb_entities_mb": 165,
    "vdb_relationships_mb": 274,
    "vdb_chunks_mb": 27,
    "graphml_mb": 20,
}


def load_stats_from_data():
    """Read real stats from the local data/ folder, falling back to defaults."""
    stats = dict(DEFAULT_STATS)

    if IMGS_DIR.exists():
        exts = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tiff"}
        stats["images"] = len([f for f in IMGS_DIR.iterdir() if f.suffix.lower() in exts])

    if DATA_DIR.exists():
        try:
            full_docs = json.loads((DATA_DIR / "kv_store_full_docs.json").read_text(encoding="utf-8"))
            stats["documents"] = len(full_docs)
        except Exception:
            pass

        try:
            full_entities = json.loads((DATA_DIR / "kv_store_full_entities.json").read_text(encoding="utf-8"))
            stats["entities_unique"] = len(full_entities)
        except Exception:
            pass

        try:
            full_relations = json.loads((DATA_DIR / "kv_store_full_relations.json").read_text(encoding="utf-8"))
            stats["relationships_unique"] = len(full_relations)
        except Exception:
            pass

        try:
            vdb_e = json.loads((DATA_DIR / "vdb_entities.json").read_text(encoding="utf-8"))
            stats["entities_raw"] = len(vdb_e.get("data", []))
            stats["embedding_dim"] = vdb_e.get("embedding_dim", stats["embedding_dim"])
            stats["vdb_entities_mb"] = round((DATA_DIR / "vdb_entities.json").stat().st_size / 1024 / 1024)
        except Exception:
            pass

        try:
            vdb_r = json.loads((DATA_DIR / "vdb_relationships.json").read_text(encoding="utf-8"))
            stats["relationships_raw"] = len(vdb_r.get("data", []))
            stats["vdb_relationships_mb"] = round((DATA_DIR / "vdb_relationships.json").stat().st_size / 1024 / 1024)
        except Exception:
            pass

        try:
            stats["vdb_chunks_mb"] = round((DATA_DIR / "vdb_chunks.json").stat().st_size / 1024 / 1024)
        except Exception:
            pass

        graphml_path = DATA_DIR / "graph_chunk_entity_relation.graphml"
        if graphml_path.exists():
            try:
                stats["graphml_mb"] = round(graphml_path.stat().st_size / 1024 / 1024)
                tree = ET.parse(graphml_path)
                root = tree.getroot()
                ns = {"g": "http://graphml.graphdrawing.org/xmlns"}
                nodes = root.findall(".//g:node", ns)
                edges = root.findall(".//g:edge", ns)
                if nodes:
                    stats["entities_raw"] = len(nodes)
                if edges:
                    stats["relationships_raw"] = len(edges)
            except Exception:
                pass

    return stats


# ── SVG building blocks ──────────────────────────────────────────────────

def svg_header():
    return """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1400 900" font-family="Segoe UI, sans-serif">
  <defs>
    <linearGradient id="g1" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#6c8cff"/><stop offset="100%" stop-color="#a78bfa"/></linearGradient>
    <linearGradient id="g2" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#f472b6"/><stop offset="100%" stop-color="#fb923c"/></linearGradient>
    <linearGradient id="g3" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#4ade80"/><stop offset="100%" stop-color="#22d3ee"/></linearGradient>
    <linearGradient id="g4" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#fbbf24"/><stop offset="100%" stop-color="#f59e0b"/></linearGradient>
    <linearGradient id="g5" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#f87171"/><stop offset="100%" stop-color="#dc2626"/></linearGradient>
    <linearGradient id="g6" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#38bdf8"/><stop offset="100%" stop-color="#818cf8"/></linearGradient>
    <filter id="shadow"><feDropShadow dx="0" dy="2" stdDeviation="4" flood-opacity=".2"/></filter>
    <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M0,0 L10,5 L0,10 z" fill="#8b8fa8"/>
    </marker>
  </defs>
"""


def svg_footer():
    return "</svg>\n"


def rect(x, y, w, h, fill="#151822", stroke="#2d3148", stroke_width=1, extra=""):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="{stroke_width}" filter="url(#shadow)" {extra}/>\n')


def text(x, y, s, size=11, fill="#e4e6f0", weight="normal", anchor="middle"):
    esc = s.replace("&", "&amp;")
    return (f'<text x="{x}" y="{y}" text-anchor="{anchor}" fill="{fill}" font-size="{size}" '
            f'font-weight="{weight}">{esc}</text>\n')


def arrow(x1, y1, x2, y2):
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#8b8fa8" stroke-width="2" marker-end="url(#arrow)"/>\n'


def line(x1, y1, x2, y2):
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#8b8fa8" stroke-width="2"/>\n'


def build_svg(stats: dict) -> str:
    s = []
    s.append(svg_header())
    s.append('<rect width="1400" height="900" rx="16" fill="#0b0d13"/>\n')
    s.append(text(700, 36, "Media Assets Marketing Agent \u2014 End-to-End GraphRAG Pipeline", 22, "#e4e6f0", "700"))
    s.append(text(700, 58, "Ingestion \u00b7 Object Extraction \u00b7 Vector Embeddings \u00b7 Knowledge Graph \u00b7 Multi-Mode Retrieval", 12, "#8b8fa8"))

    # STAGE 1: Images
    s.append(rect(30, 90, 190, 150))
    s.append(text(125, 122, "\U0001F5BC\uFE0F", 26))
    s.append(text(125, 146, f"{stats['images']} Images", 13, weight="700"))
    s.append(text(125, 164, "JPG / PNG / WebP", 10, "#8b8fa8"))
    s.append(text(125, 180, "Stock + Creative Assets", 10, "#8b8fa8"))
    s.append(text(125, 200, "imgs/ folder", 10, "#6c8cff"))
    s.append(text(125, 220, "~2-4 MB avg / image", 9, "#8b8fa8"))
    s.append(arrow(220, 165, 270, 165))

    # STAGE 2: Gemini Vision
    s.append(rect(275, 90, 220, 150, stroke="url(#g2)", stroke_width=1.5))
    s.append(text(385, 122, "\U0001F52E", 26))
    s.append(text(385, 146, "Gemini Vision Analysis", 13, weight="700"))
    s.append(text(385, 164, "gemini-2.5-flash", 10, "#8b8fa8"))
    s.append(text(385, 182, "Object &amp; scene detection", 10, "#8b8fa8"))
    s.append(text(385, 198, "Colors \u00b7 People \u00b7 Mood \u00b7 Tags", 10, "#8b8fa8"))
    s.append(text(385, 216, "Structured 8-section prompt", 9, "#f472b6"))
    s.append(arrow(495, 165, 545, 165))

    # STAGE 3: Chunking
    s.append(rect(550, 90, 230, 150, stroke="url(#g3)", stroke_width=1.5))
    s.append(text(665, 122, "\U0001F4E6", 26))
    s.append(text(665, 146, "5 Chunks / Image", 13, weight="700"))
    s.append(text(665, 164, "Core \u00b7 Visual \u00b7 People/Setting", 10, "#8b8fa8"))
    s.append(text(665, 180, "Marketing \u00b7 Full Analysis", 10, "#8b8fa8"))
    s.append(text(665, 200, f"{stats['documents']:,} documents total", 10, "#4ade80", "600"))
    s.append(text(665, 216, "CHUNK_SIZE=1200 / overlap=200", 9, "#8b8fa8"))
    s.append(arrow(780, 165, 830, 165))

    # STAGE 4: LightRAG Extraction
    s.append(rect(835, 70, 260, 190, stroke="url(#g4)", stroke_width=1.5))
    s.append(text(965, 102, "\U0001F9E0", 26))
    s.append(text(965, 126, "LightRAG Extraction (GPT-4o)", 13, weight="700"))
    s.append(text(965, 146, "Entity + Relationship extraction", 10, "#8b8fa8"))
    s.append(text(965, 164, f"{stats['entities_raw']:,} entities (raw)", 11, "#fbbf24", "600"))
    s.append(text(965, 180, f"{stats['relationships_raw']:,} relationships (raw)", 11, "#fbbf24", "600"))
    s.append(text(965, 198, f"\u2192 {stats['entities_unique']:,} unique entities", 10, "#8b8fa8"))
    s.append(text(965, 214, f"\u2192 {stats['relationships_unique']:,} unique relations", 10, "#8b8fa8"))
    s.append(text(965, 234, "Entity types: object, person, place,", 9, "#8b8fa8"))
    s.append(text(965, 248, "color, mood, industry, use-case", 9, "#8b8fa8"))
    s.append(arrow(1095, 165, 1145, 165))

    # STAGE 5: Embeddings
    s.append(rect(1150, 70, 220, 190, stroke="url(#g6)", stroke_width=1.5))
    s.append(text(1260, 102, "\U0001F9EC", 26))
    s.append(text(1260, 126, "Embeddings", 13, weight="700"))
    s.append(text(1260, 146, stats["embedding_model"], 10, "#8b8fa8"))
    s.append(text(1260, 164, f"{stats['embedding_dim']} dimensions", 12, "#38bdf8", "700"))
    s.append(text(1260, 184, "Entities \u00b7 Relations \u00b7 Chunks", 9, "#8b8fa8"))
    s.append(text(1260, 202, "3 separate vector indexes", 9, "#8b8fa8"))
    s.append(text(1260, 222, "Cosine similarity search", 9, "#8b8fa8"))
    total_vec_mb = stats["vdb_entities_mb"] + stats["vdb_relationships_mb"] + stats["vdb_chunks_mb"]
    s.append(text(1260, 240, f"~{total_vec_mb} MB total vectors", 9, "#8b8fa8"))

    s.append(arrow(965, 260, 965, 310))
    s.append(arrow(1260, 260, 1260, 310))

    s.append(text(700, 300, "STORAGE LAYER", 13, "#8b8fa8", "700"))

    # Neo4j
    s.append(rect(835, 315, 260, 130, stroke="url(#g5)", stroke_width=1.5))
    s.append(text(965, 345, "\U0001F578\uFE0F", 24))
    s.append(text(965, 368, "Neo4j Graph DB", 13, weight="700"))
    s.append(text(965, 386, "GRAPH_STORAGE=Neo4JStorage", 10, "#8b8fa8"))
    s.append(text(965, 404, f"{stats['entities_raw']:,} nodes \u00b7 {stats['relationships_raw']:,} edges", 10, "#8b8fa8"))
    s.append(text(965, 422, "Community detection (Leiden)", 9, "#8b8fa8"))
    s.append(text(965, 436, f"graph_chunk_entity_relation.graphml ({stats['graphml_mb']}MB)", 9, "#8b8fa8"))

    # NanoVectorDB
    s.append(rect(1150, 315, 220, 130, stroke="url(#g6)", stroke_width=1.5))
    s.append(text(1260, 345, "\U0001F5C2\uFE0F", 24))
    s.append(text(1260, 368, "NanoVectorDB + KV Store", 13, weight="700"))
    s.append(text(1260, 386, f"vdb_entities.json ({stats['vdb_entities_mb']} MB)", 10, "#8b8fa8"))
    s.append(text(1260, 402, f"vdb_relationships.json ({stats['vdb_relationships_mb']} MB)", 10, "#8b8fa8"))
    s.append(text(1260, 418, f"vdb_chunks.json ({stats['vdb_chunks_mb']} MB)", 10, "#8b8fa8"))
    s.append(text(1260, 434, "JsonKVStorage (docs/status/cache)", 9, "#8b8fa8"))

    s.append(arrow(965, 445, 965, 500))
    s.append(arrow(1260, 445, 1260, 500))
    s.append(line(965, 500, 1260, 500))
    s.append(arrow(1112, 500, 1112, 530))

    s.append(text(700, 560, "RETRIEVAL \u2014 5 QUERY MODES (query.py)", 13, "#8b8fa8", "700"))

    modes = [
        (60, "naive", "#2d3148", 1, [
            "Pure vector similarity",
            "over chunk embeddings",
            "No graph traversal",
        ], "Fastest, least contextual", "#4ade80"),
        (300, "local", "#2d3148", 1, [
            "Entity-centric neighborhood",
            "1-hop graph expansion from",
            "matched entities",
        ], "Good for specific objects", "#4ade80"),
        (540, "global", "#2d3148", 1, [
            "Community / theme-level",
            "summaries via Leiden clusters",
            "on the knowledge graph",
        ], "Good for broad themes", "#4ade80"),
        (780, "hybrid (default)", "url(#g1)", 1.5, [
            "local + global combined",
            "Entities + community context",
            "merged into one context window",
        ], "Balanced precision/recall", "#a78bfa"),
        (1020, "mix", "url(#g2)", 1.5, [
            "naive + local + global fused",
            "Vector search AND full graph",
            "traversal in one reranked pass",
        ], "Most thorough, slowest", "#f472b6"),
    ]

    for x, title, stroke, sw, lines_, tag, tag_color in modes:
        s.append(rect(x, 580, 220, 120, stroke=stroke, stroke_width=sw))
        cx = x + 110
        s.append(text(cx, 606, title, 13, weight="700"))
        yy = 626
        for ln in lines_:
            s.append(text(cx, yy, ln, 9, "#8b8fa8"))
            yy += 16
        s.append(text(cx, 678, tag, 9, tag_color))

    s.append(arrow(700, 700, 700, 740))

    s.append(rect(500, 745, 400, 110, stroke="url(#g4)", stroke_width=1.5))
    s.append(text(700, 775, "\u2728", 24))
    s.append(text(700, 800, "GPT-4o Answer Synthesis", 13, weight="700"))
    s.append(text(700, 818, "Retrieved context \u2192 natural language response", 10, "#8b8fa8"))
    s.append(text(700, 834, "+ matched image asset filenames for the Explorer app", 10, "#8b8fa8"))

    footer = (f"Media Assets Marketing Agent \u2014 LightRAG GraphRAG Pipeline \u00b7 "
              f"{stats['images']} images \u00b7 {stats['documents']:,} chunks \u00b7 "
              f"{stats['entities_unique']:,} entities \u00b7 {stats['relationships_unique']:,} relations \u00b7 "
              f"{stats['embedding_dim']}-dim embeddings")
    s.append(text(700, 885, footer, 11, "#8b8fa8"))

    s.append(svg_footer())
    return "".join(s)


def main():
    parser = argparse.ArgumentParser(description="Generate the architecture.svg diagram")
    parser.add_argument("--stats-from-data", action="store_true",
                        help="Read real stats from local data/ folder instead of using defaults")
    parser.add_argument("--output", type=str, default=str(OUTPUT_PATH),
                        help="Output SVG path")
    args = parser.parse_args()

    stats = load_stats_from_data() if args.stats_from_data else dict(DEFAULT_STATS)

    svg = build_svg(stats)
    out_path = Path(args.output)
    out_path.write_text(svg, encoding="utf-8")

    print(f"Generated: {out_path}")
    print(f"Stats used:")
    for k, v in stats.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
