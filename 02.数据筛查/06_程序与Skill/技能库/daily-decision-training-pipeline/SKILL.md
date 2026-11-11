---
name: daily-decision-training-pipeline
description: Execute the 02 data-screening subsystem for a date and verified 01 handoff supplied by personal-system-orchestrator, including registry, screening, factual closure, finalization, derived builds, and one quality review. It is the sole internal 02 dispatcher but must return control before 03; do not use for D/W/M reports, live prediction, or state inference.
metadata:
  version: "2.2.0"
  status: subsystem_component
  role: subsystem_orchestrator
  orchestrator: personal-system-orchestrator
  updated: "2026-09-07"
---

# Daily Decision Training Pipeline v2.2.0

This is the sole internal dispatcher for `02.数据筛查`, invoked by `personal-system-orchestrator` with a verified 01 handoff. It may complete 02 but cannot decide to enter 03 or declare the whole-system workflow complete. Its internal component Skills do not select dates, advance the workflow, or declare completion.

Read [references/data-contracts.md](references/data-contracts.md) before writing any artifact.

## Component dispatch contract

| Component Skill | Invoke only for | It must not do |
|---|---|---|
| `decision-data-pipeline` | registry sync, SHA-256 comparison, deterministic build, manifest and JSONL validation | semantic classification, date selection, or workflow completion |
| `decision-ledger-workflow` | evidence-bounded screening, candidate audit, classification, and final-report content assembly | registry transitions, derived build, or user-facing completion |
| `daily-decision-closure` | factual closure questions and reproducible answer mapping | final report persistence, manifest construction, or prediction work |

Invoke the smallest component required for the current stage. If a component returns a blocked state, stop; never route around the block or call another component to manufacture missing facts. The retired real-time prediction mode of `daily-decision-closure` is not part of subsystem 02.

## Inputs and evidence boundary

Use these workspace conventions unless the user specifies a different root:

- raw submission: `E:/个人事件量化系统/01.原始数据记录/03_事件数据/提交模块/日提交/日期：YYYY年M月D日.md`;
- analysis report: `E:/个人事件量化系统/01.原始数据记录/03_事件数据/分析模块/日分析/YYYY年M月D日.md`;
- daily artifacts: `E:/个人事件量化系统/02.数据筛查/02_筛选工作区/YYYY-M.D/`;
- immutable final report: `E:/个人事件量化系统/02.数据筛查/03_最终日报/YYYY-MM-DD最终数据报告.json`;
- training tables: `E:/个人事件量化系统/02.数据筛查/04_派生账本/`;
- quality ledgers: `E:/个人事件量化系统/02.数据筛查/05_质量审计/`;
- incremental registry: `E:/个人事件量化系统/02.数据筛查/05_质量审计/ingestion_registry.jsonl`.

Treat the raw submission as the only behavioral-fact source. Use the analysis report only to locate leads and formulate closure questions. Keep raw submissions and final reports immutable. Compare source date and daily-folder date; create a correctly dated folder if they differ.

### Observation and eligibility gate

Before extracting candidates, determine four report-level controls from the raw submission:

- `coverage_state`: `full_day`, `partial_day`, or `unknown`;
- `timing_state`: `timing_reliable`, `timing_uncertain`, or `unknown`;
- `observation_end`: the last supported same-day boundary, or `unknown`;
- `formation_method`: `single_entry`, `multi_entry`, `ai_transcribed_user_confirmed`, `other`, or `unknown`.

Coverage and timing are independent. A partial report may also have uncertain chronology. Analyze behavior only inside the supported window. `timing_uncertain` blocks claims that depend on exact ordering, duration, efficiency, or causality, but it does not invalidate a locally coherent choice whose options, choice, and outcome have their own source traces.

Blank user-owned state, emotion, internal-resistance, or subjective-explanation fields mean `unknown`, never zero, normal, absent, or available for behavioral inference. Formation method affects precision and provenance, not user credibility.

## Daily workflow

### 0. Synchronize and select

Call `decision-data-pipeline` to run `06_程序与Skill/构建器/sync_ingestion_registry.ps1` before choosing a date. It scans formal daily submissions from the configured start date, records source and analysis SHA-256 values, detects the current processing state, and preserves the final report plus build batch link.

Select the oldest `ready_for_screening` record unless the user explicitly names another date. Stop on `source_changed`, `blocked_duplicate_source`, or another blocked status; never silently reuse an old final report after upstream evidence changes. `waiting_for_analysis` is not eligible for screening.

### 1. Screen

Call `decision-ledger-workflow` with the registered date, source paths, and supported observation boundary. Read the raw submission and analysis report, then extract at most two formal candidates.

A formal candidate needs a time-bounded observable choice inside the supported observation window, at least two real mutually exclusive options for the same target, an actual choice mapping to one option, and pre-decision observations with source traces. When actions could both occur in sequence, define the target as the next action in an explicit window.

Assign decision_domain and the action-level decision_family: start_vs_defer, continue_vs_stop, consume_vs_abstain, confront_vs_avoid, timing_choice, or plan_a_vs_plan_b. This is distinct from a life domain and never a causal label.

Classify each extracted item first as `activity`, `task`, `decision`, `future_plan`, or `reflection`. Only `decision` may become a formal candidate. A future plan becomes a decision only when the current day contains real alternatives and an actual choice; its later execution remains unknown until observed. A generic “tomorrow / later / next time” plan is not automatically an unresolved decision mention. Use `unresolved_decision_mention` only when a genuine decision point is evidenced but the actual choice or outcome is unknown.

Keep task execution, coarse decisions, unresolved decision points, future plans, emotions, and reflections separate. Do not manufacture options. A known outcome with insufficient timing or option precision is coarse, not unresolved. Ordinary activities and reflections may be omitted from decision outputs once their exclusion reason is auditable.

Write 决策样本初筛.json.

### 2. Audit and close

Use `decision-ledger-workflow` to audit candidate evidence, mutual exclusivity, local chronology, report cutoff, observation window, choice-versus-outcome separation, duplicate entries, and leakage. Write 决策样本二次质检.json. The audit must state which candidates are retrospective `historical_pattern`, which remain coarse or unresolved, and why none or some qualify for strict backtesting.

When questions are material, call `daily-decision-closure`. Ask at most three short factual questions only when an answer can change classification, actual choice, options or availability, timing or window, task state, immediate outcome, or locked-evidence eligibility. First write 决策闭环补充问询.json with the evidence snapshot and field mapping. Store answers in 决策闭环用户补充.json with the exact question snapshot, mapping, and `answered_at`.

If questions are required, stop and wait for the answers. If no answer could change a record or eligibility flag, proceed without asking and preserve the uncertainty in the audit; do not create questions merely to improve narrative completeness. Do not ask for motives, diagnoses, advice, causal explanations, actual sleep when only “preparing to sleep” was recorded, or subjective fields the user intentionally left blank.

### 3. Write the final daily report

Return to `decision-ledger-workflow` to assemble the classified content. This orchestrator performs the final provenance, immutability, persistence, and registry checks.

Classify each item as one of:

- nested decision-ledger-1.0: formal, time-bounded observed choice; its `analysis_tier` may still be `historical_pattern` rather than `strict`;
- coarse_decision_record: outcome known but strict evidence incomplete;
- unresolved_decision_mention: actual outcome unknown;
- task-execution record: task state without a demonstrated choice point.

Create `03_最终日报/YYYY-MM-DD最终数据报告.json` with root schema `final-daily-decision-report-1.0`. Populate every applicable formal-decision field in the reference contract, including explicit precision, quality score, analysis tier, eligibility flags, source report, source trace, review override ID, and the user-selected `state_capture_disposition`. Record the four report-level controls in `data_quality_summary`. Use `unknown` rather than inventing facts; do not infer a 03 disposition from blank state fields.

Before writing, calculate SHA-256 directly from the unique formal 01 submission and same-day 01 analysis. The root `provenance` must contain `raw_source_file`, `raw_source_sha256`, `analysis_source_file`, `analysis_source_sha256`, current comparison hashes, `execution_version`, `source_chain_status`, and `provenance_contract: source-hash-chain-v1.0`. New reports use `execution_version: daily-decision-training-pipeline@2.2.0` and `source_chain_status: verified_current`; never infer a historical version from a filename or modification time.

Retrospectively reconstructed decisions normally use `analysis_tier: historical_pattern`, `pattern_analysis_eligible: true`, and `strict_backtest_eligible: false`. A complete choice observed after the fact is useful pattern data but is not a strict prediction sample. Strict eligibility requires a prediction or choice specification locked before the outcome, a time-bounded observed choice, mutually exclusive options, and traceable cutoff evidence.

Use only raw_fact, user_stated_reason, post_analysis_supplement, and model_hypothesis evidence classes. Model hypotheses are optional, low-confidence, non-causal, and must include an evidence basis plus falsification condition.

Validate all written JSON. If an existing final report differs, request user direction rather than overwrite it.

After creating a new final report, run the registry synchronizer. The date must become `finalized_pending_build`; if it does not, resolve the path, date, or hash inconsistency before building.

### 4. Register training data

Call `decision-data-pipeline` to run `06_程序与Skill/构建器/build_derived_v1.ps1`. It may read only `03_最终日报/*最终数据报告.json` and must rebuild:

- reports.jsonl, decisions.jsonl, coarse_decisions.jsonl, and tasks.jsonl;
- `05_质量审计/quality_issues.jsonl` and append-only `05_质量审计/human_review_overrides.jsonl`;
- codebook_v1.md and manifest.json.

Preserve source values alongside normalized values. Parse every nonempty JSONL line and manifest.json; reconcile manifest counts. The manifest must contain `build_batch_id`, final-report hash, raw-source hash, analysis-source hash, current comparison hashes, execution version, chain status, script version, record counts, override count, and `raw_files_modified: false`. The builder must reject an unexplained mismatch. An explicitly preserved historical baseline may be `source_changed`, but it cannot become `built` until re-screened. Every derived report, decision, coarse decision, task, and quality issue must carry the same source chain.

Decision-family proposals and canonical task statuses follow the component reference contract. Preserve the source family and source task status; a rule disagreement becomes a review item rather than silently replacing the source value.

The builder invokes the registry synchronizer after writing the manifest. Verify that the processed date is `built`, its `final_report_sha256` matches the manifest input hash, and its `build_batch_id` equals the manifest batch. This verification replaces manual “已接入” bookkeeping.

`built` proves file, hash, and batch consistency only. It does not imply strict-backtest eligibility, causal validity, or absence of quality issues.

### 5. Review data quality

When asked to review, this orchestrator chooses exactly one active quality issue, ordered by severity and then date/record ID. Call `daily-decision-closure` for the one factual question and `decision-data-pipeline` for override persistence, rebuild, and verification. Preserve source values and suppress only the resolved issue.

## Completion gate

Declare completion only after the registry matches the actual stage, every written JSON/JSONL parses, source hashes and execution version are complete, manifest counts and build batch reconcile, and no component independently advanced the workflow.

If an outcome remains unknown, use resolution_type: confirmed_unresolved and do not create a decision row. If a later answer supplies an outcome for an unresolved mention but timing remains insufficient, create a coarse record only.

## Non-negotiable rules

- Never modify raw submissions or final reports during later review.
- Never create a final report or manifest input without a complete `source-hash-chain-v1.0` provenance chain.
- Never label an unknown historical Skill version as a specific release; use `legacy-version-unknown`.
- Never bypass the registry when transferring a new 01 daily report into 02.
- Never continue past `source_changed` until the affected date has been re-screened and rebuilt.
- Never let analysis text override raw behavioral facts.
- Never write future outcomes into pre-decision observations.
- Never infer behavior after a partial report's observation cutoff.
- Never use globally uncertain timing to create an exact sequence, duration, efficiency comparison, or causal ordering.
- Never call correlation a cause or turn a task state into a decision without a real choice point.
- Never turn a generic future plan or reflection into a decision or unresolved mention without evidence of a genuine choice point.
- Do not score a prediction unless it was locked before the outcome.
- strict_backtest_eligible additionally requires a pre-outcome locked specification and traceable prediction cutoff; a supplied time, complete options, or a known retrospective outcome alone is insufficient.
- Never let a component Skill become a second dispatcher.
- Return the verified G3 payload to `personal-system-orchestrator`; never call 03 directly.
- Return JSON only for daily screening, closure, final-report, and review outputs.
