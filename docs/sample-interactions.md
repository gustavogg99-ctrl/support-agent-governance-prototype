# Sample Interactions

## 1. Purpose

This document provides sample command-line interactions for the AI Autonomous Support Agent prototype.

The examples show how the prototype is executed, how tickets are listed, how individual tickets are processed, and how invalid ticket IDs are handled.

These examples are based on local validation of the prototype.

---

## 2. Run All Sample Tickets

Command:

```bash
py src/prototype.py
```

Expected behavior:

- processes all simulated tickets;
- classifies each ticket;
- assigns priority;
- determines automation status;
- applies escalation rules;
- generates safe responses;
- creates or updates the local audit log;
- prints a final processing summary.

Validated summary:

```text
Total tickets processed: 10
Human escalation required: 6
Automation allowed: 4
Automation blocked: 6
Sensitive data cases: 3
```

---

## 3. List Available Tickets

Command:

```bash
py src/prototype.py --list
```

Expected behavior:

- lists the available simulated ticket IDs;
- allows the user to choose a specific ticket for processing.

This command is useful for reviewing the available test scenarios before processing an individual ticket.

---

## 4. Process a Specific Ticket

Command:

```bash
py src/prototype.py --ticket TCK-009
```

Expected behavior:

- processes only the selected ticket;
- displays the ticket classification;
- displays the assigned priority;
- displays whether automation is allowed or blocked;
- displays whether human escalation is required;
- generates a safe response;
- updates the local audit log.

---

## 5. Invalid Ticket Handling

Command:

```bash
py src/prototype.py --ticket TCK-999
```

Expected behavior:

- identifies that the ticket ID does not exist;
- prevents processing of an unknown ticket;
- returns a controlled validation message.

This demonstrates basic input validation and prevents the prototype from processing invalid ticket references.

---

## 6. Audit Log Behavior

When the prototype runs, it creates or updates:

```text
audit_log.jsonl
```

The audit log is generated locally and is ignored by Git through `.gitignore`.

This is intentional because logs may contain operational or sensitive information, even when redaction is applied.

The repository documents the audit logging behavior but does not commit runtime log files.

---

## 7. Governance Interpretation

The sample interactions demonstrate the following governance principles:

- not every ticket should be automated;
- sensitive data should trigger controls;
- high-risk cases should be escalated;
- automation should be conservative;
- audit logging should support traceability;
- runtime logs should not be committed to the repository;
- invalid inputs should be handled safely.

---

## 8. Prototype Boundary

These interactions are examples from a local prototype.

They do not represent:

- production service desk behavior;
- real user support data;
- real incident response;
- real approval workflows;
- real AI model output;
- enterprise monitoring;
- compliance certification.

The purpose is to demonstrate responsible automation design in a controlled and explainable way.
