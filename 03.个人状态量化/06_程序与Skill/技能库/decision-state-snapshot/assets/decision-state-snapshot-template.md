---
schema_version: state-snapshot-v1.0
template_status: active_candidate
---

# 状态快照｜{{EVENT_DATE}}｜{{DECISION_ID}}

> 只记录`{{INFORMATION_CUTOFF}}`以前已知的信息；未确认的主观状态保持`unknown`。

## 元数据

- 快照ID：`{{SNAPSHOT_ID}}`
- 类型：`{{SNAPSHOT_TYPE}}`
- 结果在填写时是否已知：`{{OUTCOME_KNOWN}}`
- 选择形成时间：`{{DECISION_TIME_OR_NULL}}`
- 捕获时间：`{{CAPTURED_AT}}`
- 信息截止点：`{{INFORMATION_CUTOFF}}`
- 重建时间：`{{RECONSTRUCTED_AT_OR_NOT_APPLICABLE}}`
- 决策问题：{{DECISION_QUESTION}}
- 观察窗口：{{PREDICTION_WINDOW}}

## 当前状态

- 地点：
- 是否已到行动地点：`yes / no / uncertain`
- 距下一固定安排：
- 精力（0—5）：
- 压力／认知负荷（0—5）：
- 身体状态：
- 中心主轴与阶段目标：
- 外部限制：
- 信息暴露／AI干预：

## 选项状态

为每个互斥选项分别记录：名称、`available_now`、第一动作、启动阻力、预计时长、资源／阻碍和字段证据。

## 未知与确认

- 未知字段：
- [ ] 没有写入实际选择、结果和事后反思
- [ ] 主观字段来自用户输入或明确标记的事后回忆
- [ ] 字段证据包含路径、哈希和时间边界

## 机器记录

```json
{
  "schema_version": "state-snapshot-v1.0",
  "snapshot_id": "{{SNAPSHOT_ID}}",
  "subject_id": "self-001",
  "event_date": "{{EVENT_DATE}}",
  "decision_id": "{{DECISION_ID}}",
  "snapshot_type": "{{SNAPSHOT_TYPE}}",
  "outcome_known_at_entry": {{OUTCOME_KNOWN_BOOLEAN}},
  "decision_time": {{DECISION_TIME_JSON}},
  "captured_at": "{{CAPTURED_AT}}",
  "information_cutoff": "{{INFORMATION_CUTOFF}}",
  "reconstructed_at": {{RECONSTRUCTED_AT_JSON}},
  "decision_question": "{{DECISION_QUESTION}}",
  "prediction_window": "{{PREDICTION_WINDOW}}",
  "choice_set": {"mutually_exclusive": true, "completeness": "{{COMPLETENESS}}", "options": []},
  "context": {},
  "internal_state": {"energy_0_to_5": null, "stress_load_0_to_5": null},
  "goal_state": {},
  "option_states": [],
  "unknowns": [],
  "field_evidence": [],
  "source_type": "{{SOURCE_TYPE}}",
  "source_trace": [],
  "research_eligibility": {"pattern_analysis_eligible": false, "strict_backtest_eligible": false, "causal_claim_eligible": false}
}
```
