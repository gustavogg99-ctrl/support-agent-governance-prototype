"""
Evaluation of the LLM triage against the labelled evaluation set (AGENT-V2-07).

Runs every ticket of data/eval_tickets.jsonl through the full guardrail
(rules + LLM, see src/agent.py) for each combination of prompt version and
model, and measures:

- accuracy of the LLM's category, priority and sensitive-data flag;
- invalid LLM answers (bad JSON, API errors, truncation): a person decides;
- disagreements between rules and LLM (a person decides);
- unsafe automation: the label requires a person but the final decision
  allowed an automated response. "LLM alone" is the same count if the rules
  guardrail did not exist, so the table shows what the guardrail is worth;
- unnecessary review: the label allows automation but a person was asked;
- cost, computed from the tokens the API reports.

Only classification is evaluated. Reply drafts are not part of this run.

Tests never call the API (they use a scripted client). A real run happens on
the project owner's machine with ANTHROPIC_API_KEY set in his terminal, and the
output file is committed (see docs/evaluation-run.md):

    py src/evaluate.py --output results/eval_results.json

To print the results table from a saved run, with no API call:

    py src/evaluate.py --table results/eval_results.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import prototype as p  # noqa: E402
from agent import TriageDecision, triage  # noqa: E402
from eval_set import (  # noqa: E402
    EVAL_SET_FILE,
    GROUPS,
    EvalTicket,
    load_eval_set,
    policy_requires_review,
    run_rules_baseline,
    summarize as summarize_rules,
)
from llm_classifier import (  # noqa: E402
    DEFAULT_EFFORT,
    MODELS,
    PROMPTS_DIR,
    AnthropicClient,
    LLMClient,
    LLMError,
)

PROMPT_VERSIONS = ("v1", "v2")
DEFAULT_OUTPUT = p.PROJECT_ROOT / "results" / "eval_results.json"

# US$ per million tokens (input, output). Official prices checked on PRICES_CHECKED;
# prices change, so re-check them before publishing any cost number.
PRICES_CHECKED = "2026-11-10"
PRICES_PER_MILLION_TOKENS: dict[str, tuple[float, float]] = {
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-sonnet-5-5": (2.00, 10.00),
}


def compute_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Cost in US$ from the tokens the API reported."""
    price_in, price_out = PRICES_PER_MILLION_TOKENS[model]
    return (input_tokens * price_in + output_tokens * price_out) / 1_000_000


@dataclass(frozen=True)
class Row:
    """One ticket of one run: the label and the final decision of the guardrail."""

    item: EvalTicket
    decision: TriageDecision

    @property
    def llm_ok(self) -> bool:
        return self.decision.llm.ok

    @property
    def category_ok(self) -> bool:
        return self.llm_ok and self.decision.llm.category == self.item.expected.category

    @property
    def priority_ok(self) -> bool:
        return self.llm_ok and self.decision.llm.priority == self.item.expected.priority

    @property
    def sensitive_ok(self) -> bool:
        return self.llm_ok and self.decision.llm.sensitive_data == self.item.expected.sensitive_data

    @property
    def api_error(self) -> bool:
        return self.decision.llm.error.startswith("api error")

    @property
    def unsafe_automation(self) -> bool:
        """The label requires a person, but the final decision allowed an automated response."""
        return self.item.expected.human_review and self.decision.automation_allowed

    @property
    def llm_alone_unsafe(self) -> bool:
        """Same as unsafe_automation if the LLM decided alone, with no rules guardrail."""
        llm = self.decision.llm
        return (
            self.item.expected.human_review
            and llm.ok
            and not policy_requires_review(llm.category, llm.priority, llm.sensitive_data)
        )

    @property
    def unnecessary_review(self) -> bool:
        """The label allows automation, but the final decision sent the ticket to a person."""
        return not self.item.expected.human_review and self.decision.human_review


def evaluate_combination(items: list[EvalTicket], client: LLMClient, model: str, prompt_version: str) -> list[Row]:
    return [
        Row(item=item, decision=triage(item.ticket, client, model=model, prompt_version=prompt_version))
        for item in items
    ]


def summarize(rows: list[Row], model: str) -> dict[str, Any]:
    llm_results = [row.decision.llm for row in rows]
    input_tokens = sum(r.input_tokens for r in llm_results)
    output_tokens = sum(r.output_tokens for r in llm_results)
    cost = compute_cost(model, input_tokens, output_tokens)

    by_group = {}
    for group in GROUPS:
        group_rows = [row for row in rows if row.item.group == group]
        by_group[group] = {
            "tickets": len(group_rows),
            "category_correct": sum(row.category_ok for row in group_rows),
            "unsafe_automation": sum(row.unsafe_automation for row in group_rows),
        }

    return {
        "tickets": len(rows),
        "category_correct": sum(row.category_ok for row in rows),
        "priority_correct": sum(row.priority_ok for row in rows),
        "sensitive_correct": sum(row.sensitive_ok for row in rows),
        "llm_invalid": sum(not row.llm_ok for row in rows),
        "api_errors": sum(row.api_error for row in rows),
        "disagreements": sum(bool(row.decision.disagreements) for row in rows),
        "rules_blocked_automation": sum(not row.decision.rules.automation_allowed for row in rows),
        "review_required": sum(row.item.expected.human_review for row in rows),
        "unsafe_automation": sum(row.unsafe_automation for row in rows),
        "unsafe_automation_llm_alone": sum(row.llm_alone_unsafe for row in rows),
        "unnecessary_review": sum(row.unnecessary_review for row in rows),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": round(cost, 6),
        "cost_per_ticket_usd": round(cost / len(rows), 6) if rows else 0.0,
        "by_group": by_group,
    }


def is_fully_failed(summary: dict[str, Any]) -> bool:
    """Every call failed at the API (wrong key, no balance, no network): the run says nothing about the model."""
    return summary["tickets"] > 0 and summary["api_errors"] == summary["tickets"]


def row_to_dict(row: Row) -> dict[str, Any]:
    decision, llm, rules = row.decision, row.decision.llm, row.decision.rules
    return {
        "ticket_id": row.item.ticket.ticket_id,
        "group": row.item.group,
        "expected": row.item.expected.__dict__,
        "rules": {
            "category": rules.category,
            "priority": rules.priority,
            "sensitive_data": rules.sensitive_data_detected,
            "automation_allowed": rules.automation_allowed,
        },
        "llm": {
            "ok": llm.ok,
            "category": llm.category,
            "priority": llm.priority,
            "sensitive_data": llm.sensitive_data,
            "reason": llm.reason,
            "error": llm.error,
            "input_tokens": llm.input_tokens,
            "output_tokens": llm.output_tokens,
        },
        "final": {
            "human_review": decision.human_review,
            "automation_allowed": decision.automation_allowed,
            "disagreements": decision.disagreements,
        },
        "flags": {
            "category_ok": row.category_ok,
            "priority_ok": row.priority_ok,
            "sensitive_ok": row.sensitive_ok,
            "unsafe_automation": row.unsafe_automation,
            "unsafe_automation_llm_alone": row.llm_alone_unsafe,
            "unnecessary_review": row.unnecessary_review,
        },
    }


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_report(
    items: list[EvalTicket],
    client: LLMClient,
    effort: str = DEFAULT_EFFORT,
    models: tuple[str, ...] = MODELS,
    prompt_versions: tuple[str, ...] = PROMPT_VERSIONS,
    progress=lambda message: None,
) -> dict[str, Any]:
    """Run every prompt version x model combination and return a JSON-serialisable report."""
    runs = []
    for model in models:
        for prompt_version in prompt_versions:
            rows = evaluate_combination(items, client, model, prompt_version)
            summary = summarize(rows, model)
            progress(
                f"{model} / {prompt_version}: category {summary['category_correct']}/{summary['tickets']}, "
                f"invalid {summary['llm_invalid']}, unsafe {summary['unsafe_automation']}, "
                f"cost US$ {summary['cost_usd']:.4f}"
            )
            runs.append({
                "model": model,
                "prompt_version": prompt_version,
                "summary": summary,
                "tickets": [row_to_dict(row) for row in rows],
            })

    return {
        "meta": {
            "run_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "tickets": len(items),
            "effort": effort,
            "models": list(models),
            "prompt_versions": list(prompt_versions),
            "prompt_sha256": {v: _sha256(PROMPTS_DIR / f"classify_{v}.md") for v in prompt_versions},
            "eval_set_sha256": _sha256(EVAL_SET_FILE),
            "prices_usd_per_million_tokens": {
                model: {"input": PRICES_PER_MILLION_TOKENS[model][0], "output": PRICES_PER_MILLION_TOKENS[model][1]}
                for model in models
            },
            "prices_checked": PRICES_CHECKED,
            "scope": "classification only; one call per ticket per combination; reply drafts not evaluated",
        },
        "rules_baseline": summarize_rules(run_rules_baseline(items)),
        "runs": runs,
    }


def format_markdown_table(report: dict[str, Any]) -> str:
    """Results table (ASCII only, so it prints on any console)."""
    total = report["meta"]["tickets"]
    header = (
        "| Classifier | Category | Priority | Invalid LLM output | Rules-LLM disagreements | "
        "Unsafe automation, LLM alone | Unsafe automation, with guardrail | Unnecessary review | Cost per ticket (US$) |"
    )
    lines = [header, "|" + "---|" * 9]

    baseline = report["rules_baseline"]
    lines.append(
        f"| Rules only | {baseline['category_correct']}/{total} | {baseline['priority_correct']}/{total} | - | - | "
        f"- | {baseline['unsafe_automation']}/{baseline['review_required']} | {baseline['unnecessary_review']} | 0 |"
    )
    for run in report["runs"]:
        s = run["summary"]
        lines.append(
            f"| {run['model']} / prompt {run['prompt_version']} | {s['category_correct']}/{total} | "
            f"{s['priority_correct']}/{total} | {s['llm_invalid']} | {s['disagreements']} | "
            f"{s['unsafe_automation_llm_alone']}/{s['review_required']} | "
            f"{s['unsafe_automation']}/{s['review_required']} | {s['unnecessary_review']} | "
            f"{s['cost_per_ticket_usd']:.5f} |"
        )
    return "\n".join(lines)


def main(arguments: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate the LLM triage (prompts x models) on the evaluation set.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="where to write the results JSON")
    parser.add_argument("--table", type=Path, help="print the results table from a saved JSON; no API call")
    args = parser.parse_args(arguments)

    if args.table is not None:
        print(format_markdown_table(json.loads(args.table.read_text(encoding="utf-8"))))
        return 0

    try:
        client = AnthropicClient()
    except LLMError as error:
        print(f"Cannot call the API: {error}")
        return 2

    items = load_eval_set()
    calls = len(items) * len(MODELS) * len(PROMPT_VERSIONS)
    print(f"{len(items)} tickets x {len(MODELS)} models x {len(PROMPT_VERSIONS)} prompts = {calls} API calls.")
    report = build_report(items, client, progress=print)

    failed = [r for r in report["runs"] if is_fully_failed(r["summary"])]
    if failed:
        print("Every call failed at the API in: "
              + ", ".join(f"{r['model']}/{r['prompt_version']}" for r in failed)
              + ". Nothing was written. Check the key, the balance and the connection, then run again.")
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    total_cost = sum(r["summary"]["cost_usd"] for r in report["runs"])
    print()
    print(format_markdown_table(report))
    print(f"\nTotal cost of this run: US$ {total_cost:.4f}")
    print(f"Results written to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
