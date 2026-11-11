---
name: decision-ledger-workflow
description: Perform evidence-bounded semantic screening, candidate audit, classification, and final-report content assembly for one date supplied by daily-decision-training-pipeline. This is a component Skill; it must not select dates, ask users closure questions, persist a final report, run registry/build operations, or complete the full workflow.
metadata:
  version: "2.1.0"
  status: component_only
  orchestrator: daily-decision-training-pipeline
  updated: "2026-09-07"
---

# Decision Ledger Workflow v2.1.0

Convert the supplied daily record into evidence-traceable semantic artifacts. Preserve the raw record and return control to `daily-decision-training-pipeline` after each requested stage.

## Invocation boundary

- Normal invocation is by `daily-decision-training-pipeline`; direct use is limited to component maintenance or testing explicitly requested by the user.
- Require a date, source paths, observation boundary, requested stage, and allowed working-file targets from the orchestrator.
- Do not choose a different date, synchronize or transition the registry, ask the user questions, persist/replace a final report, run the derived builder, or declare workflow completion.

Before creating or updating data, read [references/data-contracts.md](references/data-contracts.md).

## Inputs and folder check

Require the raw daily submission. Treat it as the only behavioral fact source. A first-pass analysis may identify leads but cannot override the raw record. Live prediction and prediction scoring are outside this component.

Before writing, compare the date in the raw record with the destination folder date. If they differ, create a new date-named folder for the record date; do not mix days. Keep source records immutable.

## Workflow

### 1. Initial screening

Extract at most two `decision_candidates` from the raw submission.

For a formal candidate, require all of the following:

- one observable choice in one defined or explicitly coarse time window;
- at least two real, mutually exclusive options for the same target;
- an actual choice that maps to exactly one option;
- decision-preceding observations with source traces.

Assign the standard action-level `decision_family` before asking closure questions: `start_vs_defer`, `continue_vs_stop`, `consume_vs_abstain`, `confront_vs_avoid`, `timing_choice`, or `plan_a_vs_plan_b`. Classify the observable trade-off, not incidental context words: an eat/not-eat choice remains `consume_vs_abstain` even if the question also says “下班后”. This is distinct from `decision_domain` and is never a causal label.

Predict the next action when sequential actions could both happen. For example, use “in the next 15 minutes, what happens first?” rather than “rest or check tasks.” `other_or_unknown` is allowed only as a residual option that is mutually exclusive with named options.

Put mentions with incomplete options, outcome, or time boundary outside the formal candidates. Do not invent missing labels.

### 2. Candidate audit

Audit every candidate before it enters the ledger. Check:

1. actual-choice evidence;
2. mutually exclusive, real options;
3. decision time, cutoff, and observation-window precision;
4. separation of choice, immediate outcome, and delayed unknowns;
5. pre-decision chronology and source provenance;
6. duplicated or overly fine-grained same-day entries;
7. leakage from analysis text, future facts, or causal interpretation.

Use `approved`, `revise`, `move_to_coarse`, or `reject`. Do not call a known outcome “unresolved” merely because its time precision is weak.

### 3. Closure requirements

Return a closure requirement only when a missing fact can change a label, time window, task state, immediate outcome, availability, or evidence eligibility. Propose at most three concise factual questions, but do not ask the user; `daily-decision-closure` handles the interaction through the orchestrator.

For every proposed question, return `question_id`, `question_text`, target field, source trace, answer format, and the classification effect. Do not fabricate an answer or timestamp.

Do not ask for motives, personality explanations, or causal reasons.

### 4. Final classification and report

Classify each item as one of the following:

- `decision-ledger-1.0` record: time-bounded observable choice with mutually exclusive options and an actual choice.
- `coarse_decision_record`: outcome and/or options are known, but precision is insufficient for a strict ledger or backtest. State the exact missing fields and `record_status`.
- `unresolved_decision_mention`: a recorded trade-off without an actual outcome.
- task-execution record: a task state without evidence of a genuine choice point.

Use `final-daily-decision-report-1.0` for the root report. Preserve `decision-ledger-1.0` only inside formal decision records.

Record time precision explicitly. An approximate time may use an ISO anchor only with `time_precision: "approximate"` and a `time_basis`; never represent it as an exact observed time. Keep a parseable cutoff timestamp separate from its precision label when needed.

Use only these evidence classes:

- `raw_fact`;
- `user_stated_reason`;
- `post_analysis_supplement`;
- `model_hypothesis`.

Model hypotheses are optional, low confidence, non-causal, and must include an evidence basis and falsification condition. If none are justified, emit an empty array.

Use eligibility labels that distinguish research use:

- `pattern_analysis_eligible`;
- `coarse_training_eligible`;
- `strict_backtest_eligible`;
- `causal_claim_eligible`.

For every formal ledger record, populate the fixed fields in the reference contract at first creation, even when a value is `unknown`. Copy `state_capture_disposition` only from the matching user decision block. Use `analysis_tier: strict` only if strict backtesting is actually allowed; otherwise use `historical_pattern` when pattern analysis is allowed. Do not place coarse or unresolved items in `closed_decisions` merely to fill the schema.

Preserve the exact source task status in final task records. Canonicalization is a derived-layer operation; use the mapping in the reference contract and never erase a more precise observable boundary.

Do not score predictions or produce forecasts in this component.

## Output and validation

Write separate derived JSON files for screening, audit, and user supplements in the date-scoped working folder. Keep prior-stage artifacts as provenance rather than overwriting raw records. Use the same field names from the formal decision contract in the candidate, audit, closure, and final-report artifacts whenever the field applies; only the evidence-rich final record may additionally retain nested source objects.

Return assembled `final-daily-decision-report-1.0` content to the orchestrator. Only `daily-decision-training-pipeline` may perform provenance completion, immutability comparison, final persistence, and registry transition.

Return JSON only. Validate every working JSON file. Do not report the date as finalized or built.
