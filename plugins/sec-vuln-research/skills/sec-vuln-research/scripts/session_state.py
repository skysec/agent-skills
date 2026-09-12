# /// script
# requires-python = ">=3.11"
# ///
"""Session state: checkpoints and budget enforcement for sec-vuln-research.

The pipeline's guarantees about budget and resumability live here, in code,
not in the model. All state is one JSON file: <session_dir>/session-state.json.

Subcommands:
    init <session_dir> --budget 25.0 [--depth standard] [--mode full]
        Create session-state.json (refuses to overwrite an existing one).

    resume <session_dir>
        Print resume point as JSON: first incomplete stage and its pending
        units. Exit 0 if there is work to resume, 4 if the session is complete.

    checkpoint <session_dir> stage <stage> --status started|completed|failed
    checkpoint <session_dir> unit <stage> <unit_id> --status pending|done|failed
        Record progress. Units are per-stage work items (a file to hunt, a
        finding to triage). Marking a stage completed requires no pending units.

    cost <session_dir> record <stage> <usd>
        Add spend to a stage. Prints total and remaining budget.
        EXIT CODE 3 when the recorded total exceeds the budget — the caller
        must finish the in-flight unit, checkpoint, and stop with a resume
        message (deepsec-style resumable stop). 0 budget = unlimited.

    cost <session_dir> check
        Exit 0 if under budget, 3 if over.

    estimate <session_dir> --tier-a N --tier-b M
        Print a cost estimate for the expensive stages (hunt + triage) from
        tier counts, and whether it fits the remaining budget. Per-unit
        defaults are deliberately conservative; override with flags.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

STATE_NAME = "session-state.json"
STAGES = [
    "graph_build", "dfd_generation", "diff_mode", "ranking",
    "context_generation", "hunting", "triage", "variant_analysis",
    "attack_chains", "report",
]


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def state_path(session_dir: Path) -> Path:
    return session_dir / STATE_NAME


def load(session_dir: Path) -> dict:
    p = state_path(session_dir)
    if not p.exists():
        sys.exit(f"Error: {p} not found — run `session_state.py init {session_dir}` first.")
    return json.loads(p.read_text(encoding="utf-8"))


def save(session_dir: Path, state: dict) -> None:
    state["updated_at"] = now()
    state_path(session_dir).write_text(json.dumps(state, indent=2), encoding="utf-8")


def cmd_init(args: argparse.Namespace) -> None:
    session_dir = Path(args.session_dir)
    session_dir.mkdir(parents=True, exist_ok=True)
    p = state_path(session_dir)
    if p.exists():
        print(f"session-state.json already exists — resuming, not reinitializing.")
        cmd_resume(args)
        return
    state = {
        "created_at": now(),
        "updated_at": now(),
        "config": {
            "mode": args.mode,
            "depth": args.depth,
            "budget_usd": args.budget,
        },
        "budget": {"limit_usd": args.budget, "spent_usd": 0.0, "by_stage": {}},
        "stages": {s: {"status": "pending", "units": {}} for s in STAGES},
    }
    save(session_dir, state)
    print(f"Initialized {p}")
    print(f"  budget: ${args.budget:.2f}" + (" (unlimited)" if args.budget == 0 else ""))


def cmd_resume(args: argparse.Namespace) -> None:
    session_dir = Path(args.session_dir)
    state = load(session_dir)
    for stage in STAGES:
        info = state["stages"].get(stage, {})
        status = info.get("status", "pending")
        if status in ("completed", "skipped"):
            continue
        pending = [u for u, s in info.get("units", {}).items() if s != "done"]
        out = {
            "resume_stage": stage,
            "stage_status": status,
            "pending_units": pending,
            "spent_usd": round(state["budget"]["spent_usd"], 2),
            "budget_usd": state["budget"]["limit_usd"],
        }
        print(json.dumps(out, indent=2))
        return
    print(json.dumps({"resume_stage": None, "message": "all stages completed"}))
    sys.exit(4)


def cmd_checkpoint(args: argparse.Namespace) -> None:
    session_dir = Path(args.session_dir)
    state = load(session_dir)
    if args.kind == "stage":
        stage = state["stages"].setdefault(args.stage, {"status": "pending", "units": {}})
        if args.status == "completed":
            pending = [u for u, s in stage.get("units", {}).items() if s != "done"]
            if pending:
                sys.exit(f"Error: cannot complete stage '{args.stage}' — "
                         f"{len(pending)} pending unit(s): {', '.join(pending[:5])}"
                         + (" ..." if len(pending) > 5 else ""))
        stage["status"] = args.status
        stage[f"{args.status}_at"] = now()
    else:  # unit
        stage = state["stages"].setdefault(args.stage, {"status": "pending", "units": {}})
        if stage["status"] == "pending":
            stage["status"] = "started"
        stage["units"][args.unit_id] = args.status
    save(session_dir, state)
    print(f"checkpoint: {args.stage}"
          + (f"/{args.unit_id}" if args.kind == "unit" else "")
          + f" -> {args.status}")


def cmd_cost(args: argparse.Namespace) -> None:
    session_dir = Path(args.session_dir)
    state = load(session_dir)
    budget = state["budget"]
    if args.action == "record":
        budget["by_stage"][args.stage] = round(
            budget["by_stage"].get(args.stage, 0.0) + args.usd, 4)
        budget["spent_usd"] = round(sum(budget["by_stage"].values()), 4)
        save(session_dir, state)
    limit = budget["limit_usd"]
    spent = budget["spent_usd"]
    if limit and limit > 0:
        remaining = round(limit - spent, 2)
        print(f"spent: ${spent:.2f} / ${limit:.2f}  (remaining: ${remaining:.2f})")
        if spent > limit:
            print("BUDGET EXCEEDED — finish the in-flight unit, checkpoint it, and stop.")
            print("The session is resumable: re-invoke the skill with this session dir "
                  "and a higher budget to continue where it left off.")
            sys.exit(3)
    else:
        print(f"spent: ${spent:.2f} (budget unlimited)")


def cmd_estimate(args: argparse.Namespace) -> None:
    session_dir = Path(args.session_dir)
    state = load(session_dir)
    hunt = args.tier_a * args.per_tier_a + args.tier_b * args.per_tier_b
    expected_findings = max(1, round((args.tier_a + args.tier_b) * args.findings_rate))
    triage = expected_findings * args.per_finding_triage
    total = round(hunt + triage, 2)
    limit = state["budget"]["limit_usd"]
    spent = state["budget"]["spent_usd"]
    print(f"Estimated remaining pipeline cost: ${total:.2f}")
    print(f"  hunt:   {args.tier_a} Tier A x ${args.per_tier_a:.2f} + "
          f"{args.tier_b} Tier B x ${args.per_tier_b:.2f} = ${hunt:.2f}")
    print(f"  triage: ~{expected_findings} findings x ${args.per_finding_triage:.2f} = ${triage:.2f}")
    if limit and limit > 0:
        remaining = limit - spent
        fits = "FITS" if total <= remaining else "EXCEEDS"
        print(f"  budget remaining: ${remaining:.2f} -> estimate {fits} budget")
        if total > remaining:
            print("  Show this estimate to the user before proceeding: either raise the "
                  "budget, reduce depth, or accept that the run will stop at the boundary.")
            sys.exit(3)
    else:
        print("  budget: unlimited")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init")
    p.add_argument("session_dir")
    p.add_argument("--budget", type=float, default=25.0,
                   help="Budget in USD (default 25.0; 0 = unlimited)")
    p.add_argument("--depth", default="standard")
    p.add_argument("--mode", default="full")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("resume")
    p.add_argument("session_dir")
    p.set_defaults(func=cmd_resume)

    p = sub.add_parser("checkpoint")
    p.add_argument("session_dir")
    csub = p.add_subparsers(dest="kind", required=True)
    ps = csub.add_parser("stage")
    ps.add_argument("stage", choices=STAGES)
    ps.add_argument("--status", required=True,
                    choices=["started", "completed", "failed", "skipped"])
    ps.set_defaults(func=cmd_checkpoint)
    pu = csub.add_parser("unit")
    pu.add_argument("stage", choices=STAGES)
    pu.add_argument("unit_id")
    pu.add_argument("--status", required=True, choices=["pending", "done", "failed"])
    pu.set_defaults(func=cmd_checkpoint)

    p = sub.add_parser("cost")
    p.add_argument("session_dir")
    costsub = p.add_subparsers(dest="action", required=True)
    pr = costsub.add_parser("record")
    pr.add_argument("stage", choices=STAGES)
    pr.add_argument("usd", type=float)
    pr.set_defaults(func=cmd_cost)
    pc = costsub.add_parser("check")
    pc.set_defaults(func=cmd_cost)

    p = sub.add_parser("estimate")
    p.add_argument("session_dir")
    p.add_argument("--tier-a", type=int, required=True)
    p.add_argument("--tier-b", type=int, required=True)
    p.add_argument("--per-tier-a", type=float, default=0.60,
                   help="Estimated USD per Tier A file (4 specialists)")
    p.add_argument("--per-tier-b", type=float, default=0.15,
                   help="Estimated USD per Tier B file (single pass)")
    p.add_argument("--per-finding-triage", type=float, default=0.40,
                   help="Estimated USD per finding (3 lenses + arbiter)")
    p.add_argument("--findings-rate", type=float, default=0.35,
                   help="Expected findings per hunted file")
    p.set_defaults(func=cmd_estimate)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
