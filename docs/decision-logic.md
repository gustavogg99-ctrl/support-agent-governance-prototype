# Decision Logic

## 1. Purpose

This document describes the decision logic **as implemented** in `src/prototype.py`.

It explains how the prototype detects sensitive data, classifies tickets, assigns priority, decides on human escalation, decides whether automation is allowed, and writes audit records.

The logic is intentionally rule-based and deterministic. Every decision can be traced to a specific rule in the code, which makes the prototype explainable and auditable by design.

> The Phase 1 planning taxonomy (9 categories, P1–P4 priorities) is documented in `docs/project-scope.md`. The prototype implements a simplified version of it, described below. Section 9 maps the planned taxonomy to the implemented one.

---

## 2. Decision Flow

The functions run in this order for every ticket (`analyze_ticket`):

```text
Ticket received
↓
1. Sensitive data detection        detect_sensitive_data()
↓
2. Ticket classification           classify_ticket()
↓
3. Priority assignment             assign_priority()
↓
4. Human escalation decision       evaluate_escalation()
↓
5. Automation decision             evaluate_automation()
↓
6. Safe response generation        generate_safe_response()
↓
7. Audit log entry (redacted)      write_audit_log()
```

Sensitive data detection runs first because its result affects priority, escalation and automation.

---

## 3. Sensitive Data Detection

`detect_sensitive_data()` applies regular expressions to the combined subject and description.

| Type | What it detects | Example |
|---|---|---|
| `email` | Email addresses | `name@example.com` |
| `cpf` | Brazilian CPF numbers, with or without punctuation | `123.456.789-00` |
| `phone` | Brazilian phone numbers, optional +55 and area code | `(61) 91234-5678` |
| `credit_card_like_number` | Sequences of 13–16 digits | card-like numbers |
| `exposed_secret` | Phrases that disclose a secret | `my password is ...`, `token is ...` |

Design decision: the word "password" alone is **not** treated as sensitive data. A password reset request is operationally sensitive, but it does not expose a secret. Only an explicit disclosure (`my password is ...`) is flagged.

If any type is detected, the ticket is flagged and the detected types are recorded.

---

## 4. Ticket Classification

`classify_ticket()` uses keyword matching on the lowercased subject and description. Rules are evaluated **in order**, and the first match wins. Order is a control: security must be identified before anything else.

| Order | Category | Trigger keywords (examples) |
|---|---|---|
| 1 | Security Incident | phishing, suspicious, malware, security, breach, exposed password, my password is, credential(s), compromised |
| 2 | Access Request | grant access, request access, permission, shared folder, restricted folder |
| 3 | Access Support | password reset, forgot my password, senha, login, access issue, cannot access |
| 4 | Service Request | invoice, question, information, how to, request |
| 5 | Technical Incident | slow, error, crash, not working, issue, problem, vpn, unavailable, down |
| 6 | General Support | fallback when no rule matches |

`General Support` means the ticket could not be classified with confidence. It is treated as an ambiguous request and is always escalated (see Section 6).

Known limitation: keyword matching is order-sensitive. For example, `TCK-006` ("I cannot access the VPN") is classified as Access Support because rule 3 is evaluated before rule 5.

---

## 5. Priority Assignment

`assign_priority()` assigns one of three levels. The first matching rule wins.

| Order | Condition | Priority |
|---|---|---|
| 1 | Category is Security Incident | High |
| 2 | Sensitive data detected | High |
| 3 | Urgency keywords present: urgent, immediately, critical, cannot work, business stopped | High |
| 4 | Category is Access Request, Technical Incident or Access Support | Medium |
| 5 | Any other case | Low |

---

## 6. Human Escalation

`evaluate_escalation()` returns whether a human must review the ticket, plus the reason. The first matching rule wins.

| Order | Condition | Escalation reason recorded |
|---|---|---|
| 1 | Category is Security Incident | Security-related tickets require human review. |
| 2 | Category is Access Request | Access requests require authorization and human approval. |
| 3 | Sensitive data detected | Sensitive data was detected and must be reviewed by a human. |
| 4 | Priority is High | High priority tickets require human review. |
| 5 | Category is General Support | The ticket could not be classified with confidence and requires human review. |
| — | None of the above | No mandatory escalation rule was triggered. |

Principle: when risk or uncertainty exists, the agent escalates instead of automating.

---

## 7. Automation Decision

In this prototype, "automation" means **generating a safe informational response only**. It never means performing an action in a real system.

`evaluate_automation()` rules:

| Order | Condition | Result |
|---|---|---|
| 1 | Category is Security Incident or Access Request | Blocked: automation is blocked for this category |
| 2 | Sensitive data detected | Blocked |
| 3 | Human escalation required | Blocked |
| — | None of the above | Allowed: safe informational response |

---

## 8. Response Generation and Audit Logging

`generate_safe_response()` uses fixed templates:

- **Automation blocked:** the user is told the ticket was classified and will be reviewed by a human analyst before any action.
- **Automation allowed:** a category-specific template for Access Support, Technical Incident or Service Request. Templates never claim that a real action (password reset, account change) was performed.

`write_audit_log()` appends one JSON line per ticket to `audit_log.jsonl`, with:

- UTC timestamp;
- ticket ID, user, and **redacted** subject and description;
- the full analysis: category, priority, sensitive data flag and types, escalation decision and reason, automation decision and reason, generated response.

Redaction (`redact_text()`) replaces disclosed secrets, emails, CPF numbers, phone numbers and card-like numbers with placeholders such as `[REDACTED_SECRET]` and `[REDACTED_CPF]`. The log file is excluded from version control through `.gitignore`.

---

## 9. Planned vs Implemented Taxonomy

| Planned (project-scope.md) | Implemented (prototype) |
|---|---|
| Security Concern, Data Privacy Concern | Security Incident; privacy cases are covered by sensitive data detection |
| Access Management | Access Request |
| Password Reset | Access Support |
| System Incident, Application Error | Technical Incident |
| Service Request, General Inquiry | Service Request |
| Unknown or Ambiguous Request | General Support (always escalated) |
| P1 Critical / P2 High | High |
| P3 Medium | Medium |
| P4 Low | Low |

Separating Data Privacy from Security and restoring the four-level P1–P4 scale are listed as future improvements in `docs/implementation-roadmap.md`.

---

## 10. Validated Results

Running all 10 simulated tickets produces:

| Ticket | Category | Priority | Sensitive data | Escalated | Automation |
|---|---|---|---|---|---|
| TCK-001 | Access Support | Medium | — | No | Allowed |
| TCK-002 | Technical Incident | Medium | — | No | Allowed |
| TCK-003 | Security Incident | High | — | Yes | Blocked |
| TCK-004 | Access Request | Medium | — | Yes | Blocked |
| TCK-005 | Service Request | High | cpf | Yes | Blocked |
| TCK-006 | Access Support | Medium | — | No | Allowed |
| TCK-007 | Technical Incident | High | — | Yes | Blocked |
| TCK-008 | Service Request | High | email | Yes | Blocked |
| TCK-009 | Security Incident | High | exposed_secret | Yes | Blocked |
| TCK-010 | Service Request | Low | — | No | Allowed |

Summary: 10 processed, 6 escalated, 4 allowed, 6 blocked, 3 with sensitive data.

---

## 11. Limitations

- Keyword matching, not natural language understanding or a machine learning model.
- Sensitive data detection covers a small set of patterns and can produce false positives and false negatives.
- No confidence score: ambiguity is inferred only from the absence of a keyword match.
- No real integrations, authentication or approval workflows.

These limits are intentional. The goal of this phase is transparent, auditable decision logic, not classification accuracy.
