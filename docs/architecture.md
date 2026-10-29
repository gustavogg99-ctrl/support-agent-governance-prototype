# Architecture

## 1. Purpose

This document describes the architecture of the Support Agent Governance Prototype prototype: its components, the data flow between them, where governance controls sit, and how the design would change in a production setting.

The visual version is in `assets/architecture-diagram.png` (editable source: `assets/architecture-diagram.drawio`).

---

## 2. Architecture Overview

The prototype is a single local Python module (`src/prototype.py`) with no external dependencies. It uses only the Python standard library.

It is organized as a linear pipeline. Each stage is a separate function, so every decision point can be reviewed, tested and explained on its own.

```text
                 ┌──────────────────────────┐
                 │  Simulated ticket input  │  SAMPLE_TICKETS / CLI arguments
                 └────────────┬─────────────┘
                              ▼
                 ┌──────────────────────────┐
                 │ Sensitive data check     │  detect_sensitive_data()
                 └────────────┬─────────────┘
                              ▼
                 ┌──────────────────────────┐
                 │ Ticket classification    │  classify_ticket()
                 └────────────┬─────────────┘
                              ▼
                 ┌──────────────────────────┐
                 │ Priority assessment      │  assign_priority()
                 └────────────┬─────────────┘
                              ▼
                 ┌──────────────────────────┐
                 │ Governance guardrails    │  evaluate_escalation()
                 │ (decision engine)        │  evaluate_automation()
                 └──────┬────────────┬──────┘
               low risk │            │ high risk / uncertain
                        ▼            ▼
      ┌─────────────────────┐  ┌──────────────────────────┐
      │ Allowed automation  │  │ Human escalation         │
      │ safe template reply │  │ "reviewed by a human"    │
      └──────────┬──────────┘  └────────────┬─────────────┘
                 └──────────────┬───────────┘
                                ▼
                 ┌──────────────────────────┐
                 │ Audit log (redacted)     │  write_audit_log() → audit_log.jsonl
                 └──────────────────────────┘
```

---

## 3. Components

| Component | Implementation | Responsibility |
|---|---|---|
| Ticket model | `Ticket` dataclass | Holds ticket ID, user, subject and description |
| Analysis record | `TicketAnalysis` dataclass | Holds every decision and its reason, which makes each outcome traceable |
| Ticket source | `SAMPLE_TICKETS` | 10 fictional tickets covering low-risk, sensitive, security and access scenarios |
| Sensitive data check | `detect_sensitive_data()` | Regex detection of email, CPF, phone, card-like numbers and disclosed secrets |
| Classification | `classify_ticket()` | Ordered keyword rules; security is evaluated first; unmatched tickets fall to General Support |
| Priority assessment | `assign_priority()` | High / Medium / Low based on category, sensitive data and urgency keywords |
| Escalation guardrail | `evaluate_escalation()` | Decides whether a human must review the ticket and records why |
| Automation guardrail | `evaluate_automation()` | Blocks automation for restricted categories, sensitive data or escalated tickets |
| Response generator | `generate_safe_response()` | Fixed templates only; never claims a real system action was taken |
| Redaction | `redact_text()` | Masks secrets and personal data before anything is written to disk |
| Audit logger | `write_audit_log()` | Appends one JSON Lines record per ticket with a UTC timestamp |
| CLI | `select_tickets_from_arguments()` | `--list`, `--ticket TCK-XXX`, and validation of unknown IDs |
| Orchestrator | `analyze_ticket()` / `main()` | Runs the pipeline and prints results and the execution summary |

Full rule tables for each decision are in `docs/decision-logic.md`.

---

## 4. Where the Governance Controls Sit

| Control | Stage | How it is enforced |
|---|---|---|
| Security-first classification | Classification | Security rules are evaluated before all other categories |
| Sensitive data protection | Sensitive data check + audit log | Detection raises priority and blocks automation; redaction runs before logging |
| Human-in-the-loop | Escalation guardrail | Security, access requests, sensitive data, High priority and unclassified tickets always go to a human |
| Bounded automation | Automation guardrail | Automation is limited to informational templates and is blocked whenever escalation is required |
| Explainability | Analysis record | Every escalation and automation decision stores a plain-language reason |
| Auditability | Audit logger | Every processed ticket produces a timestamped, redacted record |
| Input validation | CLI | Unknown ticket IDs are rejected before any processing |
| Log confidentiality | Repository | `audit_log.jsonl` is excluded from version control |

The design choice is **fail closed**: any condition that suggests risk or uncertainty removes the ticket from the automated path.

---

## 5. Data Flow and Data Handling

- **Input:** fictional tickets defined in code. No real personal, financial or production data is used.
- **Processing:** in memory, on the local machine. No network calls and no external APIs.
- **Output:**
  - terminal output for the operator (unredacted, local only);
  - `audit_log.jsonl`, which contains redacted ticket text plus the full decision record.
- **Retention:** the log is appended on every run and is not rotated or deleted automatically. This is acceptable for a prototype and would require a formal retention policy in production.

---

## 6. Technology

| Item | Choice | Rationale |
|---|---|---|
| Language | Python 3.10+ | Readable, standard in data and automation work |
| Dependencies | Standard library only (`re`, `json`, `dataclasses`, `datetime`, `pathlib`) | No supply chain risk, runs anywhere |
| Decision logic | Deterministic rules | Fully explainable and reproducible |
| Log format | JSON Lines | One record per event; easy to parse, append and audit |

---

## 7. From Prototype to Production

| Area | Prototype | Production target |
|---|---|---|
| Ticket source | Hard-coded samples | ITSM platform integration (API or webhook) |
| Classification | Keyword rules | NLP or LLM classification with a confidence score, keeping rule-based guardrails as a hard boundary |
| Guardrails | In-code rules | Externalized, versioned policy configuration with change control |
| Human review | Message to the user | Approval workflow with an assigned analyst queue |
| Sensitive data | Regex patterns | Enterprise DLP and data classification |
| Audit log | Local file | Centralized, access-controlled, tamper-evident logging with retention rules |
| Identity | None | Authentication and role-based access control |
| Monitoring | None | Metrics on escalation rate, false positives and model drift |

Any LLM-based classifier added in the future must run **inside** the current guardrails: the model may suggest a category, but escalation and automation rules stay deterministic and non-overridable.

---

## 8. Design Principles

1. Governance before capability: controls are defined first, automation second.
2. Fail closed: uncertainty leads to escalation, never to automation.
3. Every decision carries a reason.
4. Sensitive data is minimized in stored records.
5. The agent supports human decisions; it does not replace them.
