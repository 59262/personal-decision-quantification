# 数据格式说明

以下结构是公开文档中的最小虚构示例，不代表任何真实记录。

## 事件 JSONL

```json
{"schema_version":"event-v1","event_id":"evt-example-001","event_date":"2026-01-15","event_type":"note","text":"完成一次虚构的晨间记录。","source_type":"user_stated","source_ref":"examples/obsidian/daily-entry.example.md"}
```

## Decision JSONL

```json
{"schema_version":"decision-v1","decision_id":"dec-example-001","event_date":"2026-01-15","decision_question":"是否开始示例任务？","choice_set":{"mutually_exclusive":true,"completeness":"complete","options":["start","defer"]},"source_type":"user_stated","source_ref":"examples/data/decisions.jsonl"}
```

## 状态快照

03 快照必须绑定一个正式 Decision，并区分 `locked_prediction` 和 `retrospective_reconstruction`。主观状态只能来自用户明确填写或原话；未知值使用 `null` 或 `unknown`，不能由结果倒推。完整约束见 `03.个人状态量化/06_程序与Skill/技能库/decision-state-snapshot/`。

## 健康日汇总

健康层的汇总应包含 `schema_version`、`event_date`、`status`、客观指标、`source_batch_ids` 和缺失原因。它不包含诊断结论，也不替代用户的情绪、动机、压力或精力字段。

## 来源与隐私

正式对象应保留来源路径、SHA-256、算法或执行版本和不确定性状态。公开示例只能引用 `examples/` 内的虚构文件。
