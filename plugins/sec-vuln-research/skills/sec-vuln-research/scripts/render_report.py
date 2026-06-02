# /// script
# requires-python = ">=3.11"
# dependencies = ["jinja2>=3.1", "pyyaml>=6.0"]
# ///
"""Render a filled vuln-research-report.yaml into Markdown.

Usage:
    uv run scripts/render_report.py <path-to-report.yaml> [--output <report.md>]

If --output is omitted the Markdown is written alongside the YAML with a
.md extension (e.g. vuln-research-report.yaml → vuln-research-report.md).

The Jinja2 template is resolved relative to this script:
    ../templates/vuln-research-report.j2

The YAML is the single source of truth — render as often as needed.
Never edit the Markdown output directly.
"""

import argparse
import sys
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, Undefined

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
TEMPLATE_NAME = "vuln-research-report.j2"


def load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict) or "report" not in data:
        sys.exit(
            f"Error: {path} must be a YAML file with a top-level 'report' key."
        )
    return data


def render(data: dict, template_path: Path) -> str:
    env = Environment(
        loader=FileSystemLoader(str(template_path.parent)),
        undefined=Undefined,        # silently renders missing keys as '' (no crash)
        trim_blocks=True,           # strip newline after {% %} tags
        lstrip_blocks=True,         # strip leading whitespace before {% %} tags
        keep_trailing_newline=True,
    )
    template = env.get_template(template_path.name)
    return template.render(**data)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("yaml_file", type=Path, help="Filled vuln-research YAML report")
    parser.add_argument(
        "--output", "-o", type=Path, default=None,
        help="Output path (default: <yaml-stem>.md alongside the YAML)",
    )
    args = parser.parse_args()

    yaml_path = args.yaml_file.resolve()
    if not yaml_path.exists():
        sys.exit(f"Error: {yaml_path} not found.")

    template_path = TEMPLATES_DIR / TEMPLATE_NAME
    if not template_path.exists():
        sys.exit(f"Error: template not found at {template_path}.")

    output_path = (args.output or yaml_path.with_suffix(".md")).resolve()

    data = load_yaml(yaml_path)
    markdown = render(data, template_path)
    output_path.write_text(markdown, encoding="utf-8")
    print(f"Report written → {output_path}")


if __name__ == "__main__":
    main()
