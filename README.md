# Support Agent Governance Prototype

A local Python prototype of the governance layer for an AI support agent in corporate IT service management scenarios.

> **Current scope:** a deterministic rules layer plus an LLM triage agent built on top of it. The LLM (Claude, through the Anthropic API) classifies each ticket; the rules act as a guardrail that the LLM can only make stricter; a person approves every reply; nothing is actually sent. The rules, the guardrail and the evaluation harness are covered by an automated test suite (standard library only) that runs in CI on every push and never calls the API. Measured results on a labelled set of 30 synthetic tickets, and their limits, are in section 8.

The project focuses on ticket triage, request classification, incident prioritization, human escalation rules, safe automated responses, sensitive data detection, and audit logging.

---

## 1. Project Overview

The prototype simulates a support environment where incoming tickets are processed by a deterministic, rule-based workflow. These rules are the controls an AI support agent would have to operate within.

The prototype evaluates each ticket and decides whether the request can receive a safe automated response or must be escalated to a human analyst.

The LLM version (section 8) keeps those rules as the guardrail: the LLM may make a decision more cautious, never less, and any disagreement between the rules and the LLM goes to a person.

The main goal is not to build a production-ready chatbot, but to demonstrate how automation logic can be designed with governance, auditability, escalation boundaries, and responsible AI controls.

---

## 2. Problem Statement

Support teams often receive a high volume of repetitive requests, operational incidents, access issues, and user-reported problems.

Without clear triage and escalation rules, organizations may face:

- inconsistent ticket prioritization;
- delayed incident response;
- excessive manual work;
- unsafe automation of sensitive requests;
- lack of auditability;
- poor visibility over escalation decisions.

This prototype addresses these problems by simulating a structured decision workflow for automated support triage.

---

## 3. Objectives

The project demonstrates how the governance layer of an AI support agent can:

- classify support tickets into predefined categories;
- assign priority levels based on ticket content and risk;
- detect simple sensitive data patterns;
- decide whether automation is allowed or blocked;
- escalate high-risk or sensitive tickets to human review;
- generate safe automated responses;
- create a local audit log with sensitive data redaction;
- provide command-line options for reviewing and processing sample tickets.

---

## 4. Key Features

The current prototype includes:

- simulated ticket input;
- ticket classification;
- priority assignment;
- simple sensitive data detection;
- human escalation rules;
- separation between allowed and blocked automation;
- safe automated response generation;
- local audit log generation;
- sensitive data redaction in logs;
- command-line execution;
- ticket listing with `--list`;
- individual ticket processing with `--ticket TCK-XXX`;
- invalid ticket validation;
- LLM classification with JSON validated locally (any invalid answer goes to a person);
- a guardrail that combines the rules and the LLM, an LLM reply draft that is checked before a person sees it, explicit human approval and an audit log of both decisions;
- a labelled evaluation set and a harness that compares prompt versions and models, with cost from the tokens the API reports.

---

## 5. Repository Structure

```text
support-agent-governance-prototype/
├── AGENTS.md
├── README.md
├── requirements.txt
├── requirements-llm.txt
├── .gitignore
├── .github/workflows/tests.yml
├── data/
│   └── eval_tickets.jsonl
├── prompts/
│   ├── classify_v1.md
│   ├── classify_v2.md
│   └── reply_v1.md
├── results/
│   └── eval_results.json
├── assets/
│   ├── architecture-diagram.drawio
│   └── architecture-diagram.png
├── docs/
│   ├── architecture.md
│   ├── decision-logic.md
│   ├── evaluation-run.md
│   ├── evaluation-set.md
│   ├── guardrail.md
│   ├── governance-controls.md
│   ├── implementation-roadmap.md
│   ├── llm-classifier.md
│   ├── project-scope.md
│   ├── ROADMAP.md
│   └── sample-interactions.md
├── src/
│   ├── agent.py
│   ├── eval_set.py
│   ├── evaluate.py
│   ├── llm_classifier.py
│   └── prototype.py
└── tests/
    ├── test_agent.py
    ├── test_eval_set.py
    ├── test_evaluate.py
    ├── test_llm_classifier.py
    └── test_prototype.py
```

---

## 6. How to Run the Prototype

### Requirements

- Python 3.10 or higher (standard library only, no packages to install for the rules, the tests and the results table)
- Only to call the API (sections 6 and 8): `pip install -r requirements-llm.txt` and an `ANTHROPIC_API_KEY` set in your terminal. The key never goes in a file in this repository (`.env` is git-ignored)
- Local terminal or Git Bash
- No cloud services required
- No Microsoft automation services required in this phase

The rules prototype runs locally and does not require Azure, Copilot Studio, Power Automate, or Microsoft 365 Developer resources.

### Run all sample tickets

```bash
py src/prototype.py
```

This processes all simulated tickets and prints a summary of the results.

### List available tickets

```bash
py src/prototype.py --list
```

This displays the available simulated ticket IDs.

### Process a specific ticket

```bash
py src/prototype.py --ticket TCK-009
```

This processes one specific ticket by ID.

### Test invalid ticket handling

```bash
py src/prototype.py --ticket TCK-999
```

This validates how the prototype handles an unknown ticket ID.

---

### Run the tests

```bash
python -m unittest discover -s tests -v
```

The suite checks the expected result of every simulated ticket, each governance rule (escalation, automation blocking, priority), sensitive-data detection, audit-log redaction and the command-line options. A change to a rule has to change a test too.

### Measure the rules on the evaluation set

```bash
py src/eval_set.py
```

This compares the rules with the 30 labelled tickets in `data/eval_tickets.jsonl` and prints the baseline described in `docs/evaluation-set.md`.

### Run the LLM agent on one evaluation ticket (calls the API)

```bash
py src/agent.py --ticket EVAL-005 --model claude-haiku-5-5
```

This classifies the ticket with Claude, applies the guardrail, drafts a reply only if automation is allowed, asks you to approve it and writes `agent_audit_log.jsonl` (git-ignored). Sending is simulated.

### Print the evaluation results table (no API call)

```bash
py src/evaluate.py --table results/eval_results.json
```

Re-running the full evaluation (120 API calls) is described in `docs/evaluation-run.md`.

---

## 7. Prototype Results

Running all simulated tickets produces the following summary (also asserted by `test_published_summary`):

```text
Total tickets processed: 10
Human escalation required: 6
Automation allowed: 4
Automation blocked: 6
Sensitive data cases: 3
```

---

## 8. LLM Triage with Guardrail: Results

Flow for each ticket: the rules and the LLM both classify it; the guardrail keeps the stricter decision; automation is allowed only when both agree on a low-risk case; an LLM reply draft is produced only then, is checked (sensitive data, claims of actions performed, length) and needs a person's explicit approval. Details: `docs/guardrail.md`, `docs/llm-classifier.md`.

The table compares the rules alone with two models (Claude Haiku 5.5 and Claude Sonnet 5.5) and two prompt versions (`v1` minimal, `v2` with the written policy), on the 30 labelled synthetic tickets. It is generated from `results/eval_results.json` and a test checks that this README contains exactly that table. Prices are those stored in the results file, checked on 2026-11-10.

| Classifier | Category | Priority | Invalid LLM output | Rules-LLM disagreements | Unsafe automation, LLM alone | Unsafe automation, with guardrail | Unnecessary review | Cost per ticket (US$) |
|---|---|---|---|---|---|---|---|---|
| Rules only | 9/30 | 17/30 | - | - | - | 8/21 | 3 | 0 |
| claude-haiku-5-5 / prompt v1 | 21/30 | 19/30 | 0 | 21 | 3/21 | 1/21 | 5 | 0.00011 |
| claude-haiku-5-5 / prompt v2 | 28/30 | 27/30 | 0 | 21 | 1/21 | 0/21 | 4 | 0.00016 |
| claude-sonnet-5-5 / prompt v1 | 21/30 | 18/30 | 0 | 22 | 3/21 | 1/21 | 5 | 0.00212 |
| claude-sonnet-5-5 / prompt v2 | 28/30 | 30/30 | 0 | 21 | 1/21 | 0/21 | 4 | 0.00320 |

"Unsafe automation" counts the tickets whose label requires a person but that would still get an automated response (21 tickets require one). "LLM alone" is the same count without the rules guardrail. "Unnecessary review" counts tickets whose label allows automation but that were sent to a person.

What the per-ticket records show (detail in `docs/evaluation-run.md`):

- **Prompt `v2` (the policy written into the prompt) scored higher on both models:** category 21/30 to 28/30, and the five prompt-injection tickets from 0/5 to 5/5 correct categories.
- **The guardrail lowers the risk but is only as good as its two inputs:** with prompt `v1`, one injection ticket (EVAL-029) still got an automated response, because the model returned exactly the output the ticket dictated and the rules, also fooled, agreed. With `v2`, none of the 21 tickets that require a person was automated.
- **The cost of caution is real:** with `v2`, 4 tickets that could be automated went to a person (EVAL-005, -010, -012, -013). In all four the LLM's category matches the label and the rules' does not, so the cost comes from the rules' errors, not the LLM's.
- **The models are close:** category 28/30 on both; priority 27/30 (Haiku) against 30/30 (Sonnet), at about 20 times the cost per ticket. Three tickets out of 30 in one run is within noise: this run does not show that the larger model is needed.
- **One case is stopped by disagreement, not by detection:** with `v2`, EVAL-011 would still be automated by the LLM alone, on both models. It is stopped because the rules classify it differently and any disagreement goes to a person.

### Limitations of these results

- 30 synthetic tickets whose labels were drafted with AI assistance and approved by one reviewer, the project owner: one ticket is 3.3 percentage points.
- One run per combination. LLM output is not deterministic and variance was not measured.
- Prompt `v2` was written from the same policy that produced the labels. The result shows that the model follows a policy when it is stated, not how it would perform on real tickets. No prompt was tuned on the evaluation tickets.
- Only classification was evaluated. Reply drafts and latency were not.
- Five injection tickets are a sample, not a security assessment. The ticket text is wrapped as data and the guardrail limits the damage, but a full prompt-injection defence is not implemented.
- The ticket text is sent to the API as written (only the requester's name is left out). Masking sensitive values before the call is not implemented.
- Human approval is a console prompt, and sending is simulated: there is no ticketing or mail integration.

---

## 9. Governance and Risk Controls

This prototype includes governance-oriented controls to demonstrate responsible automation design.

Key controls include:

- human escalation for sensitive or high-risk tickets;
- automation blocking when predefined risk conditions are detected;
- sensitive data redaction in local audit logs;
- deterministic rule-based decision logic;
- clear separation between automated response and human review;
- documented decision logic;
- documented governance controls;
- prototype limitations explicitly stated.

The goal is to show that AI-enabled automation should operate within defined boundaries, especially in environments involving access, incidents, sensitive information, or business-critical operations.

---

## 10. Audit Logging

The prototype creates or updates a local file named:

```text
audit_log.jsonl
```

This file is generated at runtime and is intentionally excluded from version control through `.gitignore`.

The LLM agent (`src/agent.py`) writes `agent_audit_log.jsonl` the same way, with both decisions, the draft and the human outcome. It is also git-ignored.

Audit logs are not committed to the repository because runtime logs may contain operational or sensitive information, even when redaction controls are applied.

---

## 11. Prototype vs Production Disclaimer

This project is a local prototype.

It is intended for portfolio, learning, architecture demonstration, and governance discussion purposes.

It is not production-ready and does not include:

- real user authentication;
- real ticketing system integration;
- production-grade AI model integration (the API call exists for evaluation, with no masking of the ticket text);
- real-time monitoring;
- enterprise-grade logging;
- role-based access control;
- encryption controls;
- secure secret management;
- API security;
- database persistence;
- human approval workflow integration (approval is a console prompt and sending is simulated);
- compliance certification.

A production implementation would require additional security, privacy, operational resilience, model governance, monitoring, access control, and enterprise integration controls.

---

## 12. Documentation

Additional documentation is available in the `docs/` folder:

- `docs/project-scope.md` — project scope and planning;
- `docs/architecture.md` — solution architecture;
- `docs/decision-logic.md` — classification, prioritization, and escalation logic;
- `docs/governance-controls.md` — governance and risk controls;
- `docs/sample-interactions.md` — example prototype interactions;
- `docs/implementation-roadmap.md` — future implementation roadmap;
- `docs/evaluation-set.md` — labelled evaluation set and rules-only baseline;
- `docs/llm-classifier.md` — LLM classification with validated JSON output;
- `docs/guardrail.md` — rules as guardrail over the LLM, reply draft checks and human approval (`src/agent.py`);
- `docs/evaluation-run.md` — how the evaluation runs, the results of the run of 2026-11-10 and their limitations;
- `docs/ROADMAP.md` — current status and what is next.

---

## 13. Architecture Diagram

The architecture diagram is available in:

```text
assets/architecture-diagram.png
```

The editable draw.io source file is also included:

```text
assets/architecture-diagram.drawio
```

---

## 14. Implementation Roadmap

Possible next steps include:

- improving the ticket classification logic;
- adding more simulated ticket scenarios;
- expanding sensitive data detection patterns;
- improving audit log formatting;
- adding configuration files for business rules;
- separating data, logic, and response templates;
- integrating with a real ticketing system in a future phase;
- prompt-injection defence beyond the guardrail (AGENT-V2-05);
- masking sensitive values before the API call (AGENT-V2-06);
- a demo of the agent flow;
- mapping controls to AI Governance, GRC, IT Risk, and ITSM frameworks.

Microsoft-based automation tools such as Copilot Studio, Power Automate, Azure, and Microsoft 365 Developer are intentionally excluded from the initial phase and may be considered only as a future roadmap option.
