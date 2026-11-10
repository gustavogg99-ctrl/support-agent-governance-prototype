# Support Agent Governance Prototype

A local Python prototype of the governance layer for an AI support agent in corporate IT service management scenarios.

> **Current scope:** every decision is made by deterministic rules. There is no LLM integration yet (it is on the roadmap). The rules are covered by an automated test suite (standard library only) that runs in CI on every push. A labelled evaluation set of 30 synthetic tickets measures them (`docs/evaluation-set.md`); the LLM version is in progress (`docs/ROADMAP.md`).

The project focuses on ticket triage, request classification, incident prioritization, human escalation rules, safe automated responses, sensitive data detection, and audit logging.

---

## 1. Project Overview

The prototype simulates a support environment where incoming tickets are processed by a deterministic, rule-based workflow. These rules are the controls an AI support agent would have to operate within.

The prototype evaluates each ticket and decides whether the request can receive a safe automated response or must be escalated to a human analyst.

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
- invalid ticket validation.

---

## 5. Repository Structure

```text
support-agent-governance-prototype/
├── AGENTS.md
├── README.md
├── requirements.txt
├── .gitignore
├── .github/workflows/tests.yml
├── data/
│   └── eval_tickets.jsonl
├── assets/
│   ├── architecture-diagram.drawio
│   └── architecture-diagram.png
├── docs/
│   ├── architecture.md
│   ├── decision-logic.md
│   ├── evaluation-set.md
│   ├── governance-controls.md
│   ├── implementation-roadmap.md
│   ├── project-scope.md
│   ├── ROADMAP.md
│   └── sample-interactions.md
├── src/
│   ├── eval_set.py
│   └── prototype.py
└── tests/
    ├── test_eval_set.py
    └── test_prototype.py
```

---

## 6. How to Run the Prototype

### Requirements

- Python 3.10 or higher (standard library only, no packages to install)
- Local terminal or Git Bash
- No cloud services required
- No Microsoft automation services required in this phase

This prototype runs locally and does not require Azure, Copilot Studio, Power Automate, or Microsoft 365 Developer resources.

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

## 8. Governance and Risk Controls

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

## 9. Audit Logging

The prototype creates or updates a local file named:

```text
audit_log.jsonl
```

This file is generated at runtime and is intentionally excluded from version control through `.gitignore`.

Audit logs are not committed to the repository because runtime logs may contain operational or sensitive information, even when redaction controls are applied.

---

## 10. Prototype vs Production Disclaimer

This project is a local prototype.

It is intended for portfolio, learning, architecture demonstration, and governance discussion purposes.

It is not production-ready and does not include:

- real user authentication;
- real ticketing system integration;
- real AI model integration;
- real-time monitoring;
- enterprise-grade logging;
- role-based access control;
- encryption controls;
- secure secret management;
- API security;
- database persistence;
- human approval workflow integration;
- compliance certification.

A production implementation would require additional security, privacy, operational resilience, model governance, monitoring, access control, and enterprise integration controls.

---

## 11. Documentation

Additional documentation is available in the `docs/` folder:

- `docs/project-scope.md` — project scope and planning;
- `docs/architecture.md` — solution architecture;
- `docs/decision-logic.md` — classification, prioritization, and escalation logic;
- `docs/governance-controls.md` — governance and risk controls;
- `docs/sample-interactions.md` — example prototype interactions;
- `docs/implementation-roadmap.md` — future implementation roadmap;
- `docs/evaluation-set.md` — labelled evaluation set and rules-only baseline;
- `docs/ROADMAP.md` — current status of the LLM version (v2).

---

## 12. Architecture Diagram

The architecture diagram is available in:

```text
assets/architecture-diagram.png
```

The editable draw.io source file is also included:

```text
assets/architecture-diagram.drawio
```

---

## 13. Implementation Roadmap

Possible next steps include:

- improving the ticket classification logic;
- adding more simulated ticket scenarios;
- expanding sensitive data detection patterns;
- improving audit log formatting;
- adding configuration files for business rules;
- separating data, logic, and response templates;
- integrating with a real ticketing system in a future phase;
- integrating an LLM for classification, with the current rules acting as guardrails (planned for v2);
- mapping controls to AI Governance, GRC, IT Risk, and ITSM frameworks.

Microsoft-based automation tools such as Copilot Studio, Power Automate, Azure, and Microsoft 365 Developer are intentionally excluded from the initial phase and may be considered only as a future roadmap option.
