# Architecture

Five Python modules, run from the command line. The rules, the tests and the results table need the standard library only; the `anthropic` SDK is loaded only by the real API client.

## Modules

| Module | Responsibility |
|---|---|
| `src/prototype.py` | The deterministic rules: sensitive-data detection, classification, priority, escalation, automation. Also the 10 sample tickets, the fixed response templates, redaction and the rules-only audit log. |
| `src/llm_classifier.py` | Asks the LLM for category, priority and a sensitive-data flag, and validates the JSON locally. Any failure returns `ok=False`. The SDK sits behind the `LLMClient` interface. |
| `src/agent.py` | The guardrail `combine()`, the reply draft and its checks, human approval, and the agent audit log. |
| `src/eval_set.py` | Loads and validates `data/eval_tickets.jsonl` and computes the rules-only baseline. |
| `src/evaluate.py` | Runs every prompt version and model through the guardrail, summarises the metrics and prints the results table. |

`prototype.py` imports nothing from the other modules. `agent.py` depends on the rules and on the classifier, never the other way round, so the rules can be tested and reasoned about alone.

## Flow of one ticket through the agent

```text
Ticket
├─ rules (src/prototype.py)       → category, priority, sensitive data, escalation, automation
└─ LLM (src/llm_classifier.py)    → category, priority, sensitive data, or ok=False
        ↓
combine()                         → human review? automation allowed? reasons
        ↓
review needed ── yes → fixed handoff message; no draft and no approval prompt
        │
        no
        ↓
LLM drafts a reply → check_draft() → a person approves → simulated send
        ↓
agent_audit_log.jsonl
```

The rules pipeline inside `prototype.py` is described step by step in `docs/decision-logic.md`, and the guardrail in `docs/guardrail.md`.

## Where the controls sit

| Control | Module | How it is enforced |
|---|---|---|
| Security is classified first | `prototype.py` | Security keywords are checked before every other category |
| Sensitive data raises priority and blocks automation | `prototype.py` | `detect_sensitive_data()` runs before the other rules |
| Uncertain tickets go to a person | `prototype.py` | A ticket that matches no keyword is General Support, which always escalates |
| The LLM cannot release what the rules block | `agent.py` | `combine()` allows automation only when the rules allow it and nothing else asks for review |
| An invalid LLM answer is never guessed at | `llm_classifier.py` | `parse_output()` rejects it and `classify()` returns `ok=False` |
| No draft for a risky ticket | `agent.py` | `draft_reply()` returns the handoff message unless automation is allowed |
| Nothing is sent without approval | `agent.py` | `request_approval()` treats anything but an explicit yes as a rejection |
| Logs are redacted | `prototype.py`, `agent.py` | `redact_text()` runs on ticket text before it is written |

`docs/governance-controls.md` lists each control with the test that pins it.

## Data handling

- **Input:** synthetic tickets, in code (`SAMPLE_TICKETS`) and in `data/eval_tickets.jsonl`.
- **Rules only:** everything runs in memory on the local machine, with no network call.
- **Agent and evaluation:** the ticket subject and description are sent to the Anthropic API as written. The requester's name is not sent. Masking sensitive values before the call is not implemented.
- **Output:** terminal output (not redacted, local only); `audit_log.jsonl` and `agent_audit_log.jsonl` with redacted ticket text, both git-ignored; `results/eval_results.json` for evaluation runs, which is committed.
- **Retention:** the logs are appended on every run and never rotated. A production system would need a retention policy.

## From prototype to production

| Area | Prototype | Production would need |
|---|---|---|
| Ticket source | Samples in code and a JSONL file | Integration with a ticketing platform |
| Classification | Keyword rules plus an LLM, combined by the guardrail | The same split, measured on real tickets with more than one run |
| Rules | In code | Versioned policy configuration with change control |
| Human review | A console prompt | An approval workflow with an analyst queue |
| Sensitive data | Regular expressions | Data-loss-prevention tooling, and masking before any API call |
| Audit log | Local files | Central, access-controlled, tamper-evident logging |
| Identity | None | Authentication and role-based access |
| Monitoring | None | Escalation rate, disagreement rate and cost over time |

## The diagram in `assets/`

`assets/architecture-diagram.png` (source: `assets/architecture-diagram.drawio`) is the conceptual diagram drawn before the LLM layer existed. It shows the rules pipeline only. Two of its boxes, "Data Pre-Processing" and "Request more information", were never implemented.
