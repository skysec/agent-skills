# /// script
# requires-python = ">=3.11"
# dependencies = ["jinja2>=3.1", "ruamel.yaml>=0.18"]
# ///
"""Validate and render a vuln-research-report.yaml into Markdown.

This is a VALIDATOR first and a renderer second. The report's integrity
claims are recomputed here, in code, from the artifacts on disk — never
taken from the model that filled the YAML:

  * Any finding claiming `independently_verified` has its triage tally
    RECOMPUTED from the round records at triage/rounds/<id>/. Missing
    records, or a tally that does not match the YAML's claim, REFUSES the
    finding: it is excluded from the report and printed as `refused <id>`.
  * A claimed attack chain whose chain_file does not exist is downgraded
    (generated: false) with a warning — the finding stays.
  * Findings are deduplicated by (file, CWE, overlapping line range);
    the highest evidence level survives, merges are noted.
  * Hard-coded-credential findings (CWE-798/259/321, or *secret*/
    *credential* finding types) get their code_snippet REDACTED in every
    artifact — the snippet is the secret.
  * risk_counts and recommendation priority scores/order are recomputed;
    the YAML's values are overwritten with the computed ones.
  * A `verification` block is stamped: `verified` only when every included
    finding's tally was recomputed successfully from disk; otherwise
    `unverified` with the reason. The stamp is derived, never asserted.

Usage:
    uv run scripts/render_report.py <path-to-report.yaml> [--output <report.md>]

The session directory is the YAML's parent directory. The YAML stays the
single source of truth: computed blocks are written back into it.
Exit codes: 0 rendered (refusals are reported, not fatal); 2 structural error.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

from jinja2 import ChainableUndefined, Environment, FileSystemLoader
from ruamel.yaml import YAML

sys.path.insert(0, str(Path(__file__).parent))
from triage_tally import load_records, tally  # noqa: E402

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
TEMPLATE_NAME = "vuln-research-report.j2"

SECRET_CWES = {"CWE-798", "CWE-259", "CWE-321"}
SECRET_TYPE_MARKERS = ("secret", "credential", "hardcoded_key", "hard_coded")
SEV_SCORE = {"critical": 4, "high": 3, "medium": 2, "low": 1}
ATTACKER_SCORE = {"remote_unauth": 4, "remote_auth_low": 3,
                  "remote_auth_elevated": 2, "local": 1}
EVIDENCE_ORDER = ["suspicion", "hunter_confirmed", "independently_verified",
                  "root_cause_explained", "exploit_demonstrated"]


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def is_secret_finding(hunt: dict) -> bool:
    if (hunt.get("cwe") or "") in SECRET_CWES:
        return True
    ftype = (hunt.get("finding_type") or "").lower()
    return any(m in ftype for m in SECRET_TYPE_MARKERS)


def evidence_rank(level: str | None) -> int:
    try:
        return EVIDENCE_ORDER.index(level)
    except ValueError:
        return -1


def ranges_overlap(a_start, a_end, b_start, b_end) -> bool:
    try:
        return int(a_start) <= int(b_end) and int(b_start) <= int(a_end)
    except (TypeError, ValueError):
        return False


def verify_triage(finding: dict, session_dir: Path,
                  warnings: list[str]) -> tuple[bool, str | None]:
    """Recompute the triage tally from disk. Returns (ok, refusal_reason).

    A finding that claims no verification passes trivially. A finding that
    claims `independently_verified` (or carries an arbiter verdict) must
    have round records on disk whose recomputed tally matches the YAML.
    """
    triage = finding.get("triage") or {}
    claimed_level = triage.get("final_evidence_level")
    claims_verification = (
        claimed_level in ("independently_verified",)
        or triage.get("arbiter_verdict") is not None
    )
    # Attack-chain evidence levels imply verification too.
    chain_level = (finding.get("attack_chain") or {}).get("final_evidence_level")
    if chain_level in ("root_cause_explained", "exploit_demonstrated"):
        claims_verification = True
    if not claims_verification:
        return True, None

    fid = str(finding.get("id"))
    rounds_dir = session_dir / "triage" / "rounds" / fid
    if not rounds_dir.is_dir():
        return False, (f"claims verification but has no round records at "
                       f"triage/rounds/{fid}/ — a verification that never ran")
    records = load_records(rounds_dir)
    severity = (finding.get("hunt") or {}).get("severity")
    computed = tally(records, severity)

    if computed["final_evidence_level"] == "independently_verified" \
            and claimed_level != "independently_verified" \
            and claimed_level is not None:
        warnings.append(f"{fid}: YAML claims {claimed_level!r} but records compute "
                        "independently_verified — using computed value")
    if claimed_level == "independently_verified" \
            and computed["final_evidence_level"] != "independently_verified":
        return False, (f"claims independently_verified but records compute "
                       f"{computed['final_verdict']}"
                       + (f" ({computed['tally_note']})" if computed["tally_note"] else ""))
    yaml_arbiter = triage.get("arbiter_verdict")
    if yaml_arbiter is not None and yaml_arbiter != computed["arbiter_verdict"]:
        return False, (f"YAML arbiter_verdict {yaml_arbiter!r} does not match the "
                       f"arbiter record on disk ({computed['arbiter_verdict']!r})")
    yaml_conf = triage.get("confidence_score")
    if yaml_conf is not None and abs(float(yaml_conf) - computed["confidence_score"]) > 0.02:
        warnings.append(f"{fid}: confidence corrected "
                        f"{yaml_conf} -> {computed['confidence_score']}")

    # Overwrite the YAML triage block with the computed tally — code wins.
    for key in ("rounds", "verdicts", "lenses", "arbiter_verdict",
                "confidence_score", "low_confidence", "final_evidence_level",
                "tally_note", "computed_by", "computed_at"):
        triage[key] = computed[key]
    if computed["crux"]:
        triage["crux"] = computed["crux"]
    finding["triage"] = triage
    return True, None


def validate_attack_chain(finding: dict, session_dir: Path,
                          warnings: list[str]) -> None:
    chain = finding.get("attack_chain") or {}
    if not chain.get("generated"):
        return
    chain_file = chain.get("chain_file")
    if not chain_file or not (session_dir / chain_file).exists():
        warnings.append(f"{finding.get('id')}: attack chain claimed but "
                        f"{chain_file or '(no path)'} does not exist — downgraded")
        chain["generated"] = False
        chain["poc_skeleton_available"] = False
        chain["final_evidence_level"] = None
        finding["attack_chain"] = chain


def redact_secrets(finding: dict, warnings: list[str]) -> None:
    hunt = finding.get("hunt") or {}
    if is_secret_finding(hunt) and hunt.get("code_snippet"):
        hunt["code_snippet"] = "[redacted — the flagged line contains the credential; " \
                               "locate it by file, line, and function]"
        warnings.append(f"{finding.get('id')}: secret finding — snippet redacted")


def dedup(findings: list[dict], warnings: list[str]) -> list[dict]:
    """Mark duplicates in place (duplicate_of: <id>) — nothing is deleted from
    the YAML, so the merge is auditable and re-renders are idempotent."""
    kept: list[dict] = []
    for f in findings:
        hunt = f.get("hunt") or {}
        merged = False
        for k in kept:
            kh = k.get("hunt") or {}
            if (hunt.get("file") and hunt.get("file") == kh.get("file")
                    and hunt.get("cwe") == kh.get("cwe")
                    and ranges_overlap(hunt.get("line_start"), hunt.get("line_end"),
                                       kh.get("line_start"), kh.get("line_end"))):
                keep_f = f if evidence_rank(
                    (f.get("triage") or {}).get("final_evidence_level")
                    or hunt.get("evidence_level")) > evidence_rank(
                    (k.get("triage") or {}).get("final_evidence_level")
                    or kh.get("evidence_level")) else k
                drop = f if keep_f is k else k
                drop["duplicate_of"] = str(keep_f.get("id"))
                warnings.append(f"dedup: {drop.get('id')} merged into {keep_f.get('id')} "
                                f"({hunt.get('file')}:{hunt.get('line_start')} {hunt.get('cwe')})")
                if keep_f is f:
                    kept[kept.index(k)] = f
                merged = True
                break
        if not merged:
            kept.append(f)
    return kept


def compute_recommendations(report: dict, findings: list[dict]) -> None:
    """Recompute priority scores and order in code (pipeline-stages.md §Stage 8)."""
    recs = report.get("recommendations") or []
    by_id = {str(f.get("id")): f for f in findings}
    scored = []
    for rec in recs:
        fid = str(rec.get("id"))
        f = by_id.get(fid)
        if f is None:
            continue  # recommendation for a refused/deduped finding — dropped
        level = (f.get("triage") or {}).get("final_evidence_level")
        if level != "independently_verified":
            continue  # only confirmed findings earn a recommendation
        sev = (f.get("final_severity") or (f.get("hunt") or {}).get("severity") or "low")
        conf = float((f.get("triage") or {}).get("confidence_score") or 0.0)
        attacker = rec.get("attacker_position")
        a_score = ATTACKER_SCORE.get(attacker, 2)
        score = round(SEV_SCORE.get(sev, 1) * 0.50 + (conf * 4) * 0.25 + a_score * 0.25, 2)
        rec["priority_score"] = score
        rec["severity"] = sev
        scored.append(rec)
    scored.sort(key=lambda r: (-float(r.get("priority_score") or 0),
                               -SEV_SCORE.get(r.get("severity") or "low", 1),
                               str(r.get("id"))))
    for i, rec in enumerate(scored, 1):
        rec["rank"] = i
    report["recommendations"] = scored


def compute_risk_counts(report: dict, findings: list[dict]) -> None:
    counts = {"total": 0, "critical": 0, "high": 0, "medium": 0, "low": 0,
              "triage_confirmed": 0, "triage_rejected": 0, "triage_uncertain": 0,
              "variants_surfaced": len(report.get("variants") or []),
              "attack_chains_generated": 0}
    for f in findings:
        triage = f.get("triage") or {}
        level = triage.get("final_evidence_level")
        if level == "independently_verified" or evidence_rank(level) > \
                EVIDENCE_ORDER.index("independently_verified"):
            counts["triage_confirmed"] += 1
            counts["total"] += 1
            sev = f.get("final_severity") or (f.get("hunt") or {}).get("severity")
            if sev in counts:
                counts[sev] += 1
        elif level == "suspicion":
            counts["triage_rejected"] += 1
        elif level == "uncertain":
            counts["triage_uncertain"] += 1
        if (f.get("attack_chain") or {}).get("generated"):
            counts["attack_chains_generated"] += 1
    summary = report.setdefault("summary", {})
    summary["risk_counts"] = counts


SARIF_LEVEL = {"critical": "error", "high": "error", "medium": "warning", "low": "note"}

# Default validation method per finding class — DAST is only for the
# network/HTTP-reachable subset; other classes route elsewhere.
DEFAULT_METHOD = {
    "memory_safety": "fuzz",
    "injection": "dast",
    "auth_logic": "dast",
    "crypto_logic": "unit",
    "subsystem": "manual",
}
STEP_RE = re.compile(r"^\s*(?P<name>[^()]+?)\s*(?:\((?P<file>[^:()]+):(?P<line>\d+)\))?\s*$")


def parse_path_steps(path_str) -> list[dict]:
    """Parse an entrypoint_path string like
    'recv_request (net/server.c:88) -> parse_header -> parse_packet'
    into ordered {name, file, line} steps. Arrows may be -> or the unicode →."""
    if not path_str or not isinstance(path_str, str):
        return []
    raw = re.split(r"\s*(?:→|->|=>)\s*", path_str)
    steps = []
    for seg in raw:
        m = STEP_RE.match(seg)
        if not m or not m.group("name"):
            continue
        steps.append({
            "name": m.group("name").strip(),
            "file": (m.group("file") or "").strip() or None,
            "line": int(m.group("line")) if m.group("line") else None,
        })
    return steps


def sarif_code_flow(finding: dict) -> list | None:
    """A SARIF codeFlow tracing source → hops → sink from the finding's graph
    context, so a SARIF-aware triage/validation tool can re-walk the taint path.
    Falls back to a two-step source→sink flow when only endpoints are known."""
    hunt = finding.get("hunt") or {}
    gctx = hunt.get("graph_context") or {}
    validation = (finding.get("attack_chain") or {}).get("validation") or {}
    sink_file = hunt.get("file") or ""
    sink_line = hunt.get("line_start")

    steps = parse_path_steps(gctx.get("entrypoint_path"))
    if not steps and validation.get("path"):
        steps = [{"name": n, "file": None, "line": None} for n in validation["path"]]

    tf_locations = []
    for step in steps:
        loc = {"physicalLocation": {
            "artifactLocation": {"uri": step["file"] or sink_file}}}
        if step["line"]:
            loc["physicalLocation"]["region"] = {"startLine": step["line"]}
        tf_locations.append({"location": {
            **loc, "message": {"text": step["name"]}}})

    # Ensure the sink is the final location.
    if sink_file and (not steps or steps[-1].get("file") not in (None, sink_file)
                      or steps[-1].get("line") != sink_line):
        sink_loc = {"physicalLocation": {"artifactLocation": {"uri": sink_file}}}
        if sink_line:
            sink_loc["physicalLocation"]["region"] = {"startLine": int(sink_line)}
        tf_locations.append({"location": {
            **sink_loc,
            "message": {"text": hunt.get("taint_sink") or hunt.get("function") or "sink"}}})

    if len(tf_locations) < 2:
        return None
    return [{"threadFlows": [{"locations": tf_locations}]}]


def build_sarif(report: dict, included: list[dict]) -> dict:
    """SARIF v2.1.0 log from the same validated pass as the Markdown report:
    refused and duplicate findings are already gone, secret snippets already
    redacted. Includes every finding ≥ hunter_confirmed that triage did not
    demote to suspicion. stableId in result properties is the dedup/gate key."""
    rules: dict[str, dict] = {}
    results = []
    for f in included:
        hunt = f.get("hunt") or {}
        triage = f.get("triage") or {}
        level_name = triage.get("final_evidence_level") or hunt.get("evidence_level")
        if level_name in (None, "suspicion"):
            continue  # rejected or never confirmed — not shippable
        cwe = hunt.get("cwe") or "CWE-unknown"
        if cwe not in rules:
            rules[cwe] = {
                "id": cwe,
                "name": (hunt.get("finding_type") or cwe).replace("_", " ").title().replace(" ", ""),
                "helpUri": (f"https://cwe.mitre.org/data/definitions/"
                            f"{cwe.split('-')[-1]}.html" if cwe.startswith("CWE-") else None),
            }
        severity = f.get("final_severity") or hunt.get("severity") or "medium"
        message = hunt.get("description") or hunt.get("finding_type") or str(f.get("id"))
        region = {}
        if hunt.get("line_start"):
            region["startLine"] = int(hunt["line_start"])
        if hunt.get("line_end"):
            region["endLine"] = int(hunt["line_end"])
        if hunt.get("code_snippet"):    # already redacted for secret findings
            region["snippet"] = {"text": str(hunt["code_snippet"])}
        location = {"physicalLocation": {
            "artifactLocation": {"uri": str(hunt.get("file") or "")}}}
        if region:
            location["physicalLocation"]["region"] = region
        if hunt.get("function"):
            location["logicalLocations"] = [
                {"name": str(hunt["function"]), "kind": "function"}]
        result = {
            "ruleId": cwe,
            "level": SARIF_LEVEL.get(severity, "warning"),
            "message": {"text": message},
            "locations": [location],
            "properties": {
                "secVulnResearchId": str(f.get("id")),
                "stableId": f.get("stable_id"),
                "severity": severity,
                "evidenceLevel": level_name,
                "triageVerdict": triage.get("arbiter_verdict"),
                "confidence": triage.get("confidence_score"),
                "specialist": hunt.get("specialist"),
            },
        }
        code_flows = sarif_code_flow(f)
        if code_flows:
            result["codeFlows"] = code_flows
        results.append(result)
    metadata = report.get("metadata") or {}
    verification = report.get("verification") or {}
    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [{
            "tool": {"driver": {
                "name": "sec-vuln-research",
                "version": str(metadata.get("skill_version") or ""),
                "informationUri": "https://github.com/hecbercordova/sec-vuln-research",
                "rules": [{k: v for k, v in r.items() if v is not None}
                          for r in rules.values()],
            }},
            "results": results,
            "properties": {
                "repository": metadata.get("repository"),
                "commit": metadata.get("commit"),
                "sessionId": metadata.get("session_id"),
                "verificationStatus": verification.get("status"),
                "generatedBy": "render_report.py",
            },
        }],
    }


def apply_validation_result(finding: dict, warnings: list[str]) -> None:
    """Close the evidence ladder: a validator's confirmed result with evidence
    promotes the finding to exploit_demonstrated. This is the only way to reach
    the top rung, and it happens in code from the written-back result."""
    chain = finding.get("attack_chain") or {}
    result = ((chain.get("validation") or {}).get("result")) or {}
    if result.get("status") == "confirmed":
        if not result.get("evidence"):
            warnings.append(f"{finding.get('id')}: validation status 'confirmed' but no "
                            "evidence — not promoted to exploit_demonstrated")
            return
        chain["final_evidence_level"] = "exploit_demonstrated"
        finding["attack_chain"] = chain


def build_validation_plan(report: dict, included: list[dict]) -> dict:
    """Tool-agnostic validation plan for findings that reached an attack chain.
    A DAST tool, a fuzzer, or a sec-vuln-validate agent consumes this and writes
    each finding's `result` back into the YAML (attack_chain.validation.result)."""
    metadata = report.get("metadata") or {}
    entries = []
    for f in included:
        chain = f.get("attack_chain") or {}
        level = chain.get("final_evidence_level")
        if not chain.get("generated") or level not in (
                "root_cause_explained", "exploit_demonstrated"):
            continue
        hunt = f.get("hunt") or {}
        v = chain.get("validation") or {}
        method = v.get("method") or DEFAULT_METHOD.get(hunt.get("specialist"), "manual")
        ep = v.get("entry_point") or {}
        entries.append({
            "id": str(f.get("id")),
            "stableId": f.get("stable_id"),
            "cwe": hunt.get("cwe"),
            "class": hunt.get("specialist"),
            "severity": f.get("final_severity") or hunt.get("severity"),
            "evidenceLevel": level,
            "validationMethod": method,
            "reachability": {
                "interface": v.get("interface"),
                "entryPoint": {
                    "symbol": ep.get("symbol"),
                    "file": ep.get("file"),
                    "line": ep.get("line"),
                    "trustLevel": ep.get("trust_level"),
                },
                "path": v.get("path") or parse_path_names(
                    (hunt.get("graph_context") or {}).get("entrypoint_path")),
            },
            "sink": {"file": hunt.get("file"), "line": hunt.get("line_start"),
                     "function": hunt.get("function")},
            "testVector": v.get("test_vector") or {},
            "oracle": v.get("oracle") or {},
            "requestTemplate": v.get("request_template"),
            "preconditions": v.get("preconditions") or [],
            "poc": {"skeleton": chain.get("chain_file"),
                    "available": bool(chain.get("poc_skeleton_available"))},
            "result": v.get("result") or {"status": "unattempted"},
        })
    return {
        "schema": "sec-vuln-research/validation-plan/1.0",
        "generatedBy": "render_report.py",
        "session": {
            "repository": metadata.get("repository"),
            "commit": metadata.get("commit"),
            "sessionId": metadata.get("session_id"),
        },
        "note": ("Each finding routes to validationMethod. Run it, then write the "
                 "outcome into `result` (status: confirmed|not_reproduced|inconclusive). "
                 "A confirmed result with evidence copied into the report's "
                 "attack_chain.validation.result promotes the finding to "
                 "exploit_demonstrated on the next render."),
        "findings": entries,
    }


def parse_path_names(path_str) -> list:
    return [s["name"] for s in parse_path_steps(path_str)]


def render(data: dict, template_path: Path) -> str:
    env = Environment(
        loader=FileSystemLoader(str(template_path.parent)),
        undefined=ChainableUndefined,   # missing nested keys render as '', never crash
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    template = env.get_template(template_path.name)
    return template.render(**data)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("yaml_file", type=Path, help="Filled vuln-research YAML report")
    parser.add_argument("--output", "-o", type=Path, default=None,
                        help="Output path (default: <yaml-stem>.md alongside the YAML)")
    args = parser.parse_args()

    yaml_path = args.yaml_file.resolve()
    if not yaml_path.exists():
        print(f"Error: {yaml_path} not found.", file=sys.stderr)
        sys.exit(2)
    session_dir = yaml_path.parent

    template_path = TEMPLATES_DIR / TEMPLATE_NAME
    if not template_path.exists():
        print(f"Error: template not found at {template_path}.", file=sys.stderr)
        sys.exit(2)

    yaml = YAML()
    yaml.preserve_quotes = True
    with yaml_path.open(encoding="utf-8") as f:
        data = yaml.load(f)
    if not isinstance(data, dict) or "report" not in data:
        print(f"Error: {yaml_path} must have a top-level 'report' key.", file=sys.stderr)
        sys.exit(2)
    report = data["report"]
    findings = [f for f in (report.get("findings") or []) if f.get("id")]

    warnings: list[str] = []
    refused: list[dict] = []
    included: list[dict] = []

    for finding in findings:
        # Clear flags from earlier renders so the pass is idempotent.
        finding.pop("refused", None)
        finding.pop("refusal_reason", None)
        finding.pop("duplicate_of", None)
        ok, reason = verify_triage(finding, session_dir, warnings)
        if not ok:
            finding["refused"] = True
            finding["refusal_reason"] = reason
            refused.append({"id": str(finding.get("id")), "reason": reason})
            continue
        validate_attack_chain(finding, session_dir, warnings)
        apply_validation_result(finding, warnings)
        redact_secrets(finding, warnings)
        included.append(finding)

    included = dedup(included, warnings)
    included = [f for f in included if not f.get("duplicate_of")]

    # Findings stay in the YAML (marked refused/duplicate_of) for audit;
    # counts, recommendations, and the rendered report use only `included`.
    compute_risk_counts(report, included)
    compute_recommendations(report, included)

    # Verification stamp — derived from what was checked, never asserted.
    verified_findings = [f for f in included
                         if (f.get("triage") or {}).get("computed_by") == "triage_tally.py"]
    claiming = [f for f in included if (f.get("triage") or {}).get("final_evidence_level")]
    if refused:
        status = "unverified"
        reason = (f"{len(refused)} finding(s) refused for verification claims "
                  "without matching records")
    elif claiming and len(verified_findings) < len(claiming):
        status = "unverified"
        reason = "some findings' triage was not recomputable from round records"
    else:
        status = "verified"
        reason = None
    report["verification"] = {
        "status": status,
        "reason": reason,
        "findings_included": len(included),
        "findings_refused": len(refused),
        "refused": refused,
        "validation_warnings": warnings,
        "computed_by": "render_report.py",
        "computed_at": now(),
    }

    # Write computed state back — the YAML stays the single source of truth.
    with yaml_path.open("w", encoding="utf-8") as f:
        yaml.dump(data, f)

    output_path = (args.output or yaml_path.with_suffix(".md")).resolve()
    markdown = render(data, template_path)
    output_path.write_text(markdown, encoding="utf-8")

    # SARIF and the validation plan are products of the same validated pass —
    # never hand-written, so neither can disagree with the report.
    sarif = build_sarif(report, included)
    sarif_path = session_dir / "findings.sarif"
    sarif_path.write_text(json.dumps(sarif, indent=2), encoding="utf-8")

    plan = build_validation_plan(report, included)
    plan_path = session_dir / "validation-plan.json"
    plan_path.write_text(json.dumps(plan, indent=2), encoding="utf-8")

    for r in refused:
        print(f"refused {r['id']} — {r['reason']}")
    for w in warnings:
        print(f"warning: {w}")
    print(f"verification: {status}" + (f" ({reason})" if reason else ""))
    print(f"Report written     -> {output_path}")
    print(f"SARIF written       -> {sarif_path} "
          f"({len(sarif['runs'][0]['results'])} result(s))")
    print(f"Validation plan     -> {plan_path} "
          f"({len(plan['findings'])} finding(s) with an attack chain)")


if __name__ == "__main__":
    main()
