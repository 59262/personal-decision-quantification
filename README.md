# 个人情境化决策量化系统

一个以 Obsidian、Markdown、JSONL、Python、PowerShell 和 Codex Skills 组成的本地优先个人记录与决策分析系统。它把原始记录、健康客观数据、决策筛查和状态快照分成有来源边界的阶段，强调可追溯、可复核和不自动补全主观状态。

> 当前工作区是个人使用中的完整 Vault，包含真实日记、健康数据、运行数据库和历史备份。它**不适合直接整体上传到 GitHub**。公开发布应从干净副本开始，并只复制确认可公开的代码、文档和虚构示例。

## 解决的问题

- 将日记或转写材料整理为结构化的每日记录。
- 在原始事实、健康客观指标、决策对象和状态快照之间建立来源链。
- 对缺失、未知、来源变化和用户确认保留明确状态。
- 在本地导入 Apple Health 数据并生成可追溯的日汇总与 Markdown 报告。

## 功能

- `01` 原始数据记录：日期门禁、日记转写、用户确认和日分析。
- `H1` 健康层：Apple Health XML/ZIP 导入、SHA-256 来源登记、SQLite 追加导入、日汇总和报告。
- `02` 数据筛查：决策候选筛选、闭环问询、JSONL 账本和派生构建。
- `03` 个人状态量化：针对单个正式 Decision 的状态快照校验。
- Codex Skills：总调度器、子系统 Skill、参考契约和校验脚本。

## 项目结构

```text
00_全系统调度/                 全局交接契约和唯一调度入口
01.原始数据记录/               日记输入、模板和 01 Skill（公开副本只保留模板）
02.数据筛查/                   筛查规则、Schema、构建器和 02 Skill
03.个人状态量化/               状态快照 Schema、校验器和 03 Skill
H1.个人健康层/health-runtime/  本地健康数据运行时与合成测试
docs/                         公开使用、架构和数据契约说明
examples/                     虚构示例和演示流程
scripts/                      公开副本校验脚本
```

历史归档、真实数据和恢复包不属于公开运行时，应在公开副本中排除。

## 环境要求

- Windows 或兼容 PowerShell 的环境。
- Python 3.11 或更高版本。
- Obsidian（仅在本地使用 Vault 时需要）。
- 健康层运行时只使用 Python 标准库；构建环境声明在 `H1.个人健康层/health-runtime/pyproject.toml`。

## 安装与启动

在干净公开副本中：

```powershell
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
python scripts/check_skill_structure.py
```

健康层的本地运行：

```powershell
Set-Location 'H1.个人健康层/health-runtime'
python -m health_layer init
python -m health_layer import 'inbox\\export.zip'
python -m health_layer audit
python -m health_layer aggregate --from 2026-10-13 --to 2026-10-13
python -m health_layer report 2026-10-13
```

`inbox/export.zip`、`data/health.db` 和 `reports/` 只应在本地使用；不要将真实导出复制到公开副本。

## Obsidian 配置

1. 将干净公开副本作为新 Vault 打开。
2. 只启用需要的核心插件；不要把现有个人 Vault 的 `.obsidian` 配置直接复制进公开仓库。
3. 从 `examples/obsidian/` 复制虚构模板到本地工作区。
4. 把真实日记和健康数据放在仓库外，并确认 `git status` 不显示它们。

## Python 和 PowerShell 脚本

- `H1.个人健康层/health-runtime/health_layer/`：健康导入、审计、汇总和报告模块。
- `02.数据筛查/06_程序与Skill/构建器/build_derived_v1.ps1`：从正式报告构建派生账本；运行前确认输入目录和备份。
- `02.数据筛查/06_程序与Skill/构建器/sync_ingestion_registry.ps1`：同步登记信息。
- `02.数据筛查/06_程序与Skill/构建器/backfill_source_hash_chain_v1.ps1`：补充来源哈希链；`-Apply` 会写入文件，必须先审阅预览结果。

这些脚本面向当前个人 Vault 的路径约定，尚未承诺跨机器即插即用。

## Codex Skill

总调度入口是 `00_全系统调度/personal-system-orchestrator/SKILL.md`。当前运行时 Skill 及触发范围：

| Skill | 触发与职责 |
| --- | --- |
| `personal-system-orchestrator` | 完整流程、跨层续跑、系统更新和阶段交接 |
| `diary-transcription` | 日记、字幕或转写材料进入 01 |
| `personal-health-layer` | Apple Health 导入、日汇总和健康报告 |
| `daily-decision-training-pipeline` | 已确认 01 资料进入 02 筛查 |
| `decision-data-pipeline` | 登记、哈希、派生构建等确定性操作 |
| `decision-ledger-workflow` | 证据边界内的决策候选筛查 |
| `daily-decision-closure` | 缺失事实的结构化闭环问询 |
| `decision-state-snapshot` | 对单个正式 Decision 生成或校验 03 快照 |

每个 Skill 都应说明输入、步骤、输出、缺失数据、禁止推断、询问条件、停止条件和依赖文件。历史版本位于归档目录，不应与当前运行时重复注册。

## 示例工作流程

从虚构输入到输出的最小流程见 [`examples/workflow/README.md`](examples/workflow/README.md)。示例不会访问真实目录，也不会生成健康诊断或预测概率。

## 数据格式

最小 JSONL 示例和字段说明见 [`docs/data-schema.md`](docs/data-schema.md)。系统区分用户明确陈述、设备客观指标、AI 整理出的分析，以及未知、缺失和待确认字段。

## 隐私与安全

- 不提交真实日记、健康记录、财务数据、个人身份信息、截图、数据库、导出包或访问凭证。
- 不把 `.env`、Cookie、Token、私钥或数据库连接串写入文档。
- 发现疑似凭证时只记录路径、行号、类型和风险等级，并立即撤销或轮换。
- 健康层不上传数据、不做疾病诊断、不从设备指标推断情绪或动机。
- 公开前必须阅读 [`SECURITY_AUDIT.md`](SECURITY_AUDIT.md) 和 [`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md)。

## 已知限制

- 当前顶层工作区不是 Git 仓库，无法从这里核验历史提交。
- 公开副本仍需作者选择许可证；见 [`LICENSE.md`](LICENSE.md)。
- 当前没有网站前端、持续集成或在线漏洞数据库核验流程。
- PowerShell 构建器依赖当前 Windows 路径约定，需在合成数据上验证后再迁移。
- 健康层的基线、异常和跨层联合分析仍是增量能力，不应被当作医学结论。

## 贡献

请先阅读 [`CONTRIBUTING.md`](CONTRIBUTING.md)。任何贡献都必须使用虚构数据，并在提交前通过 Skill 结构检查和相关测试。

## 许可证

许可证尚未确认。作者完成选择前，不能把项目宣传为 MIT、Apache-2.0 或其他已授权许可证。
