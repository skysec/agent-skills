# /// script
# requires-python = ">=3.11"
# dependencies = ["ruamel.yaml>=0.18"]
# ///
"""CI gate for sec-vuln-research: fail a pipeline only on NET-NEW findings.

Compares the verified findings in a session report against a baseline of
known stable IDs, so pre-existing findings never block a PR — only new
ones do (deepsec-style gating).

Exit codes:
    0  no net-new verified findings at/above the threshold
    1  at least one net-new verified finding (not an error — the gate)
    2  runtime/usage error

Usage:
    # gate against a stored baseline
    uv run ci_gate.py <session>/vuln-research-report.yaml \\
        --baseline baseline.json [--min-severity high]

    # produce/update the baseline from a report (after human review)
    uv run ci_gate.py <session>/vuln-research-report.yaml \\
        --write-baseline baseline.json

Only findings whose triage verdict is VALID (tally-computed) and that
carry a stable_id are gated; anything else is listed as unverified and
never fails the gate on its own.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ruamel.yaml import YAML

SEV_ORDER = {"critical": 4, "high": 3, "medium": 2, "low": 1}


def load_report_findings(path: Path) -> list[dict]:
    yaml = YAML(typ="safe")
    with path.open(encoding="utf-8") as f:
        data = yaml.load(f)
    findings = ((data or {}).get("report") or {}).get("findings") or []
    out = []
    for f in findings:
        hunt = f.get("hunt") or {}
        triage = f.get("triage") or {}
        out.append({
            "id": f.get("id"),
            "stable_id": f.get("stable_id"),
            "severity": f.get("final_severity") or hunt.get("severity"),
            "verdict": triage.get("arbiter_verdict") or triage.get("final_evidence_level"),
            "verified": triage.get("final_evidence_level") == "independently_verified",
            "file": hunt.get("file"),
            "finding_type": hunt.get("finding_type"),
        })
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("report_yaml", type=Path)
    parser.add_argument("--baseline", type=Path, default=None)
    parser.add_argument("--write-baseline", type=Path, default=None)
    parser.add_argument("--min-severity", default="high",
                        choices=["critical", "high", "medium", "low"])
    args = parser.parse_args()

    if not args.report_yaml.exists():
        print(f"Error: {args.report_yaml} not found", file=sys.stderr)
        sys.exit(2)

    findings = load_report_findings(args.report_yaml)
    verified = [f for f in findings if f["verified"] and f["stable_id"]]
    unstamped = [f for f in findings if f["verified"] and not f["stable_id"]]

    if args.write_baseline:
        baseline = {
            "generated_from": str(args.report_yaml),
            "stable_ids": sorted({f["stable_id"] for f in verified}),
        }
        args.write_baseline.write_text(json.dumps(baseline, indent=2), encoding="utf-8")
        print(f"Baseline written: {args.write_baseline} ({len(baseline['stable_ids'])} ids)")
        return

    if not args.baseline:
        print("Error: pass --baseline <file> to gate, or --write-baseline to create one.",
              file=sys.stderr)
        sys.exit(2)

    known: set[str] = set()
    if args.baseline.exists():
        try:
            known = set(json.loads(args.baseline.read_text(encoding="utf-8"))["stable_ids"])
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error: bad baseline {args.baseline}: {e}", file=sys.stderr)
            sys.exit(2)
    else:
        print(f"Note: baseline {args.baseline} does not exist — every finding is net-new.")

    threshold = SEV_ORDER[args.min_severity]
    net_new = [f for f in verified
               if f["stable_id"] not in known
               and SEV_ORDER.get(f["severity"] or "", 0) >= threshold]

    if unstamped:
        print(f"Note: {len(unstamped)} verified finding(s) lack a stable_id and were "
              "not gated — stamp them with finding_id.py.")

    if net_new:
        print(f"NET-NEW verified findings >= {args.min_severity}: {len(net_new)}")
        for f in net_new:
            print(f"  {f['id']} ({f['stable_id']}) {f['severity']:>8}  "
                  f"{f['finding_type']}  {f['file']}")
        sys.exit(1)

    print(f"Gate clean: no net-new verified findings >= {args.min_severity} "
          f"({len(verified)} verified, {len(known)} in baseline).")


if __name__ == "__main__":
    main()
