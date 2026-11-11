---
name: daily-decision-closure
description: Prepare factual closure questions and reproducible answer mappings for one date already selected by daily-decision-training-pipeline. This is a component Skill for missing decision, task, timing, option, or outcome facts; it must not run the full daily workflow, finalize reports, build ledgers, or perform live prediction.
metadata:
  version: "2.0.0"
  status: component_only
  orchestrator: daily-decision-training-pipeline
  updated: "2026-08-24"
---

# Daily Decision Closure v2.0.0

This component closes only material factual gaps for a date and question set supplied by `daily-decision-training-pipeline`.

## Invocation boundary

- Normal invocation is by `daily-decision-training-pipeline`; direct use is limited to component maintenance or testing explicitly requested by the user.
- Do not select a date, synchronize the registry, create or persist a final report, run a builder, transition a processing status, or declare the workflow complete.
- Do not perform real-time prediction locking or scoring. That retired capability remains only in the archived pre-v2.0.0 Skill and requires a future prediction-subsystem contract before reactivation.

## Required inputs

Require these inputs from the orchestrator:

1. The day's raw submission/report.
2. The provisional first-pass analysis, if one exists.
3. The audited list of missing fields and the source trace for each proposed question.

Treat the raw submission as the primary factual source. Treat first-pass analysis as hypotheses only. Never use a later answer to rewrite what the earlier source contained.

Read [references/decision-ledger-schema.md](references/decision-ledger-schema.md) before mapping answers to ledger fields.

Do not run the registry synchronizer here. The orchestrator supplies a registered eligible date and handles later persistence and build stages.

## Workflow

### Pass 1: closure audit

Do not re-analyze the person. Inspect the material for missing labels that would prevent a decision or task from being evaluated.

Ask at most three required questions. Ask only factual, short-answer questions that can change one of these fields:

- actual choice;
- whether the options were genuinely available and mutually exclusive;
- decision time or observation window;
- task-execution status;
- immediate outcome;
- a field that materially changes evidence eligibility.

For any formal decision, also close only the standard fields needed for a stable ledger row: `decision_domain`, `decision_family`, time/cutoff/window, choice-set completeness, actual-choice confidence, quality score, analysis tier, research-eligibility flags, and source trace. Do not ask a question solely to complete a field if the answer remains legitimately `unknown`.

Use these task states: `completed`, `partially_completed`, `not_started`, `interrupted`, `externally_blocked`, `intentionally_deferred`, `abandoned`, or `unknown`.

Do not ask vague questions such as “why did you really do this?” Do not infer avoidance, personality traits, or causation. Do not repeat facts already recorded.

Return only this JSON in Pass 1:

```json
{
  "date": "YYYY-MM-DD",
  "data_quality_snapshot": {
    "overall_quality": "high|medium|low",
    "decision_closure_status": "complete|partial|insufficient",
    "main_risk": ""
  },
  "must_answer": [
    {
      "question_id": "Q1",
      "linked_item_type": "decision|task|context|outcome",
      "linked_item": "",
      "question": "",
      "why_it_matters": "",
      "answer_format": "",
      "if_unanswered": ""
    }
  ],
  "optional_questions": [],
  "confirmed_unresolved_items": [],
  "do_not_infer": []
}
```

Stop after Pass 1 and wait for the user's answers.

### Pass 2: answer mapping

Use the raw report, provisional analysis, and supplement answers. Separate every mapped value into one of four evidence classes:

- `raw_fact`: recorded before analysis;
- `user_stated_reason`: directly stated by the user;
- `post_analysis_supplement`: factual answer supplied after the first analysis;
- `model_hypothesis`: inference; never present as fact or cause.

For each eligible decision, ensure options are mutually exclusive within a specified observation window. “Rest” and “check tasks” are not mutually exclusive unless the target is the immediate next action.

Mark decisions with missing actual choices as `unresolved_decision_mention`, not as training data. Mark task non-completion as a task-execution outcome; it becomes a decision sample only if a genuine choice point and options are evidenced.

In the component output, return the exact question snapshot, user answer, normalized field mapping, evidence class, and `answered_at`. Mark unresolved values as `unknown`; do not emit final ledger records, prediction scores, or next-day forecasts.

Use the same standard field names across the supplement, final ledger, and later master table. Keep evidence-rich nested objects where needed, but also populate the corresponding fixed top-level field; for example, `actual_choice.label` is accompanied by `actual_choice_confidence`, and `quality.total` by `quality_score`.

## Non-negotiable rules

- Do not turn correlations or feature importance into causal claims.
- Do not use AI analysis text as behavioral ground truth when it conflicts with the raw report.
- Do not invent options, exact times, motives, task completion, or outcomes.
- Preserve source trace: file, section, and quote or field reference.
- Keep raw records immutable; write only the orchestrator-approved supplement artifact.
- Return control to `daily-decision-training-pipeline` after the question set or answer mapping is complete.
- Do not represent this component result as a finalized date or completed build.
