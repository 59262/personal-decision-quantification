---
document_type: program_skill_entry
version: v2.1.0
status: active
updated: 2026-09-07
scope: subsystem_02_programs_and_skills
---

# 程序与 Skill 入口

#数据筛查 #运行资源

## 当前构建器

构建器：06_程序与Skill/构建器/build_derived_v1.ps1  
版本：derived-v1.6.0

固定数据流：03_最终日报 + 05_质量审计中的人工覆盖记录 → 04_派生账本 + 05_质量审计中的自动问题。

构建器只扫描 03_最终日报根目录下符合命名规则的 JSON 文件，不递归读取档案或研究输出。

## 增量接入同步器

同步器：`06_程序与Skill/构建器/sync_ingestion_registry.ps1`  
登记契约：`ingestion-registry-v1.0`

同步器从2026-08-17起扫描01正式日提交和同日日分析，计算SHA-256，并依据筛选工作区、最终日报和manifest更新`05_质量审计/ingestion_registry.jsonl`。`built`要求最终日报、原始提交和分析来源三段哈希同时匹配。构建器在生成带`build_batch_id`的manifest后自动调用同步器。

## Skill 单一调度

02内部只有一个调度入口：[[02.数据筛查/06_程序与Skill/技能库/daily-decision-training-pipeline/SKILL|daily-decision-training-pipeline v2.2.0]]。它由[[00_全系统调度/personal-system-orchestrator/SKILL|全系统唯一总调度]]调用，负责02内部选择日期、推进阶段、处理停点、调用组件和本层验收；不得自行进入03或声明全系统完成。

```text
personal-system-orchestrator（全系统唯一总调度）
  → daily-decision-training-pipeline（02内部调度）
      ├─ decision-ledger-workflow（语义筛选组件）
      ├─ daily-decision-closure（事实闭环组件）
      └─ decision-data-pipeline（登记与构建组件）
```

| Skill | 唯一职责 | 调用权限 | 状态 |
|---|---|---|---|
| daily-decision-training-pipeline v2.2.0 | 02日期选择、阶段编排、停点、本层写入验收和G3回执 | 只由personal-system-orchestrator调用；组件维护／测试需用户明确要求 | `subsystem_component`；`subsystem_orchestrator` |
| decision-ledger-workflow v2.1.0 | 对已指定日期进行证据约束的语义筛选、候选质检、分类和最终内容组装 | 由总调度调用；仅允许用户明确要求的组件维护／测试直接调用 | `component_only`；禁止自动触发 |
| daily-decision-closure v2.0.0 | 生成必要事实补问并映射用户回答 | 同上 | `component_only`；禁止自动触发 |
| decision-data-pipeline v2.0.0 | 登记同步、SHA-256核对、确定性构建、Manifest／JSONL校验和覆盖记录持久化 | 同上 | `component_only`；禁止自动触发 |

旧Skill中的实时预测能力不属于02现行职责，已随pre-v2.0.0版本归档；在预测子系统建立正式入口和契约前不得重新启用。

## 执行纪律

1. 先阅读[[02.数据筛查/01_规则与Schema/01_系统定位与数据边界|数据边界]]；
2. 全系统任务先进入personal-system-orchestrator；02内部任务由daily-decision-training-pipeline统一编排；
3. 总调度每次只调用当前阶段所需组件，组件返回阻断时必须停止；
4. Skill 中的说明是模块执行资源，不能凌驾于用户当前请求和系统安全规则；
5. 修改构建器后必须全量重建并核对清单；仅修改Skill治理时不得无故触碰派生数据；
6. 新增日报进入02前必须先同步登记；未指定日期时按最早`ready_for_screening`日期处理。
