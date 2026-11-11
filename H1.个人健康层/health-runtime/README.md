# 个人健康层

这是《健康与身体状态模块：产品功能方案 v0.1》的首个可运行实现。当前版本专注于 Windows 本地闭环：

- 导入 Apple 健康导出的 `export.zip` 或 `export.xml`；
- 使用 SHA-256 记录来源文件，流式解析大型 XML；
- 将原始样本以追加方式写入 SQLite，并以确定性 ID 去重；
- 将原始样本标准化到版本化指标字典；
- 审计原始/标准化样本数量、未知指标和有效日期覆盖；
- 对步数和步行距离按分钟执行 Watch 优先、iPhone 补缺口的来源消重；
- 将苹果0—1比例值正确转换为百分比；
- 将报告日期当晚18:00至次日12:00的整段睡眠归入同一夜；
- 生成版本化的每日汇总 JSON；
- 生成可读的 Markdown 健康日报；
- 不上传任何健康数据，不进行疾病诊断或情绪推断。

## 立即运行

要求 Python 3.11 或更高版本，不依赖第三方 Python 包。

```powershell
python -m health_layer init
python -m health_layer import "inbox\export.zip"
python -m health_layer audit
python -m health_layer aggregate --from 2026-10-01 --to 2026-10-13
python -m health_layer report 2026-10-13
```

默认数据库为 `data/health.db`，日报写入 `reports/daily/`。这些目录中的个人数据已被 `.gitignore` 排除。

也可以一次完成导入、汇总和报告：

```powershell
python -m health_layer pipeline "inbox\export.zip"
```

## 测试

```powershell
python -m unittest discover -s tests -v
```

测试只使用合成数据，不包含真实健康信息。

## 当前边界

这是数据底座的第一个增量，不是完整产品界面。已实现可追溯导入、标准化、基础来源消重、每日聚合和双格式报告；更完整的来源阶段识别、14/28 天个人基线、异常规则、周月报和既有视频日报连接将在后续增量完成。当前生成的统计会明确标为初始算法版本。

设计说明见 [docs/architecture.md](docs/architecture.md)，开源选型记录见 [docs/open-source-review.md](docs/open-source-review.md)。

苹果健康与视频日记的联合分析规则见
[docs/health-diary-analysis-protocol-v0.1.md](docs/health-diary-analysis-protocol-v0.1.md)。
公开副本不包含真实日报；请使用 tests/fixtures/ 和临时输出目录验证流程。



