---
name: decision-data-pipeline
description: Run deterministic registry, SHA-256, derived-build, manifest, JSONL, and review-override persistence operations for a date supplied by daily-decision-training-pipeline. This is a component Skill; it must not screen semantics, select dates, create final-report content, ask users questions, or complete the end-to-end workflow.
metadata:
  version: "2.0.0"
  status: component_only
  orchestrator: daily-decision-training-pipeline
  updated: "2026-08-24"
---

# Decision Data Pipeline v2.0.0

Run only deterministic data operations requested by `daily-decision-training-pipeline`. Never change raw submissions or existing final daily reports to resolve a later inconsistency.

## Invocation boundary

- Normal invocation is by `daily-decision-training-pipeline`; direct use is limited to component maintenance or testing explicitly requested by the user.
- The orchestrator supplies the date, intended operation, expected stage, and allowed write targets.
- Do not perform semantic screening, infer facts, create final-report content, ask closure questions, choose another date, or declare the workflow complete.

Read [references/data-contracts.md](references/data-contracts.md) before creating derived files or review overrides.

## 1. Locate and protect inputs

Use the workspace conventions unless the user specifies another root:

- raw submission: `E:/个人事件量化系统/01.原始数据记录/03_事件数据/提交模块/日提交/日期：YYYY年M月D日.md`;
- analysis module: `E:/个人事件量化系统/01.原始数据记录/03_事件数据/分析模块/日分析/YYYY年M月D日.md`;
- daily working artifacts: `E:/个人事件量化系统/02.数据筛查/02_筛选工作区/YYYY-M.D/`;
- immutable final reports: `E:/个人事件量化系统/02.数据筛查/03_最终日报/YYYY-MM-DD最终数据报告.json`;
- derivative data layer: `E:/个人事件量化系统/02.数据筛查/04_派生账本/`;
- quality ledgers: `E:/个人事件量化系统/02.数据筛查/05_质量审计/`.

Treat the submission module as the sole behavioral fact source. Use the analysis module only to locate leads or draft factual closure questions. Preserve every source file and final report unchanged. Before creating a daily final report, compare its contents with any existing final report; if different, request direction rather than overwrite it.

## 2. Synchronize and verify one supplied date

1. Run `sync_ingestion_registry.ps1` for the supplied scope and report the supplied date's current record.
2. Recalculate source, analysis, and existing final-report SHA-256 values from the exact registered paths.
3. Compare them with the registry and manifest without changing semantic artifacts.
4. Return `eligible`, `blocked`, or the exact processing state plus the reason and next mechanical action.
5. Never reinterpret `source_changed`, duplicate sources, or missing analysis as a semantic question; return the block to the orchestrator.

## 3. Build or rebuild the derived layer

Maintain the deterministic rebuild script at `06_程序与Skill/构建器/build_derived_v1.ps1`. It must read only `03_最终日报/*最终数据报告.json` and produce:

- `reports.jsonl` — one row per final daily report;
- `decisions.jsonl` — one row per formal decision;
- `coarse_decisions.jsonl` — one row per coarse decision, including human-resolved outcomes when timing remains insufficient;
- `tasks.jsonl` — one row per task record;
- `05_质量审计/quality_issues.jsonl` — active machine-detected issues only;
- `05_质量审计/human_review_overrides.jsonl` — append-only factual review answers;
- `codebook_v1.md` and `manifest.json`.

The manifest must include script version, generation time, input report list, input SHA-256 hashes, record counts, override count, and `raw_files_modified: false`.

Normalize conservatively. Preserve nested source context where useful. Keep source values alongside human-confirmed values in derived rows. Do not invent a timestamp: represent `unknown`, a relative period, or an approximate ISO time with an explicit precision label.

For formal decisions, assign `decision_family` by the action trade-off (`start_vs_defer`, `continue_vs_stop`, `consume_vs_abstain`, `confront_vs_avoid`, `timing_choice`, or `plan_a_vs_plan_b`), and assign `analysis_tier` as `strict`, `historical_pattern`, `coarse`, or `unresolved`. A formal row is normally `strict` only when strict backtest eligibility is true; otherwise it is `historical_pattern` when it remains pattern-analysis eligible.

After every rebuild, parse every nonempty JSONL line and `manifest.json`. Reconcile manifest counts with line counts.

## 4. Persist one reviewed quality issue

When the user asks to start or continue review:

1. Accept exactly one issue and its mapped factual answer from the orchestrator; do not select the issue or ask the user.
2. Confirm the referenced source report and issue ID still match current files.
3. Append one `human_review_override` row with source value, exact question, answer, confirmed value, source report, and `review_status: "resolved"`.
5. Rebuild the derivative layer. Apply the override to the derived row and suppress only the matching active issue. Keep the raw value and override ID for audit.
6. If the user confirms that an outcome remains unknown, write `resolution_type: "confirmed_unresolved"`; close the review issue but do not create a decision row.
7. If an unresolved mention receives a later outcome, create only a coarse record with an explicit cross-day/unknown-time status; never promote it to a strict decision without a valid decision window.
8. Return validation and build status to the orchestrator; do not select the next issue.

## Guardrails

- Never modify raw submissions or final reports during review.
- Never erase a conflict; preserve its source text in the override row.
- Do not upgrade a coarse record to strict backtest eligibility merely because a time was supplied; also require a valid mutually exclusive choice set and observation window.
- Do not interpret `analysis_module` text as behavioral fact.
- Use `unknown` instead of completing missing facts.
- Return a concise machine-readable status to the orchestrator and never represent component success as end-to-end completion.
