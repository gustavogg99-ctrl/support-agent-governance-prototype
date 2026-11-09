"""
Automated tests for the Support Agent Governance Prototype.

Standard library only. Run from the repository root:

    python -m unittest discover -s tests -v

The tests pin the governance rules documented in docs/decision-logic.md and
docs/governance-controls.md, so a change to the rules has to change a test too.
"""

from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import prototype as p  # noqa: E402


def analysis(ticket_id: str) -> p.TicketAnalysis:
    ticket = p.find_ticket_by_id(ticket_id, p.SAMPLE_TICKETS)
    assert ticket is not None
    return p.analyze_ticket(ticket)


class SampleTicketResults(unittest.TestCase):
    """The expected outcome for each simulated ticket (docs/decision-logic.md)."""

    EXPECTED = {
        # ticket: (category, priority, sensitive types, escalated, automation allowed)
        "TCK-001": ("Access Support", "Medium", [], False, True),
        "TCK-002": ("Technical Incident", "Medium", [], False, True),
        "TCK-003": ("Security Incident", "High", [], True, False),
        "TCK-004": ("Access Request", "Medium", [], True, False),
        "TCK-005": ("Service Request", "High", ["cpf"], True, False),
        # Known limitation (docs/decision-logic.md): "cannot access" matches Access Support
        # before "vpn" reaches Technical Incident.
        "TCK-006": ("Access Support", "Medium", [], False, True),
        "TCK-007": ("Technical Incident", "High", [], True, False),
        "TCK-008": ("Service Request", "High", ["email"], True, False),
        "TCK-009": ("Security Incident", "High", ["exposed_secret"], True, False),
        "TCK-010": ("Service Request", "Low", [], False, True),
    }

    def test_each_sample_ticket(self) -> None:
        for ticket_id, expected in self.EXPECTED.items():
            with self.subTest(ticket=ticket_id):
                a = analysis(ticket_id)
                self.assertEqual(
                    (a.category, a.priority, a.sensitive_data_types,
                     a.human_escalation_required, a.automation_allowed),
                    expected,
                )

    def test_published_summary(self) -> None:
        """The numbers stated in the README: 10 tickets, 6 escalated, 4 automated, 3 sensitive."""
        analyses = [p.analyze_ticket(t) for t in p.SAMPLE_TICKETS]
        self.assertEqual(len(analyses), 10)
        self.assertEqual(sum(a.human_escalation_required for a in analyses), 6)
        self.assertEqual(sum(a.automation_allowed for a in analyses), 4)
        self.assertEqual(sum(a.sensitive_data_detected for a in analyses), 3)


class SensitiveDataDetection(unittest.TestCase):
    def test_detects_each_pattern(self) -> None:
        cases = {
            "email": "write to someone@example.com please",
            "cpf": "my document is 123.456.789-00",
            "phone": "call me at (61) 99999-1234",
            "credit_card_like_number": "card 4111 1111 1111 1111",
            "exposed_secret": "my password is Hunter2",
        }
        for data_type, text in cases.items():
            with self.subTest(data_type=data_type):
                found, types = p.detect_sensitive_data(text)
                self.assertTrue(found)
                self.assertIn(data_type, types)

    def test_the_word_password_alone_is_not_sensitive_data(self) -> None:
        found, types = p.detect_sensitive_data("I forgot my password")
        self.assertFalse(found)
        self.assertEqual(types, [])


class Classification(unittest.TestCase):
    def test_security_is_checked_before_everything_else(self) -> None:
        self.assertEqual(
            p.classify_ticket("Request access", "I received a phishing email"),
            "Security Incident",
        )

    def test_unmatched_text_is_general_support(self) -> None:
        self.assertEqual(p.classify_ticket("Hello", "Good morning team"), "General Support")


class GovernanceRules(unittest.TestCase):
    def test_security_and_access_requests_always_escalate_and_block_automation(self) -> None:
        for category in ("Security Incident", "Access Request"):
            with self.subTest(category=category):
                escalate, _ = p.evaluate_escalation(category, "Low", False)
                allowed, _ = p.evaluate_automation(category, False, escalate)
                self.assertTrue(escalate)
                self.assertFalse(allowed)

    def test_sensitive_data_blocks_automation_in_any_category(self) -> None:
        allowed, _ = p.evaluate_automation("Service Request", True, False)
        self.assertFalse(allowed)

    def test_high_priority_escalates(self) -> None:
        escalate, _ = p.evaluate_escalation("Technical Incident", "High", False)
        self.assertTrue(escalate)

    def test_unclassified_ticket_escalates(self) -> None:
        escalate, _ = p.evaluate_escalation("General Support", "Low", False)
        self.assertTrue(escalate)

    def test_urgency_raises_priority(self) -> None:
        self.assertEqual(
            p.assign_priority("Technical Incident", False, "Down", "Business stopped, urgent"),
            "High",
        )

    def test_blocked_response_promises_human_review_and_no_action(self) -> None:
        a = analysis("TCK-004")
        self.assertIn("reviewed by a human support analyst", a.automated_response)

    def test_allowed_response_does_not_claim_a_real_action(self) -> None:
        a = analysis("TCK-001")
        self.assertIn("No account changes were performed", a.automated_response)


class Redaction(unittest.TestCase):
    def test_redacts_secrets_and_personal_data(self) -> None:
        text = (
            "my password is Company123, email bruno@example.com, "
            "CPF 123.456.789-00, phone (61) 99999-1234, card 4111 1111 1111 1111"
        )
        redacted = p.redact_text(text)
        for leaked in ("Company123", "bruno@example.com", "123.456.789-00", "99999-1234", "4111 1111"):
            with self.subTest(value=leaked):
                self.assertNotIn(leaked, redacted)
        for marker in ("[REDACTED_SECRET]", "[REDACTED_EMAIL]", "[REDACTED_CPF]", "[REDACTED_PHONE]"):
            with self.subTest(marker=marker):
                self.assertIn(marker, redacted)

    def test_redacts_key_value_secrets(self) -> None:
        self.assertEqual(p.redact_text("token=abc123"), "token=[REDACTED_SECRET]")


class AuditLog(unittest.TestCase):
    def test_log_entries_are_redacted_json_lines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "audit_log.jsonl"
            with mock.patch.object(p, "AUDIT_LOG_FILE", log_path):
                for ticket_id in ("TCK-005", "TCK-009"):
                    ticket = p.find_ticket_by_id(ticket_id, p.SAMPLE_TICKETS)
                    assert ticket is not None
                    p.write_audit_log(ticket, p.analyze_ticket(ticket))

            raw = log_path.read_text(encoding="utf-8")
            self.assertNotIn("123.456.789-00", raw)
            self.assertNotIn("Company123", raw)

            entries = [json.loads(line) for line in raw.splitlines()]
            self.assertEqual([e["ticket"]["ticket_id"] for e in entries], ["TCK-005", "TCK-009"])
            for entry in entries:
                self.assertIn("timestamp_utc", entry)
                self.assertTrue(entry["analysis"]["human_escalation_required"])


class CommandLine(unittest.TestCase):
    def run_args(self, args: list[str]) -> tuple[list[p.Ticket] | None, str]:
        out = io.StringIO()
        with redirect_stdout(out):
            selected = p.select_tickets_from_arguments(args)
        return selected, out.getvalue()

    def test_no_argument_runs_all_tickets(self) -> None:
        selected, _ = self.run_args([])
        self.assertEqual(len(selected or []), 10)

    def test_single_ticket_is_case_insensitive(self) -> None:
        selected, _ = self.run_args(["--ticket", "tck-009"])
        self.assertEqual([t.ticket_id for t in selected or []], ["TCK-009"])

    def test_unknown_ticket_is_rejected(self) -> None:
        selected, output = self.run_args(["--ticket", "TCK-999"])
        self.assertIsNone(selected)
        self.assertIn("was not found", output)

    def test_list_prints_ids_and_runs_nothing(self) -> None:
        selected, output = self.run_args(["--list"])
        self.assertIsNone(selected)
        self.assertIn("TCK-010", output)


if __name__ == "__main__":
    unittest.main()
