## Project rules (Support Agent Governance Prototype, by Gustavo Rodrigues)

Read these before changing anything:

- `docs/ROADMAP.md`: current status, how we work, and what's next. **Start here.**
- `docs/decision-logic.md`: the deterministic rules as implemented. They are the guardrail; do not change them without changing their tests.
- `docs/evaluation-set.md`: the labelled evaluation set and the labelling policy.

Conventions:
- **Nothing in the README or docs that the code does not prove.** Every number published comes from a script in this repository and is pinned by a test or produced by an evaluation run whose output is committed.
- **Tests never call the API.** LLM calls are behind a client interface; tests use simulated responses. The core and the tests use the Python standard library only, and CI installs nothing.
- **The API key never enters the chat or the repository.** Real evaluation runs happen on Gustavo's machine with `ANTHROPIC_API_KEY` set in his terminal; he brings the results back.
- **Data is 100% synthetic.** No real names, tickets, documents, CPFs, card numbers or addresses.
- **The rules always win when they are stricter.** The LLM may make a decision more cautious, never less.
- Run `python -m unittest discover -s tests -v` before committing. CI must be green before merge.
- One part = one branch + one pull request.
