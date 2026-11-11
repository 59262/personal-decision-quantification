# Data contracts

## Root final report

```json
{
  "report_type": "final_daily_decision_data_report",
  "schema_version": "final-daily-decision-report-1.0",
  "event_date": "YYYY-MM-DD",
  "data_quality_summary": {},
  "closed_decisions": [],
  "coarse_decision_records": [],
  "unresolved_decision_mentions": [],
  "task_execution_records": [],
  "evidence_separation": {
    "raw_fact": [],
    "user_stated_reason": [],
    "post_analysis_supplement": [],
    "model_hypothesis": []
  },
  "locked_prediction_scoring": {},
  "optional_data_requests": [],
  "research_use_assessment": {},
  "provenance": {}
}
```

## Formal decision record

```json
{
  "schema_version": "decision-ledger-1.0",
  "decision_id": "D-YYYYMMDD-01",
  "subject_id": "self-001",
  "event_date": "YYYY-MM-DD",
  "decision_domain": "diet|exercise|project|work|creation|social|spending|recovery|self_management|other",
  "decision_family": "start_vs_defer|continue_vs_stop|consume_vs_abstain|confront_vs_avoid|timing_choice|plan_a_vs_plan_b",
  "decision_time": "ISO 8601 timestamp or unknown",
  "time_precision": "exact|approximate|coarse|unknown",
  "time_basis": "required when approximate",
  "prediction_cutoff": "ISO 8601 timestamp or unknown",
  "prediction_cutoff_precision": "exact|approximate|unknown",
  "observation_window": "for example: next_15_minutes",
  "decision_target": {
    "question": "neutral observable question",
    "domain": "diet|exercise|project|work|creation|social|spending|recovery|self_management|other",
    "target_type": "next_action|choice|task_execution"
  },
  "choice_set": {
    "mutually_exclusive": true,
    "completeness": "complete|partial|unknown",
    "options": []
  },
  "choice_set_completeness": "complete|partial|unknown",
  "actual_choice": {
    "label": "one option label",
    "confidence": "high|medium|low",
    "evidence": []
  },
  "actual_choice_confidence": "high|medium|low|unknown",
  "pre_decision_observations": [],
  "post_analysis_supplements": [],
  "immediate_outcome": {
    "observed": "",
    "unknowns": []
  },
  "quality": {},
  "quality_score": 0,
  "analysis_tier": "strict|historical_pattern|coarse|unresolved",
  "pattern_analysis_eligible": false,
  "strict_backtest_eligible": false,
  "causal_claim_eligible": false,
  "state_capture_disposition": "fill|explicit_unknown|not_requested|undecided|unknown",
  "source_report": "03_最终日报/YYYY-MM-DD最终数据报告.json",
  "source_trace": [],
  "human_review_override_id": null,
  "eligibility": {
    "pattern_analysis_eligible": false,
    "coarse_training_eligible": "yes|review_required|no",
    "strict_backtest_eligible": false,
    "causal_claim_eligible": false
  },
  "provenance": {}
}
```

## Supplement answer

```json
{
  "question_id": "Q1",
  "question_text": "",
  "answer": "",
  "answer_mapping": "",
  "answered_at": "ISO 8601 timestamp or unknown",
  "normalized_fact": ""
}
```

## Classification rules

- A known actual choice with missing timing is a `coarse_decision_record`, not an unresolved mention.
- An unknown actual choice is an `unresolved_decision_mention`.
- A stated task outcome without a documented choice point is a task-execution record.
- `pre_decision_observations` contains only non-causal facts known before the choice.
- Do not insert post-choice outcomes into actual-choice or pre-decision fields.
- `decision_domain` is the topic area; `decision_family` is the observable action trade-off. Do not use either as a causal explanation.
- Family classification uses the decision target and mutually exclusive options. Consumption semantics (`吃/不吃`, food, diet) take precedence over incidental schedule words such as `下班`; unresolved semantic conflicts remain review items rather than forced replacements.
- `quality_score` mirrors `quality.total`. `choice_set_completeness` mirrors `choice_set.completeness`; retain both for stable downstream querying.
- Formal records normally use `analysis_tier: strict` or `historical_pattern`. Route `coarse` and `unresolved` items to their respective arrays.

## Derived canonical task status

Preserve the source status and additionally map known observable states:

- `completed`, `marked_completed`, `reported_completed`, `completed_publication_unknown`, `completed_observable_scope`, and `completed_content_present_timing_unknown` → `completed`;
- `partially_completed`, `partially_completed_rescheduled`, `worked_on`, `started`, and `partially_done` → `partial`;
- explicit not-started/not-done/blocked states → `not_completed`;
- `intentionally_deferred` → `deferred`;
- anything else → `execution_or_completion_unknown` plus a quality review item.
