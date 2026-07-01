#!/usr/bin/env python3
"""
Neo4j Graph Initializer — Load graph from LightRAG's graphml backup.

Since LightRAG uses Neo4JStorage for graph queries, Neo4j must be populated
with the knowledge graph. This script reads the graphml file from LightRAG's
rag_storage and imports all nodes and relationships into Neo4j.

Run this ONCE after `docker compose up -d` on a fresh clone:
    python init_neo4j.py

It is safe to run multiple times — it will skip if graph is already populated.
"""

import os
import sys
import time
import xml.etree.ElementTree as ET
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

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USERNAME", "neo4j")
NEO4J_PASS = os.environ.get("NEO4J_PASSWORD", "lightrag2026")
GRAPHML_PATH = Path(__file__).resolve().parent / "data" / "lightrag" / "rag_storage" / "graph_chunk_entity_relation.graphml"


def check_neo4j_ready(driver, retries=10, delay=3):
    """Wait for Neo4j to be ready."""
    for i in range(retries):
        try:
            with driver.session() as session:
                session.run("RETURN 1").single()
            return True
        except Exception:
            if i < retries - 1:
                print(f"   ⏳ Waiting for Neo4j... ({i+1}/{retries})")
                time.sleep(delay)
    return False


def get_node_count(driver):
    """Get current node count in Neo4j."""
    with driver.session() as session:
        result = session.run("MATCH (n) RETURN count(n) as cnt").single()
        return result["cnt"]


def parse_graphml(graphml_path):
    """Parse the graphml file and extract nodes and edges."""
    tree = ET.parse(graphml_path)
    root = tree.getroot()

    # Handle GraphML namespace
    ns = {"gml": "http://graphml.graphstruct.org/xmlns"}
    # Try to detect namespace from root tag
    if root.tag.startswith("{"):
        ns_uri = root.tag.split("}")[0][1:]
        ns = {"gml": ns_uri}

    # Find all key definitions (attribute names)
    keys = {}
    for key_elem in root.findall(".//gml:key", ns):
        key_id = key_elem.get("id")
        key_name = key_elem.get("attr.name", key_id)
        key_for = key_elem.get("for", "all")
        keys[key_id] = {"name": key_name, "for": key_for}

    # If no namespace, try without
    if not keys:
        for key_elem in root.iter():
            if key_elem.tag.endswith("key") or key_elem.tag == "key":
                key_id = key_elem.get("id")
                key_name = key_elem.get("attr.name", key_id)
                key_for = key_elem.get("for", "all")
                keys[key_id] = {"name": key_name, "for": key_for}

    nodes = []
    edges = []

    # Try with namespace first, then without
    graph = root.find(".//gml:graph", ns)
    if graph is None:
        graph = root.find("graph")
    if graph is None:
        # Try iterating
        for elem in root.iter():
            if elem.tag.endswith("graph") or elem.tag == "graph":
                graph = elem
                break

    if graph is None:
        print("   ❌ Could not find <graph> element in graphml")
        return [], []

    for elem in graph:
        tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag

        if tag == "node":
            node_id = elem.get("id")
            props = {}
            for data in elem:
                data_tag = data.tag.split("}")[-1] if "}" in data.tag else data.tag
                if data_tag == "data":
                    key_id = data.get("key")
                    key_name = keys.get(key_id, {}).get("name", key_id)
                    props[key_name] = data.text or ""
            nodes.append({"id": node_id, "properties": props})

        elif tag == "edge":
            source = elem.get("source")
            target = elem.get("target")
            props = {}
            for data in elem:
                data_tag = data.tag.split("}")[-1] if "}" in data.tag else data.tag
                if data_tag == "data":
                    key_id = data.get("key")
                    key_name = keys.get(key_id, {}).get("name", key_id)
                    props[key_name] = data.text or ""
            edges.append({"source": source, "target": target, "properties": props})

    return nodes, edges


def import_to_neo4j(driver, nodes, edges, batch_size=500):
    """Import nodes and edges into Neo4j in batches."""
    print(f"\n   📦 Importing {len(nodes)} nodes...")

    with driver.session() as session:
        # Create constraint/index for faster lookups
        try:
            session.run("CREATE INDEX entity_id IF NOT EXISTS FOR (n:Entity) ON (n.entity_id)")
        except Exception:
            pass

        # Import nodes in batches
        for i in range(0, len(nodes), batch_size):
            batch = nodes[i:i + batch_size]
            for node in batch:
                props = node["properties"]
                # Determine label from entity_type or default to Entity
                label = props.pop("entity_type", "Entity").replace('"', '').replace("'", "").strip()
                if not label or label == "N/A":
                    label = "Entity"
                # Clean label for Cypher (only alphanumeric and underscore)
                label = "".join(c if c.isalnum() or c == "_" else "_" for c in label)

                node_id = node["id"]
                props["entity_id"] = node_id

                # Build property string
                prop_pairs = []
                params = {"node_id": node_id}
                for k, v in props.items():
                    safe_key = "".join(c if c.isalnum() or c == "_" else "_" for c in k)
                    param_name = f"p_{safe_key}"
                    params[param_name] = v
                    prop_pairs.append(f"n.{safe_key} = ${param_name}")

                set_clause = ", ".join(prop_pairs) if prop_pairs else ""
                query = f"MERGE (n:`{label}` {{entity_id: $node_id}}) "
                if set_clause:
                    query += f"SET {set_clause}"

                try:
                    session.run(query, **params)
                except Exception as e:
                    # Fallback: use generic Entity label
                    try:
                        query = f"MERGE (n:Entity {{entity_id: $node_id}}) "
                        if set_clause:
                            query += f"SET {set_clause}"
                        session.run(query, **params)
                    except Exception:
                        pass

            done = min(i + batch_size, len(nodes))
            print(f"      ✅ {done}/{len(nodes)} nodes")

        print(f"\n   📦 Importing {len(edges)} relationships...")

        # Import edges in batches
        for i in range(0, len(edges), batch_size):
            batch = edges[i:i + batch_size]
            for edge in batch:
                props = edge["properties"]
                rel_type = props.pop("relationship_type",
                           props.pop("label",
                           props.pop("description", "RELATED_TO")))
                # Clean relationship type
                rel_type = rel_type.replace('"', '').replace("'", "").strip().upper()
                rel_type = "".join(c if c.isalnum() or c == "_" else "_" for c in rel_type)
                if not rel_type:
                    rel_type = "RELATED_TO"

                params = {"source": edge["source"], "target": edge["target"]}
                prop_pairs = []
                for k, v in props.items():
                    safe_key = "".join(c if c.isalnum() or c == "_" else "_" for c in k)
                    param_name = f"p_{safe_key}"
                    params[param_name] = v
                    prop_pairs.append(f"r.{safe_key} = ${param_name}")

                set_clause = ""
                if prop_pairs:
                    set_clause = " SET " + ", ".join(prop_pairs)

                query = (
                    f"MATCH (a {{entity_id: $source}}) "
                    f"MATCH (b {{entity_id: $target}}) "
                    f"MERGE (a)-[r:`{rel_type}`]->(b)"
                    f"{set_clause}"
                )

                try:
                    session.run(query, **params)
                except Exception:
                    pass

            done = min(i + batch_size, len(edges))
            print(f"      ✅ {done}/{len(edges)} relationships")


def main():
    try:
        from neo4j import GraphDatabase
    except ImportError:
        print("❌ neo4j driver not installed. Run: pip install neo4j")
        sys.exit(1)

    print("=" * 60)
    print("🔄 Neo4j Graph Initializer")
    print("=" * 60)

    if not GRAPHML_PATH.exists():
        print(f"\n❌ GraphML file not found: {GRAPHML_PATH}")
        print("   Make sure you have the data/ directory with LightRAG storage.")
        sys.exit(1)

    print(f"\n📄 GraphML file: {GRAPHML_PATH}")
    print(f"   Size: {GRAPHML_PATH.stat().st_size / 1024 / 1024:.1f} MB")

    print(f"\n🔌 Connecting to Neo4j: {NEO4J_URI}")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))

    if not check_neo4j_ready(driver):
        print("\n❌ Neo4j is not ready. Make sure it's running:")
        print("   docker compose up -d")
        driver.close()
        sys.exit(1)

    print("   ✅ Connected!")

    # Check if already populated
    node_count = get_node_count(driver)
    if node_count > 0:
        print(f"\n✅ Neo4j already has {node_count} nodes — skipping import.")
        print("   To reimport, clear the database first:")
        print("   python init_neo4j.py --force")
        if "--force" not in sys.argv:
            driver.close()
            return
        print("   🗑️  --force flag detected, clearing and reimporting...")
        with driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
        print("   ✅ Database cleared")

    # Parse graphml
    print(f"\n📖 Parsing GraphML file...")
    nodes, edges = parse_graphml(GRAPHML_PATH)
    print(f"   Found {len(nodes)} nodes and {len(edges)} edges")

    if not nodes:
        print("   ⚠️  No nodes found in graphml — nothing to import")
        driver.close()
        return

    # Import
    import_to_neo4j(driver, nodes, edges)

    # Verify
    final_count = get_node_count(driver)
    print(f"\n{'=' * 60}")
    print(f"🎉 Import complete! Neo4j now has {final_count} nodes.")
    print(f"   🌐 Neo4j Browser: http://localhost:7474")
    print(f"{'=' * 60}")

    driver.close()


if __name__ == "__main__":
    main()
