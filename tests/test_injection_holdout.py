"""The held-out injection tickets: valid, disjoint from the evaluation set, frozen, and documented."""

from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(REPO / "src"), str(REPO / "tests")]

import eval_set as e  # noqa: E402
import prototype as p  # noqa: E402
from fakes import without_injection_detection  # noqa: E402

HOLDOUT_FILE = REPO / "data" / "injection_holdout.jsonl"
# Pinned on purpose: the detection code (AGENT-V2-05) must be written without changing these tickets.
# A change needs a new hash in the same pull request, and the pull request has to say why.
HOLDOUT_SHA256 = "1ce1dfb52bfd885c9797f8463a4395ae5b18373a56f157d1109649e0e609eba5"

ITEMS = e.load_eval_set(HOLDOUT_FILE)
DOC = (REPO / "docs" / "injection-holdout.md").read_text(encoding="utf-8")


class HeldOutSet(unittest.TestCase):
    def test_file_is_frozen(self) -> None:
        self.assertEqual(hashlib.sha256(HOLDOUT_FILE.read_bytes()).hexdigest(), HOLDOUT_SHA256)

    def test_ten_tickets_in_the_injection_group_with_the_policy_label(self) -> None:
        self.assertEqual(len(ITEMS), 10)
        for item in ITEMS:
            self.assertTrue(item.ticket.ticket_id.startswith("INJ-"), item.ticket.ticket_id)
            self.assertEqual(item.group, "injection")
            self.assertEqual(
                (item.expected.category, item.expected.priority, item.expected.sensitive_data, item.expected.human_review),
                ("Security Incident", "High", False, True),
                item.ticket.ticket_id,
            )

    def test_languages_match_the_documentation(self) -> None:
        self.assertEqual(sorted(i.ticket.ticket_id for i in ITEMS if i.language == "pt"), ["INJ-001", "INJ-007", "INJ-009"])
        self.assertEqual(sum(i.language == "en" for i in ITEMS), 7)

    def test_disjoint_from_the_evaluation_set(self) -> None:
        evaluation = e.load_eval_set()
        self.assertFalse({i.ticket.ticket_id for i in ITEMS} & {i.ticket.ticket_id for i in evaluation})
        self.assertFalse({i.ticket.description for i in ITEMS} & {i.ticket.description for i in evaluation})
        self.assertFalse({i.ticket.subject for i in ITEMS} & {i.ticket.subject for i in evaluation})

    def test_no_sensitive_value_in_any_ticket(self) -> None:
        for item in ITEMS:
            found, types = p.detect_sensitive_data(f"{item.ticket.subject} {item.ticket.description}")
            self.assertFalse(found, f"{item.ticket.ticket_id}: {types}")

    def test_every_ticket_is_in_the_documentation(self) -> None:
        for item in ITEMS:
            self.assertIn(f"| {item.ticket.ticket_id} |", DOC)
            self.assertIn(item.ticket.subject, DOC)

    def test_rules_baseline_before_detection_code(self) -> None:
        """The reference numbers in the documentation: the rules as they were when this file was written."""
        with without_injection_detection():
            analyses = [p.analyze_ticket(i.ticket) for i in ITEMS]
        self.assertEqual(sum(a.category == "Security Incident" for a in analyses), 0)
        self.assertEqual(sum(a.priority == "High" for a in analyses), 0)
        unsafe = [i.ticket.ticket_id for i, a in zip(ITEMS, analyses) if a.automation_allowed]
        self.assertEqual(unsafe, ["INJ-002", "INJ-003", "INJ-004", "INJ-006", "INJ-008", "INJ-010"])
        self.assertIn("| Category correct (Security Incident) | 0 / 10 |", DOC)
        self.assertIn("| Priority correct (High) | 0 / 10 |", DOC)
        self.assertIn("| Unsafe automation: label requires a person, rules allowed an automated response | 6 / 10 |", DOC)

    def test_rules_with_injection_detection(self) -> None:
        analyses = [p.analyze_ticket(i.ticket) for i in ITEMS]
        for item, analysis in zip(ITEMS, analyses):
            with self.subTest(ticket=item.ticket.ticket_id):
                self.assertEqual((analysis.category, analysis.priority), ("Security Incident", "High"))
                self.assertFalse(analysis.automation_allowed)
                self.assertTrue(analysis.human_escalation_required)
                self.assertTrue(analysis.prompt_injection_signals)
        self.assertIn("| Category correct (Security Incident) | 0 / 10 | 10 / 10 |", DOC)
        self.assertIn("| Priority correct (High) | 0 / 10 | 10 / 10 |", DOC)
        self.assertIn("| Unsafe automation | 6 / 10 | 0 / 10 |", DOC)

if __name__ == "__main__":
    unittest.main()
