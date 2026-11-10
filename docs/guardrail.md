# Guardrail and Human Approval

`src/agent.py` connects the LLM classifier to the deterministic rules and to a person. It covers tasks AGENT-V2-04 (rules as guardrail) and AGENT-V2-10 (suggested reply with human approval).

## Flow

```text
Ticket
├─ rules (src/prototype.py)           → category, priority, sensitive data, escalation, automation
└─ LLM (src/llm_classifier.py)        → category, priority, sensitive data (or ok=False)
        ↓
combine()  — the guardrail, a pure function
        ↓
human review? ── yes → fixed handoff message, no LLM draft, no approval prompt
        │
        no
        ↓
LLM drafts a reply → check_draft() → a person types "yes" to approve → simulated send
        ↓
agent_audit_log.jsonl: both decisions, disagreements, reasons, draft, human outcome (redacted)
```

## Guardrail rules (`combine`)

A person reviews the ticket, and automation is blocked, if **any** of these holds:

1. The rules escalate or block automation. Whatever the LLM says, it cannot release it.
2. The LLM's answer was rejected (invalid JSON, unknown value, refusal, truncation, API error).
3. Rules and LLM disagree on category, priority or sensitive data.
4. The LLM's own classification requires review under the policy (security incident, access request, unclassifiable, sensitive data or High priority).

Automation is allowed only when the rules allow it **and** none of the above holds.

`tests/test_agent.py` checks rule 1 exhaustively. For every evaluation and sample ticket the rules block, it tries all 36 possible LLM answers plus an invalid one, and automation is never allowed.

## Reply draft checks (`check_draft`)

The LLM drafts a reply only when automation is allowed. The draft is discarded, and the fixed handoff message is used instead, if:

- it is empty or longer than 1,200 characters;
- it contains sensitive data (the same detector as the rules);
- it claims an action was performed ("I have reset…", "has been granted…", "já redefini…", "foi liberado…"): a keyword heuristic in English and Portuguese, not a guarantee.

## Human approval

Nothing is sent without a person's explicit approval. Only `yes`/`y`/`sim`/`s` approves; anything else, including an empty answer, rejects. Sending is **simulated**: the prototype has no mail or ticketing integration.

## Design consequence

In this version the LLM can only make a decision more cautious. Automation needs the rules **and** the LLM to agree. So the LLM can lower unsafe automation, but it cannot raise the automation rate above what the rules allow. Where the rules are wrong but harmless (for example, they fall back to General Support), the ticket still goes to a person.

This is deliberate for a first version: the evaluation (Part 4) measures how much human review this costs. Letting the LLM decide some disagreements on its own would need that evidence first.

## Running it

```powershell
pip install -r requirements-llm.txt
$env:ANTHROPIC_API_KEY = "<your key>"
py src/agent.py --ticket EVAL-005 --model claude-haiku-5-5
```

It prints both decisions, the reasons and the draft, asks for approval, and appends to `agent_audit_log.jsonl`. The log is excluded from version control.
