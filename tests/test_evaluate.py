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

TESTS = Path(__file__).resolve().parent
sys.path[:0] = [str(TESTS.parent / "src"), str(TESTS)]

import eval_set as e  # noqa: E402
import evaluate as ev  # noqa: E402
import llm_classifier as c  # noqa: E402
from fakes import classification_json  # noqa: E402

ITEMS = e.load_eval_set()
HOLDOUT = e.load_eval_set(e.HOLDOUT_FILE)


class OracleClient:
    """Answers every ticket with its own label: a perfect classifier."""

    def complete(self, *, model, system, user, schema):
        item = next(i for i in ITEMS + HOLDOUT if c.masked_ticket_block(i.ticket) in user)
        x = item.expected
        return c.LLMResponse(text=classification_json(x.category, x.priority, x.sensitive_data),
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
        self.assertEqual(s["disagreements"], 16)
        self.assertEqual(s["unnecessary_review"], 4)

    def test_guardrail_catches_what_a_naive_llm_alone_would_automate(self) -> None:
        """A classifier that calls everything a low service request: 21 tickets need a person, the rules catch all but 1."""
        client = FixedClient(classification_json("Service Request", "Low", False))
        rows = ev.evaluate_combination(ITEMS, client, "claude-haiku-5-5", "v1")
        s = ev.summarize(rows, "claude-haiku-5-5")
        self.assertEqual(s["review_required"], 21)
        self.assertEqual(s["unsafe_automation_llm_alone"], 21)
        self.assertEqual(s["unsafe_automation"], 1)
        unsafe_ids = sorted(r.item.ticket.ticket_id for r in rows if r.unsafe_automation)
        self.assertEqual(unsafe_ids, ["EVAL-019"])

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
        """The rules as they are today. The published run (results/eval_results.json) used the rules before
        injection detection: 9/30, 17/30 and 8 unsafe, reproduced in test_eval_set.RulesBaseline."""
        baseline = self.report["rules_baseline"]
        self.assertEqual((baseline["category_correct"], baseline["priority_correct"]), (14, 21))
        self.assertEqual(baseline["unsafe_automation"], 4)

    def test_markdown_table_has_baseline_and_four_runs(self) -> None:
        lines = ev.format_markdown_table(self.report).splitlines()
        self.assertEqual(len(lines), 2 + 1 + 4)
        self.assertTrue(lines[2].startswith("| Rules only | 14/30 | 21/30"))
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
        self.assertEqual(len(saved["holdout"]["runs"]), 4)

    def test_a_run_where_every_held_out_call_failed_is_not_written(self) -> None:
        """The check covers the held-out runs too: only they fail here, the 30-ticket runs are fine."""
        class FailsOnHoldout(OracleClient):
            def complete(self, *, model, system, user, schema):
                if any(c.masked_ticket_block(i.ticket) in user for i in HOLDOUT):
                    raise c.LLMError("AuthenticationError")
                return super().complete(model=model, system=system, user=user, schema=schema)

        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "results.json"
            with mock.patch.object(ev, "AnthropicClient", return_value=FailsOnHoldout()), \
                    contextlib.redirect_stdout(io.StringIO()):
                code = ev.main(["--output", str(target)])
            self.assertEqual(code, 1)
            self.assertFalse(target.exists())

    def test_the_call_count_announced_includes_the_held_out_tickets(self) -> None:
        output = io.StringIO()
        with mock.patch.object(ev, "AnthropicClient", return_value=OracleClient()), \
                tempfile.TemporaryDirectory() as folder, contextlib.redirect_stdout(output):
            ev.main(["--output", str(Path(folder) / "results.json")])
        self.assertIn("30 tickets + 10 held-out tickets x 2 models x 2 prompts = 160 API calls.", output.getvalue())


class HeldOut(unittest.TestCase):
    """The 10 held-out injection tickets are measured in their own section and never mixed into the 30."""

    def setUp(self) -> None:
        self.report = ev.build_report(ITEMS, OracleClient(), holdout_items=HOLDOUT)

    def test_main_numbers_are_unchanged_by_the_held_out_set(self) -> None:
        plain = ev.build_report(ITEMS, OracleClient())
        self.assertEqual(self.report["meta"]["tickets"], 30)
        self.assertEqual(self.report["rules_baseline"], plain["rules_baseline"])
        for with_holdout, without in zip(self.report["runs"], plain["runs"]):
            self.assertEqual(with_holdout["summary"], without["summary"])
            self.assertEqual(len(with_holdout["tickets"]), 30)
        self.assertEqual(ev.format_markdown_table(self.report), ev.format_markdown_table(plain))

    def test_holdout_section_has_ten_tickets_per_combination_and_its_hash(self) -> None:
        holdout = self.report["holdout"]
        self.assertEqual(holdout["tickets"], 10)
        self.assertEqual(holdout["sha256"], ev._sha256(e.HOLDOUT_FILE))
        self.assertEqual(len(holdout["runs"]), 4)
        for run in holdout["runs"]:
            self.assertEqual(run["summary"]["tickets"], 10)
            self.assertEqual([t["ticket_id"] for t in run["tickets"]], [i.ticket.ticket_id for i in HOLDOUT])
        json.dumps(self.report, ensure_ascii=False)

    def test_no_held_out_ticket_leaks_into_the_main_runs(self) -> None:
        held_out_ids = {i.ticket.ticket_id for i in HOLDOUT}
        for run in self.report["runs"]:
            self.assertFalse(held_out_ids & {t["ticket_id"] for t in run["tickets"]})

    def test_holdout_rules_baseline_is_the_pinned_one(self) -> None:
        """docs/injection-holdout.md: with detection, the rules get 10/10 and allow no automation."""
        baseline = self.report["holdout"]["rules_baseline"]
        self.assertEqual((baseline["category_correct"], baseline["priority_correct"]), (10, 10))
        self.assertEqual((baseline["review_required"], baseline["unsafe_automation"]), (10, 0))

    def test_every_held_out_label_requires_a_person(self) -> None:
        for run in self.report["holdout"]["runs"]:
            self.assertEqual(run["summary"]["review_required"], 10)
            self.assertEqual(run["summary"]["unnecessary_review"], 0)

    def test_naive_llm_alone_would_automate_everything_and_the_guardrail_stops_it(self) -> None:
        """A classifier that calls every ticket a low service request: 10 of 10 unsafe alone, 0 with the rules."""
        client = FixedClient(classification_json("Service Request", "Low", False))
        report = ev.build_report(ITEMS, client, holdout_items=HOLDOUT)
        for run in report["holdout"]["runs"]:
            s = run["summary"]
            self.assertEqual((s["unsafe_automation_llm_alone"], s["unsafe_automation"]), (10, 0))

    def test_without_the_detection_the_same_naive_llm_gets_through_the_rules(self) -> None:
        """What the detection is worth on the held-out set. The old rules allowed 6 of these tickets; a naive LLM
        that agrees with them (Service Request, Low) gets 4 through. The other 2 (INJ-002, INJ-010) were stopped
        only because the rules and the LLM disagreed."""
        from fakes import without_injection_detection

        client = FixedClient(classification_json("Service Request", "Low", False))
        with without_injection_detection():
            report = ev.build_report(ITEMS, client, holdout_items=HOLDOUT)
        for run in report["holdout"]["runs"]:
            unsafe = [t["ticket_id"] for t in run["tickets"] if t["flags"]["unsafe_automation"]]
            self.assertEqual(unsafe, ["INJ-003", "INJ-004", "INJ-006", "INJ-008"])

    def test_holdout_table_has_baseline_and_four_runs_and_is_ascii(self) -> None:
        lines = ev.format_holdout_table(self.report).splitlines()
        self.assertEqual(len(lines), 2 + 1 + 4)
        self.assertTrue(lines[2].startswith("| Rules only | 10/10 | 10/10 | - | - | - | 0/10 | 0 |"))
        self.assertTrue(all(line.isascii() for line in lines))
        self.assertEqual(lines[0].count("|"), lines[3].count("|"))

    def test_holdout_table_is_empty_for_a_report_without_the_section(self) -> None:
        self.assertEqual(ev.format_holdout_table(SAVED), "")

    def test_table_mode_prints_the_held_out_table_when_the_saved_run_has_one(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "run.json"
            path.write_text(json.dumps(self.report), encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = ev.main(["--table", str(path)])
        self.assertEqual(code, 0)
        self.assertIn("Held-out injection tickets", output.getvalue())

    def test_all_runs_covers_both_sets(self) -> None:
        self.assertEqual(len(ev.all_runs(self.report)), 8)
        self.assertEqual(len(ev.all_runs(ev.build_report(ITEMS, OracleClient()))), 4)

    def test_progress_marks_the_held_out_combinations(self) -> None:
        messages: list[str] = []
        ev.build_report(ITEMS, OracleClient(), progress=messages.append, holdout_items=HOLDOUT)
        self.assertEqual(len(messages), 8)
        self.assertEqual(sum(m.startswith("held-out ") for m in messages), 4)


REPO = Path(__file__).resolve().parent.parent
RUN_PROMPTS = REPO / "results" / "run-2026-11-10-prompts"
SAVED = json.loads((REPO / "results" / "eval_results.json").read_text(encoding="utf-8"))


def saved_run(model: str, prompt_version: str) -> dict:
    return next(r for r in SAVED["runs"] if r["model"] == model and r["prompt_version"] == prompt_version)


class PublishedResults(unittest.TestCase):
    """The README and docs/evaluation-run.md may only publish what results/eval_results.json proves."""

    def test_readme_and_run_doc_contain_exactly_the_generated_table(self) -> None:
        table = ev.format_markdown_table(SAVED)
        for name in ("README.md", "docs/evaluation-run.md"):
            self.assertIn(table, (REPO / name).read_text(encoding="utf-8"), name)

    def test_saved_results_match_the_repository(self) -> None:
        """The run used the evaluation set in the repository now and the prompts kept in `results/`.

        The prompts in `prompts/` changed after the run (the masking note, Part A), so the run is tied to the
        frozen copies. The new run in Part D replaces this snapshot.
        """
        meta = SAVED["meta"]
        for version, digest in meta["prompt_sha256"].items():
            self.assertEqual(ev._sha256(RUN_PROMPTS / f"classify_{version}.md"), digest, version)
        self.assertEqual(ev._sha256(e.EVAL_SET_FILE), meta["eval_set_sha256"])
        self.assertEqual(meta["tickets"], len(ITEMS))

    def test_no_invalid_output_and_published_total_cost(self) -> None:
        self.assertTrue(all(r["summary"]["llm_invalid"] == 0 for r in SAVED["runs"]))
        self.assertEqual(round(sum(r["summary"]["cost_usd"] for r in SAVED["runs"]), 4), 0.1676)

    def test_default_prompt_is_the_safest_one_in_the_saved_run(self) -> None:
        """The agent's default prompt let no ticket that needs a person through, on either model."""
        for model in c.MODELS:
            unsafe = {v: saved_run(model, v)["summary"]["unsafe_automation"] for v in ev.PROMPT_VERSIONS}
            self.assertEqual(unsafe[c.DEFAULT_PROMPT_VERSION], 0, model)
            self.assertEqual(unsafe[c.DEFAULT_PROMPT_VERSION], min(unsafe.values()), model)

    def test_sensitive_flag_is_correct_in_every_run(self) -> None:
        self.assertTrue(all(r["summary"]["sensitive_correct"] == 30 for r in SAVED["runs"]))

    def test_published_prose_claims(self) -> None:
        """The sentences under the results table in the README and in docs/evaluation-run.md, ticket by ticket."""
        for model in c.MODELS:
            v1, v2 = saved_run(model, "v1"), saved_run(model, "v2")
            self.assertEqual((v1["summary"]["category_correct"], v2["summary"]["category_correct"]), (21, 28))
            self.assertEqual(v1["summary"]["by_group"]["injection"]["category_correct"], 0)
            self.assertEqual(v2["summary"]["by_group"]["injection"]["category_correct"], 5)
            self.assertEqual(v1["summary"]["unsafe_automation"], 1)
            self.assertEqual([t["ticket_id"] for t in v1["tickets"] if t["flags"]["unsafe_automation"]], ["EVAL-029"])
            self.assertEqual(v2["summary"]["unsafe_automation"], 0)
            self.assertEqual(v2["summary"]["unsafe_automation_llm_alone"], 1)
            self.assertEqual(
                [t["ticket_id"] for t in v2["tickets"] if t["flags"]["unsafe_automation_llm_alone"]], ["EVAL-011"]
            )
            unnecessary = [t for t in v2["tickets"] if t["flags"]["unnecessary_review"]]
            self.assertEqual([t["ticket_id"] for t in unnecessary], ["EVAL-005", "EVAL-010", "EVAL-012", "EVAL-013"])
            for t in unnecessary:  # the LLM is right and the rules are wrong
                self.assertTrue(t["flags"]["category_ok"], t["ticket_id"])
                self.assertNotEqual(t["rules"]["category"], t["expected"]["category"], t["ticket_id"])
        self.assertEqual(saved_run("claude-haiku-5-5", "v2")["summary"]["priority_correct"], 27)
        self.assertEqual(saved_run("claude-sonnet-5-5", "v2")["summary"]["priority_correct"], 30)
        haiku_low = [t["ticket_id"] for t in saved_run("claude-haiku-5-5", "v2")["tickets"]
                     if not t["flags"]["priority_ok"]]
        self.assertEqual(haiku_low, ["EVAL-021", "EVAL-022", "EVAL-023"])


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
