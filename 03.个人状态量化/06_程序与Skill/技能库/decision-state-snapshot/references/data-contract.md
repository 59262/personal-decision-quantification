# Skill数据契约提示

字段定义和研究资格以[[03.个人状态量化/01_规则与Schema/02_状态快照Schema规范|03·state_snapshot Schema v1.0]]为唯一权威。本参考只补充Skill执行时容易遗漏的检查点：

- `state_capture_disposition`只允许`fill / explicit_unknown / not_requested / undecided`；没有02正式Decision时由总调度使用`not_eligible`，不写入快照。
- `not_requested`与`undecided`不生成快照文件；`explicit_unknown`生成草稿时，未知字段仍须在`unknowns`中逐项登记并保留用户去向来源。
- `snapshot_id`在正式登记范围内唯一；修订使用新修订号，不覆盖旧证据。
- `decision_time`、`captured_at`与`reconstructed_at`分开；历史发生时间不是事后填写时间。
- `field_evidence`逐字段区分`pre_lock_user_report / raw_fact / user_recall / post_analysis_supplement`。
- `available_now`只允许`yes / no / uncertain`，不知道不能写`unknown`。
- 0—5量表只能写整数或`null`，且同一尺度跨日期保持含义一致。
- `unknowns`应与机器对象中的空字段对应；无关字段才用`not_applicable`。
- `retrospective_reconstruction`永久`strict_backtest_eligible: false`。
- 实际选择、结果、事后反思和模型假设不得出现在快照事实字段。

旧`legacy-decision-state-snapshot-v1`文件可由校验器兼容读取，但兼容通过不表示已经迁移到新Schema。
