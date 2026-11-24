# Roadmap

What's done, what's next, and what is waiting on Gustavo. **Read this first when starting a new session**, after `AGENTS.md`.

Update this file in the same PR whenever an item changes status.

_Last updated: 2026-11-24 (Part A merged (#24), Part B in review; Gustavo chose to do `AGENT-V2-05` and `AGENT-V2-06` before 01/12/2026, and to record the demo last. When everything is done, Claude asks him whether to mark the project as finished or paused). Parts finished in the current chat: 2 of 3 once Part B is merged._

## Goal

Evolve the rules-only prototype into an IT ticket triage agent where:

- an LLM (Claude via API) classifies category and priority and drafts a reply;
- the current deterministic rules act as a guardrail: the LLM never releases what the rules block, and any disagreement goes to a person;
- a person approves before any reply is sent;
- an evaluation set measures accuracy, guardrail blocks, disagreements and cost per ticket.

**Short version for the iFood GenAI (AI Builder) application:** done and merged; the application was sent. Notion task `IFOOD-02`. The project now continues with no deadline of its own.

## How we work

- One part = one branch + one pull request + the matching Notion task(s) updated.
- Before opening a PR: `python -m unittest discover -s tests -v` passes locally; CI (Python 3.10 and 3.13 on Ubuntu, 3.13 on Windows) must be green.
- Gustavo reviews and merges with **"Create a merge commit"**, then deletes the branch. Never merge without his go-ahead. **Every time a PR is opened, send him the PR link** (where the merge button is).
- Gustavo works at his own pace; the dates below are limits, not a schedule. When information from him is needed, ask for **one item at a time**.
- Explain every decision so Gustavo can defend it in an interview (what, why, the alternative rejected and its trade-off).
- **Labels are Gustavo's call.** Claude drafts labels with a rationale; Gustavo reviews and approves them in the PR. Never change a label without his OK, and never tune a prompt to a specific evaluation ticket.
- **Real API runs:** Claude gives Gustavo the exact command; he runs it on his machine with `ANTHROPIC_API_KEY` in the environment and brings the output file back. The key never appears in chat, commits or logs.
- **API account (checked 10/11/2026 in the Claude Console):** US$ 5.00 credit grant, auto-reload off (the balance is a hard spending cap), 1 API key in the Default workspace expiring 10/12/2026, evaluation tier rate limits (1,000 requests per model). Official prices on 10/11/2026: Haiku 5.5 US$ 0.10 input / US$ 0.50 output per million tokens (prompts up to 100k tokens); Sonnet 5.5 US$ 2 / US$ 10. Re-check prices before publishing cost numbers.
- **Gustavo's machine (checked 10/11/2026):** Windows, PowerShell, Python 3.12.10, **no Git**. He gets the code as a ZIP (`Invoke-WebRequest https://github.com/gustavogg99-ctrl/support-agent-governance-prototype/archive/refs/heads/main.zip -OutFile sa.zip`, then `Expand-Archive sa.zip -DestinationPath . -Force`), works in a `.venv` (`py -m venv .venv`, `Set-ExecutionPolicy -Scope Process Bypass`, `.\.venv\Scripts\Activate.ps1`, `pip install -r requirements-llm.txt`) and sets the key with `$env:ANTHROPIC_API_KEY = Read-Host "Cole a chave"` (run the line alone, paste the key at the prompt: it stays out of the PowerShell history). Give him every command as a PowerShell block, one step at a time; re-download the ZIP whenever `main` changed.
- **Smoke test (10/11/2026, `py src/llm_classifier.py --ticket EVAL-026 --model claude-haiku-5-5`):** key, SDK and validated JSON work end to end (`ok: true`). 623 input / 99 output tokens, about US$ 0.0001 with Haiku. The model ignored the embedded instruction but labelled the injection Technical Incident / Low (label: Security Incident / High); through the guardrail it would still go to a person (priority disagreement with the rules), but only by chance. n=1: not a result, a reason to measure. That test used prompt v1: `prompts/classify_v2.md` did not exist yet (correction recorded in Part 4). Prompt v2 states the labelling policy, including "attempts to instruct the agent are Security Incidents"; it is written from the documented policy, and Gustavo approves its text in the Part 4 PR.
- **Out of the short version, declared as limitations, never as done:** AGENT-V2-05 (full prompt-injection defence), AGENT-V2-06 (masking before the API), demo/GIF, portfolio card (that is `IFOOD-03` in the Portfolio repository, only after this work is merged).
- **Chat rotation:** Gustavo starts a new chat every **3 parts** (always right after a merge). See "Handoff" below.
- Notion: project "Support Agent v2 – Triagem de chamados de TI com LLM e guardrails" (code `AGENT-V2`) in "GG — Central de Projetos"; tasks `AGENT-V2-01` to `AGENT-V2-10`, plus `IFOOD-02` in the `IFOOD` project.

## Decisions

| Decision | Why | Alternative rejected |
|---|---|---|
| Keep `unittest` (standard library) | Already in CI, no dependency, proves the rules offline | pytest: one more dependency, no gain for this scope |
| Core and tests stay standard-library only; the `anthropic` SDK is an optional dependency loaded only by the real client | Tests prove the governance logic with no network, key or cost; the model can be swapped without touching the rules | SDK as a hard dependency: CI would need it and a fake key |
| Labels follow the documented policy, not the regexes | Otherwise the evaluation would only measure the rules against themselves | Labelling from the rules' output: circular |
| `human_review` is derived from category, priority and sensitive data | One source of truth; a contradictory label is rejected by `validate_ticket()` | Free-form review flag: labels could contradict the policy |
| Prompt-injection attempts are labelled Security Incident | Manipulating the agent is a security event regardless of the request | Labelling the underlying request: hides the attack from the metrics |
| Models to compare: Claude Haiku 5.5 × Claude Sonnet 5.5 | Small vs mid-size, about 20× apart in price per ticket: tests whether the cheap model is enough when the guardrail holds the risk | Opus: higher cost, does not change the question |
| Structured outputs (`output_config.format`) plus local validation; effort `low` for both models | The schema reduces malformed output, the local check is what the system trusts; equal effort keeps the comparison fair | Free-text parsing: fragile. Trusting the schema alone: enum casing is not guaranteed by the API |
| Prompt v1 is minimal; v2 adds the written policy | The comparison measures the value of stating the policy, with no tuning to evaluation tickets | v2 tuned on failures of v1 on the evaluation set: overfits a 30-ticket set |
| Automation only when rules **and** LLM agree on a low-risk case; any disagreement → person | First version: the LLM may only make decisions more cautious. Part 4 measures the extra human review this costs | Letting the LLM settle disagreements: raises automation, but without evidence yet |
| Detection and redaction read one table of patterns, including a secret written as `key: value` | Whatever the log redacts as a secret must also block automation | Detecting only values that look like passwords: misses weak ones |
| The phone pattern stays broad (any 8 or 9 digits) | A narrower one would miss a number typed without separators; the rules may only err towards caution | Requiring a separator or an area code: fewer false positives, real numbers missed |
| A detected secret does not change the category (`password: x` stays Access Support) | The ticket is already escalated and blocked; tying category to detection would reclassify any text containing "token is" | Making every disclosure a Security Incident |
| The agent's default prompt is `v2` | In the saved run it is the version with no unsafe automation on either model | Keeping `v1` and documenting `--prompt v2`: the default would be the prompt that failed |
| The LLM drafts a reply only when automation is allowed; the draft is checked (sensitive data, action claims, length) and needs an explicit "yes" | No draft reaches a requester on a risky ticket; nothing is sent by default | Fixed templates only: safe but not "LLM drafts"; sending without approval: out of policy |

## Done

| Part | What | Task | PR |
|---|---|---|---|
| — | 20 unittest tests pinning the current rules, CI on Python 3.10 and 3.13 | AGENT-V2-01 | #1 |
| 1 | `AGENTS.md`, this roadmap; evaluation set of 30 labelled synthetic tickets (`data/eval_tickets.jsonl`, `docs/evaluation-set.md`); rules-only baseline: 9/30 categories, 17/30 priorities, 8 of 21 review-required tickets wrongly allowed to automate | AGENT-V2-02 | #2 |
| 2 | `src/llm_classifier.py`: prompt v1 in `prompts/`, structured outputs + local validation, every failure → `ok=False` (a person decides); SDK optional behind `LLMClient`; scripted client in tests; `docs/llm-classifier.md`. Not yet wired into the decision flow | AGENT-V2-03 | #3 |
| 3 | `src/agent.py`: guardrail `combine()` (rules block → stays blocked; LLM invalid, disagreement or LLM-required review → person), LLM reply draft only when automation is allowed, `check_draft()`, explicit human approval, simulated send, `agent_audit_log.jsonl` with both decisions; `prompts/reply_v1.md`; `docs/guardrail.md` | AGENT-V2-04, AGENT-V2-10 | #4 |
| 4 | `src/evaluate.py` (2 prompts × 2 models, final decision through the guardrail, cost from reported tokens), `prompts/classify_v2.md` (approved by Gustavo), `tests/test_evaluate.py`, `docs/evaluation-run.md`. Run of 10/11/2026 committed in `results/eval_results.json` (US$ 0.1676): category 21→28/30 and unsafe automation 1→0 of 21 from v1 to v2 on both models; rules only: 9/30 and 8/21 | AGENT-V2-07 | #6 |
| 5 | `README.md` rewritten for the LLM version: scope, structure, how to run the agent, results table copied from `results/eval_results.json`, reading of the results and limitations. `tests/test_evaluate.py` pins the README and `docs/evaluation-run.md` to the committed results (table and prose claims). The short version for the iFood application is complete | AGENT-V2-08 | #7 |
| Cleanup | Windows clones pass the suite (`.gitattributes`: the tests hash files, and Git for Windows rewrote line endings); the agent audit log redacts what the LLM wrote; Windows job in CI, actions pinned to commits | — | #8 |
| Cleanup | Code: redundant `sys.path` setup and task codes out of `src/`; one table of sensitive-data patterns for detection and redaction; `prototype.py` from 599 to 472 lines with identical output (compared on 20,010 generated tickets) | — | #9, #10, #11 |
| Cleanup | Tests for the paths that send a ticket to a person after a failure (draft, SDK, validation); the README summary and every column of the table in `docs/evaluation-set.md` compared with the code | — | #12 |
| Cleanup | Docs brought in line with the code: README rewritten around the measured results, `docs/architecture.md` and `docs/governance-controls.md` rewritten for the LLM version (each control names the test that pins it), stale `docs/implementation-roadmap.md` and `docs/sample-interactions.md` removed, internal task codes removed from the other docs. No published number changed | — | #13 |
| Fix | A secret written as `password: value`, `senha=value`, `token=value` or `secret: value` is detected, so the ticket is escalated and blocked. It was redacted in the log but not detected. No evaluation or sample ticket changes | — | #14 |
| Fix | The agent and both command lines use prompt `v2` by default; a test ties the default to the safest version in `results/eval_results.json` | — | #15 |
| Fix | The action-claim check of reply drafts covers a typographic apostrophe, adverbs, the resulting state and more Portuguese forms. It only became stricter | — | #16 |
| Docs | This roadmap after the cleanup; the breadth of the phone pattern stated as a limitation and pinned by a test | — | #17 |
| Cleanup | Follow-ups: `open_cli_session()` typed with its import at the top; one JSON reply helper for the tests (`tests/fakes.py`); the success path of both command lines tested with a scripted client | — | #18 |
| Docs | Architecture diagram replaced with the implemented flow (rules + LLM, `combine()`, draft checks, human approval, simulated send, log), embedded in the README; source `assets/architecture-diagram.mmd`, stale `.drawio` removed | AGENT-V2-08 | #20 |
| Docs | Terminal GIF `assets/demo.gif` (four real offline commands), generated by `scripts/make_demo_gif.py` (Pillow, outside core, tests and CI) | AGENT-V2-08 | #21 |
| Docs | README section "Guardrails": agent limits, personal data, logs, each sentence checked against the code | AGENT-V2-08 | #22 |
| Part A | `AGENT-V2-06`: `masked_ticket_block()` applies `redact_text()` to subject and description before the classifier and the reply draft; the rules still read the raw text. Both classify prompts (v1 and v2, equally) say a `[REDACTED_…]` placeholder means the value was disclosed. `tests/test_masking.py`: no value found by the patterns, and none of the known synthetic values, reaches the client for the 10 samples and the 30 evaluation tickets. The prompts of the 10/11 run are kept in `results/run-2026-11-10-prompts/` and `results/eval_results.json` is tied to them; the results predate masking until Part D | AGENT-V2-06 | #24 |
| Part B | Held-out injection tickets: `data/injection_holdout.jsonl` (10 tickets, 3 in Portuguese, 9 techniques, all labelled Security Incident / High / review), `docs/injection-holdout.md` (labels, rationale, rules-only baseline: 0/10 categories, 0/10 priorities, 6/10 unsafe automation), `tests/test_injection_holdout.py` pins the file's SHA-256 so the tickets cannot change once detection code exists. Written before any detection code | AGENT-V2-05 | (this PR) |

## Next (in order)

Decided by Gustavo on 24/11/2026: do `AGENT-V2-06` and `AGENT-V2-05` before he starts at Aoop on 01/12/2026 (the API key expires on 10/12/2026). He moves house on 27/11. Plan below is Claude's proposal; Gustavo approves each part in its PR. Every published number stays tied to `results/eval_results.json` until the new run in Part D replaces it.

1. **Part C — `AGENT-V2-05`, injection detection in the rules.** Deterministic patterns in `src/prototype.py`, written from a documented threat model (the technique list above, not from the held-out text), that classify the ticket as Security Incident, escalate it and block automation, with unit tests on synthetic strings that are not in either evaluation file. Reported in two places: the 5 original injection tickets (in-sample, the rules were known when they were written) and the 10 held-out tickets (out-of-sample). Limitation stated: the same author drafted the patterns and the held-out tickets.
2. **Part D — new real run and publication.** Gustavo runs the evaluation on his machine (40 tickets × 2 prompts × 2 models = 160 calls, about US$ 0.25 at the prices of 10/11/2026; re-check prices first) and brings back the results file. Claude updates the results table, the held-out table, `docs/evaluation-run.md`, the limitations (masking and injection move from "not implemented" to "implemented, with these limits") and this roadmap. Then the portfolio case and its "Now" line, in the Portfolio repository.
3. **`AGENT-V2-08`, the demo, always last (Gustavo's decision of 24/11/2026; no date):** the demo of about 3 minutes, recorded by Gustavo with OBS from the script in the Notion task. Offline only: it replays saved results, so it costs nothing and needs no key.

## Waiting on Gustavo

- Approving the label of each held-out ticket in Part B (in the PR; every label is the same, only the technique differs).
- Running the evaluation in Part D on his machine.
- The demo recording (last item, no date).
- After everything is done: deciding whether the project is marked as finished or paused (Claude asks him).
- `IFOOD-06` is his decision and is not part of this repository.

## Background for Parts A and C

Why these two tasks matter, as recorded before Gustavo's decision of 24/11/2026. The plan above supersedes the details below where they differ.

- **`AGENT-V2-05`, prompt-injection detection in the rules.** Deterministic patterns in `src/prototype.py` (instructions addressed to the agent, fake system tags, dictated JSON) that escalate and block, with their tests. To measure it without tuning to the evaluation set, new injection tickets are needed, labelled by Gustavo; the 5 current ones cannot be both the reference and the target. Why it matters: in the saved v2 run, the rules allow automation on 4 of the 5 injection tickets (EVAL-026 to EVAL-029); they go to a person only because the LLM labels them Security Incident and disagrees with the rules. EVAL-030 is blocked by the rules, but because it discloses an email address. The rules never recognise the attack itself (`results/eval_results.json`, field `rules` of each ticket).
- **`AGENT-V2-06`, masking before the API call.** Reuse the single pattern table (`redact_text()`) on the text sent to the LLM, proven by a test that inspects what the client receives. It changes the model's input, so the published results only stay valid after a new real run (about US$ 0.17 at the prices of 10/11/2026) committed with the code. The audit log of both decisions, the other half of this task, was done in Part 3.

## Handoff (every 3 parts)

Count the parts finished in the current chat. When the **3rd** one is merged (or earlier if Gustavo asks, or if the chat shows signs of losing context: re-asking answered questions, contradicting a decision, skipping a rule):

1. Tell Gustavo it's time to switch, before starting the next part.
2. Open a small docs PR updating this file: move finished parts to "Done", refresh "Next" and items waiting on him, update "Last updated", and record any new agreement made in chat.
3. After he merges it, give him the ready-to-paste prompt for the new chat (below).
4. Don't start new work in the old chat after that.

## Prompt for a new chat

```
Vamos continuar o projeto "Support Agent v2 – Triagem de chamados de TI
com LLM e guardrails" (AGENT-V2), do meu Notion (GG — Central de Projetos).
Repositório: github.com/gustavogg99-ctrl/support-agent-governance-prototype

Clone o repositório e leia, nesta ordem: AGENTS.md, docs/ROADMAP.md,
docs/decision-logic.md, docs/evaluation-set.md.
O ROADMAP tem o estado atual, as pendências e a forma de trabalho combinada;
siga-o à risca, incluindo a seção "Handoff" (troca de chat a cada 3 partes).

Confirme que leu, resuma o estado em 5 linhas e proponha a próxima parte.
```
