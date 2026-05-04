# Decision Logic

## 1. Purpose

This document describes the decision logic used by the AI Autonomous Support Agent prototype.

The goal is to explain how the prototype classifies support tickets, assigns priorities, detects simple sensitive data patterns, determines whether automation is allowed, and decides when human escalation is required.

This logic is intentionally rule-based and deterministic. It is designed for learning, governance demonstration, and portfolio purposes.

---

## 2. Decision Flow Overview

The prototype follows this decision flow:

```text
Ticket Received
↓
Sensitive Data Detection
↓
Ticket Classification
↓
Priority Assignment
↓
Automation Eligibility Check
↓
Escalation Decision
↓
Safe Response Generation
↓
Audit Log Entry
```

The agent does not make unrestricted autonomous decisions. Every automated action is limited by predefined business rules and governance boundaries.

---

## 3. Ticket Classification

Each ticket is classified into a predefined support category.

The simulated categories include:

- Access Management
- Password Reset
- System Incident
- Application Error
- Service Request
- Security Concern
- Data Privacy Concern
- General Inquiry
- Unknown or Ambiguous Request

The classification logic is based on simple keyword and pattern matching. This keeps the prototype transparent and easy to audit.

---

## 4. Priority Levels

The prototype assigns one of four priority levels:

| Priority | Meaning | Example |
|---|---|---|
| P1 - Critical | Severe business impact or security risk | Major outage, suspected account compromise |
| P2 - High | Important issue requiring urgent review | Repeated access failure, sensitive request |
| P3 - Medium | Standard support issue | Application issue, service request |
| P4 - Low | Low-risk inquiry or non-urgent request | General question, informational request |

Priority assignment is based on ticket content, category, risk indicators, and sensitive data detection.

---

## 5. Sensitive Data Detection

The prototype includes simple detection for sensitive data patterns.

Examples of sensitive data indicators include:

- passwords;
- credentials;
- tokens;
- personal data;
- confidential information;
- access-related secrets.

When sensitive data is detected, the ticket is flagged and automation is blocked.

The audit log applies redaction to reduce exposure of sensitive information.

---

## 6. Automation Eligibility

Automation is allowed only when the ticket is considered low-risk and does not contain sensitive data.

Automation may be allowed for:

- general inquiries;
- low-risk service requests;
- basic informational requests;
- non-sensitive support guidance.

Automation is blocked when the ticket includes:

- sensitive data;
- security concerns;
- privacy concerns;
- critical incidents;
- ambiguous or risky requests;
- access-related issues requiring validation;
- any condition requiring human judgment.

---

## 7. Human Escalation Rules

Human escalation is required when one or more of the following conditions are met:

- sensitive data is detected;
- the ticket is classified as a security concern;
- the ticket is classified as a data privacy concern;
- the ticket is classified as a critical system incident;
- the ticket involves access risk;
- the request is ambiguous;
- automation is not explicitly allowed;
- the issue may require business, compliance, or security review.

The purpose of escalation is to preserve human oversight for sensitive, critical, or high-risk scenarios.

---

## 8. Response Generation

The prototype generates safe automated responses only when automation is allowed.

The response avoids:

- requesting sensitive data;
- exposing internal rules;
- confirming risky actions;
- making irreversible decisions;
- pretending that human validation occurred.

If escalation is required, the response informs the user that the ticket must be reviewed by a human support analyst.

---

## 9. Audit Logging Logic

For each processed ticket, the prototype creates an audit log entry.

The audit log records:

- ticket ID;
- category;
- priority;
- escalation decision;
- automation status;
- sensitive data flag;
- generated response;
- redacted ticket content.

The audit log is generated locally as:

```text
audit_log.jsonl
```

This file is intentionally excluded from version control because runtime logs may contain operational or sensitive information.

---

## 10. Prototype Limitations

The decision logic is intentionally simplified.

It does not include:

- machine learning classification;
- natural language understanding;
- real user authentication;
- real service desk integration;
- real approval workflows;
- enterprise monitoring;
- advanced data loss prevention;
- legal or regulatory validation;
- production-grade security controls.

A production implementation would require stronger controls, formal testing, secure integrations, monitoring, access management, and governance review.

---

## 11. Summary

The decision logic demonstrates how an AI-enabled support workflow can be designed with clear boundaries.

The prototype prioritizes:

- transparency;
- auditability;
- human oversight;
- conservative automation;
- sensitive data protection;
- governance-oriented design.

The purpose is to show that automation should support operational efficiency without removing human responsibility from high-risk decisions.
