# Data contracts

## Incremental ingestion registry

`05_质量审计/ingestion_registry.jsonl` contains one current control record per `event_date`, starting from the configured incremental cutover date. It is a rebuildable registry snapshot, not an append-only evidence ledger.

Required fields:

~~~text
schema_version, ingestion_id, event_date,
source_submission, source_sha256,
analysis_report, analysis_sha256,
screening_workspace, processing_status, status_reason,
final_report, final_report_sha256,
build_batch_id, builder_version,
last_built_source_sha256, last_built_analysis_sha256,
last_built_final_report_sha256,
registered_at, updated_at, next_action
~~~

Allowed processing states are `waiting_for_analysis`, `ready_for_screening`, `screening_in_progress`, `finalized_pending_build`, `built`, `source_changed`, and `blocked_duplicate_source`. A `built` record requires the current final-report SHA-256 to equal the matching manifest input and the build batch to be recorded. Upstream hash drift after a successful build must become `source_changed` until a changed final report is rebuilt.

## Formal decision fields

Every decisions.jsonl row must include these fields. Final-report ledger records use the same names where applicable and may add nested evidence objects.

~~~text
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
state_capture_disposition
source_report
source_trace
human_review_override_id
~~~

- choice_set includes mutually_exclusive, completeness, and evidence-traceable options.
- decision_family is exactly one of start_vs_defer, continue_vs_stop, consume_vs_abstain, confront_vs_avoid, timing_choice, or plan_a_vs_plan_b.
- analysis_tier is strict, historical_pattern, coarse, or unresolved. Formal rows are normally only strict or historical_pattern.
- quality_score is the source 0–10 total, not a new model score.
- source_trace records source file and section. human_review_override_id is a review ID or null.
- state_capture_disposition is `fill`, `explicit_unknown`, `not_requested`, `undecided`, or `unknown`; it is copied from the corresponding v13 decision block and never inferred from state-field completeness.

## Final report structure

Use root schema final-daily-decision-report-1.0 and include:

~~~text
report_type, schema_version, event_date, subject_id,
data_quality_summary, closed_decisions, coarse_decision_records,
unresolved_decision_mentions, task_execution_records,
evidence_separation, locked_prediction_scoring,
optional_data_requests, research_use_assessment, provenance
~~~

`provenance` must contain:

~~~text
raw_source_file, raw_source_sha256,
analysis_source_file, analysis_source_sha256,
raw_current_sha256, analysis_current_sha256,
execution_version, source_chain_status, provenance_contract
~~~

`provenance_contract` is `source-hash-chain-v1.0`. New reports created by this Skill use `execution_version: daily-decision-training-pipeline@2.2.0`. Historical execution versions that cannot be proven use `<workflow>@legacy-version-unknown`; they must not be guessed.

`source_chain_status` is `verified_current`, `source_changed`, or `historical_unverified`. A `source_changed` report keeps the last successfully built source hashes while `*_current_sha256` records the current files. `historical_unverified` means hashes were backfilled from current files without a preserved execution-time baseline; it is complete as metadata but not verified historical provenance.

Classify a known outcome without strict timing/options as a coarse record. Do not place it in closed_decisions just to increase sample count.

### Observation and formation metadata

New `final-daily-decision-report-1.0` reports must preserve these backward-compatible fields inside `data_quality_summary`:

~~~text
coverage_state: full_day | partial_day | unknown
timing_state: timing_reliable | timing_uncertain | unknown
observation_end: supported same-day boundary | unknown
formation_method: single_entry | multi_entry | ai_transcribed_user_confirmed | other | unknown
~~~

Coverage and timing are independent controls. `partial_day` prohibits claims about unobserved later behavior. `timing_uncertain` prohibits exact-order, duration, efficiency, and causal-order claims unless a candidate has an independent local time bundle. These fields do not change the root schema version and do not reduce source credibility.

Generic future plans and reflections are not `unresolved_decision_mentions`. That class requires evidence of a real decision point with an unknown actual choice or outcome.

Retrospective complete choices normally use `analysis_tier: historical_pattern`, `pattern_analysis_eligible: true`, and `strict_backtest_eligible: false`. Strict backtesting additionally requires a prediction or choice specification locked before the outcome and traceable cutoff evidence.

## Derived layer

derived_v1 must contain:

| File | Grain |
|---|---|
| reports.jsonl | one final daily report |
| decisions.jsonl | one formal decision |
| coarse_decisions.jsonl | one coarse decision |
| tasks.jsonl | one observable task state |
| quality_issues.jsonl | one active machine-detected issue |
| human_review_overrides.jsonl | one user-confirmed review answer |
| ingestion_registry.jsonl | one current incremental-control row per event date |

Every derived row carries `source_report`, `source_report_sha256`, `raw_source_file`, `raw_source_sha256`, `analysis_source_file`, `analysis_source_sha256`, `execution_version`, and `provenance_contract`. Manifest input rows carry the same chain; `sha256` remains a compatibility alias of `final_report_sha256`.

## Review override

Append, never edit in place:

~~~json
{
  "schema_version": "human-review-override-v1.0",
  "review_id": "R-YYYYMMDD-XX",
  "event_date": "YYYY-MM-DD",
  "record_type": "report|decision|coarse_decision|task|unresolved_decision",
  "record_id": "source ID",
  "field": "field name",
  "source_value": "preserved source value",
  "question": "exact question asked",
  "answer": "user answer",
  "confirmed_value": "normalized answer or unknown",
  "confirmed_time_precision": "exact|approximate|coarse|unknown",
  "resolution_type": "confirmed_unresolved when applicable",
  "review_status": "resolved",
  "answered_at": "ISO timestamp or unknown",
  "source_report": "03_最终日报/YYYY-MM-DD最终数据报告.json"
}
~~~
