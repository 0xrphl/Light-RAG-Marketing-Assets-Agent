#!/usr/bin/env python3
"""
Media Assets Marketing Agent — LightRAG Query Tool

Query your image asset library using LightRAG's knowledge graph.
Supports all 5 query modes: naive, local, global, hybrid, mix.

Usage:
    python query.py "sunset beach photos"
    python query.py "professional headshots" --mode hybrid
    python query.py "images with warm colors" --mode global
    python query.py "outdoor adventure" --mode mix
"""

import os
import sys
import argparse
import requests
from pathlib import Path


def load_env():
    env_file = Path(__file__).resolve().parent / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

load_env()

LIGHTRAG_URL = os.environ.get("LIGHTRAG_URL", "http://localhost:9621")

QUERY_MODES = ["naive", "local", "global", "hybrid", "mix"]


def query_lightrag(query: str, mode: str = "hybrid") -> str:
    """Send a query to LightRAG and return the response."""
    payload = {"query": query, "mode": mode}
    try:
        resp = requests.post(
            f"{LIGHTRAG_URL}/query", json=payload, timeout=60
        )
        if resp.status_code == 200:
            data = resp.json()
            return data.get("response", data.get("result", str(data)))
        else:
            return f"Error ({resp.status_code}): {resp.text[:500]}"
    except Exception as e:
        return f"Connection error: {e}"


def check_health() -> bool:
    try:
        return requests.get(f"{LIGHTRAG_URL}/health", timeout=5).status_code == 200
    except Exception:
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Media Assets Marketing Agent — Query Tool"
    )
    parser.add_argument("query", nargs="?", help="Search query for your image library")
    parser.add_argument(
        "--mode", choices=QUERY_MODES, default="hybrid",
        help="Query mode (default: hybrid)"
    )
    parser.add_argument(
        "--all-modes", action="store_true",
        help="Run the query in all 5 modes and compare results"
    )
    args = parser.parse_args()

    if not check_health():
        print(f"❌ LightRAG not reachable at {LIGHTRAG_URL}")
        print("   Start it with: docker compose up -d")
        sys.exit(1)

    print(f"✅ LightRAG connected: {LIGHTRAG_URL}\n")

    # Interactive mode if no query provided
    if not args.query:
        print("🔍 Interactive Query Mode (type 'quit' to exit)")
        print(f"   Current mode: {args.mode}\n")
        while True:
            try:
                query = input("Query> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nBye!")
                break
            if not query or query.lower() in ("quit", "exit", "q"):
                break
            if query.startswith("/mode "):
                new_mode = query.split()[1]
                if new_mode in QUERY_MODES:
                    args.mode = new_mode
                    print(f"   Mode changed to: {args.mode}")
                else:
                    print(f"   Invalid mode. Choose from: {', '.join(QUERY_MODES)}")
                continue

            print(f"\n{'─' * 60}")
            print(f"Mode: {args.mode}")
            print(f"{'─' * 60}")
            result = query_lightrag(query, args.mode)
            print(result)
            print(f"{'─' * 60}\n")
        return

    # Single query or all-modes
    if args.all_modes:
        print(f"🔍 Query: {args.query}\n")
        for mode in QUERY_MODES:
            print(f"{'=' * 60}")
            print(f"  Mode: {mode.upper()}")
            print(f"{'=' * 60}")
            result = query_lightrag(args.query, mode)
            print(result)
            print()
    else:
        print(f"🔍 Query: {args.query}")
        print(f"   Mode:  {args.mode}\n")
        print(f"{'─' * 60}")
        result = query_lightrag(args.query, args.mode)
        print(result)
        print(f"{'─' * 60}")


if __name__ == "__main__":
    main()
