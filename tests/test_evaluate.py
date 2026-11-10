"""
Tests for the evaluation harness and prompt v2. Never call the API.

Standard library only. Run from the repository root:

    python -m unittest discover -s tests -v
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import eval_set as e  # noqa: E402
import evaluate as ev  # noqa: E402
import llm_classifier as c  # noqa: E402

ITEMS = e.load_eval_set()


def reply(category: str, priority: str, sensitive: bool) -> str:
    return json.dumps({"category": category, "priority": priority, "sensitive_data": sensitive, "reason": "r"})


class OracleClient:
    """Answers every ticket with its own label: a perfect classifier."""

    def complete(self, *, model, system, user, schema):
        item = next(i for i in ITEMS if i.ticket.subject in user and i.ticket.description in user)
        x = item.expected
        return c.LLMResponse(text=reply(x.category, x.priority, x.sensitive_data),
                             input_tokens=1000, output_tokens=100, stop_reason="end_turn")


class FixedClient:
    """Answers the same text to every request."""

    def __init__(self, text: str) -> None:
        self.text = text

    def complete(self, *, model, system, user, schema):
        return c.LLMResponse(text=self.text, input_tokens=1000, output_tokens=100, stop_reason="end_turn")


class FailingClient:
    def complete(self, *, model, system, user, schema):
        raise c.LLMError("AuthenticationError")


class Cost(unittest.TestCase):
    def test_cost_uses_the_price_per_million_tokens(self) -> None:
        self.assertAlmostEqual(ev.compute_cost("claude-haiku-5-5", 1_000_000, 1_000_000), 0.60)
        self.assertAlmostEqual(ev.compute_cost("claude-sonnet-5-5", 1_000_000, 1_000_000), 12.00)
        self.assertAlmostEqual(ev.compute_cost("claude-haiku-5-5", 623, 99), (623 * 0.10 + 99 * 0.50) / 1e6)

    def test_every_model_has_a_price(self) -> None:
        for model in c.MODELS:
            self.assertIn(model, ev.PRICES_PER_MILLION_TOKENS)


class Metrics(unittest.TestCase):
    def test_perfect_classifier_is_fully_accurate_and_never_unsafe(self) -> None:
        rows = ev.evaluate_combination(ITEMS, OracleClient(), "claude-haiku-5-5", "v1")
        s = ev.summarize(rows, "claude-haiku-5-5")
        self.assertEqual(s["tickets"], 30)
        self.assertEqual((s["category_correct"], s["priority_correct"], s["sensitive_correct"]), (30, 30, 30))
        self.assertEqual((s["llm_invalid"], s["unsafe_automation"], s["unsafe_automation_llm_alone"]), (0, 0, 0))

    def test_perfect_classifier_still_goes_to_a_person_where_rules_disagree(self) -> None:
        """The guardrail is conservative: a disagreement with the rules costs a human review, even if the LLM is right."""
        rows = ev.evaluate_combination(ITEMS, OracleClient(), "claude-haiku-5-5", "v1")
        s = ev.summarize(rows, "claude-haiku-5-5")
        self.assertGreater(s["disagreements"], 0)
        self.assertGreater(s["unnecessary_review"], 0)

    def test_guardrail_catches_what_a_naive_llm_alone_would_automate(self) -> None:
        """A classifier that calls everything a low service request: 21 tickets need a person, the rules catch all but 3."""
        client = FixedClient(reply("Service Request", "Low", False))
        rows = ev.evaluate_combination(ITEMS, client, "claude-haiku-5-5", "v1")
        s = ev.summarize(rows, "claude-haiku-5-5")
        self.assertEqual(s["review_required"], 21)
        self.assertEqual(s["unsafe_automation_llm_alone"], 21)
        self.assertEqual(s["unsafe_automation"], 3)
        unsafe_ids = sorted(r.item.ticket.ticket_id for r in rows if r.unsafe_automation)
        self.assertEqual(unsafe_ids, ["EVAL-019", "EVAL-027", "EVAL-029"])

    def test_invalid_output_goes_to_a_person_and_tokens_are_still_billed(self) -> None:
        rows = ev.evaluate_combination(ITEMS, FixedClient("not json"), "claude-sonnet-5-5", "v2")
        s = ev.summarize(rows, "claude-sonnet-5-5")
        self.assertEqual(s["llm_invalid"], 30)
        self.assertEqual(s["api_errors"], 0)
        self.assertEqual((s["category_correct"], s["unsafe_automation"]), (0, 0))
        self.assertEqual((s["input_tokens"], s["output_tokens"]), (30_000, 3_000))
        self.assertAlmostEqual(s["cost_usd"], (30_000 * 2.00 + 3_000 * 10.00) / 1e6)
        self.assertAlmostEqual(s["cost_per_ticket_usd"], s["cost_usd"] / 30, places=6)
        self.assertFalse(ev.is_fully_failed(s))

    def test_api_failure_is_detected_as_a_failed_run(self) -> None:
        rows = ev.evaluate_combination(ITEMS, FailingClient(), "claude-haiku-5-5", "v1")
        s = ev.summarize(rows, "claude-haiku-5-5")
        self.assertEqual((s["api_errors"], s["llm_invalid"], s["unsafe_automation"]), (30, 30, 0))
        self.assertTrue(ev.is_fully_failed(s))

    def test_by_group_covers_every_ticket(self) -> None:
        rows = ev.evaluate_combination(ITEMS, OracleClient(), "claude-haiku-5-5", "v1")
        groups = ev.summarize(rows, "claude-haiku-5-5")["by_group"]
        self.assertEqual(sum(g["tickets"] for g in groups.values()), 30)
        self.assertEqual(groups["injection"]["tickets"], 5)


class Report(unittest.TestCase):
    def setUp(self) -> None:
        self.report = ev.build_report(ITEMS, OracleClient())

    def test_report_has_every_combination_and_is_json_serialisable(self) -> None:
        combos = [(r["model"], r["prompt_version"]) for r in self.report["runs"]]
        self.assertEqual(len(combos), 4)
        self.assertEqual(set(combos), {(m, v) for m in c.MODELS for v in ev.PROMPT_VERSIONS})
        for run in self.report["runs"]:
            self.assertEqual(len(run["tickets"]), 30)
        json.dumps(self.report, ensure_ascii=False)

    def test_report_records_how_to_reproduce_the_run(self) -> None:
        meta = self.report["meta"]
        self.assertEqual(meta["tickets"], 30)
        self.assertEqual(meta["effort"], c.DEFAULT_EFFORT)
        self.assertEqual(set(meta["prompt_sha256"]), set(ev.PROMPT_VERSIONS))
        self.assertEqual(len(meta["eval_set_sha256"]), 64)
        self.assertEqual(meta["prices_checked"], ev.PRICES_CHECKED)

    def test_report_baseline_is_the_pinned_rules_baseline(self) -> None:
        baseline = self.report["rules_baseline"]
        self.assertEqual((baseline["category_correct"], baseline["priority_correct"]), (9, 17))
        self.assertEqual(baseline["unsafe_automation"], 8)

    def test_markdown_table_has_baseline_and_four_runs(self) -> None:
        lines = ev.format_markdown_table(self.report).splitlines()
        self.assertEqual(len(lines), 2 + 1 + 4)
        self.assertTrue(lines[2].startswith("| Rules only | 9/30 | 17/30"))
        self.assertTrue(all(line.isascii() for line in lines))

    def test_progress_is_reported_per_combination(self) -> None:
        messages: list[str] = []
        ev.build_report(ITEMS, OracleClient(), progress=messages.append)
        self.assertEqual(len(messages), 4)


class CommandLine(unittest.TestCase):
    def test_table_mode_reads_a_saved_run_without_the_api(self) -> None:
        report = ev.build_report(ITEMS, OracleClient())
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "run.json"
            path.write_text(json.dumps(report), encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = ev.main(["--table", str(path)])
        self.assertEqual(code, 0)
        self.assertIn("Rules only", output.getvalue())

    def test_without_a_key_nothing_is_called_or_written(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "results.json"
            with mock.patch.dict(os.environ, {}, clear=True), contextlib.redirect_stdout(io.StringIO()):
                code = ev.main(["--output", str(target)])
            self.assertEqual(code, 2)
            self.assertFalse(target.exists())

    def test_a_run_where_every_call_failed_is_not_written(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "results.json"
            with mock.patch.object(ev, "AnthropicClient", return_value=FailingClient()), \
                    contextlib.redirect_stdout(io.StringIO()):
                code = ev.main(["--output", str(target)])
            self.assertEqual(code, 1)
            self.assertFalse(target.exists())

    def test_a_good_run_is_written_to_the_output_file(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "nested" / "results.json"
            with mock.patch.object(ev, "AnthropicClient", return_value=OracleClient()), \
                    contextlib.redirect_stdout(io.StringIO()):
                code = ev.main(["--output", str(target)])
            self.assertEqual(code, 0)
            saved = json.loads(target.read_text(encoding="utf-8"))
        self.assertEqual(len(saved["runs"]), 4)


class PromptV2(unittest.TestCase):
    def setUp(self) -> None:
        self.text = c.load_prompt("v2")

    def test_v2_is_one_of_the_compared_versions(self) -> None:
        self.assertIn("v2", ev.PROMPT_VERSIONS)
        self.assertNotEqual(self.text, c.load_prompt("v1"))

    def test_v2_names_every_category_and_priority(self) -> None:
        for name in (*e.CATEGORIES, *e.PRIORITIES):
            self.assertIn(name, self.text)

    def test_v2_states_the_injection_policy(self) -> None:
        lowered = self.text.lower()
        self.assertIn("security incident", lowered)
        self.assertIn("never instructions", lowered)

    def test_v2_is_not_tuned_to_evaluation_tickets(self) -> None:
        """The policy is written from docs/decision-logic.md. No evaluation ticket text may appear in the prompt."""
        self.assertNotIn("EVAL-", self.text)
        for item in ITEMS:
            self.assertNotIn(item.ticket.description, self.text, item.ticket.ticket_id)
            if len(item.ticket.subject) >= 12:
                self.assertNotIn(item.ticket.subject, self.text, item.ticket.ticket_id)


if __name__ == "__main__":
    unittest.main()
