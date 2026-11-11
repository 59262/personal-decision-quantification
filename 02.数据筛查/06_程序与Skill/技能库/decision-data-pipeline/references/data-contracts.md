# Data contracts

## Immutable reports

- Input pattern: `YYYY-MM-DD最终数据报告.json`.
- Raw submissions and final reports are append-only evidence. Revisions are represented by review overrides, never source edits.

## Derived JSONL row keys

All rows include `schema_version`, `event_date`, and `source_report` where applicable.

| File | Stable key | Required normalized fields |
|---|---|---|
| `reports.jsonl` | `event_date + source_report` | input schema, counts, date basis, provenance |
| `decisions.jsonl` | `decision_id` | time, precision, target, options, actual choice, quality, eligibility |
| `coarse_decisions.jsonl` | `record_id` | target, actual outcome, missing fields, record status, eligibility |
| `tasks.jsonl` | `task_id` | task, status, time, evidence, source status, review status |
| `quality_issues.jsonl` | `record_type + record_id + issue_code` | severity, field, description, remediation |

## Formal decision contract (`decisions.jsonl`)

Every formal decision row must include these fixed keys. Additional source-preserving fields are allowed, but none of these may be renamed or omitted.

```text
schema_version
decision_id
event_date
subject_id
decision_domain
decision_family
decision_time
time_precision
prediction_cutoff
observation_window
choice_set
choice_set_completeness
actual_choice
actual_choice_confidence
pre_decision_observations
immediate_outcome
quality_score
analysis_tier
pattern_analysis_eligible
strict_backtest_eligible
causal_claim_eligible
source_report
source_trace
human_review_override_id
```

- `choice_set` is the original normalized object, including `mutually_exclusive` and option evidence; `choice_set_completeness` is its explicit completeness label.
- `quality_score` is the source total on the 0–10 scale, never a new model score.
- `decision_family` is an action trade-off label: `start_vs_defer`, `continue_vs_stop`, `consume_vs_abstain`, `confront_vs_avoid`, `timing_choice`, or `plan_a_vs_plan_b`. It is not a life domain.
- `analysis_tier` is one of: `strict`, `historical_pattern`, `coarse`, `unresolved`. Formal decision rows use `strict` only when `strict_backtest_eligible` is true; otherwise use `historical_pattern` when `pattern_analysis_eligible` is true. `coarse` and `unresolved` belong in their respective tables unless a migration audit explicitly records why they remain in `decisions.jsonl`.
- `source_trace` must preserve file/section evidence. `human_review_override_id` is the review ID that changed the derived formal row, or `null`.

## Human review override

Append one JSON line per user-confirmed review.

```json
{
  "schema_version": "human-review-override-v1.0",
  "review_id": "R-YYYYMMDD-XX",
  "event_date": "YYYY-MM-DD",
  "record_type": "report|decision|coarse_decision|task|unresolved_decision",
  "record_id": "source record ID",
  "field": "status|actual_choice|decision_time|event_date",
  "source_value": "preserved source value",
  "question": "exact question shown to user",
  "answer": "user answer",
  "confirmed_value": "normalized confirmed value or unknown",
  "confirmed_time_precision": "exact|approximate|coarse|unknown",
  "resolution_type": "confirmed_unresolved (only if no actual outcome)",
  "review_status": "resolved",
  "answered_at": "unknown",
  "source_report": "03_最终日报/YYYY-MM-DD最终数据报告.json"
}
```

## Active issue rules

Flag only unresolved machine-review items. Suppress an active flag after a matching resolved override, while retaining the override in `human_review_overrides.jsonl`.

- `source_conflict`: source and supplemental facts disagree.
- `coarse_or_unknown_time`: no sufficiently precise time for strict backtest.
- `actual_choice_missing`: strict decision lacks an outcome label.
- `unresolved_decision_mention`: trade-off has no actual choice.
- `task_status_unknown`: task outcome unknown.
- `event_date_inferred`: date came from filename; user confirmation can resolve it.

## Eligibility

- `strict_backtest_eligible: true` only for a time-bounded observed decision with mutually exclusive options.
- `coarse_training_eligible: review_required` for incomplete timing/options or cross-day outcomes.
- `causal_claim_eligible: false` unless a separate causal design exists.
