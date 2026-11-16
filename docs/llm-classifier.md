# LLM Classifier

`src/llm_classifier.py` asks Claude (Anthropic API) to classify a ticket.

## What the LLM decides, and what it does not

The LLM proposes three fields: **category**, **priority** and **sensitive_data**, plus a one-sentence reason.

It does **not** decide escalation or automation. Those stay with the deterministic rules in `src/prototype.py`, which act as the guardrail (`docs/guardrail.md`): the LLM can make a decision more cautious, never less.

## Flow

```text
Ticket
↓
Prompt (prompts/classify_<version>.md) + ticket wrapped in <ticket> tags as data
↓
Claude API with structured outputs (JSON schema with closed enums)
↓
Local validation (parse_output): JSON object, exact keys, known category and priority, boolean flag
↓
ok=True  → classification goes to the guardrail
ok=False → the ticket goes to a person, and the failure is counted in the evaluation
```

## Design decisions

| Decision | Why |
|---|---|
| The prompt is a versioned file | A prompt change is a reviewable diff, and the evaluation compares versions by name. |
| Structured outputs **and** local validation | The schema request reduces malformed output; the local check is what the system relies on. Values are matched case-insensitively, so a difference in casing alone does not send a ticket to a person. |
| Any failure returns `ok=False`, never an exception or a guess | Invalid JSON, unknown values, a refusal, truncation (`max_tokens`) and API errors all mean "a person decides". Tokens are still counted, because they are still billed. |
| The ticket text goes inside `<ticket>` tags, labelled as data | A basic separation between instructions and user content. It is **not** a full prompt-injection defence, which is not implemented. The guardrail is what limits the damage if the model is manipulated. |
| The requester's name is not sent | It is not needed to triage. Masking of other personal data before the call is not implemented. |
| The SDK sits behind `LLMClient` and is imported only by `AnthropicClient` | The tests and the rest of the project run on the standard library with no key, network or cost. Tests use a scripted client. |
| Effort `low` by default | Classification is a routing task, and the same effort for every model keeps the comparison fair. |

## Prompt versions

- `v1`: minimal: lists the categories and priorities and defines sensitive data. It deliberately does not explain the categories. It is the starting point for the evaluation.
- `v2`: adds the written policy from `docs/decision-logic.md`. It is derived from the documented policy, never from individual evaluation tickets (a test enforces this). The comparison of `v1` and `v2` is in `docs/evaluation-run.md`.

## Running it against the real API

This step is optional and costs a fraction of a cent per ticket. Run it on your own machine, with the key set only in that terminal:

```powershell
pip install -r requirements-llm.txt
$env:ANTHROPIC_API_KEY = "<your key>"
py src/llm_classifier.py --ticket EVAL-026 --model claude-haiku-5-5
```

The command prints the model's classification next to the expected label.

## Models

`claude-haiku-5-5` and `claude-sonnet-5-5` (IDs from the Anthropic models overview, checked on 2026-11-10).
