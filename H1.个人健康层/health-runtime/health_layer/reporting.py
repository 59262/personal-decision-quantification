from __future__ import annotations

import json
import uuid
from contextlib import closing
from datetime import datetime
from pathlib import Path

from .aggregate import aggregate_day
from .database import connect, initialize, json_dumps


REPORT_VERSION = "health-report-v0.2"


def _show(value: object, suffix: str = "") -> str:
    return "暂无数据" if value is None else f"{value}{suffix}"


def render_markdown(summary: dict) -> str:
    coverage = summary["coverage"]
    sleep = summary["sleep"]
    activity = summary["activity"]
    cardio = summary["cardiovascular"]
    body = summary["body"]
    other = summary["respiratory_and_other"]
    heart = cardio["heart_rate_bpm"]
    workouts = summary["workouts"]
    workout_lines = [
        f"- {item['type']}：{_show(item['duration_minutes'], ' 分钟')}（{item.get('source') or '来源未知'}）"
        for item in workouts
    ] or ["- 当天没有已导入的训练记录。"]

    limitations = "、".join(coverage.get("limitations", [])) or "无"
    return f"""# {summary['date']} 健康日报

> 状态：`{summary['status']}`  
> 时区：`{summary['timezone']}`  
> 计算版本：`{summary['calculation_version']}`  
> 本报告是个人观察资料，不构成医学诊断。

## 1. 数据覆盖与同步状态

- 睡眠：{coverage['sleep_data']}
- 活动：{coverage['activity_data']}
- 心率：{coverage['heart_data']}
- 最近导入完成时间：{_show(coverage['last_sync_at'])}
- 当前限制：{limitations}

## 2. 睡眠与恢复

- 睡眠归属：报告日期当晚18:00至次日12:00窗口
- 睡眠区间：{_show(sleep.get('session_start'))} 至 {_show(sleep.get('session_end'))}
- 睡眠总时长：{_show(sleep['total_sleep_minutes'], ' 分钟')}
- 在床时长：{_show(sleep['in_bed_minutes'], ' 分钟')}
- 清醒时长：{_show(sleep['awake_minutes'], ' 分钟')}
- 睡眠效率：{_show(sleep.get('sleep_efficiency_percentage'), '%')}
- 睡眠样本数：{sleep['sample_count']}

## 3. 日间活动

- 步数：{_show(activity['steps'], ' 步')}
- 步行与跑步距离：{_show(activity['distance_walking_running_m'], ' 米')}
- 活动能量：{_show(activity['active_energy_kcal'], ' 千卡')}
- 基础能量：{_show(activity.get('basal_energy_kcal'), ' 千卡')}
- 运动时间：{_show(activity['exercise_minutes'], ' 分钟')}
- 站立小时：{_show(activity.get('stand_hours'), ' 小时')}
- 爬楼层数：{_show(activity['flights_climbed'], ' 层')}

## 4. 心率与心血管信号

- 全天心率：最低 {_show(heart['minimum'])} / 平均 {_show(heart['average'])} / 最高 {_show(heart['maximum'])} bpm
- 静息心率：{_show(cardio['resting_heart_rate_bpm'], ' bpm')}
- 步行平均心率：{_show(cardio['walking_heart_rate_bpm'], ' bpm')}
- HRV（SDNN）：{_show(cardio['hrv_sdnn_ms'], ' ms')}
- HRV（RMSSD）：{_show(cardio.get('hrv_rmssd_ms'), ' ms')}
- 有氧适能估计：{_show(cardio['vo2_max'])}

## 5. 训练记录

{chr(10).join(workout_lines)}

## 6. 身体指标

- 体重：{_show(body['weight_kg'], ' kg')}
- 体脂率：{_show(body['body_fat_percentage'], '%')}
- 瘦体重：{_show(body['lean_body_mass_kg'], ' kg')}
- 身高：{_show(body['height_m'], ' m')}

## 7. 相对个人基线的变化

当前处于观察阶段；基线引擎尚未启用，因此不输出稳定异常结论。

## 8. 报告内异常提示

当前版本尚未启用异常规则。不会根据心率或 HRV 推断情绪。

## 9. 与当日日记的明确关联

尚未连接既有视频日记日报。

## 10. 缺失项、限制与来源

- 不可用字段保持为空，不使用零值替代未知值。
- 步数和步行距离已按分钟应用来源优先级：Watch 优先，iPhone 用于补足未覆盖时段；规则版本仍处于验证阶段。
- 来源导入批次：{', '.join(summary['source_batch_ids']) or '无'}
"""


def generate_report(
    day: str,
    db_path: str | Path = "data/health.db",
    output_dir: str | Path = "reports/daily",
) -> tuple[dict, Path, Path]:
    initialize(db_path)
    with closing(connect(db_path)) as connection:
        row = connection.execute(
            "SELECT summary_json FROM health_daily_summaries WHERE date = ?",
            (day,),
        ).fetchone()
    summary = json.loads(row["summary_json"]) if row else aggregate_day(day, db_path=db_path)
    markdown = render_markdown(summary)
    report_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"health-report:{REPORT_VERSION}:{day}"))
    report = {
        "schema_version": "health_daily_report_v1",
        "report_id": report_id,
        "date": day,
        "status": summary["status"],
        "summary": summary,
        "related_daily_report_id": None,
        "report_version": REPORT_VERSION,
        "generated_at": datetime.now().astimezone().isoformat(),
    }
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    json_path = output / f"{day}.json"
    markdown_path = output / f"{day}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path.write_text(markdown, encoding="utf-8")

    with closing(connect(db_path)) as connection:
        connection.execute(
            """
            INSERT INTO health_daily_reports(
                report_id, date, status, report_json, markdown,
                related_daily_report_id, report_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(date, report_version) DO UPDATE SET
                status = excluded.status,
                report_json = excluded.report_json,
                markdown = excluded.markdown,
                related_daily_report_id = excluded.related_daily_report_id,
                generated_at = CURRENT_TIMESTAMP
            """,
            (
                report_id,
                day,
                summary["status"],
                json_dumps(report),
                markdown,
                None,
                REPORT_VERSION,
            ),
        )
        connection.commit()
    return report, json_path, markdown_path

