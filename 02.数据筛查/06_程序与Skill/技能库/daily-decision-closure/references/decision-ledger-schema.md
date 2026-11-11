# Decision ledger schema

Use one record for one observable choice in one time window. Do not store a whole day as a decision.

```json
{
  "schema_version": "decision-ledger-1.0",
  "decision_id": "D-YYYYMMDD-01",
  "subject_id": "self-001",
  "event_date": "YYYY-MM-DD",
  "decision_domain": "diet|exercise|project|work|creation|social|spending|recovery|self_management|other",
  "decision_family": "start_vs_defer|continue_vs_stop|consume_vs_abstain|confront_vs_avoid|timing_choice|plan_a_vs_plan_b",
  "decision_time": "ISO timestamp or unknown",
  "time_precision": "exact|approximate|coarse|unknown",
  "prediction_cutoff": "ISO timestamp or unknown",
  "observation_window": "for example: next 15 minutes",
  "decision_target": {
    "question": "neutral, observable prediction question",
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
    "label": "option label or unknown",
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
  "quality": {
    "temporal_clarity": 0,
    "choice_set_clarity": 0,
    "actual_choice_clarity": 0,
    "context_clarity": 0,
    "reusability": 0,
    "total": 0
  },
  "quality_score": 0,
  "analysis_tier": "strict|historical_pattern|coarse|unresolved",
  "pattern_analysis_eligible": false,
  "strict_backtest_eligible": false,
  "causal_claim_eligible": false,
  "source_report": "03_最终日报/YYYY-MM-DD最终数据报告.json",
  "source_trace": [],
  "human_review_override_id": null,
  "eligibility": {
    "pattern_analysis_eligible": false,
    "coarse_training_eligible": "review_required|yes|no",
    "strict_backtest_eligible": false,
    "causal_claim_eligible": false
  },
  "provenance": {
    "raw_source_priority": "submission_module",
    "source_trace": [],
    "screening_version": "",
    "audit_status": ""
  }
}
```

Use `unresolved_decision_mention` for a mentioned trade-off lacking an actual outcome. Use task states separately when no explicit choice point is documented.

`decision_domain` is the topic area; `decision_family` is the action trade-off and never a causal label. `quality_score` mirrors `quality.total`; `choice_set_completeness` mirrors `choice_set.completeness`. Formal ledger rows normally use `analysis_tier: strict` or `historical_pattern`; route coarse and unresolved items outside the strict ledger.
