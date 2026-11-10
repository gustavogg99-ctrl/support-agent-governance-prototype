# Roadmap

What's done, what's next, and what is waiting on Gustavo. **Read this first when starting a new session**, after `AGENTS.md`.

Update this file in the same PR whenever an item changes status.

_Last updated: 2026-11-10 (Part 1 in review)._

## Goal

Evolve the rules-only prototype into an IT ticket triage agent where:

- an LLM (Claude via API) classifies category and priority and drafts a reply;
- the current deterministic rules act as a guardrail: the LLM never releases what the rules block, and any disagreement goes to a person;
- a person approves before any reply is sent;
- an evaluation set measures accuracy, guardrail blocks, disagreements and cost per ticket.

**Short version for the iFood GenAI (AI Builder) application:** merged by **13/11/2026** (slack until 15/11); Gustavo applies on 16/11. Notion task `IFOOD-02`. After that the project continues with no deadline.

## How we work

- One part = one branch + one pull request + the matching Notion task(s) updated.
- Before opening a PR: `python -m unittest discover -s tests -v` passes locally; CI (Python 3.10 and 3.13) must be green.
- Gustavo reviews and merges with **"Create a merge commit"**, then deletes the branch. Never merge without his go-ahead. **Every time a PR is opened, send him the PR link** (where the merge button is).
- Gustavo works at his own pace; the dates below are limits, not a schedule. When information from him is needed, ask for **one item at a time**.
- Explain every decision so Gustavo can defend it in an interview (what, why, the alternative rejected and its trade-off).
- **Labels are Gustavo's call.** Claude drafts labels with a rationale; Gustavo reviews and approves them in the PR. Never change a label without his OK, and never tune a prompt to a specific evaluation ticket.
- **Real API runs:** Claude gives Gustavo the exact command; he runs it on his machine with `ANTHROPIC_API_KEY` in the environment and brings the output file back. The key never appears in chat, commits or logs.
- **API account (checked 10/11/2026 in the Claude Console):** US$ 5.00 credit grant, auto-reload off (the balance is a hard spending cap), 1 API key in the Default workspace expiring 10/12/2026, evaluation tier rate limits (1,000 requests per model). Official prices on 10/11/2026: Haiku 5.5 US$ 0.10 input / US$ 0.50 output per million tokens (prompts up to 100k tokens); Sonnet 5.5 US$ 2 / US$ 10. Re-check prices before publishing cost numbers.
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

## Done

| Part | What | Task | PR |
|---|---|---|---|
| — | 20 unittest tests pinning the current rules, CI on Python 3.10 and 3.13 | AGENT-V2-01 | #1 |
| 1 | `AGENTS.md`, this roadmap; evaluation set of 30 labelled synthetic tickets (`data/eval_tickets.jsonl`, `docs/evaluation-set.md`); rules-only baseline: 9/30 categories, 17/30 priorities, 8 of 21 review-required tickets wrongly allowed to automate | AGENT-V2-02 | PR_TBD |

## Next (in order)

1. **Part 2 (AGENT-V2-03):** `src/llm_classifier.py`. Prompt v1 in a versioned file; output JSON validated against the closed enums; invalid output → human review and counted as a failure; real client (SDK, optional) and simulated client for tests.
2. **Part 3 (AGENT-V2-04 + AGENT-V2-10):** guardrail combination (most restrictive decision wins; disagreement on category or priority → person); suggested reply shown only when automation is allowed; approve/reject in the CLI; audit log with both decisions.
3. **Handoff** (docs-only PR) → new chat.
4. **Part 4 (AGENT-V2-07):** `src/evaluate.py`: 2 prompt versions × 2 models; accuracy, guardrail blocks, disagreements, invalid JSON, cost from the tokens the API reports; simulated tests; the command for Gustavo to run. Results file committed.
5. **Part 5 (AGENT-V2-08):** README with the results table generated from Gustavo's run, and the limitations.

## Later (no deadline, after 16/11)

- AGENT-V2-05: prompt-injection defence beyond the guardrail.
- AGENT-V2-06: masking sensitive values before the API call; audit of both decisions.
- Demo/GIF; AGENT-V2-09 (portfolio card and LinkedIn), done in the Portfolio repository.

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
