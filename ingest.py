#!/usr/bin/env python3
"""
Media Assets Marketing Agent — LightRAG Image Ingestion Pipeline

Scans the imgs/ folder, analyzes each image with Gemini Vision API to extract
rich descriptions (objects, colors, people, emotions, places, style, tags),
then ingests multi-chunk text documents into LightRAG for knowledge graph
construction and semantic search.

Each image produces multiple text chunks:
  1. Core Description — subject, scene, composition
  2. Visual Details  — colors, lighting, textures, objects
  3. People & Emotion — people, expressions, body language, demographics
  4. Marketing Tags   — use-cases, industries, mood tags, keywords

Usage:
    python ingest.py                    # Ingest all images
    python ingest.py --resume           # Skip already-ingested images
    python ingest.py --batch-size 10    # Process 10 at a time
    python ingest.py --dry-run          # Analyze without ingesting
    python ingest.py --limit 5          # Process only first 5 images
    python ingest.py --clear            # Clear LightRAG graph first
"""

import os
import sys
import json
import time
import base64
import argparse
import requests
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROGRESS_FILE = SCRIPT_DIR / "ingestion_progress.json"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tiff"}


def load_env():
    env_file = SCRIPT_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

load_env()

LIGHTRAG_URL = os.environ.get("LIGHTRAG_URL", "http://localhost:9621")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")
IMAGES_DIR = Path(os.environ.get("IMAGES_DIR", SCRIPT_DIR / "imgs"))


VISION_PROMPT = """You are an expert image analyst for a marketing asset library. Analyze this image
and produce a DETAILED structured description. Be thorough — every detail matters for searchability.

Respond in this EXACT format (fill every section, use "N/A" only if truly not applicable):

## CORE DESCRIPTION
[2-3 sentences describing the main subject, scene, and what is happening]

## OBJECTS & ELEMENTS
[Exhaustive comma-separated list of every visible object, item, element, prop, furniture,
vehicle, animal, plant, food, tool, device, clothing item, accessory, etc.]

## COLORS & PALETTE
Primary colors: [list dominant colors]
Secondary colors: [list accent/background colors]
Color mood: [warm/cool/neutral/vibrant/muted/pastel/dark/high-contrast/monochrome]
Color harmony: [complementary/analogous/triadic/split-complementary/earth-tones/etc.]

## PEOPLE & DEMOGRAPHICS
People count: [number or "none"]
Apparent demographics: [age range, gender presentation, ethnicity if visible]
Clothing & style: [what they are wearing, fashion style]
Expressions & emotions: [facial expressions, body language, mood conveyed]
Activities: [what the people are doing]

## SETTING & PLACE
Location type: [indoor/outdoor/studio/urban/rural/nature/abstract]
Specific setting: [office, beach, mountain, kitchen, street, park, etc.]
Architecture: [building style, interior design if visible]
Time of day: [morning/afternoon/evening/night/golden-hour/blue-hour/unknown]
Season/weather: [if determinable]
Geography: [region/country feel if identifiable]

## PHOTOGRAPHY & STYLE
Shot type: [close-up/medium/wide/aerial/macro/portrait/landscape/still-life]
Angle: [eye-level/low-angle/high-angle/bird's-eye/Dutch-angle]
Lighting: [natural/artificial/studio/dramatic/soft/backlit/side-lit/golden-hour]
Focus: [sharp/shallow-DOF/bokeh/tilt-shift/panoramic]
Style: [photojournalistic/editorial/commercial/fine-art/candid/lifestyle/stock/abstract]
Post-processing: [HDR/vintage/film-grain/desaturated/high-saturation/minimal-edit]

## MOOD & ATMOSPHERE
Overall mood: [3-5 mood descriptors]
Emotional tone: [what feeling does this image evoke in the viewer]
Energy level: [calm/moderate/dynamic/intense]

## MARKETING USE CASES
Industries: [tech, healthcare, finance, travel, food, fashion, etc.]
Campaign types: [brand awareness, social media, website hero, blog post, ad campaign, etc.]
Target audience: [millennials, professionals, families, etc.]
Themes: [sustainability, innovation, wellness, adventure, luxury, community, etc.]
Seasonal relevance: [all-year/spring/summer/fall/winter/holiday-specific]

## TAGS
[Generate 30-50 comma-separated searchable tags covering ALL aspects above. Include both
specific and general terms. Mix single words and short phrases. Include synonyms.]
"""


def analyze_image_with_gemini(image_path: Path) -> str:
    """Send an image to Gemini Vision API and get a rich description."""
    if not GEMINI_API_KEY:
        print("  ❌ GEMINI_API_KEY not set in .env")
        sys.exit(1)

    image_bytes = image_path.read_bytes()
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")

    ext = image_path.suffix.lower()
    mime_map = {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
        ".webp": "image/webp", ".gif": "image/gif", ".bmp": "image/bmp",
        ".tiff": "image/tiff",
    }
    mime_type = mime_map.get(ext, "image/jpeg")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    payload = {
        "contents": [{"parts": [
            {"text": VISION_PROMPT},
            {"inline_data": {"mime_type": mime_type, "data": image_b64}}
        ]}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 4096},
    }

    try:
        resp = requests.post(
            f"{url}?key={GEMINI_API_KEY}",
            headers={"Content-Type": "application/json"},
            json=payload, timeout=60,
        )
        if resp.status_code == 200:
            data = resp.json()
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "")
        else:
            print(f"    ⚠️ Gemini API error ({resp.status_code}): {resp.text[:200]}")
        return ""
    except requests.exceptions.Timeout:
        print(f"    ⚠️ Gemini API timeout for {image_path.name}")
        return ""
    except Exception as e:
        print(f"    ❌ Gemini API error: {e}")
        return ""


def build_chunks(filename: str, analysis: str) -> list:
    """Split the Gemini analysis into multiple labeled chunks for LightRAG."""
    chunks = []
    stem = Path(filename).stem
    sections = {}
    current_section = None
    current_lines = []

    for line in analysis.splitlines():
        if line.startswith("## "):
            if current_section:
                sections[current_section] = "\n".join(current_lines).strip()
            current_section = line[3:].strip()
            current_lines = []
        else:
            current_lines.append(line)
    if current_section:
        sections[current_section] = "\n".join(current_lines).strip()

    core = sections.get("CORE DESCRIPTION", "")
    objects = sections.get("OBJECTS & ELEMENTS", "")
    chunks.append({"doc_id": f"{stem}__core", "text": (
        f"[IMAGE ASSET: {filename}]\n[CHUNK: Core Description & Objects]\n\n"
        f"Image file: {filename}\nAsset ID: {stem}\n\n"
        f"Description:\n{core}\n\nObjects and elements visible:\n{objects}\n"
    )})

    colors = sections.get("COLORS & PALETTE", "")
    photo = sections.get("PHOTOGRAPHY & STYLE", "")
    chunks.append({"doc_id": f"{stem}__visual", "text": (
        f"[IMAGE ASSET: {filename}]\n[CHUNK: Visual Details]\n\n"
        f"Image file: {filename}\nAsset ID: {stem}\n\n"
        f"Color palette and tones:\n{colors}\n\nPhotography technique and style:\n{photo}\n"
    )})

    people = sections.get("PEOPLE & DEMOGRAPHICS", "")
    setting = sections.get("SETTING & PLACE", "")
    mood = sections.get("MOOD & ATMOSPHERE", "")
    chunks.append({"doc_id": f"{stem}__people_setting", "text": (
        f"[IMAGE ASSET: {filename}]\n[CHUNK: People, Emotion & Setting]\n\n"
        f"Image file: {filename}\nAsset ID: {stem}\n\n"
        f"People and demographics:\n{people}\n\n"
        f"Setting and location:\n{setting}\n\nMood and atmosphere:\n{mood}\n"
    )})

    marketing = sections.get("MARKETING USE CASES", "")
    tags = sections.get("TAGS", "")
    chunks.append({"doc_id": f"{stem}__marketing", "text": (
        f"[IMAGE ASSET: {filename}]\n[CHUNK: Marketing Use Cases & Tags]\n\n"
        f"Image file: {filename}\nAsset ID: {stem}\n\n"
        f"Marketing applications:\n{marketing}\n\nSearchable tags and keywords:\n{tags}\n"
    )})

    chunks.append({"doc_id": f"{stem}__full", "text": (
        f"[IMAGE ASSET: {filename}]\n[CHUNK: Complete Analysis]\n\n"
        f"Image file: {filename}\nAsset ID: {stem}\n\n{analysis}\n"
    )})

    return chunks


def lightrag_health() -> bool:
    try:
        return requests.get(f"{LIGHTRAG_URL}/health", timeout=5).status_code == 200
    except Exception:
        return False


def lightrag_insert(text: str, doc_id: str = None) -> bool:
    payload = {"text": text}
    if doc_id:
        payload["file_source"] = f"{doc_id}.txt"
    try:
        resp = requests.post(
            f"{LIGHTRAG_URL}/documents/text", json=payload, timeout=120
        )
        if resp.status_code in (200, 201):
            return True
        print(f"    ⚠️ LightRAG insert failed ({resp.status_code}): {resp.text[:300]}")
        return False
    except Exception as e:
        print(f"    ❌ LightRAG error: {e}")
        return False


def lightrag_clear() -> bool:
    try:
        return requests.delete(f"{LIGHTRAG_URL}/documents", timeout=30).status_code in (200, 204)
    except Exception as e:
        print(f"    ❌ LightRAG clear error: {e}")
        return False


def load_progress() -> dict:
    if PROGRESS_FILE.exists():
        try:
            return json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"ingested": [], "failed": []}


def save_progress(progress: dict):
    PROGRESS_FILE.write_text(json.dumps(progress, indent=2), encoding="utf-8")



def ingest_images(resume=False, batch_size=5, dry_run=False, limit=None, clear=False):
    """Main ingestion pipeline: scan images -> Gemini Vision -> LightRAG."""
    if not dry_run:
        if lightrag_health():
            print(f"✅ LightRAG connected: {LIGHTRAG_URL}")
        else:
            print(f"❌ LightRAG not reachable at {LIGHTRAG_URL}")
            print("   Start it with: docker compose up -d")
            sys.exit(1)

    if clear and not dry_run:
        print("🗑️  Clearing LightRAG graph...")
        if lightrag_clear():
            print("   ✅ Graph cleared")
        else:
            print("   ⚠️  Could not clear graph")

    if not IMAGES_DIR.exists():
        print(f"❌ Images directory not found: {IMAGES_DIR}")
        sys.exit(1)

    all_images = sorted([
        f for f in IMAGES_DIR.iterdir()
        if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
    ])
    print(f"\n📁 Found {len(all_images)} images in {IMAGES_DIR}")

    progress = load_progress() if resume else {"ingested": [], "failed": []}
    if resume:
        already_done = set(progress.get("ingested", []))
        images_to_process = [f for f in all_images if f.name not in already_done]
        print(f"   ↳ Already ingested: {len(already_done)}, remaining: {len(images_to_process)}")
    else:
        images_to_process = all_images
        progress = {"ingested": [], "failed": []}

    if limit:
        images_to_process = images_to_process[:limit]
        print(f"   ↳ Limited to {limit} images")

    if not images_to_process:
        print("\n✅ Nothing to process — all images already ingested!")
        return

    print(f"\n{'=' * 70}")
    print(f"🖼️  INGESTING {len(images_to_process)} IMAGES INTO LIGHTRAG")
    print(f"   Chunks per image: 5 (core, visual, people/setting, marketing, full)")
    print(f"   Total chunks: ~{len(images_to_process) * 5}")
    if dry_run:
        print(f"   ⚠️  DRY RUN — analyzing only, not ingesting")
    print(f"{'=' * 70}\n")

    total_chunks = 0
    failed_count = 0

    for idx, image_path in enumerate(images_to_process, 1):
        filename = image_path.name
        print(f"\n[{idx}/{len(images_to_process)}] 🖼️  {filename}")

        print(f"   📡 Analyzing with Gemini ({GEMINI_MODEL})...")
        analysis = analyze_image_with_gemini(image_path)

        if not analysis or len(analysis) < 50:
            print(f"   ❌ Analysis failed or too short — skipping")
            progress["failed"].append(filename)
            save_progress(progress)
            failed_count += 1
            continue

        print(f"   ✅ Analysis received ({len(analysis)} chars)")
        chunks = build_chunks(filename, analysis)
        print(f"   📦 Built {len(chunks)} chunks")

        if dry_run:
            for chunk in chunks:
                print(f"      • {chunk['doc_id']} ({len(chunk['text'])} chars)")
            progress["ingested"].append(filename)
            total_chunks += len(chunks)
            continue

        chunk_ok = 0
        for chunk in chunks:
            if lightrag_insert(chunk["text"], doc_id=chunk["doc_id"]):
                chunk_ok += 1
                print(f"      ✅ {chunk['doc_id']}")
            else:
                print(f"      ❌ {chunk['doc_id']}")
            time.sleep(0.15)

        if chunk_ok > 0:
            progress["ingested"].append(filename)
            total_chunks += chunk_ok
            print(f"   {'✅' if chunk_ok == len(chunks) else '⚠️'} {chunk_ok}/{len(chunks)} chunks ingested")
        else:
            progress["failed"].append(filename)
            failed_count += 1
            print(f"   ❌ All chunks failed")

        save_progress(progress)
        if idx < len(images_to_process):
            time.sleep(0.5)
        if batch_size and idx % batch_size == 0 and idx < len(images_to_process):
            print(f"\n   ⏸️  Batch of {batch_size} complete — pausing 2s...")
            time.sleep(2)

    print(f"\n{'=' * 70}")
    print(f"🎉 INGESTION COMPLETE!")
    print(f"   Images processed: {len(images_to_process)}")
    print(f"   Chunks ingested:  {total_chunks}")
    print(f"   Failed:           {failed_count}")
    print(f"   Total in library: {len(progress.get('ingested', []))}")
    print(f"{'=' * 70}")
    if not dry_run:
        print(f"\n   🌐 LightRAG WebUI:  {LIGHTRAG_URL}")
        print(f"   🔍 Neo4j Browser:   http://localhost:7474")
        print(f"\n   Next steps:")
        print(f"   1. Check LightRAG WebUI → Documents tab")
        print(f"   2. Explore the knowledge graph in Neo4j")
        print(f"   3. Query your image library: python query.py \"sunset photos\"")


def main():
    parser = argparse.ArgumentParser(
        description="Media Assets Marketing Agent — Image Ingestion Pipeline"
    )
    parser.add_argument("--resume", action="store_true",
                        help="Skip already-ingested images")
    parser.add_argument("--batch-size", type=int, default=5,
                        help="Images per batch before pausing (default: 5)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Analyze images but don't ingest into LightRAG")
    parser.add_argument("--limit", type=int, default=None,
                        help="Process only the first N images")
    parser.add_argument("--clear", action="store_true",
                        help="Clear the LightRAG graph before ingesting")
    args = parser.parse_args()

    ingest_images(
        resume=args.resume, batch_size=args.batch_size,
        dry_run=args.dry_run, limit=args.limit, clear=args.clear,
    )


if __name__ == "__main__":
    main()


