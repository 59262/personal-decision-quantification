---
name: personal-health-layer
description: 将Apple健康导出接入个人情境化决策量化系统，执行来源去重、日汇总、健康日报、日记联合分析和登记；缺少健康数据时返回可回填状态，不阻塞01至03主链，也不推断用户主观状态。
metadata:
  version: v1.1.0
  status: active_candidate
  role: health_layer_component
  updated: 2026-10-15
---

#H1个人健康层 #skill
# Personal Health Layer v1.1.0

本Skill由`personal-system-orchestrator`调用。交接权威为[[H1.个人健康层/01_规则与Schema/01_健康层数据与交接契约|健康层交接契约]]；健康、选择与生活的关联判断以[[H1.个人健康层/01_规则与Schema/02_健康选择生活关联分析规则|关联分析规则]]为唯一权威；实际数据程序位于`E:/个人事件量化系统/H1.个人健康层/health-runtime/`。原`E:/个人健康层/`仅作迁移前只读备份。

## 1. 输入

- `event_date`；
- 01正式日报路径和SHA-256；
- 同日D分析路径和SHA-256；
- 可用的Apple健康导出路径；
- 用户明确纠正；
- 目标终点：检查、基础报告、联合报告或登记。

## 2. 状态机

| 状态 | 处理 | 合法输出 |
|---|---|---|
| `H0 source_checked` | 检查导出文件、数据库日期覆盖和既有报告 | 新源、复用或`pending_health_data` |
| `H1 ingested` | 对新SHA-256执行导入；同哈希跳过 | `imported / reused / pending_health_data` |
| `H2 summary_ready` | 按日期与睡眠窗口聚合 | 日汇总JSON或暂定状态 |
| `H3 base_report_ready` | 生成基础健康Markdown/JSON | 客观健康报告 |
| `H4 integrated_report_ready` | 合并正式日报、D分析和用户纠正 | 联合报告；证据类型分层 |
| `H5 registered` | 校验路径和哈希，追加主系统登记 | 可追溯登记记录 |

## 3. 执行

在`E:/个人事件量化系统/H1.个人健康层/health-runtime/`中使用当前Python环境：

```powershell
python -m health_layer import "inbox\export.zip"
python -m health_layer audit
python -m health_layer aggregate --from YYYY-MM-DD --to YYYY-MM-DD
python -m health_layer report YYYY-MM-DD
```

联合报告按`E:/个人事件量化系统/H1.个人健康层/health-runtime/docs/health-diary-analysis-protocol-v0.2.md`生成到`reports/daily/YYYY-MM-DD_integrated.md/.json`。现有程序尚未自动生成联合报告时，可以由编排器依据协议生成，但必须保留实际输入路径和SHA-256。

联合分析先建立统一时间轴，再输出`health_before_life_or_choice / life_or_choice_before_health / overlap_or_co_occurrence / user_stated_explanation`。事件没有时间时不得判断方向；当晚睡眠不得解释当天白天的选择。单日结果只到时间关联或跨来源一致，多日等级按3次重复、14日初始范围和28日滚动基线逐级判断。

## 4. 停点

- 没有新导出且数据库无该日数据：返回`pending_health_data`；不向用户索要每日手填指标。
- D+1中午前夜间睡眠可能不完整：返回`provisional`，允许次日补算。
- 01正式日报或D分析未完成：可以生成基础健康报告，联合报告停在H3。
- 来源冲突、时间无法对齐或算法版本不明：返回`limited`并登记质量标志。
- 任何主观状态缺失：保持未知，不根据设备数据补齐。

## 5. 回执

```text
执行日期：
H0 来源检查：状态｜来源SHA-256
H1 导入：imported / reused / pending_health_data｜批次
H2 日汇总：状态｜路径｜SHA-256
H3 基础健康报告：状态｜路径｜SHA-256
H4 日记联合报告：状态｜路径｜SHA-256
H5 主系统登记：状态｜登记ID
基线：insufficient / initial_14d / rolling_28d｜有效日数
质量标志：
```

同时返回`association_status`、规则版本、候选数量及每条候选的方向、等级、反证和来源哈希。健康资料缺失时返回`pending_health_data`，不省略未来D报告的固定关联节。

## 6. 版本记录

### v1.1.0 · 2026-10-15

- 新增健康、选择与生活关联分析，固定时间方向、证据等级和3／14／28日升级门槛。
- 保持用户模板和每日填写负担不变；缺失保持未知，单日不输出因果。
