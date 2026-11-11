# 全系统阶段交接契约

本参考定义`personal-system-orchestrator`在01、H1、02、03之间传递的最小数据包。字段内容仍以各层Schema为准。

## 01 ↔ H1

在进入01正式交接前，必须完成日期门禁：用户日期、来源文件日期和转写锚点一致，或已由用户明确裁决。冲突期间只允许候选草稿，交接状态为`date_conflict`。

H1联合报告至少需要01正式日提交和同日D分析；H1基础报告可独立生成。交接字段：

~~~text
event_date
raw_submission_path and sha256
daily_analysis_path and sha256
health_status
source_export_path and sha256
import_batch_id
daily_summary_path and sha256
base_report_path and sha256
integrated_report_path and sha256
metric_window_start and metric_window_end
sleep_window: D 18:00 -> D+1 12:00
valid_health_days
baseline_state: insufficient | initial_14d | rolling_28d
algorithm_versions
quality_flags
association_status
association_rule_version
association_candidates: direction, evidence_grade, counterevidence, source traces
~~~

`pending_health_data`不阻断01→02→03。H1资料后到时只补算H分支；不得因此改写01原始提交。完整契约见[[H1.个人健康层/01_规则与Schema/01_健康层数据与交接契约|健康层数据与交接契约]]。

完整Apple Health导出必须传递`source_export_sha256`、`import_batch_id`、`health_scope_date`和`historical_refresh_policy`。默认只筛选本次事件日期；已登记历史日发生汇总变化时返回`source_changed`，不得静默覆盖旧登记。健康目录不可写时使用`pending_permission`。

关联候选按[[H1.个人健康层/01_规则与Schema/02_健康选择生活关联分析规则|健康、选择与生活关联分析规则]]生成。只有结束时间不晚于节点的窗口可作前置情境；事件无时间时只传递同日共现。健康缺失时`association_status`为`pending_health_data`，不阻断主链。

## 01 → 02

必须同时满足：唯一正式日提交、同日D分析、用户确认完成、日期一致、文件存在且SHA-256已重新计算。

~~~text
event_date
raw_submission_path
raw_submission_sha256
daily_analysis_path
daily_analysis_sha256
coverage_state
timing_state
observation_end
formation_method
template_version
analysis_rule_version
action_bridge_id
action_bridge_source_date
action_bridge_target_date
state_capture_dispositions_by_decision: D1/D2 -> fill | explicit_unknown | not_requested | undecided
handoff_status: ready | blocked
block_reason
~~~

不得传递待确认草稿、字幕副本、桌面模板母版、无来源的AI推断或把空白主观字段解释为正常／没有。

用户说“已完成填写”只能作为重读工作副本的触发信号。交接前必须记录`user_copy_path`、`user_copy_sha256`、`date_confirmation_status`和`unchecked_optional_fields_policy=unknown`；未勾选字段不自动补成“无”。

## 02 → 03

每个状态快照只接收一个02正式Decision：

~~~text
event_date
decision_id
decision_question
decision_time and precision
observation_window
choice_set
pre_decision_observations with source traces
source_final_report
source_final_report_sha256
raw_source_file and sha256
analysis_source_file and sha256
execution_version
source_chain_status
analysis_tier
strict_backtest_eligible
state_capture_disposition
upstream_choice_point_state
upstream_choice_point_state_source
upstream_choice_point_state_timing
~~~

只有`source_chain_status: verified_current`且来源未被登记为阻断时，才能自动进入03草稿创建。历史保留的`historical_unverified`或当前`source_changed`只能停下复核，不能伪装成当前可靠来源。

实际选择和结果只用于决定`locked_prediction`或`retrospective_reconstruction`模式，不写入03状态字段。粗粒度记录、未决提及、任务和普通活动不能自动成为状态快照对象。

每个正式Decision的`state_capture_disposition`必须沿用01正式日报对应D1／D2的用户选择：`fill / explicit_unknown / not_requested / undecided`；02没有正式Decision时由总调度返回`not_eligible`。下游不得用空白字段替用户选择去向，也不得把D1的去向复制给D2。

`upstream_choice_point_state`是可选预填包，只能逐字段复制用户在v14日报D1／D2选择点状态区明确填写的内容，并保留正式提交路径、SHA-256、记录时点和`user_stated / user_recall`来源。只有`state_capture_disposition: fill`且字段来源合格时才生成；其他去向、字段发生在结果之后、只有第1节全天状态或02未形成正式Decision时均不得生成。

## 03用户自填字段

以下字段只接受用户在对应时点的明确输入，或历史重建中有时间标记的`user_recall`：

- 精力、压力、困倦、疼痛和身体状态；
- 情绪及其用户原话；
- 动机、启动阻力和主观限制；
- 各选项的主观可行性、预计时长和第一动作。

v14中选项可得性、启动阻力和预计用时必须按A／B／C分别传递，不得把一个选项的值复制到另一个选项。`事后回忆`只能进入历史重建，不获得严格前瞻资格。行动桥对象、最低标准和10分钟动作必须指向同一对象；完成度只接受用户明示或外部可核验边界。

实时记录时无法证明发生在`information_cutoff`之前的内容不得使用。缺失值按03 Schema写`null/unknown`并登记`unknowns`，不能从后续选择、任务完成度、娱乐时长或AI日分析倒推。

## H1 → 03客观情境

健康数据只有在样本或派生窗口结束时间不晚于`information_cutoff`，且来源路径、SHA-256和算法版本可追溯时，才可作为03客观情境。结果发生后的睡眠、心率、活动和恢复数据不得回填选择前状态。

健康数据永远不能替用户填写精力、压力、困倦、疼痛、情绪、动机、启动阻力或选项主观可行性。设备缺失保持未知。

健康层可以回填客观睡眠区间、活动、训练、心率和用户在日记中明确说出的原话；不能把设备指标映射成睡眠质量、心情或其他量表分数。

## 运行时与审计

派生构建脚本必须记录Python版本、PowerShell或pwsh版本和健康目录权限状态。若Windows PowerShell不支持脚本使用的哈希API，切换到pwsh；运行时错误不能改写成数据阻断。

## 阶段恢复

“继续”时按以下证据选择起点：

1. 正式文件和登记状态均存在且哈希一致：复用该阶段；
2. 文件存在但登记、哈希或版本不一致：停在该阶段复核；
3. 只有草稿：恢复用户确认，不重新转写；
4. 02已完成但没有正式Decision：03为`not_eligible`；
5. 03待确认快照存在：恢复字段确认和校验，不新建同ID文件。
6. 03去向为`not_requested`：保留该日合法终点；除非用户明确改选，不创建快照。
7. 03去向为`explicit_unknown`：恢复显式未知草稿的确认与登记，不追问无法回忆的状态值。
