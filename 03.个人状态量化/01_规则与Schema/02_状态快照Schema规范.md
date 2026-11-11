---
document_type: schema_contract
module: personal_state_quantification
status: active_candidate
schema_version: state-snapshot-v1.0
authority_scope: state_snapshot_fields_enums_eligibility
---

#03个人状态量化 #Schema

# state_snapshot Schema规范 v1.0

## 1. 最小对象

每个文件只保存一个选择点。机器记录至少包含：

```json
{
  "schema_version": "state-snapshot-v1.0",
  "snapshot_id": "S-YYYYMMDD-D01-L01",
  "subject_id": "self-001",
  "event_date": "YYYY-MM-DD",
  "decision_id": "D-YYYYMMDD-01",
  "snapshot_type": "locked_prediction",
  "outcome_known_at_entry": false,
  "decision_time": null,
  "captured_at": "YYYY-MM-DDTHH:MM:SS+08:00",
  "information_cutoff": "YYYY-MM-DDTHH:MM:SS+08:00",
  "reconstructed_at": null,
  "decision_question": "",
  "prediction_window": "",
  "choice_set": {
    "mutually_exclusive": true,
    "completeness": "complete",
    "options": []
  },
  "context": {},
  "internal_state": {},
  "goal_state": {},
  "option_states": [],
  "unknowns": [],
  "field_evidence": [],
  "source_type": "pre_lock_user_report",
  "source_trace": [],
  "research_eligibility": {
    "pattern_analysis_eligible": false,
    "strict_backtest_eligible": false,
    "causal_claim_eligible": false
  }
}
```

## 2. 记录类型

| 类型 | `outcome_known_at_entry` | 严格回测 |
|---|---:|---:|
| `locked_prediction` | `false` | 03对象内固定为`false`；未来由下游统一注册表在04预测与结果链完整后另行计算 |
| `retrospective_reconstruction` | `true` | 永远为`false` |

## 3. 允许值

- `available_now`：`yes / no / uncertain`。
- `choice_set.completeness`：`complete / partial`；partial必须保留“其他或未知”。
- 精力、压力和启动阻力：整数`0—5`或`null`。
- `external_constraints`：数组；允许`time / transport / weather / others / equipment / money / body / social`。
- 未观测使用`null`或`unknown`并同步写入`unknowns`；无关才使用`not_applicable`。

## 4. 字段级证据

`field_evidence`至少记录`field_path`、`evidence_class`、`source_path`、`source_hash`、`source_location`和`observed_before_cutoff`。同一文件级`source_type`不能替代字段级来源。

`research_eligibility.strict_backtest_eligible`和`research_eligibility.causal_claim_eligible`在03内必须为`false`。03只登记状态证据是否完整，不自行授予预测评估或因果研究资格。

`decision_time`表示选择实际形成时间，未知时为`null`；`captured_at`表示状态采集时间；`reconstructed_at`只表示事后重建时间。三者不得相互替代。

## 5. 历史兼容

当前3份正式快照属于`legacy-decision-state-snapshot-v1`，保留原字节并在登记表中标记`registered_legacy`。它们不因迁移自动获得新Schema资格；需要使用v1.0时，应生成可追溯的新版本，不能覆盖旧文件。
