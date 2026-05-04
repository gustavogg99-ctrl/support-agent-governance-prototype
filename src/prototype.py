"""
AI Autonomous Support Agent - Local Prototype

This file implements a local Python prototype for simulated IT support ticket triage.

Prototype scope:
- Simulate support tickets
- Classify tickets
- Assign priority
- Detect simple sensitive data patterns
- Decide whether automation is allowed or blocked
- Decide whether human escalation is required
- Generate safe automated responses
- Create a local audit log

Important:
This is not a production system.
It does not connect to real systems.
It does not perform real password resets, approvals, access changes, or incident actions.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
AUDIT_LOG_FILE = PROJECT_ROOT / "audit_log.jsonl"


@dataclass
class Ticket:
    ticket_id: str
    user: str
    subject: str
    description: str


@dataclass
class TicketAnalysis:
    ticket_id: str
    category: str
    priority: str
    sensitive_data_detected: bool
    sensitive_data_types: list[str]
    human_escalation_required: bool
    escalation_reason: str
    automation_allowed: bool
    automation_decision_reason: str
    automated_response: str


SAMPLE_TICKETS = [
    Ticket(
        ticket_id="TCK-001",
        user="Maria Silva",
        subject="Password reset request",
        description="I forgot my password and cannot access the corporate portal.",
    ),
    Ticket(
        ticket_id="TCK-002",
        user="Joao Pereira",
        subject="Laptop is slow",
        description="My laptop is very slow when opening Excel and browser tabs.",
    ),
    Ticket(
        ticket_id="TCK-003",
        user="Ana Costa",
        subject="Possible phishing email",
        description="I received a suspicious email asking me to confirm my password urgently.",
    ),
    Ticket(
        ticket_id="TCK-004",
        user="Carlos Souza",
        subject="Request access to finance folder",
        description="Please grant me access to the restricted finance shared folder.",
    ),
    Ticket(
        ticket_id="TCK-005",
        user="Fernanda Lima",
        subject="Issue with invoice",
        description="My CPF is 123.456.789-00 and I need help with an invoice problem.",
    ),
]


def detect_sensitive_data(text: str) -> tuple[bool, list[str]]:
    """
    Detect simple sensitive data patterns.

    This prototype detects explicit sensitive data values, such as CPF,
    email addresses, phone numbers, and card-like numbers.

    It does not treat the word "password" alone as sensitive data.
    A password reset request is sensitive from an operational perspective,
    but it is not the same as the user exposing an actual secret.
    """

    patterns = {
        "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        "cpf": r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b",
        "phone": r"\b(?:\+55\s?)?(?:\(?\d{2}\)?\s?)?\d{4,5}-?\d{4}\b",
        "credit_card_like_number": r"\b(?:\d[ -]*?){13,16}\b",
        "exposed_secret": r"\b(my password is|minha senha é|token is|secret is|my token is)\b",
    }

    detected_types: list[str] = []

    for data_type, pattern in patterns.items():
        if re.search(pattern, text, flags=re.IGNORECASE):
            detected_types.append(data_type)

    return bool(detected_types), detected_types


def classify_ticket(subject: str, description: str) -> str:
    """
    Classify a ticket into a simulated ITSM category.

    The order matters:
    - Security incidents must be identified first.
    - Access requests must be separated from access support.
    - Service requests should be identified before generic technical issues.
    """

    text = f"{subject} {description}".lower()

    if any(keyword in text for keyword in ["phishing", "suspicious", "malware", "security", "breach"]):
        return "Security Incident"

    if any(keyword in text for keyword in ["grant access", "request access", "permission", "shared folder", "restricted folder"]):
        return "Access Request"

    if any(keyword in text for keyword in ["password reset", "forgot my password", "senha", "login", "access issue", "cannot access"]):
        return "Access Support"

    if any(keyword in text for keyword in ["invoice", "question", "information", "how to", "request"]):
        return "Service Request"

    if any(keyword in text for keyword in ["slow", "error", "crash", "not working", "issue", "problem"]):
        return "Technical Incident"

    return "General Support"


def assign_priority(
    category: str,
    sensitive_data_detected: bool,
    subject: str,
    description: str,
) -> str:
    """
    Assign priority based on category, sensitive data, and urgency indicators.
    """

    text = f"{subject} {description}".lower()

    urgent_keywords = ["urgent", "immediately", "critical", "cannot work", "business stopped"]
    urgent = any(keyword in text for keyword in urgent_keywords)

    if category == "Security Incident":
        return "High"

    if sensitive_data_detected:
        return "High"

    if urgent:
        return "High"

    if category == "Access Request":
        return "Medium"

    if category in ["Technical Incident", "Access Support"]:
        return "Medium"

    return "Low"


def evaluate_escalation(
    category: str,
    priority: str,
    sensitive_data_detected: bool,
) -> tuple[bool, str]:
    """
    Decide whether the ticket must be escalated to a human.
    """

    if category == "Security Incident":
        return True, "Security-related tickets require human review."

    if category == "Access Request":
        return True, "Access requests require authorization and human approval."

    if sensitive_data_detected:
        return True, "Sensitive data was detected and must be reviewed by a human."

    if priority == "High":
        return True, "High priority tickets require human review."

    return False, "No mandatory escalation rule was triggered."


def evaluate_automation(
    category: str,
    sensitive_data_detected: bool,
    human_escalation_required: bool,
) -> tuple[bool, str]:
    """
    Decide whether automation is allowed.

    In this prototype, automation means generating a safe response only.
    It never means performing real actions in real systems.
    """

    blocked_categories = ["Security Incident", "Access Request"]

    if category in blocked_categories:
        return False, "Automation is blocked for this category."

    if sensitive_data_detected:
        return False, "Automation is blocked when sensitive data is detected."

    if human_escalation_required:
        return False, "Automation is blocked because human escalation is required."

    return True, "Automation is allowed for a safe informational response."


def generate_safe_response(
    ticket: Ticket,
    category: str,
    priority: str,
    automation_allowed: bool,
    human_escalation_required: bool,
) -> str:
    """
    Generate a safe automated response.

    The response avoids exposing sensitive details and does not claim that
    real system actions were performed.
    """

    if not automation_allowed:
        return (
            f"Hello {ticket.user}, your request has been received and classified as "
            f"'{category}' with priority '{priority}'. Due to internal control rules, "
            "this ticket will be reviewed by a human support analyst before any action is taken."
        )

    if category == "Access Support":
        return (
            f"Hello {ticket.user}, your access support request has been received. "
            "Please follow the official password recovery or access support procedure. "
            "No account changes were performed by this prototype."
        )

    if category == "Technical Incident":
        return (
            f"Hello {ticket.user}, your technical issue has been received. "
            "Please restart the device, check your network connection, and document any error messages. "
            "If the issue continues, a support analyst should review the case."
        )

    if category == "Service Request":
        return (
            f"Hello {ticket.user}, your service request has been received. "
            "The support team will review the information and provide guidance according to internal procedures."
        )

    return (
        f"Hello {ticket.user}, your request has been received. "
        "A support analyst will review it if further action is required."
    )


def redact_text(text: str) -> str:
    """
    Redact basic sensitive data from audit logs.
    """

    redacted = text

    redacted = re.sub(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        "[REDACTED_EMAIL]",
        redacted,
    )

    redacted = re.sub(
        r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b",
        "[REDACTED_CPF]",
        redacted,
    )

    redacted = re.sub(
        r"\b(?:\+55\s?)?(?:\(?\d{2}\)?\s?)?\d{4,5}-?\d{4}\b",
        "[REDACTED_PHONE]",
        redacted,
    )

    redacted = re.sub(
        r"\b(?:\d[ -]*?){13,16}\b",
        "[REDACTED_NUMBER]",
        redacted,
    )

    return redacted


def write_audit_log(ticket: Ticket, analysis: TicketAnalysis) -> None:
    """
    Write a local audit log entry in JSON Lines format.

    The log is stored locally and uses redacted ticket text.
    """

    log_entry: dict[str, Any] = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "ticket": {
            "ticket_id": ticket.ticket_id,
            "user": ticket.user,
            "subject": redact_text(ticket.subject),
            "description": redact_text(ticket.description),
        },
        "analysis": asdict(analysis),
    }

    with AUDIT_LOG_FILE.open("a", encoding="utf-8") as log_file:
        log_file.write(json.dumps(log_entry, ensure_ascii=False) + "\n")


def analyze_ticket(ticket: Ticket) -> TicketAnalysis:
    """
    Run the full ticket analysis flow.
    """

    combined_text = f"{ticket.subject} {ticket.description}"

    sensitive_data_detected, sensitive_data_types = detect_sensitive_data(combined_text)

    category = classify_ticket(ticket.subject, ticket.description)

    priority = assign_priority(
        category=category,
        sensitive_data_detected=sensitive_data_detected,
        subject=ticket.subject,
        description=ticket.description,
    )

    human_escalation_required, escalation_reason = evaluate_escalation(
        category=category,
        priority=priority,
        sensitive_data_detected=sensitive_data_detected,
    )

    automation_allowed, automation_decision_reason = evaluate_automation(
        category=category,
        sensitive_data_detected=sensitive_data_detected,
        human_escalation_required=human_escalation_required,
    )

    automated_response = generate_safe_response(
        ticket=ticket,
        category=category,
        priority=priority,
        automation_allowed=automation_allowed,
        human_escalation_required=human_escalation_required,
    )

    return TicketAnalysis(
        ticket_id=ticket.ticket_id,
        category=category,
        priority=priority,
        sensitive_data_detected=sensitive_data_detected,
        sensitive_data_types=sensitive_data_types,
        human_escalation_required=human_escalation_required,
        escalation_reason=escalation_reason,
        automation_allowed=automation_allowed,
        automation_decision_reason=automation_decision_reason,
        automated_response=automated_response,
    )


def print_analysis(ticket: Ticket, analysis: TicketAnalysis) -> None:
    """
    Print the ticket analysis result to the terminal.
    """

    print("=" * 80)
    print(f"Ticket ID: {ticket.ticket_id}")
    print(f"User: {ticket.user}")
    print(f"Subject: {ticket.subject}")
    print("-" * 80)
    print(f"Category: {analysis.category}")
    print(f"Priority: {analysis.priority}")
    print(f"Sensitive Data Detected: {analysis.sensitive_data_detected}")
    print(f"Sensitive Data Types: {', '.join(analysis.sensitive_data_types) or 'None'}")
    print(f"Human Escalation Required: {analysis.human_escalation_required}")
    print(f"Escalation Reason: {analysis.escalation_reason}")
    print(f"Automation Allowed: {analysis.automation_allowed}")
    print(f"Automation Decision Reason: {analysis.automation_decision_reason}")
    print("-" * 80)
    print("Automated Response:")
    print(analysis.automated_response)
    print("=" * 80)
    print()

def print_execution_summary(analyses: list[TicketAnalysis]) -> None:
    """
    Print an execution summary for the local prototype run.
    """

    total_tickets = len(analyses)
    escalated_tickets = sum(1 for analysis in analyses if analysis.human_escalation_required)
    automation_allowed = sum(1 for analysis in analyses if analysis.automation_allowed)
    automation_blocked = total_tickets - automation_allowed
    sensitive_data_cases = sum(1 for analysis in analyses if analysis.sensitive_data_detected)

    print("=" * 80)
    print("Execution Summary")
    print("-" * 80)
    print(f"Total tickets processed: {total_tickets}")
    print(f"Human escalation required: {escalated_tickets}")
    print(f"Automation allowed: {automation_allowed}")
    print(f"Automation blocked: {automation_blocked}")
    print(f"Sensitive data cases: {sensitive_data_cases}")
    print("=" * 80)
    print()

def main() -> None:
    """
    Execute the local prototype using simulated tickets.
    """

    print("AI Autonomous Support Agent - Local Prototype")
    print("Running simulated ticket analysis...")
    print()

    analyses: list[TicketAnalysis] = []

    for ticket in SAMPLE_TICKETS:
        analysis = analyze_ticket(ticket)
        analyses.append(analysis)

        write_audit_log(ticket, analysis)
        print_analysis(ticket, analysis)

    print_execution_summary(analyses)

    print(f"Audit log created or updated at: {AUDIT_LOG_FILE}")


if __name__ == "__main__":
    main()