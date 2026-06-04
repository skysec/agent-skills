#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["jinja2>=3.1", "pyyaml>=6.0"]
# ///
"""
SecDeepWiki report renderer.

Reads a snapshot.yaml and renders it to secdeepwiki.md (index wiki)
and components/{id}/component.md (per-component pages).

Usage:
    uv run scripts/render_report.py <path-to-snapshot.yaml> [--output <output-dir>]
"""

import argparse
import sys
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, Undefined, StrictUndefined


def load_yaml(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def render(snapshot_path: Path, output_dir: Path | None = None) -> None:
    snapshot_path = snapshot_path.resolve()

    data = load_yaml(snapshot_path)
    if "secdeepwiki" not in data:
        print(f"ERROR: {snapshot_path} does not have a top-level 'secdeepwiki' key.", file=sys.stderr)
        sys.exit(1)

    if output_dir is None:
        output_dir = snapshot_path.parent

    output_dir.mkdir(parents=True, exist_ok=True)

    # Locate the template directory (sibling ../templates/ relative to this script)
    script_dir = Path(__file__).parent
    template_dir = script_dir.parent / "templates"
    if not template_dir.exists():
        # Fallback: look for template next to snapshot
        template_dir = snapshot_path.parent
    if not (template_dir / "snapshot.j2").exists():
        print(f"ERROR: template 'snapshot.j2' not found in {template_dir}", file=sys.stderr)
        sys.exit(1)

    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
        undefined=Undefined,  # silently empty on missing keys
    )

    template = env.get_template("snapshot.j2")
    rendered = template.render(**data)

    # Write index wiki
    index_path = output_dir / "secdeepwiki.md"
    index_path.write_text(rendered, encoding="utf-8")
    print(f"[secdeepwiki] Written: {index_path}")

    # Write per-component pages
    components = data.get("secdeepwiki", {}).get("components", []) or []
    for comp in components:
        comp_id = comp.get("id")
        if not comp_id:
            continue

        comp_dir = output_dir / "components" / comp_id
        comp_dir.mkdir(parents=True, exist_ok=True)

        # Per-component YAML
        comp_yaml_path = comp_dir / "component.yaml"
        with open(comp_yaml_path, "w") as f:
            yaml.dump({"component": comp}, f, default_flow_style=False, allow_unicode=True)
        print(f"[secdeepwiki] Written: {comp_yaml_path}")

        # Per-component Markdown (render with single-component data)
        single_data = dict(data)
        single_data["secdeepwiki"] = dict(data["secdeepwiki"])
        single_data["secdeepwiki"]["components"] = [comp]
        single_data["secdeepwiki"]["cross_component"] = {
            "relationships": [],
            "data_flow_diagrams": [],
            "attack_surface": None,
            "security_observations_summary": [],
        }
        single_data["secdeepwiki"]["open_questions"] = [
            q for q in (data["secdeepwiki"].get("open_questions") or [])
            if q.get("component") == comp_id
        ]
        single_data["secdeepwiki"]["tester_handoff"] = None

        comp_rendered = template.render(**single_data)
        comp_md_path = comp_dir / "component.md"
        comp_md_path.write_text(comp_rendered, encoding="utf-8")
        print(f"[secdeepwiki] Written: {comp_md_path}")

    print(f"\n[secdeepwiki] Render complete. Index: {index_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Render SecDeepWiki snapshot.yaml to Markdown")
    parser.add_argument("snapshot", type=Path, help="Path to snapshot.yaml")
    parser.add_argument("--output", "-o", type=Path, default=None,
                        help="Output directory (default: same directory as snapshot.yaml)")
    args = parser.parse_args()

    if not args.snapshot.exists():
        print(f"ERROR: {args.snapshot} does not exist.", file=sys.stderr)
        sys.exit(1)

    render(args.snapshot, args.output)


if __name__ == "__main__":
    main()
