# Project Scope — Support Agent Governance Prototype

> **Note:** this is the Phase 1 planning document. It defines the target taxonomy (9 categories, P1–P4 priorities). The prototype implements a simplified version (6 categories, High / Medium / Low). The implemented rules and the mapping between both are in `docs/decision-logic.md`.

## 1. Project Overview

The Support Agent Governance Prototype is a local prototype designed to simulate the governance layer of an AI-assisted support triage workflow in a corporate IT environment.

The agent receives support ticket descriptions, classifies the request, assigns an initial priority level, identifies potential risk indicators, decides whether the case can receive an automated response, and determines when human escalation is required.

The project focuses on functional scope, governance, risk control, and decision logic. It does not aim to replace human support analysts or operate as a production system.

This prototype is intended for portfolio demonstration, GitHub documentation, LinkedIn positioning, and interview discussions related to GRC, AI Governance, Technology Risk, ITSM, and automation.

---

## 2. Problem Statement

Corporate support teams often receive a high volume of tickets with different levels of urgency, complexity, risk, and business impact.

Manual triage can be inconsistent, slow, and highly dependent on the experience of each analyst. This may result in delayed escalation, incorrect prioritization, inconsistent responses, poor visibility, and limited auditability.

The problem this project addresses is the lack of a standardized first-level triage process that can classify requests, detect risk indicators, prioritize incidents, and support human decision-making in a controlled and auditable way.

---

## 3. Project Objective

The objective of this project is to design and document a functional prototype of the governance layer of an AI-assisted support agent, capable of:

1. receiving simulated support tickets;
2. classifying the ticket into predefined categories;
3. assigning an initial priority level;
4. identifying potential security, privacy, or operational risks;
5. determining whether automated response is appropriate;
6. escalating high-risk or ambiguous cases to a human analyst;
7. documenting the decision rationale for audit and governance purposes.

The agent must operate as a controlled decision-support layer, not as an unrestricted autonomous system.

---

## 4. Simulated Target Users

The prototype simulates interaction between the following user groups:

### 4.1 End User

The employee or business user who submits a support request.

Examples:

- employee unable to access a system;
- user requesting password reset;
- user reporting application errors;
- employee reporting a suspicious email;
- business user requesting support for a service.

### 4.2 Support Analyst

The human analyst responsible for reviewing tickets, validating classifications, handling escalated cases, and taking operational actions when needed.

### 4.3 ITSM Manager

The manager responsible for service quality, prioritization rules, incident management, support performance, and escalation governance.

### 4.4 Risk, Compliance, or Governance Reviewer

The stakeholder responsible for reviewing audit logs, escalation decisions, sensitive data handling, and AI governance controls.

---

## 5. Types of Tickets the Agent Will Receive

The prototype will process simulated support tickets related to:

1. access issues;
2. password reset requests;
3. application errors;
4. system incidents;
5. service requests;
6. security concerns;
7. data privacy concerns;
8. general support questions;
9. ambiguous or incomplete requests.

The tickets will be fictional and must not contain real personal, financial, confidential, or production data.

---

## 6. Classification Categories

The agent will classify tickets into the following categories:

### 6.1 Access Management

Requests related to user access, permissions, account unlocks, or inability to access systems.

### 6.2 Password Reset

Requests related to forgotten passwords, expired passwords, or login credential issues.

### 6.3 System Incident

Issues involving outages, unavailability, degraded performance, or business-critical system disruption.

### 6.4 Application Error

Issues involving application bugs, error messages, failed transactions, or unexpected application behavior.

### 6.5 Service Request

Standard requests for information, configuration, support, or non-urgent operational assistance.

### 6.6 Security Concern

Tickets involving suspicious activity, phishing, malware, unauthorized access, credential exposure, or potential cyber risk.

### 6.7 Data Privacy Concern

Tickets involving personal data, sensitive information, data exposure, privacy incidents, or improper data handling.

### 6.8 General Inquiry

Low-risk informational requests that do not require technical action or escalation.

### 6.9 Unknown or Ambiguous Request

Tickets that do not contain enough information to be safely classified.

---

## 7. Priority Levels

The prototype will use four priority levels.

### P1 — Critical

Used for tickets involving severe business impact, major outage, confirmed or suspected security incident, data exposure, or critical operational disruption.

Examples:

- core system unavailable for multiple users;
- suspected data breach;
- ransomware or malware report;
- unauthorized access to sensitive systems;
- business-critical process stopped.

### P2 — High

Used for urgent tickets with significant impact, but without confirmed major outage or severe security/privacy impact.

Examples:

- important user or team unable to access a key system;
- repeated application failure affecting business operations;
- urgent access issue blocking work;
- incident affecting a limited but important group.

### P3 — Medium

Used for standard support issues with moderate impact and no immediate critical risk.

Examples:

- single-user application error;
- routine access request;
- non-critical service issue;
- standard operational support request.

### P4 — Low

Used for informational, low-impact, or non-urgent requests.

Examples:

- general questions;
- how-to guidance;
- minor support requests;
- low-impact service inquiries.

---

## 8. Initial Escalation Rules

The agent must escalate a ticket to a human analyst when one or more of the following conditions are present:

1. the ticket indicates a security concern;
2. the ticket indicates a data privacy concern;
3. the ticket describes a system outage or critical business impact;
4. the ticket contains sensitive data;
5. the ticket involves possible credential exposure;
6. the ticket is ambiguous or lacks enough information;
7. the ticket requires privileged access;
8. the ticket may require operational approval;
9. the ticket involves a user expressing high urgency without enough context;
10. the agent cannot classify the request with reasonable confidence.

The escalation principle is conservative: when risk or uncertainty exists, the agent should escalate instead of automating.

---

## 9. Initial Automation Rules

The agent may generate an automated response only when all of the following conditions are met:

1. the ticket is low-risk;
2. the category is clear;
3. the priority is P3 or P4;
4. no sensitive data is detected;
5. no security or privacy concern is present;
6. no privileged action is required;
7. the response can be generated from a predefined safe template;
8. human escalation is not required.

Automated responses should provide guidance, acknowledge the request, or ask for non-sensitive clarification when appropriate.

The agent must not claim that an issue has been resolved unless the prototype explicitly simulates that outcome.

---

## 10. Agent Boundaries

The agent must not:

1. access real corporate systems;
2. modify user accounts;
3. reset real passwords;
4. approve access requests;
5. close real incidents;
6. process real personal data;
7. process real financial data;
8. process real confidential business data;
9. make irreversible decisions;
10. bypass human review for high-risk tickets;
11. provide security instructions that could increase risk;
12. hide or delete decision logs;
13. operate without clear escalation rules.

The agent is a prototype for decision-support, not a production-grade autonomous system.

---

## 11. Governance Principles

The project will demonstrate the following governance principles:

### 11.1 Human Oversight

High-risk, ambiguous, sensitive, or critical cases must be escalated to a human analyst.

### 11.2 Auditability

The agent should maintain a record of its classification, priority assignment, escalation decision, and decision rationale.

### 11.3 Transparency

The agent should provide a clear explanation for why a ticket was classified in a certain way.

### 11.4 Data Minimization

The prototype should avoid collecting or repeating unnecessary personal, sensitive, or confidential information.

### 11.5 Conservative Automation

The agent should prefer escalation over automation when the risk level is unclear.

### 11.6 Risk-Based Decision-Making

The agent should consider urgency, impact, sensitivity, and operational risk before deciding whether to automate or escalate.

---

## 12. Prototype Success Criteria

The prototype will be considered successful if it can demonstrate the following capabilities:

1. classify simulated tickets into predefined categories;
2. assign consistent priority levels;
3. identify tickets requiring human escalation;
4. distinguish low-risk tickets from high-risk tickets;
5. generate safe automated responses for eligible tickets;
6. avoid automation when sensitive, ambiguous, or high-risk content is present;
7. produce decision rationale for each ticket;
8. support auditability and governance review;
9. clearly distinguish prototype limitations from production requirements;
10. support a professional portfolio narrative for GRC, AI Governance, Technology Risk, ITSM, and automation roles.

---

## 13. Out of Scope

The following items are outside the scope of this phase and this initial prototype:

1. production deployment;
2. real ITSM platform integration;
3. Microsoft Copilot Studio;
4. Power Automate;
5. Azure services;
6. Microsoft 365 Developer environment;
7. user authentication;
8. database persistence;
9. external API calls;
10. machine learning model training;
11. real ticket processing;
12. real customer data usage;
13. real incident resolution;
14. real access provisioning;
15. legal or regulatory compliance certification.

These items may be considered in a future roadmap, but they are not part of the initial prototype.

---

## 14. Final Deliverables of Phase 1

The final deliverables of Phase 1 are:

1. a clear problem statement;
2. a defined project objective;
3. a simulated target user model;
4. a list of supported ticket types;
5. a classification taxonomy;
6. initial priority levels;
7. initial escalation rules;
8. initial automation rules;
9. agent boundaries and limitations;
10. prototype success criteria;
11. documented scope for use in the repository.

---

## 15. Phase 1 Conclusion

Phase 1 defines the functional scope of the Support Agent Governance Prototype.

At this stage, the project has a clear purpose, target scenario, ticket taxonomy, priority structure, escalation principles, automation limits, governance principles, and success criteria.

No code, technical architecture, or platform integration is defined in this phase.

The next phase should focus on architecture and governance design, including how the agent workflow, decision points, audit logs, and human escalation controls will be represented.