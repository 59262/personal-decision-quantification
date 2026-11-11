# 最小演示流程

1. 打开 `examples/obsidian/daily-entry.example.md`，把它作为虚构的 01 输入。
2. 将 `examples/data/events.jsonl` 作为事件对象示例。
3. 将 `examples/data/decisions.jsonl` 作为一个已确认 Decision 的示例。
4. 在真实运行时，先由总调度器核对日期、来源和用户确认，再把正式 Decision 交给 03 Skill。
5. 健康层如有数据，只能以客观汇总形式并行提供，不得填补主观状态。

该流程不会读取真实 Vault，不会访问网络，也不会生成预测概率或医学结论。
