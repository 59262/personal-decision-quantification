# 使用说明

## 1. 建立公开副本

从当前个人 Vault 复制代码、文档、Skill、Schema、测试和 `examples/`，不要复制真实数据目录、`.obsidian`、恢复压缩包或生成报表。复制后先运行：

```powershell
python scripts/check_skill_structure.py
git status
```

## 2. 运行健康层合成流程

健康层测试夹具位于其 `tests/fixtures/`，只用于测试。真实 Apple Health 导出应放在本地 `inbox/`，并确保该目录被忽略。

```powershell
Set-Location 'H1.个人健康层/health-runtime'
python -m unittest discover -s tests -v
python -m health_layer init
python -m health_layer pipeline 'inbox/export.zip'
```

## 3. 运行 01/02/03

这些阶段依赖当前 Obsidian Vault 的中文路径和用户确认门禁。公开发布版只提供模板、契约和 Skill；真实运行应在仓库外的个人工作区完成。跨阶段时始终从 `personal-system-orchestrator` 进入，不要直接跳过日期、来源哈希或用户确认。

## 4. 数据安全检查

每次提交前检查：

```powershell
git status --short
git diff --cached --name-only
```

确认输出中没有日记、健康数据库、导出包、报告、屏幕截图、绝对路径或凭证。
