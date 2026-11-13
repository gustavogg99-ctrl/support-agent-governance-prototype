"""
Tests for the labelled evaluation set and the rules-only baseline.

Standard library only; no network. Run from the repository root:

    python -m unittest discover -s tests -v
"""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import eval_set as e  # noqa: E402


VALID_RECORD = {
    "ticket_id": "EVAL-999",
    "group": "common",
    "language": "en",
    "user": "Test User",
    "subject": "Printer error",
    "description": "The printer shows an error.",
    "expected": {
        "category": "Technical Incident",
        "priority": "Medium",
        "sensitive_data": False,
        "human_review": False,
    },
    "rationale": "Single device fault.",
}


class EvalSetFile(unittest.TestCase):
    """The committed data file is valid and covers every group the scope asks for."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.items = e.load_eval_set()

    def test_has_thirty_tickets(self) -> None:
        self.assertEqual(len(self.items), 30)

    def test_every_group_has_at_least_five_tickets(self) -> None:
        counts = Counter(item.group for item in self.items)
        self.assertEqual(set(counts), set(e.GROUPS))
        for group in e.GROUPS:
            with self.subTest(group=group):
                self.assertGreaterEqual(counts[group], 5)

    def test_includes_portuguese_tickets(self) -> None:
        self.assertEqual(sum(item.language == "pt" for item in self.items), 6)

    def test_injection_attempts_are_labelled_security_incidents(self) -> None:
        for item in self.items:
            if item.group == "injection":
                with self.subTest(ticket=item.ticket.ticket_id):
                    self.assertEqual(item.expected.category, "Security Incident")
                    self.assertTrue(item.expected.human_review)

    def test_sensitive_labels_match_disclosed_values(self) -> None:
        """A ticket labelled sensitive must disclose a value the detector can see, and vice versa."""
        from prototype import detect_sensitive_data

        for item in self.items:
            with self.subTest(ticket=item.ticket.ticket_id):
                found, _ = detect_sensitive_data(f"{item.ticket.subject} {item.ticket.description}")
                self.assertEqual(found, item.expected.sensitive_data)


class EvalSetDocumentation(unittest.TestCase):
    def test_docs_table_matches_the_data_file(self) -> None:
        """docs/evaluation-set.md shows every ticket as it is in the data file, and what the rules decide for it."""
        doc = (Path(__file__).resolve().parent.parent / "docs" / "evaluation-set.md").read_text(encoding="utf-8")
        rows = {line.split("|")[1].strip(): line for line in doc.splitlines() if line.startswith("| EVAL-")}
        items = e.load_eval_set()
        self.assertEqual(sorted(rows), [item.ticket.ticket_id for item in items])
        for item, baseline in zip(items, e.run_rules_baseline(items)):
            with self.subTest(ticket=item.ticket.ticket_id):
                cells = [cell.strip() for cell in rows[item.ticket.ticket_id].split("|")]
                rules = f"{baseline.analysis.category}, {baseline.analysis.priority}"
                self.assertEqual(cells[2:11], [
                    item.group,
                    item.language,
                    f"**{item.ticket.subject}**: {item.ticket.description}",
                    item.expected.category,
                    item.expected.priority,
                    "yes" if item.expected.sensitive_data else "no",
                    "yes" if item.expected.human_review else "no",
                    item.rationale,
                    rules + (" ⚠️ unsafe" if baseline.unsafe_automation else ""),
                ])


class Validation(unittest.TestCase):
    def test_accepts_a_valid_record(self) -> None:
        item = e.validate_ticket(VALID_RECORD)
        self.assertEqual(item.ticket.ticket_id, "EVAL-999")

    def test_rejects_invalid_records(self) -> None:
        def broken(path: tuple[str, ...], value: object) -> dict:
            record = copy.deepcopy(VALID_RECORD)
            target = record
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = value
            return record

        cases = {
            "unknown category": broken(("expected", "category"), "Hardware"),
            "unknown priority": broken(("expected", "priority"), "P1"),
            "unknown group": broken(("group",), "easy"),
            "non-boolean flag": broken(("expected", "human_review"), "no"),
            "empty rationale": broken(("rationale",), " "),
            "review contradicts policy": broken(("expected", "human_review"), True),
            "sensitive but not High": broken(("expected", "sensitive_data"), True),
            "unknown language": broken(("language",), "es"),
            "missing field": {key: value for key, value in VALID_RECORD.items() if key != "rationale"},
            "security incident but not High": broken(
                ("expected",),
                {"category": "Security Incident", "priority": "Medium", "sensitive_data": False, "human_review": True},
            ),
        }
        for name, record in cases.items():
            with self.subTest(case=name):
                with self.assertRaises(ValueError):
                    e.validate_ticket(record)

    def test_rejects_duplicate_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "eval.jsonl"
            line = json.dumps(VALID_RECORD)
            path.write_text(f"{line}\n{line}\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                e.load_eval_set(path)

    def test_a_broken_line_is_reported_with_its_number_and_blank_lines_are_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "eval.jsonl"
            path.write_text(f"{json.dumps(VALID_RECORD)}\n\n{{not json\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "eval.jsonl, line 3"):
                e.load_eval_set(path)


class RulesBaseline(unittest.TestCase):
    """Pins the rules-only baseline so later comparisons with the LLM start from known numbers."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.rows = e.run_rules_baseline(e.load_eval_set())

    def test_summary(self) -> None:
        self.assertEqual(
            e.summarize(self.rows),
            {
                "tickets": 30,
                "category_correct": 9,
                "priority_correct": 17,
                "review_required": 21,
                "unsafe_automation": 8,
                "unnecessary_review": 3,
            },
        )

    def test_unsafe_cases_are_incomplete_tickets_and_injection_attempts(self) -> None:
        unsafe = [row.ticket_id for row in self.rows if row.unsafe_automation]
        self.assertEqual(
            unsafe,
            ["EVAL-016", "EVAL-017", "EVAL-018", "EVAL-019",
             "EVAL-026", "EVAL-027", "EVAL-028", "EVAL-029"],
        )

    def test_sensitive_values_are_always_escalated_by_the_rules(self) -> None:
        for row in self.rows:
            if row.expected.sensitive_data:
                with self.subTest(ticket=row.ticket_id):
                    self.assertTrue(row.analysis.human_escalation_required)


if __name__ == "__main__":
    unittest.main()
