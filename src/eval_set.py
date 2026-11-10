"""
Labelled evaluation set and the rules-only baseline.

The evaluation set (data/eval_tickets.jsonl) holds synthetic IT support tickets,
each with the expected triage decision written by hand. It is used to measure
the deterministic rules today and, later, the LLM classifier against the same
labels.

Labelling policy (the labels follow the documented policy, not the regexes):
- category: one of the six categories implemented in src/prototype.py;
- priority: High for security incidents, disclosed sensitive data, urgency or
  business-wide impact; otherwise Medium for access and technical cases and Low
  for informational or unclassifiable ones;
- sensitive_data: the ticket discloses an actual value (CPF, email, phone, card
  number or secret), not merely mentions a password;
- human_review: derived from the policy in docs/decision-logic.md: security
  incident, access request, unclassifiable (General Support), sensitive data or
  High priority. validate_ticket() enforces this derivation.

Prompt-injection attempts are labelled Security Incident: an attempt to
manipulate the triage agent is treated as a security event, whatever the
underlying request is.

Run from the repository root:

    python src/eval_set.py
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import prototype as p  # noqa: E402

EVAL_SET_FILE = p.PROJECT_ROOT / "data" / "eval_tickets.jsonl"

CATEGORIES = (
    "Security Incident",
    "Access Request",
    "Access Support",
    "Service Request",
    "Technical Incident",
    "General Support",
)
PRIORITIES = ("High", "Medium", "Low")
GROUPS = ("common", "ambiguous", "incomplete", "sensitive", "injection")
LANGUAGES = ("en", "pt")

ALWAYS_REVIEWED_CATEGORIES = ("Security Incident", "Access Request", "General Support")


@dataclass(frozen=True)
class Expected:
    category: str
    priority: str
    sensitive_data: bool
    human_review: bool


@dataclass(frozen=True)
class EvalTicket:
    ticket: p.Ticket
    group: str
    language: str
    expected: Expected
    rationale: str


def policy_requires_review(category: str, priority: str, sensitive_data: bool) -> bool:
    """Human review required by the documented policy (decision-logic.md, section 6)."""
    return category in ALWAYS_REVIEWED_CATEGORIES or sensitive_data or priority == "High"


def validate_ticket(raw: dict[str, Any]) -> EvalTicket:
    """Validate one JSON record and return it typed. Raises ValueError on any problem."""
    required = ("ticket_id", "group", "language", "user", "subject", "description", "expected", "rationale")
    missing = [key for key in required if key not in raw]
    if missing:
        raise ValueError(f"missing fields: {missing}")

    ticket_id = raw["ticket_id"]
    expected = raw["expected"]

    if raw["group"] not in GROUPS:
        raise ValueError(f"{ticket_id}: unknown group {raw['group']!r}")
    if raw["language"] not in LANGUAGES:
        raise ValueError(f"{ticket_id}: unknown language {raw['language']!r}")
    if expected.get("category") not in CATEGORIES:
        raise ValueError(f"{ticket_id}: unknown category {expected.get('category')!r}")
    if expected.get("priority") not in PRIORITIES:
        raise ValueError(f"{ticket_id}: unknown priority {expected.get('priority')!r}")
    for flag in ("sensitive_data", "human_review"):
        if not isinstance(expected.get(flag), bool):
            raise ValueError(f"{ticket_id}: {flag} must be true or false")
    if not raw["rationale"].strip():
        raise ValueError(f"{ticket_id}: rationale is empty")

    label = Expected(
        category=expected["category"],
        priority=expected["priority"],
        sensitive_data=expected["sensitive_data"],
        human_review=expected["human_review"],
    )

    if label.human_review != policy_requires_review(label.category, label.priority, label.sensitive_data):
        raise ValueError(f"{ticket_id}: human_review contradicts the documented policy")
    if (label.category == "Security Incident" or label.sensitive_data) and label.priority != "High":
        raise ValueError(f"{ticket_id}: security incidents and sensitive data must be High priority")

    return EvalTicket(
        ticket=p.Ticket(
            ticket_id=ticket_id,
            user=raw["user"],
            subject=raw["subject"],
            description=raw["description"],
        ),
        group=raw["group"],
        language=raw["language"],
        expected=label,
        rationale=raw["rationale"],
    )


def load_eval_set(path: Path = EVAL_SET_FILE) -> list[EvalTicket]:
    """Load and validate the evaluation set. Ticket IDs must be unique."""
    tickets: list[EvalTicket] = []
    seen: set[str] = set()

    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                item = validate_ticket(json.loads(line))
            except (json.JSONDecodeError, ValueError) as error:
                raise ValueError(f"{path.name}, line {line_number}: {error}") from error
            if item.ticket.ticket_id in seen:
                raise ValueError(f"{path.name}, line {line_number}: duplicate {item.ticket.ticket_id}")
            seen.add(item.ticket.ticket_id)
            tickets.append(item)

    return tickets


@dataclass(frozen=True)
class BaselineRow:
    ticket_id: str
    group: str
    expected: Expected
    analysis: p.TicketAnalysis

    @property
    def category_ok(self) -> bool:
        return self.analysis.category == self.expected.category

    @property
    def priority_ok(self) -> bool:
        return self.analysis.priority == self.expected.priority

    @property
    def unsafe_automation(self) -> bool:
        """The label requires a person, but the rules allowed an automated response."""
        return self.expected.human_review and self.analysis.automation_allowed

    @property
    def unnecessary_review(self) -> bool:
        """The label allows automation, but the rules sent the ticket to a person."""
        return not self.expected.human_review and self.analysis.human_escalation_required


def run_rules_baseline(items: list[EvalTicket]) -> list[BaselineRow]:
    """Run the current deterministic rules on every evaluation ticket."""
    return [
        BaselineRow(
            ticket_id=item.ticket.ticket_id,
            group=item.group,
            expected=item.expected,
            analysis=p.analyze_ticket(item.ticket),
        )
        for item in items
    ]


def summarize(rows: list[BaselineRow]) -> dict[str, int]:
    return {
        "tickets": len(rows),
        "category_correct": sum(row.category_ok for row in rows),
        "priority_correct": sum(row.priority_ok for row in rows),
        "review_required": sum(row.expected.human_review for row in rows),
        "unsafe_automation": sum(row.unsafe_automation for row in rows),
        "unnecessary_review": sum(row.unnecessary_review for row in rows),
    }


def main() -> None:
    rows = run_rules_baseline(load_eval_set())

    print(f"{'Ticket':<9} {'Group':<11} {'Expected category':<19} {'Rules category':<19} "
          f"{'Exp.prio':<8} {'Rules':<7} Flag")
    print("-" * 92)
    for row in rows:
        flag = "UNSAFE" if row.unsafe_automation else ("over-review" if row.unnecessary_review else "")
        print(f"{row.ticket_id:<9} {row.group:<11} {row.expected.category:<19} {row.analysis.category:<19} "
              f"{row.expected.priority:<8} {row.analysis.priority:<7} {flag}")

    s = summarize(rows)
    print("-" * 92)
    print(f"Category correct: {s['category_correct']}/{s['tickets']}")
    print(f"Priority correct: {s['priority_correct']}/{s['tickets']}")
    print(f"Unsafe automation (label requires a person, rules allowed automation): "
          f"{s['unsafe_automation']}/{s['review_required']}")
    print(f"Unnecessary review (label allows automation, rules escalated): {s['unnecessary_review']}")


if __name__ == "__main__":
    main()
