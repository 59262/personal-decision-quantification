# 公开暂存目录范围

此目录只包含框架、规则、Schema、Codex Skills、实现脚本、Python 测试夹具、文档和虚构示例。

## 未复制内容

- 真实日记、字幕和转写
- Apple Health 导出包、SQLite 数据库和逐日报告
- 真实决策记录、状态快照、登记表和质量审计数据
- `.obsidian`、`.codex-tmp`、`.research` 和历史恢复包
- 办公文档及其他可能包含私人元数据的文件

## 发布前复核

在此目录执行：

```powershell
python scripts/check_skill_structure.py
Set-Location 'H1.个人健康层/health-runtime'
python -m unittest discover -s tests -v
```

确认 `git status` 和 `git diff --cached` 中只出现本目录允许的框架与逻辑文件。

