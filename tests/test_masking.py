"""Nothing sensitive reaches the API client: every request is built from masked text."""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import agent as a  # noqa: E402
import eval_set as e  # noqa: E402
import llm_classifier as c  # noqa: E402
import prototype as p  # noqa: E402
from fakes import classification_json  # noqa: E402

# Values written in the synthetic tickets that must never leave the machine.
KNOWN_VALUES = (
    "Spring2026!",
    "111.222.333-44",
    "4111 1111 1111 1111",
    "(61) 90000-0000",
    "wrong.person@example.org",
    "user.thirty@example.com",
)


def all_tickets() -> list[p.Ticket]:
    return list(p.SAMPLE_TICKETS) + [item.ticket for item in e.load_eval_set()]


def sensitive_values(text: str) -> list[str]:
    """Every value the detection patterns find in the raw text."""
    found = [m.group(0).strip() for pattern, _ in p.PERSONAL_DATA_PATTERNS.values() for m in re.finditer(pattern, text)]
    for m in re.finditer(p.SECRET_DISCLOSURE + r"\s*:?\s*(\S+)", text, flags=re.IGNORECASE):
        found.append(m.group(2))
    for m in re.finditer(r"\b(?:password|senha|token|secret)\s*[:=]\s*(\S+)", text, flags=re.IGNORECASE):
        found.append(m.group(1))
    return found


class Recorder:
    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.requests: list[str] = []

    def complete(self, *, model, system, user, schema):
        self.requests.append(user)
        return c.LLMResponse(text=self.reply, input_tokens=1, output_tokens=1, stop_reason="end_turn")


class NothingSensitiveIsSent(unittest.TestCase):
    def test_no_value_found_by_the_patterns_reaches_the_client(self) -> None:
        checked = 0
        for ticket in all_tickets():
            client = Recorder(classification_json())
            c.classify(ticket, client)
            sent = client.requests[0]
            for value in sensitive_values(f"{ticket.subject} {ticket.description}"):
                self.assertNotIn(value, sent, f"{ticket.ticket_id}: {value!r}")
                checked += 1
        self.assertGreaterEqual(checked, len(KNOWN_VALUES))

    def test_known_values_never_reach_the_client_on_classification_or_draft(self) -> None:
        for ticket in all_tickets():
            raw = f"{ticket.subject} {ticket.description}"
            client = Recorder(classification_json("Access Support", "Medium"))
            decision = a.triage(ticket, client)
            a.draft_reply(decision, ticket, client)
            for request in client.requests:
                for value in KNOWN_VALUES:
                    if value in raw:
                        self.assertNotIn(value, request, ticket.ticket_id)

    def test_the_masked_block_replaces_values_with_placeholders(self) -> None:
        ticket = p.Ticket("T", "Requester", "Contact", "Write to me at someone@example.com, password: hunter2")
        block = c.masked_ticket_block(ticket)
        self.assertNotIn("someone@example.com", block)
        self.assertNotIn("hunter2", block)
        self.assertIn("[REDACTED_EMAIL]", block)
        self.assertIn("[REDACTED_SECRET]", block)

    def test_the_rules_still_read_the_raw_text(self) -> None:
        ticket = p.Ticket("T", "Requester", "Reembolso", "Meu CPF é 111.222.333-44")
        analysis = p.analyze_ticket(ticket)
        self.assertTrue(analysis.sensitive_data_detected)
        self.assertIn("cpf", analysis.sensitive_data_types)

    def test_both_prompts_explain_the_placeholders(self) -> None:
        for version in ("v1", "v2"):
            prompt = c.load_prompt(version)
            self.assertIn("[REDACTED_SECRET]", prompt, version)
            self.assertIn("set sensitive_data to true", prompt, version)


if __name__ == "__main__":
    unittest.main()
