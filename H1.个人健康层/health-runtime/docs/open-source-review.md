# GitHub 开源项目选型记录

评估日期：2026-10-13。

## 结论

没有直接整体采用某个仓库。产品核心采用独立数据契约，同时借鉴成熟项目在流式解析、SQLite 索引和本地展示方面的工程经验。当前实现未复制候选项目源码。

| 项目 | 许可证 | 优点 | 与本 PRD 的差距 | 采用方式 |
|---|---|---|---|---|
| [dogsheep/healthkit-to-sqlite](https://github.com/dogsheep/healthkit-to-sqlite) | Apache-2.0 | 简单成熟的 Apple Health ZIP→SQLite 路径 | 最近提交较早；缺少日报、基线、异常、导入批次和原始/派生分层 | 作为导入路径参考 |
| [jordangarrison/vitals](https://github.com/jordangarrison/vitals) | MIT | SAX 流式解析、SQLite、数百万记录验证、睡眠/训练/路线展示 | 原始记录冲突使用替换语义；缺少算法版本、缺失原因和报告体系 | 借鉴大文件解析与索引策略 |
| [mrf/personal-health-dashboard](https://github.com/mrf/personal-health-dashboard) | MIT | Python/FastAPI + React，本地优先，已有趋势与相关分析 | 项目历史较短；数据契约较简化，不满足全链路可追溯要求 | 作为未来本地 UI 参考 |
| [MBombeck/HealthLog](https://github.com/MBombeck/HealthLog) | PolyForm Noncommercial 1.0.0（v1.15.18 及以前为 AGPL-3.0） | 完整自托管健康 PWA、多来源同步 | 当前许可证限制商业使用；产品范围更偏健康记录与用药；部署和模型均重于 Windows 首版 | 不作为首版底座 |
| [meltforce/FreeReps](https://github.com/meltforce/FreeReps) | MIT | 自托管、多源、趋势/相关性、iOS 增量同步 | 自动同步依赖额外客户端和服务；与既有日报契约不同 | 后续自动同步阶段重新评估 |

## 选择独立核心的原因

PRD 的差异化不在“画健康图表”，而在以下数据治理约束：原始样本不可静默覆盖、每个指标可追溯到批次和来源、用户陈述与设备信号分离、缺失原因明确、基线和异常规则带版本、报告可重算并与既有日报按对象连接。候选项目可以提供实现参考，但直接作为底座会先引入迁移成本，再重写其核心数据模型。

## 复用政策

如后续复制或修改任何第三方源码，必须在合入时记录文件来源、固定提交、许可证和修改说明，并保留相应许可证文本。仅阅读公开实现或采用通用工程思想不计为源码复用。

