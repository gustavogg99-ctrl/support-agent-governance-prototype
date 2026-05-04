# AI Autonomous Support Agent

A local Python prototype that simulates an AI-enabled autonomous support agent for corporate IT service management scenarios.

The project focuses on ticket triage, request classification, incident prioritization, human escalation rules, safe automated responses, sensitive data detection, and audit logging.

This repository was created as a practical portfolio project for Governance, Risk and Compliance (GRC), AI Governance, Technology Risk, Responsible AI, ITSM, and automation.

---

## 1. Project Overview

The AI Autonomous Support Agent simulates a support environment where incoming tickets are processed by a rule-based AI support workflow.

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

The project aims to demonstrate how an AI-enabled support agent can:

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
ai-autonomous-support-agent/
├── README.md
├── requirements.txt
├── .gitignore
├── assets/
│   ├── architecture-diagram.drawio
│   └── architecture-diagram.png
├── docs/
│   ├── architecture.md
│   ├── decision-logic.md
│   ├── governance-controls.md
│   ├── implementation-roadmap.md
│   ├── project-scope.md
│   └── sample-interactions.md
└── src/
    └── prototype.py
```

---

## 6. How to Run the Prototype

### Requirements

- Python 3.13 or higher
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

## 7. Validated Prototype Results

During local validation, the prototype successfully processed the simulated ticket set with the following result:

```text
Total tickets processed: 10
Human escalation required: 6
Automation allowed: 4
Automation blocked: 6
Sensitive data cases: 3
```

The following commands were tested successfully:

```bash
py src/prototype.py
py src/prototype.py --list
py src/prototype.py --ticket TCK-009
py src/prototype.py --ticket TCK-999
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
- `docs/implementation-roadmap.md` — future implementation roadmap.

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
- creating a structured test file;
- improving audit log formatting;
- adding configuration files for business rules;
- separating data, logic, and response templates;
- integrating with a real ticketing system in a future phase;
- evaluating controlled AI model integration;
- mapping controls to AI Governance, GRC, IT Risk, and ITSM frameworks.

Microsoft-based automation tools such as Copilot Studio, Power Automate, Azure, and Microsoft 365 Developer are intentionally excluded from the initial phase and may be considered only as a future roadmap option.

---

## 14. Career Relevance

This project demonstrates practical skills related to:

- AI Governance;
- Responsible AI;
- Governance, Risk and Compliance;
- Technology Risk;
- IT Service Management;
- ITIL-inspired incident handling;
- support automation;
- auditability;
- human-in-the-loop controls;
- secure automation boundaries;
- documentation for technical and non-technical stakeholders.

It is designed to support professional positioning for roles involving GRC, AI Governance, Technology Risk, IT Risk, ITSM, automation governance, and digital transformation.

---