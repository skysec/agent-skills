# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "trailmark>=0.1",
# ]
# ///
"""
Stage 0 — Ingestion & Structural Analysis (trailmark-backed)

Builds a trailmark CodeGraph for the target directory, runs all four pre-analysis
passes (blast_radius, taint, privilege_boundaries, entrypoints), and writes a
structured ingest_graph.json with per-file metrics, pre-analysis subgraph membership,
attack surface classification, and confidence-tagged edge counts.

Usage:
    uv run analyze.py <target_path> --output <session_dir>/ingest_graph.json [--sarif <path>]

Options:
    --sarif PATH   Optional SARIF file to augment onto the graph before export.
                   Maps external tool findings (Semgrep, CodeQL) to graph nodes.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path


def normalize_location(location: dict | None) -> tuple[str, int, int]:
    """Extract (file, start_line, end_line) from a trailmark location dict."""
    if not location:
        return ("", 0, 0)
    return (
        location.get("file", ""),
        location.get("start_line", 0),
        location.get("end_line", 0),
    )


def build_graph(target: Path, sarif_path: Path | None) -> dict:
    """
    Build and query the trailmark CodeGraph. Returns the full ingest_graph dict.
    Raises ImportError if trailmark is not installed (caller catches for fallback).
    """
    from trailmark import CodeGraph  # type: ignore[import]

    t0 = time.monotonic()
    print(f"Building trailmark graph for {target} ...")
    engine = CodeGraph.from_directory(str(target), language="auto")

    print("Running pre-analysis passes (blast_radius, taint, privilege_boundaries, entrypoints) ...")
    engine.preanalysis()

    # Optional SARIF augmentation (Stage 0b)
    if sarif_path and sarif_path.exists():
        print(f"Augmenting SARIF findings from {sarif_path} ...")
        engine.augment_sarif(str(sarif_path))

    summary = engine.summary()
    attack_surface = engine.attack_surface()
    hotspots = engine.complexity_hotspots(n=5)

    # Pre-analysis subgraph membership sets (node IDs)
    subgraph_names = engine.subgraph_names() if hasattr(engine, "subgraph_names") else []
    tainted_ids: set[str] = set()
    blast_ids: set[str] = set()
    priv_ids: set[str] = set()
    entry_ids: set[str] = set()

    for sg_name in subgraph_names:
        sg = engine.subgraph(sg_name)
        if sg is None:
            continue
        nodes = [n for n in (sg.nodes() if hasattr(sg, "nodes") else [])]
        node_ids = {n.id if hasattr(n, "id") else str(n) for n in nodes}
        if "taint" in sg_name:
            tainted_ids.update(node_ids)
        if "blast_radius" in sg_name or "high_blast" in sg_name:
            blast_ids.update(node_ids)
        if "privilege" in sg_name:
            priv_ids.update(node_ids)
        if "entrypoint" in sg_name:
            entry_ids.update(node_ids)

    # Attack surface: entrypoints with trust/asset classification
    attack_surface_list = []
    for ep in (attack_surface if attack_surface else []):
        file_, start, _ = normalize_location(ep.location if hasattr(ep, "location") else None)
        attack_surface_list.append({
            "id": ep.id if hasattr(ep, "id") else str(ep),
            "name": ep.name if hasattr(ep, "name") else "",
            "file": file_,
            "line": start,
            "trust_level": ep.trust_level if hasattr(ep, "trust_level") else None,
            "asset_value": ep.asset_value if hasattr(ep, "asset_value") else None,
        })

    # Export full graph as JSON to read per-node data
    graph_json = json.loads(engine.to_json())

    # Build per-file aggregates from node data
    files_by_path: dict[str, dict] = {}
    for node in graph_json.get("nodes", []):
        loc = node.get("location", {})
        file_path = loc.get("file", "")
        if not file_path:
            continue
        rel = str(Path(file_path).relative_to(target) if Path(file_path).is_absolute() else file_path)
        if rel not in files_by_path:
            files_by_path[rel] = {
                "path": rel,
                "language": node.get("language", ""),
                "loc": 0,
                "function_count": 0,
                "max_cyclomatic_complexity": 0,
                "total_branches": 0,
                "tainted": False,
                "high_blast_radius": False,
                "privilege_boundary": False,
                "entrypoint_reachable": False,
                "entrypoint_distance": None,
                "certain_callers": 0,
                "inferred_callers": 0,
            }
        entry = files_by_path[rel]
        node_id = node.get("id", "")
        # Subgraph membership
        if node_id in tainted_ids:
            entry["tainted"] = True
        if node_id in blast_ids:
            entry["high_blast_radius"] = True
        if node_id in priv_ids:
            entry["privilege_boundary"] = True
        if node_id in entry_ids:
            entry["entrypoint_reachable"] = True
        # Complexity
        cc = node.get("cyclomatic_complexity") or 0
        if cc > entry["max_cyclomatic_complexity"]:
            entry["max_cyclomatic_complexity"] = cc
        entry["total_branches"] += node.get("branches") or 0
        if node.get("kind") in ("function", "method"):
            entry["function_count"] += 1

    # Edge confidence counts per file
    for edge in graph_json.get("edges", []):
        if edge.get("kind") != "calls":
            continue
        src_id = edge.get("source_id", "")
        confidence = edge.get("confidence", "")
        # Find which file src_id belongs to by scanning nodes (build a lookup once)
        pass  # filled via node lookup below

    # Build node_id -> file lookup for edge traversal
    node_to_file: dict[str, str] = {}
    for node in graph_json.get("nodes", []):
        loc = node.get("location", {})
        file_path = loc.get("file", "")
        if file_path:
            rel = str(Path(file_path).relative_to(target) if Path(file_path).is_absolute() else file_path)
            node_to_file[node.get("id", "")] = rel

    for edge in graph_json.get("edges", []):
        if edge.get("kind") != "calls":
            continue
        src_id = edge.get("source_id", "")
        dst_id = edge.get("target_id", "")
        dst_file = node_to_file.get(dst_id, "")
        if not dst_file or dst_file not in files_by_path:
            continue
        confidence = edge.get("confidence", "")
        if confidence == "certain":
            files_by_path[dst_file]["certain_callers"] += 1
        elif confidence == "inferred":
            files_by_path[dst_file]["inferred_callers"] += 1

    # Normalize blast_radius_rank and entrypoint_distance for Stage 1 ranking
    # blast_radius_rank: 1–5 normalized from certain_callers count
    caller_counts = [f["certain_callers"] for f in files_by_path.values()]
    max_callers = max(caller_counts) if caller_counts else 1
    for f in files_by_path.values():
        raw = f["certain_callers"] / max(max_callers, 1)
        f["blast_radius_rank"] = max(1, round(raw * 4) + 1)  # 1–5
        # entrypoint_distance: 0 if IS an entrypoint, 1 if entrypoint_reachable, else 3 (unknown)
        if any(ep["file"] == f["path"] for ep in attack_surface_list):
            f["entrypoint_distance"] = 0
        elif f["entrypoint_reachable"]:
            f["entrypoint_distance"] = 1
        else:
            f["entrypoint_distance"] = 3

    elapsed = round(time.monotonic() - t0, 1)
    print(f"Graph built in {elapsed}s — {summary.get('node_count', '?')} nodes, "
          f"{summary.get('edge_count', '?')} edges, {len(files_by_path)} files")

    return {
        "target": str(target),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "elapsed_seconds": elapsed,
        "backend": "trailmark",
        "summary": summary,
        "attack_surface": attack_surface_list,
        "complexity_hotspots": [
            {
                "id": h.id if hasattr(h, "id") else str(h),
                "name": h.name if hasattr(h, "name") else "",
                "cyclomatic_complexity": h.cyclomatic_complexity if hasattr(h, "cyclomatic_complexity") else 0,
            }
            for h in (hotspots or [])
        ],
        "files": list(files_by_path.values()),
    }


def fallback_build(target: Path, sarif_path: Path | None) -> dict:
    """
    Fallback when trailmark is not installed. Uses the legacy import-count heuristic
    (original ingest.py logic) and emits a warning. All trailmark-specific fields are
    set to conservative defaults so downstream stages degrade gracefully.
    """
    import os
    import re

    print("WARNING: trailmark not available. Falling back to import-count heuristic.")
    print("         Install trailmark for accurate blast-radius and taint analysis.")
    print("         uv pip install trailmark")

    EXTENSION_MAP = {
        ".c": "C", ".h": "C", ".cpp": "C++", ".cc": "C++", ".cxx": "C++", ".hpp": "C++",
        ".py": "Python", ".go": "Go", ".rs": "Rust",
        ".js": "JavaScript", ".mjs": "JavaScript", ".cjs": "JavaScript",
        ".ts": "TypeScript", ".tsx": "TypeScript",
        ".java": "Java", ".rb": "Ruby", ".php": "PHP", ".swift": "Swift",
    }
    SKIP_DIRS = {"node_modules", "__pycache__", "target", ".git", "dist", "vendor",
                 ".venv", "venv", "build", "out", "bin", ".next", ".nuxt"}
    IMPORT_PATTERNS = re.compile(r'^\s*(import|from|#include|require|use)\s+', re.M)

    files_out = []
    t0 = time.monotonic()
    for dirpath, dirnames, filenames in os.walk(target):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for filename in filenames:
            fpath = Path(dirpath) / filename
            lang = EXTENSION_MAP.get(fpath.suffix.lower())
            if not lang:
                continue
            try:
                text = fpath.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            lines = text.splitlines()
            loc = sum(1 for l in lines if l.strip() and not l.strip().startswith(("//","#","/*","*","<!--")))
            import_count = len(IMPORT_PATTERNS.findall(text))
            rel = str(fpath.relative_to(target))
            files_out.append({
                "path": rel,
                "language": lang,
                "loc": loc,
                "function_count": 0,
                "max_cyclomatic_complexity": 0,
                "total_branches": 0,
                "tainted": False,
                "high_blast_radius": False,
                "privilege_boundary": False,
                "entrypoint_reachable": False,
                "entrypoint_distance": 3,
                "certain_callers": import_count,
                "inferred_callers": 0,
                "blast_radius_rank": min(5, max(1, import_count // 3)),
            })

    elapsed = round(time.monotonic() - t0, 1)
    return {
        "target": str(target),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "elapsed_seconds": elapsed,
        "backend": "fallback-heuristic",
        "warning": "trailmark not installed — blast_radius_rank and entrypoint_distance are approximations",
        "summary": {"node_count": 0, "edge_count": 0},
        "attack_surface": [],
        "complexity_hotspots": [],
        "files": files_out,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage 0 ingestion — trailmark backend")
    parser.add_argument("target", help="Path to the repository root")
    parser.add_argument("--output", required=True, help="Output path for ingest_graph.json")
    parser.add_argument("--sarif", default=None,
                        help="Optional SARIF file to augment onto the graph (Stage 0b)")
    args = parser.parse_args()

    target = Path(args.target).resolve()
    if not target.is_dir():
        print(f"Error: {target} is not a directory", file=sys.stderr)
        sys.exit(1)

    sarif_path = Path(args.sarif) if args.sarif else None

    try:
        result = build_graph(target, sarif_path)
    except ImportError:
        result = fallback_build(target, sarif_path)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2))
    print(f"Written to {out_path}")
    print(f"  Files: {len(result['files'])}, Backend: {result['backend']}")


if __name__ == "__main__":
    main()
