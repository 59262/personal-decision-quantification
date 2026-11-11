# Strict real-time prediction schema

Use two append-only JSONL ledgers in `预测数据集合/02_数据账本/`:

- `locked_predictions.jsonl`: one immutable prediction lock per line.
- `prediction_outcomes.jsonl`: one later outcome or invalidation per line, linked by `prediction_id`.

## Lock record

```json
{
  "schema_version": "locked-prediction-v1.0",
  "prediction_id": "P-YYYYMMDD-01",
  "subject_id": "self-001",
  "event_date": "YYYY-MM-DD",
  "locked_at": "YYYY-MM-DDThh:mm:ss+08:00",
  "prediction_cutoff": "YYYY-MM-DDThh:mm:ss+08:00",
  "observation_window": "next 60 minutes",
  "question": "neutral observable question",
  "decision_domain": "diet|exercise|project|work|creation|social|spending|recovery|self_management|other",
  "decision_family": "start_vs_defer|continue_vs_stop|consume_vs_abstain|confront_vs_avoid|timing_choice|plan_a_vs_plan_b",
  "options": [
    {"option_id": "A", "label": "...", "probability": 0.50},
    {"option_id": "B", "label": "...", "probability": 0.30},
    {"option_id": "C", "label": "...", "probability": 0.20}
  ],
  "probability_sum": 1.00,
  "pre_lock_observations": [
    {"feature_family": "", "value": "", "evidence_class": "raw_fact", "source": ""}
  ],
  "model_hypotheses": [],
  "source_trace": [],
  "model_version": "manual-baseline-v1",
  "lock_status": "locked",
  "revision": 0
}
```

## Outcome record

```json
{
  "schema_version": "prediction-outcome-v1.0",
  "prediction_id": "P-YYYYMMDD-01",
  "outcome_status": "observed|invalidated|missing|out_of_set",
  "outcome_observed_at": "YYYY-MM-DDThh:mm:ss+08:00",
  "actual_option_id": "A|B|C|O|unknown",
  "actual_action": "",
  "evidence": [],
  "recorded_at": "YYYY-MM-DDThh:mm:ss+08:00",
  "invalidation_reason": null,
  "scoring_eligible": true
}
```

For an observed in-set outcome, calculate multiclass Brier score as `sum((p_i - y_i)^2) / number_of_options`; lower is better. Do not score invalidated, missing, or out-of-set records.

## Validity conditions

- `locked_at` must precede the actual outcome and the cutoff.
- Option labels must be complete enough for the stated window and mutually exclusive.
- Probabilities must sum to 1.00 exactly.
- Use one source of truth for the locked record: append, never modify.
- Do not use daily post-hoc analysis or outcome evidence in `pre_lock_observations`.
