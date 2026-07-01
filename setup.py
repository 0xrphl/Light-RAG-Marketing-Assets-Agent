#!/usr/bin/env python3
"""
Media Assets Marketing Agent — Setup Script

Downloads pre-ingested LightRAG data from HuggingFace and sets up the
local data/ directory so you can run the project without re-ingesting.

Usage:
    python setup.py              # Download data from HuggingFace
    python setup.py --force      # Re-download even if data exists
"""

import os
import sys
import argparse
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data" / "lightrag"
RAG_STORAGE_DIR = DATA_DIR / "rag_storage"
HF_REPO = "0xrphl/Light-RAG-Marketing-Assets-Agent"

EXPECTED_FILES = [
    "rag_storage/vdb_relationships.json",
    "rag_storage/vdb_entities.json",
    "rag_storage/vdb_chunks.json",
    "rag_storage/graph_chunk_entity_relation.graphml",
    "rag_storage/kv_store_full_docs.json",
    "rag_storage/kv_store_full_entities.json",
    "rag_storage/kv_store_full_relations.json",
    "rag_storage/kv_store_text_chunks.json",
    "rag_storage/kv_store_entity_chunks.json",
    "rag_storage/kv_store_relation_chunks.json",
    "rag_storage/kv_store_doc_status.json",
]


def check_existing():
    """Check if data is already downloaded."""
    if not RAG_STORAGE_DIR.exists():
        return False
    for f in EXPECTED_FILES:
        if not (DATA_DIR / f).exists():
            return False
    return True


def download_from_huggingface():
    """Download the dataset from HuggingFace."""
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        print("❌ huggingface_hub not installed. Installing...")
        os.system(f"{sys.executable} -m pip install huggingface_hub")
        from huggingface_hub import snapshot_download

    print(f"📥 Downloading from HuggingFace: {HF_REPO}")
    print(f"   Target: {DATA_DIR}")
    print(f"   This may take a few minutes (~513 MB)...\n")

    # Download to a temp location, then move files
    cache_dir = snapshot_download(
        repo_id=HF_REPO,
        repo_type="dataset",
        local_dir=str(DATA_DIR),
        local_dir_use_symlinks=False,
    )

    print(f"\n✅ Download complete: {cache_dir}")
    return True


def verify_data():
    """Verify all expected files exist."""
    missing = []
    for f in EXPECTED_FILES:
        if not (DATA_DIR / f).exists():
            missing.append(f)

    if missing:
        print(f"\n⚠️  Missing {len(missing)} files:")
        for f in missing:
            print(f"   • {f}")
        return False

    # Calculate total size
    total_size = 0
    for f in DATA_DIR.rglob("*"):
        if f.is_file():
            total_size += f.stat().st_size

    print(f"\n✅ Data verified: {len(EXPECTED_FILES)} files, {total_size / 1024 / 1024:.1f} MB")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Download pre-ingested data from HuggingFace"
    )
    parser.add_argument("--force", action="store_true",
                        help="Re-download even if data already exists")
    args = parser.parse_args()

    print("=" * 60)
    print("🔄 Media Assets Marketing Agent — Setup")
    print("=" * 60)

    if check_existing() and not args.force:
        print(f"\n✅ Data already exists at {DATA_DIR}")
        print("   Use --force to re-download.")
        verify_data()
        print(f"\n   Next steps:")
        print(f"   1. docker compose up -d")
        print(f"   2. python init_neo4j.py")
        print(f"   3. python query.py \"sunset photos\"")
        return

    # Create directories
    RAG_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "tiktoken").mkdir(parents=True, exist_ok=True)

    # Download
    if not download_from_huggingface():
        print("❌ Download failed")
        sys.exit(1)

    # Verify
    if not verify_data():
        print("\n⚠️  Some files may be missing. Check the HuggingFace repo.")
        sys.exit(1)

    print(f"\n{'=' * 60}")
    print(f"🎉 Setup complete!")
    print(f"{'=' * 60}")
    print(f"\n   Next steps:")
    print(f"   1. cp .env.example .env  (add your API keys)")
    print(f"   2. docker compose up -d")
    print(f"   3. python init_neo4j.py")
    print(f"   4. python query.py \"sunset photos\"")


if __name__ == "__main__":
    main()
