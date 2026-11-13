"""
Deterministic rules for IT support ticket triage: the guardrail of this project.

Each simulated ticket goes through sensitive-data detection, classification,
priority, escalation and automation rules (docs/decision-logic.md), gets a
fixed-template response and one redacted line in a local audit log.

Nothing here touches a real system: no password is reset, no access is granted
and no incident is closed.

    py src/prototype.py [--list | --ticket TCK-009]
"""

from __future__ import annotations

import json
import re
import sys
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
    Ticket(
        ticket_id="TCK-006",
        user="Rafael Mendes",
        subject="VPN connection issue",
        description="I cannot access the VPN from home and need support to connect.",
    ),
    Ticket(
        ticket_id="TCK-007",
        user="Patricia Gomes",
        subject="Critical system unavailable",
        description="The customer service system is not working and business stopped.",
    ),
    Ticket(
        ticket_id="TCK-008",
        user="Bruno Almeida",
        subject="Update my contact information",
        description="Please update my email to bruno.almeida@example.com in the support records.",
    ),
    Ticket(
        ticket_id="TCK-009",
        user="Larissa Rocha",
        subject="Exposed password in request",
        description="My password is Company123 and I need help changing it urgently.",
    ),
    Ticket(
        ticket_id="TCK-010",
        user="Eduardo Martins",
        subject="How to request a new monitor",
        description="I would like to know how to request a new monitor for my workstation.",
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


# Checked in order: the first category with a matching keyword wins, so
# security comes before everything else.
CATEGORY_KEYWORDS = (
    ("Security Incident", (
        "phishing", "suspicious", "malware", "security", "breach", "exposed password",
        "my password is", "minha senha é", "credential", "credentials", "compromised",
    )),
    ("Access Request", ("grant access", "request access", "permission", "shared folder", "restricted folder")),
    ("Access Support", ("password reset", "forgot my password", "senha", "login", "access issue", "cannot access")),
    ("Service Request", ("invoice", "question", "information", "how to", "request")),
    ("Technical Incident", ("slow", "error", "crash", "not working", "issue", "problem", "vpn", "unavailable", "down")),
)
URGENT_KEYWORDS = ("urgent", "immediately", "critical", "cannot work", "business stopped")


def classify_ticket(subject: str, description: str) -> str:
    """Keyword match on subject and description. A ticket that matches nothing is General Support."""
    text = f"{subject} {description}".lower()
    for category, keywords in CATEGORY_KEYWORDS:
        if any(keyword in text for keyword in keywords):
            return category
    return "General Support"


def assign_priority(
    category: str,
    sensitive_data_detected: bool,
    subject: str,
    description: str,
) -> str:
    text = f"{subject} {description}".lower()

    if category == "Security Incident" or sensitive_data_detected or any(k in text for k in URGENT_KEYWORDS):
        return "High"
    if category in ("Access Request", "Technical Incident", "Access Support"):
        return "Medium"
    return "Low"


def evaluate_escalation(
    category: str,
    priority: str,
    sensitive_data_detected: bool,
) -> tuple[bool, str]:
    """Whether a person must review the ticket, and the reason that goes to the audit log."""
    if category == "Security Incident":
        return True, "Security-related tickets require human review."

    if category == "Access Request":
        return True, "Access requests require authorization and human approval."

    if sensitive_data_detected:
        return True, "Sensitive data was detected and must be reviewed by a human."

    if priority == "High":
        return True, "High priority tickets require human review."

    if category == "General Support":
        return True, "The ticket could not be classified with confidence and requires human review."

    return False, "No mandatory escalation rule was triggered."


def evaluate_automation(
    category: str,
    sensitive_data_detected: bool,
    human_escalation_required: bool,
) -> tuple[bool, str]:
    """Whether an automated response is allowed. Automation never means an action in a real system."""
    if category in ("Security Incident", "Access Request"):
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
) -> str:
    """A fixed template. It never claims that an action was performed in a real system."""
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

    This prototype redacts common sensitive data patterns before writing
    ticket subject and description fields to the local audit log.
    """

    redacted = text

    redacted = re.sub(
        r"\b(my password is|minha senha é|token is|secret is|my token is)\s*:?\s*\S+",
        r"\1 [REDACTED_SECRET]",
        redacted,
        flags=re.IGNORECASE,
    )

    redacted = re.sub(
        r"\b(password|senha|token|secret)\s*[:=]\s*\S+",
        r"\1=[REDACTED_SECRET]",
        redacted,
        flags=re.IGNORECASE,
    )

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
    """Append one JSON line to the local audit log, with the ticket text redacted."""
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
    """Run every rule on one ticket. Sensitive data comes first: priority, escalation and automation depend on it."""
    sensitive, sensitive_types = detect_sensitive_data(f"{ticket.subject} {ticket.description}")
    category = classify_ticket(ticket.subject, ticket.description)
    priority = assign_priority(category, sensitive, ticket.subject, ticket.description)
    escalate, escalation_reason = evaluate_escalation(category, priority, sensitive)
    automate, automation_reason = evaluate_automation(category, sensitive, escalate)

    return TicketAnalysis(
        ticket_id=ticket.ticket_id,
        category=category,
        priority=priority,
        sensitive_data_detected=sensitive,
        sensitive_data_types=sensitive_types,
        human_escalation_required=escalate,
        escalation_reason=escalation_reason,
        automation_allowed=automate,
        automation_decision_reason=automation_reason,
        automated_response=generate_safe_response(ticket, category, priority, automate),
    )


def print_analysis(ticket: Ticket, analysis: TicketAnalysis) -> None:
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
    allowed = sum(analysis.automation_allowed for analysis in analyses)

    print("=" * 80)
    print("Execution Summary")
    print("-" * 80)
    print(f"Total tickets processed: {len(analyses)}")
    print(f"Human escalation required: {sum(analysis.human_escalation_required for analysis in analyses)}")
    print(f"Automation allowed: {allowed}")
    print(f"Automation blocked: {len(analyses) - allowed}")
    print(f"Sensitive data cases: {sum(analysis.sensitive_data_detected for analysis in analyses)}")
    print("=" * 80)
    print()


def list_sample_tickets(tickets: list[Ticket]) -> None:
    print("Available simulated tickets:")
    print("-" * 80)

    for ticket in tickets:
        print(f"{ticket.ticket_id} - {ticket.subject}")

    print("-" * 80)


def find_ticket_by_id(ticket_id: str, tickets: list[Ticket]) -> Ticket | None:
    wanted = ticket_id.strip().upper()
    return next((ticket for ticket in tickets if ticket.ticket_id.upper() == wanted), None)


def select_tickets_from_arguments(arguments: list[str]) -> list[Ticket] | None:
    """
    The tickets to process, or None when there is nothing to run.

    No argument runs every sample ticket, --list prints them and
    --ticket TCK-001 runs one.
    """
    if not arguments:
        return SAMPLE_TICKETS

    command = arguments[0].strip().lower()

    if command in ["--list", "list"]:
        list_sample_tickets(SAMPLE_TICKETS)
        return None

    if command in ["--ticket", "ticket"]:
        if len(arguments) < 2:
            print("Missing ticket ID.")
            print("Example: py src/prototype.py --ticket TCK-009")
            return None

        selected_ticket = find_ticket_by_id(arguments[1], SAMPLE_TICKETS)

        if selected_ticket is None:
            print(f"Ticket ID '{arguments[1]}' was not found.")
            print("Use --list to see available simulated tickets.")
            return None

        return [selected_ticket]

    print(f"Unknown argument: {arguments[0]}")
    print("Available commands:")
    print("  py src/prototype.py")
    print("  py src/prototype.py --list")
    print("  py src/prototype.py --ticket TCK-009")

    return None


def main() -> None:
    print("Support Agent Governance Prototype")

    tickets_to_process = select_tickets_from_arguments(sys.argv[1:])

    if tickets_to_process is None:
        return

    print("Running simulated ticket analysis...")
    print()

    analyses: list[TicketAnalysis] = []

    for ticket in tickets_to_process:
        analysis = analyze_ticket(ticket)
        analyses.append(analysis)

        write_audit_log(ticket, analysis)
        print_analysis(ticket, analysis)

    print_execution_summary(analyses)

    print(f"Audit log created or updated at: {AUDIT_LOG_FILE}")


if __name__ == "__main__":
    main()
