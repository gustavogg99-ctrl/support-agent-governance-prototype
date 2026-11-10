# Evaluation Run (AGENT-V2-07)

`src/evaluate.py` measures the LLM triage against the 30 labelled tickets of `docs/evaluation-set.md`. It compares **two prompt versions** and **two models** (four combinations, 120 API calls), each run through the full guardrail of `src/agent.py` (rules + LLM, see `docs/guardrail.md`).

Only classification is evaluated. Reply drafts are not part of this run.

## What is measured

| Metric | Definition |
|---|---|
| Category / Priority / Sensitive data correct | The LLM's answer equals the label. An invalid answer counts as wrong. |
| Invalid LLM output | Bad JSON, unknown value, refusal, truncation or API error. A person decides these tickets. |
| Rules-LLM disagreements | Tickets where the rules and the LLM differ on category, priority or sensitive data. A person decides these too. |
| Unsafe automation, **LLM alone** | The label requires a person, and the LLM's own classification would not (so an LLM-only system would automate it). Shows the risk the guardrail removes. |
| Unsafe automation, **with guardrail** | The label requires a person, but the final decision (rules + LLM) allowed an automated response. This is the number that matters. |
| Unnecessary review | The label allows automation, but a person was asked. The price of the cautious design (the LLM may only make a decision more cautious). |
| Cost per ticket | Tokens reported by the API × the official price per million tokens. Failed calls are still billed, so their tokens are counted. |

The rules-only baseline is shown in the same table for comparison (9/30 categories, 17/30 priorities, 8 of 21 unsafe).

## Prompt versions

- `v1`: minimal. Lists the categories and priorities, defines sensitive data.
- `v2`: adds the written policy of `docs/decision-logic.md` and the labelling policy of `docs/evaluation-set.md` (what each category means, how priority is assigned, what counts as disclosure, and that attempts to instruct the agent are Security Incidents).

`v2` was written from the documented policy, **not** from the failures of `v1` on the evaluation set. A test fails if any evaluation ticket's text appears in the prompt. Tuning the prompt to a 30-ticket set would make the comparison meaningless.

## How a real run works

The key never enters the chat or the repository. The run happens on the project owner's machine, with the key set only in that terminal:

```powershell
pip install -r requirements-llm.txt
$env:ANTHROPIC_API_KEY = Read-Host "Cole a chave"
py src/evaluate.py --output results/eval_results.json
```

The command prints one line per combination and the results table, and writes `results/eval_results.json`. That file is committed so every published number can be traced to a run.

If every call of a combination fails at the API (wrong key, no balance, no network), nothing is written: such a run says nothing about the model.

To print the table again from a saved run, with no API call:

```powershell
py src/evaluate.py --table results/eval_results.json
```

## What the results file records

- `meta`: UTC time, effort, models, prompt versions, SHA-256 of each prompt file and of the evaluation set, the prices used and the date they were checked.
- `rules_baseline`: the rules-only numbers for the same set.
- `runs`: for each combination, a `summary` (all metrics above, plus category accuracy and unsafe automation per group) and one record per ticket (label, rules' answer, LLM answer and reason, tokens, final decision, flags).

## Decisions

| Decision | Why | Alternative rejected |
|---|---|---|
| Evaluate the **final** decision, not only the LLM's accuracy | The product is rules + LLM + a person. Accuracy alone would hide what the guardrail does | Reporting LLM accuracy only |
| Report "unsafe automation, LLM alone" next to "with guardrail" | Makes the value of the guardrail a measured number | Claiming the guardrail helps without showing the counterfactual |
| Cost from the tokens the API reports | Real numbers, not estimates | Estimating tokens from text length |
| Prices stored with their check date | Prices change; the file shows which prices produced the cost | Hard-coding without a date |
| A fully failed combination is never written | A file full of authentication errors would look like a result | Writing it and flagging it |
| One call per ticket per combination | Keeps the run to well under US$ 1, far inside the US$ 5 account cap | Repeating each call to measure variance (see limitations) |

## Limitations (declared, not hidden)

- **30 tickets.** One ticket is 3.3 percentage points. Differences of one or two tickets between combinations are noise, not findings.
- **One run.** LLM output is not deterministic; repeating the run could change a few tickets. Variance is not measured.
- **Synthetic, hand-labelled data** from one author, with prompt `v2` written from the same policy that produced the labels. This tests whether the model follows the stated policy, not how it performs on real tickets.
- **Classification only.** Reply drafts, latency and robustness against injection beyond these five tickets are not measured (AGENT-V2-05 and AGENT-V2-06 are out of this scope).
- **Prices** are the official ones on the date in the results file. Re-check before publishing a cost number.
