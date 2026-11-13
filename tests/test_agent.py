"""
Tests for the guardrail, the reply draft and human approval. Never call the API.

Standard library only. Run from the repository root:

    python -m unittest discover -s tests -v
"""

from __future__ import annotations

import itertools
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import agent as a  # noqa: E402
import eval_set as e  # noqa: E402
import llm_classifier as c  # noqa: E402
import prototype as p  # noqa: E402


def llm(category: str, priority: str, sensitive: bool = False, ok: bool = True) -> c.LLMClassification:
    if not ok:
        return c.LLMClassification(ticket_id="T", model="m", prompt_version="v1", ok=False, error="invalid JSON")
    return c.LLMClassification(
        ticket_id="T", model="m", prompt_version="v1", ok=True,
        category=category, priority=priority, sensitive_data=sensitive, reason="r",
    )


def ticket(ticket_id: str) -> p.Ticket:
    found = p.find_ticket_by_id(ticket_id, p.SAMPLE_TICKETS)
    assert found is not None
    return found


class RoutingClient:
    """Classification requests (with a schema) get one reply; draft requests (no schema) get another."""

    def __init__(self, classification: str, draft: str = "Please follow the official recovery procedure.") -> None:
        self.classification, self.draft = classification, draft
        self.calls: list[str] = []

    def complete(self, *, model, system, user, schema):
        kind = "classify" if schema is not None else "draft"
        self.calls.append(kind)
        text = self.classification if kind == "classify" else self.draft
        return c.LLMResponse(text=text, input_tokens=100, output_tokens=30, stop_reason="end_turn")


def classification_json(category: str, priority: str, sensitive: bool = False) -> str:
    return json.dumps({"category": category, "priority": priority, "sensitive_data": sensitive, "reason": "r"})


class Guardrail(unittest.TestCase):
    def test_llm_cannot_release_what_the_rules_block(self) -> None:
        """Exhaustive: for every evaluation and sample ticket the rules block, no LLM answer allows automation."""
        tickets = [item.ticket for item in e.load_eval_set()] + list(p.SAMPLE_TICKETS)
        blocked = [p.analyze_ticket(t) for t in tickets if not p.analyze_ticket(t).automation_allowed]
        self.assertGreater(len(blocked), 20)
        answers = [llm(cat, pri, sens) for cat, pri, sens in
                   itertools.product(e.CATEGORIES, e.PRIORITIES, (False, True))] + [llm("", "", ok=False)]
        for rules in blocked:
            for answer in answers:
                decision = a.combine(rules, answer)
                self.assertFalse(decision.automation_allowed, (rules.ticket_id, answer))
                self.assertTrue(decision.human_review)

    def test_agreement_on_low_risk_allows_automation(self) -> None:
        decision = a.combine(p.analyze_ticket(ticket("TCK-002")), llm("Technical Incident", "Medium"))
        self.assertTrue(decision.automation_allowed)
        self.assertFalse(decision.human_review)
        self.assertEqual(decision.disagreements, [])

    def test_more_cautious_llm_wins(self) -> None:
        """Rules allow TCK-002, but the LLM sees a security incident: a person reviews."""
        decision = a.combine(p.analyze_ticket(ticket("TCK-002")), llm("Security Incident", "High"))
        self.assertFalse(decision.automation_allowed)
        self.assertEqual(decision.disagreements, ["category", "priority"])

    def test_any_disagreement_goes_to_a_person(self) -> None:
        rules = p.analyze_ticket(ticket("TCK-002"))  # Technical Incident, Medium, no sensitive data
        cases = {
            "priority": llm("Technical Incident", "Low"),
            "category": llm("Service Request", "Medium"),
            "sensitive_data": llm("Technical Incident", "Medium", sensitive=True),
        }
        for field_name, answer in cases.items():
            with self.subTest(field=field_name):
                decision = a.combine(rules, answer)
                self.assertIn(field_name, decision.disagreements)
                self.assertFalse(decision.automation_allowed)

    def test_invalid_llm_output_goes_to_a_person(self) -> None:
        decision = a.combine(p.analyze_ticket(ticket("TCK-002")), llm("", "", ok=False))
        self.assertFalse(decision.automation_allowed)
        self.assertTrue(any("rejected" in reason for reason in decision.reasons))


class DraftReply(unittest.TestCase):
    def test_no_draft_is_requested_when_automation_is_blocked(self) -> None:
        client = RoutingClient(classification_json("Security Incident", "High"))
        decision = a.triage(ticket("TCK-003"), client)
        draft = a.draft_reply(decision, ticket("TCK-003"), client)
        self.assertEqual(client.calls, ["classify"])
        self.assertFalse(draft.ok)
        self.assertEqual(draft.text, a.HANDOFF_MESSAGE)

    def test_draft_is_requested_when_automation_is_allowed(self) -> None:
        client = RoutingClient(classification_json("Access Support", "Medium"))
        decision = a.triage(ticket("TCK-001"), client)
        draft = a.draft_reply(decision, ticket("TCK-001"), client)
        self.assertEqual(client.calls, ["classify", "draft"])
        self.assertTrue(draft.ok)

    def test_unacceptable_drafts_are_replaced_by_the_handoff_message(self) -> None:
        cases = {
            "action claim (en)": "Done! I have reset your password.",
            "passive action claim": "Your access has been granted.",
            "action claim (pt)": "Pronto, já redefini a sua senha.",
            "sensitive data": "We will contact you at someone@example.com.",
            "empty": "   ",
            "too long": "x" * (a.MAX_REPLY_CHARACTERS + 1),
        }
        for name, text in cases.items():
            with self.subTest(case=name):
                client = RoutingClient(classification_json("Access Support", "Medium"), draft=text)
                decision = a.triage(ticket("TCK-001"), client)
                draft = a.draft_reply(decision, ticket("TCK-001"), client)
                self.assertFalse(draft.ok)
                self.assertEqual(draft.text, a.HANDOFF_MESSAGE)

    def test_guidance_without_action_claims_passes(self) -> None:
        self.assertEqual(a.check_draft("Please use the self-service portal to reset your password."), "")


class HumanApproval(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.log = Path(self.tmp.name) / "agent_audit_log.jsonl"
        self.patch = mock.patch.object(a, "AGENT_AUDIT_LOG_FILE", self.log)
        self.patch.start()

    def tearDown(self) -> None:
        self.patch.stop()
        self.tmp.cleanup()

    def run_ticket(self, ticket_id: str, classification: str, answer: str) -> tuple[a.Outcome, list[str]]:
        asked: list[str] = []

        def ask(prompt: str) -> str:
            asked.append(prompt)
            return answer

        outcome = a.run(ticket(ticket_id), RoutingClient(classification), ask=ask, show=lambda _: None)
        return outcome, asked

    def test_only_an_explicit_yes_sends(self) -> None:
        for answer, status in (("yes", "approved_simulated_send"), ("sim", "approved_simulated_send"),
                               ("", "rejected"), ("no", "rejected"), ("maybe", "rejected")):
            with self.subTest(answer=answer):
                outcome, asked = self.run_ticket("TCK-001", classification_json("Access Support", "Medium"), answer)
                self.assertEqual(outcome.status, status)
                self.assertEqual(len(asked), 1)
                self.assertEqual(outcome.sent_text is not None, status == "approved_simulated_send")

    def test_blocked_ticket_is_handed_off_without_asking(self) -> None:
        outcome, asked = self.run_ticket("TCK-009", classification_json("Security Incident", "High", True), "yes")
        self.assertEqual(outcome.status, "handoff_to_analyst")
        self.assertEqual(asked, [])
        self.assertIsNone(outcome.sent_text)

    def test_audit_log_records_both_decisions_and_is_redacted(self) -> None:
        self.run_ticket("TCK-009", classification_json("Security Incident", "High", True), "yes")
        raw = self.log.read_text(encoding="utf-8")
        self.assertNotIn("Company123", raw)
        entry = json.loads(raw.splitlines()[0])
        self.assertEqual(entry["rules_decision"]["category"], "Security Incident")
        self.assertEqual(entry["llm_decision"]["category"], "Security Incident")
        self.assertTrue(entry["final_decision"]["human_review"])
        self.assertEqual(entry["human_outcome"], "handoff_to_analyst")

    def test_audit_log_redacts_what_the_llm_wrote(self) -> None:
        """The model can repeat a value from the ticket in its reason, or in an answer that gets rejected."""
        cpf = "123.456.789-00"  # disclosed in TCK-005
        answers = {
            "accepted": json.dumps({"category": "Service Request", "priority": "High", "sensitive_data": True,
                                    "reason": f"The requester discloses the CPF {cpf}."}),
            "rejected": classification_json(f"CPF {cpf}", "High", True),
        }
        for name, answer in answers.items():
            with self.subTest(answer=name):
                self.run_ticket("TCK-005", answer, "yes")
                raw = self.log.read_text(encoding="utf-8")
                self.log.unlink()
                self.assertNotIn(cpf, raw)


if __name__ == "__main__":
    unittest.main()
