# /// script
# requires-python = ">=3.11"
# dependencies = ["ruamel.yaml>=0.18"]
# ///
"""Deterministic triage tally for sec-vuln-research.

The triage verdict, confidence score, and evidence-level transition are
computed HERE, from the round records the triage lens subagents wrote to
disk — never by a model. This is what lets the report's verification
claims be checked.

Round records live at:
    <session_dir>/triage/rounds/<FINDING_ID>/<seq>_<lens>.json

Record schema (written by each triage lens subagent):
    {
      "finding_id": "VULN-001",
      "lens": "reachability" | "defenses" | "impact" | "combined"
              | "arbiter" | "redteam",
      "verdict": "VALID" | "INVALID" | "UNCERTAIN",
      "reasoning": "...",
      "evidence": [{"file": "net/parser.c", "line": 42, "note": "..."}],
      "crux": "one sentence (arbiter records only)",
      "recorded_at": "ISO-8601"
    }

Tally rules (fixed — not model-adjustable):
  * final verdict = the arbiter record's verdict.
  * With no arbiter record: unanimous INVALID across >=2 lenses -> INVALID
    (early exit); anything else -> UNCERTAIN (tally incomplete).
  * confidence = VALID votes / total records (arbiter included).
  * low_confidence = final VALID and confidence < 0.6.
  * A VALID verdict on a critical/high finding requires all three core
    lenses (reachability, defenses, impact) — otherwise the tally refuses
    to confirm and the finding stays UNCERTAIN with reason insufficient_lenses.
  * evidence level: VALID -> independently_verified; INVALID -> suspicion;
    UNCERTAIN -> uncertain.

Usage:
    uv run triage_tally.py <session_dir> [--finding VULN-001]

Writes results into vuln-research-report.yaml (findings[].triage and
pipeline.stages.triage counts) and appends INVALID findings to
rejected.jsonl. Prints one line per finding tallied.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from ruamel.yaml import YAML

CORE_LENSES = {"reachability", "defenses", "impact"}
VERDICTS = {"VALID", "INVALID", "UNCERTAIN"}
LENS_LETTER = {"reachability": "R", "defenses": "D", "impact": "I",
               "combined": "C", "redteam": "X", "arbiter": "A"}


def load_records(rounds_dir: Path) -> list[dict]:
    records = []
    for p in sorted(rounds_dir.glob("*.json")):
        try:
            rec = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            print(f"  WARNING: unreadable round record {p.name}: {e}", file=sys.stderr)
            continue
        if rec.get("verdict") not in VERDICTS:
            print(f"  WARNING: {p.name} has invalid verdict "
                  f"{rec.get('verdict')!r} — ignored", file=sys.stderr)
            continue
        rec["_file"] = p.name
        records.append(rec)
    return records


def tally(records: list[dict], severity: str | None) -> dict:
    """Pure tally function — the only place verdict math happens."""
    lens_records = [r for r in records if r.get("lens") != "arbiter"]
    arbiter = next((r for r in records if r.get("lens") == "arbiter"), None)

    verdict_letters = "".join(r["verdict"][0] for r in lens_records)
    lens_str = " ".join(
        f"{LENS_LETTER.get(r.get('lens', '?'), '?')}:{r['verdict'][0]}" for r in lens_records)
    n_valid = sum(1 for r in records if r["verdict"] == "VALID")
    n_total = len(records)

    reason = None
    if arbiter is not None:
        final = arbiter["verdict"]
    elif len(lens_records) >= 2 and all(r["verdict"] == "INVALID" for r in lens_records):
        final = "INVALID"
        reason = "unanimous INVALID across lenses (early exit, no arbiter needed)"
    elif n_total == 0:
        final = "UNCERTAIN"
        reason = "no round records on disk"
    else:
        final = "UNCERTAIN"
        reason = "tally incomplete: no arbiter record and lenses not unanimous INVALID"

    # A VALID verdict on critical/high needs all three core lenses on record.
    if final == "VALID" and severity in ("critical", "high"):
        present = {r.get("lens") for r in lens_records}
        missing = CORE_LENSES - present
        if missing:
            final = "UNCERTAIN"
            reason = (f"insufficient_lenses: VALID on a {severity} finding requires "
                      f"all core lenses; missing: {', '.join(sorted(missing))}")

    confidence = round(n_valid / n_total, 3) if n_total else 0.0
    evidence_level = {
        "VALID": "independently_verified",
        "INVALID": "suspicion",
        "UNCERTAIN": "uncertain",
    }[final]

    return {
        "rounds": n_total,
        "verdicts": verdict_letters,
        "lenses": lens_str,
        "arbiter_verdict": arbiter["verdict"] if arbiter else None,
        "final_verdict": final,
        "confidence_score": confidence,
        "low_confidence": bool(final == "VALID" and confidence < 0.6),
        "crux": (arbiter or {}).get("crux"),
        "final_evidence_level": evidence_level,
        "tally_note": reason,
        "computed_by": "triage_tally.py",
        "computed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("session_dir", type=Path)
    parser.add_argument("--finding", default=None, help="Tally one finding only")
    args = parser.parse_args()

    session_dir = args.session_dir.resolve()
    report_path = session_dir / "vuln-research-report.yaml"
    rounds_root = session_dir / "triage" / "rounds"
    if not report_path.exists():
        sys.exit(f"Error: {report_path} not found.")
    if not rounds_root.exists():
        sys.exit(f"Error: {rounds_root} not found — no round records to tally. "
                 "Triage lens subagents must write their records there first.")

    yaml = YAML()
    yaml.preserve_quotes = True
    with report_path.open(encoding="utf-8") as f:
        data = yaml.load(f)
    findings = (data.get("report") or {}).get("findings") or []

    counts = {"VALID": 0, "INVALID": 0, "UNCERTAIN": 0}
    rejected_path = session_dir / "rejected.jsonl"
    tallied = 0

    for finding in findings:
        fid = finding.get("id")
        if not fid or (args.finding and fid != args.finding):
            continue
        rounds_dir = rounds_root / str(fid)
        if not rounds_dir.is_dir():
            if args.finding:
                sys.exit(f"Error: no round records at {rounds_dir}")
            continue
        records = load_records(rounds_dir)
        severity = (finding.get("hunt") or {}).get("severity")
        result = tally(records, severity)

        triage_block = finding.setdefault("triage", {})
        triage_block["rounds"] = result["rounds"]
        triage_block["verdicts"] = result["verdicts"]
        triage_block["lenses"] = result["lenses"]
        triage_block["arbiter_verdict"] = result["arbiter_verdict"]
        triage_block["confidence_score"] = result["confidence_score"]
        triage_block["low_confidence"] = result["low_confidence"]
        if result["crux"]:
            triage_block["crux"] = result["crux"]
        triage_block["final_evidence_level"] = result["final_evidence_level"]
        triage_block["tally_note"] = result["tally_note"]
        triage_block["computed_by"] = result["computed_by"]
        triage_block["computed_at"] = result["computed_at"]

        counts[result["final_verdict"]] += 1
        tallied += 1

        if result["final_verdict"] == "INVALID":
            with rejected_path.open("a", encoding="utf-8") as rf:
                rf.write(json.dumps({
                    "id": fid,
                    "file": (finding.get("hunt") or {}).get("file"),
                    "finding_type": (finding.get("hunt") or {}).get("finding_type"),
                    "verdicts": result["verdicts"],
                    "arbiter_verdict": result["arbiter_verdict"],
                    "rejected_at": result["computed_at"],
                }) + "\n")

        print(f"{fid}: {result['final_verdict']} "
              f"({result['lenses'] or 'no lenses'}"
              f"{' -> A:' + result['arbiter_verdict'][0] if result['arbiter_verdict'] else ''}) "
              f"confidence={result['confidence_score']:.0%}"
              + (f"  [{result['tally_note']}]" if result["tally_note"] else ""))

    if tallied == 0:
        sys.exit("Error: no findings tallied — check finding IDs and round record paths.")

    # Update pipeline triage counts only on a full tally — a single-finding
    # tally must not overwrite whole-run counts with partial ones.
    if not args.finding:
        pipeline = (data.get("report") or {}).setdefault("pipeline", {})
        stage = pipeline.setdefault("stages", {}).setdefault("triage", {})
        stage["valid"] = counts["VALID"]
        stage["rejected"] = counts["INVALID"]
        stage["uncertain"] = counts["UNCERTAIN"]

    with report_path.open("w", encoding="utf-8") as f:
        yaml.dump(data, f)
    print(f"\nTallied {tallied} finding(s): {counts['VALID']} valid, "
          f"{counts['INVALID']} rejected, {counts['UNCERTAIN']} uncertain")
    print(f"Written back to {report_path.name}")


if __name__ == "__main__":
    main()
