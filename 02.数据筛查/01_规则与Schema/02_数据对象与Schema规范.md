# 数据对象与 Schema 规范

#数据筛查 #Schema

## 当前生产 Schema

当前最终日报采用 Schema 1.0。历史目录中的 v2 模板属于候选方案，在完成兼容性迁移和全量验证前，不得直接替换生产格式。

## 主要对象

| 对象 | 定义 | 互斥要求 |
|---|---|---|
| decision | 存在明确选择、取舍或路径变化的事件 | 不与 coarse_event 重复计数 |
| coarse_event | 有意义但不足以构成决策的事件 | 不与 decision 重复计数 |
| task | 可执行、可跟踪的行动项 | 可关联事件，但不替代事件 |
| quality_issue | 自动或人工发现的数据缺陷 | 不作为事实对象 |
| human_review_override | 对自动结果的人工修订记录 | 必须保留修订依据 |
| ingestion_registry | 01→02增量接入的日期级控制记录 | 每个 event_date 只允许一条当前记录 |

## 标识与来源

- ID 必须稳定、唯一，并在重新构建后保持一致；
- source_report 使用模块根目录相对路径，例如 03_最终日报/日期最终数据报告.json；
- 迁移前的旧绝对路径不批量改写历史证据，通过[[02.数据筛查/99_系统演化档案/2026-08-17_路径迁移映射_v1|路径迁移映射]]解释；
- 原始片段、推断字段和人工说明应保持来源区分。
- 增量登记的状态、哈希和构建批次遵循[[02.数据筛查/01_规则与Schema/04_增量接入登记规范|增量接入登记规范]]。

## 最终日报来源哈希链

每份现行最终日报的`provenance`必须保存：

| 字段 | 规则 |
|---|---|
| `raw_source_file` / `raw_source_sha256` | 唯一正式01日提交的库内相对路径和小写SHA-256 |
| `analysis_source_file` / `analysis_source_sha256` | 同日01日分析路径和小写SHA-256 |
| `execution_version` | 实际执行流程及可证明版本；未知历史版本写`legacy-version-unknown` |
| `provenance_contract` | 固定为`source-hash-chain-v1.0` |
| `raw_current_sha256` / `analysis_current_sha256` | 当前正式文件哈希，用于与执行时或上次构建基线比较 |
| `source_chain_status` | `verified_current / source_changed / historical_unverified` |

Manifest输入和所有派生对象必须继续携带最终日报哈希及上述来源链。最终日报不能保存自身哈希，避免形成循环；自身哈希由Manifest和派生对象登记。无解释的哈希不一致必须停止；若登记表保存了上次成功构建基线，则允许显式保留`source_changed`，但不得标为`built`。

## 变更原则

新增字段应优先保持向后兼容；删除或重命名字段必须先生成迁移规则、测试样本和回滚点。Schema 版本变化必须同步更新入口、构建器、Skill、代码本和演化档案。
