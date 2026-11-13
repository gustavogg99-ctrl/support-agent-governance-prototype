# Governance Controls

This document lists the controls of the prototype and separates what the code enforces from what exists only as a design intention, so that no reader mistakes one for the other. Every implemented control names the code that enforces it and the test that pins it.

## Principles

| Principle | What it means here |
|---|---|
| Human oversight | High-risk, sensitive and unclassifiable tickets go to a person, and a person approves every reply. |
| Fail closed | Any doubt (an invalid LLM answer, a disagreement, a failed draft check) removes the ticket from the automated path. |
| The rules win when they are stricter | The LLM may make a decision more cautious, never less. |
| Traceability | Every decision is logged with its reason, and both the rules' and the LLM's decisions are kept. |
| Data protection | Sensitive values are detected, block automation and are redacted before anything is written to a log. |

## Implemented controls

| Control | Enforced by | Test |
|---|---|---|
| Security incidents and access requests always escalate and never automate | `evaluate_escalation()`, `evaluate_automation()` | `test_security_and_access_requests_always_escalate_and_block_automation` |
| Sensitive data blocks automation in any category | `detect_sensitive_data()`, `evaluate_automation()` | `test_sensitive_data_blocks_automation_in_any_category` |
| High priority tickets escalate | `evaluate_escalation()` | `test_high_priority_escalates` |
| Unclassified tickets escalate | `evaluate_escalation()`, General Support | `test_unclassified_ticket_escalates` |
| Template responses never claim that an action was performed | `generate_safe_response()` | `test_allowed_response_does_not_claim_a_real_action` |
| The rules-only audit log is redacted | `redact_text()`, `write_audit_log()` | `test_log_entries_are_redacted_json_lines` |
| The LLM cannot release what the rules block | `combine()` | `test_llm_cannot_release_what_the_rules_block` |
| Any disagreement between rules and LLM goes to a person | `combine()` | `test_any_disagreement_goes_to_a_person` |
| An invalid LLM answer goes to a person | `parse_output()`, `classify()`, `combine()` | `test_invalid_replies`, `test_invalid_llm_output_goes_to_a_person` |
| No reply is drafted for a ticket that needs review | `draft_reply()` | `test_no_draft_is_requested_when_automation_is_blocked` |
| A draft with sensitive data, an action claim, no text or too much text is discarded | `check_draft()` | `test_unacceptable_drafts_are_replaced_by_the_handoff_message` |
| Nothing is sent without an explicit yes | `request_approval()` | `test_only_an_explicit_yes_sends` |
| The agent audit log keeps both decisions | `write_agent_audit_log()` | `test_audit_log_records_both_decisions_and_is_redacted` |
| The requester's name is not sent to the API | `build_user_message()` | `test_requester_name_is_not_sent` |
| The prompt is not tuned to the evaluation tickets | `prompts/classify_v2.md` | `test_v2_is_not_tuned_to_evaluation_tickets` |
| Published numbers match the committed run | `results/eval_results.json` | `PublishedResults` in `tests/test_evaluate.py` |
| Runtime logs and local secrets stay out of version control | `.gitignore` | none |

## Designed, not implemented

| Control | Status |
|---|---|
| A separate Critical (P1) priority level | The prototype uses High, Medium and Low. See `docs/decision-logic.md`, section 9. |
| A separate Data Privacy category | Privacy cases are caught through sensitive-data detection. |
| Confidence-based escalation | The rules have no confidence score. A ticket that matches no keyword escalates. |
| Detection of multi-user or business-critical impact | Only through urgency keywords such as "business stopped". |
| Detection of requests outside the approved scope | Only for access requests. |
| Asking the requester for missing information | Not implemented. An incomplete ticket goes to a person. |
| Telling the requester that a response is automated | Not implemented. |
| Masking sensitive values before the API call | Not implemented. Only the requester's name is left out. |
| Prompt-injection defence beyond the guardrail | Not implemented. The ticket is wrapped as data, and five injection tickets are in the evaluation set. |
| Log retention and access control | Local files, with no rotation and no access control. |

## What the agent must never do

The prototype has no integration that could do any of this, and a production version would have to keep it that way: approve or deny an access request, reset a password, close an incident, change a system or an account, or override an escalation rule.

## Risks considered

| Risk | Impact | Control |
|---|---|---|
| A ticket is misclassified | Wrong handling or delay | Unclassified tickets and any disagreement between rules and LLM go to a person |
| Priority is underestimated | A critical issue is not escalated | Security incidents and sensitive data are always High, and urgency keywords raise priority |
| Sensitive data is mishandled | Privacy exposure | Detection blocks automation, and logs are redacted |
| A reply gives unsafe guidance or claims an action | Operational or security impact | Fixed templates in the rules layer, draft checks and human approval in the agent |
| There is no audit trail | Decisions cannot be reviewed | One log line per ticket with both decisions and their reasons |
| The agent automates too much | Human accountability is bypassed | Automation is limited to a reply, and it needs the rules, the LLM and a person to agree |
| A ticket manipulates the LLM | The model returns what the ticket dictates | The rules decide independently, and the evaluation measures it (one such case passed with prompt `v1`) |
| The prototype is taken for a production system | False expectation of readiness | Limitations are stated in the README and next to the results |
