from __future__ import annotations

import json
from collections import defaultdict
from contextlib import closing
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from statistics import fmean

from .database import connect, initialize, json_dumps


CALCULATION_VERSION = "health-aggregate-v0.3"


def _round(value: float | None, digits: int = 2) -> float | None:
    return round(value, digits) if value is not None else None


def _metric_rows(connection, day: str):
    next_day = (date.fromisoformat(day) + timedelta(days=1)).isoformat()
    return connection.execute(
        """
        SELECT n.*, r.record_kind, r.metadata_json, r.source_app, r.source_device,
               r.first_import_batch_id
        FROM health_normalized_samples n
        JOIN health_raw_samples r ON r.sample_id = n.sample_id
        WHERE n.local_start_time >= ?
          AND n.local_start_time < ?
          AND n.canonical_metric <> 'sleep.stage'
          AND n.quality_status IN ('accepted', 'review')
        ORDER BY n.local_start_time
        """,
        (f"{day}T00:00:00", f"{next_day}T00:00:00"),
    ).fetchall()


def _sleep_window(day: str, timezone_name: str) -> tuple[datetime, datetime]:
    report_date = date.fromisoformat(day)
    if timezone_name != "Asia/Shanghai":
        raise ValueError(f"当前版本尚未配置时区：{timezone_name}")
    timezone_value = timezone(timedelta(hours=8))
    return (
        datetime.combine(report_date, time(18, 0), timezone_value),
        datetime.combine(report_date + timedelta(days=1), time(12, 0), timezone_value),
    )


def _sleep_rows(connection, window_start: datetime, window_end: datetime):
    return connection.execute(
        """
        SELECT n.*, r.record_kind, r.source_app, r.source_device,
               r.first_import_batch_id
        FROM health_normalized_samples n
        JOIN health_raw_samples r ON r.sample_id = n.sample_id
        WHERE n.canonical_metric = 'sleep.stage'
          AND n.local_start_time < ?
          AND COALESCE(n.local_end_time, n.local_start_time) > ?
          AND n.quality_status IN ('accepted', 'review')
        ORDER BY n.local_start_time
        """,
        (window_end.isoformat(), window_start.isoformat()),
    ).fetchall()


def _values(grouped: dict[str, list], metric: str) -> list[float]:
    return [float(row["numeric_value"]) for row in grouped.get(metric, []) if row["numeric_value"] is not None]


def _sum(grouped: dict[str, list], metric: str) -> float | None:
    values = _values(grouped, metric)
    return _round(sum(values)) if values else None


def _device_priority(row) -> int:
    source = f"{row['source_app'] or ''} {row['source_device'] or ''}".lower()
    if "watch" in source:
        return 0
    if "iphone" in source:
        return 1
    return 2


def _priority_sum(rows: list) -> float | None:
    """Sum additive samples by minute, using Watch first and iPhone for gaps.

    Apple Health exports raw contributions from multiple devices. Directly adding
    Watch and iPhone step/distance rows double-counts periods recorded by both.
    """
    buckets: dict[datetime, dict[int, float]] = defaultdict(lambda: defaultdict(float))
    for row in rows:
        if row["numeric_value"] is None or not row["local_start_time"]:
            continue
        value = float(row["numeric_value"])
        try:
            start = datetime.fromisoformat(row["local_start_time"])
            end = datetime.fromisoformat(row["local_end_time"] or row["local_start_time"])
        except ValueError:
            continue
        priority = _device_priority(row)
        if end <= start:
            buckets[start.replace(second=0, microsecond=0)][priority] += value
            continue
        duration = (end - start).total_seconds()
        cursor = start.replace(second=0, microsecond=0)
        while cursor < end:
            bucket_end = cursor + timedelta(minutes=1)
            overlap_start = max(start, cursor)
            overlap_end = min(end, bucket_end)
            overlap = max(0.0, (overlap_end - overlap_start).total_seconds())
            if overlap:
                buckets[cursor][priority] += value * overlap / duration
            cursor = bucket_end
    if not buckets:
        return None
    return _round(sum(values[min(values)] for values in buckets.values()))


def _priority_count(rows: list) -> int | None:
    value = _priority_sum(rows)
    return int(round(value)) if value is not None else None


def _mean(grouped: dict[str, list], metric: str) -> float | None:
    values = _values(grouped, metric)
    return _round(fmean(values)) if values else None


def _prefer_activity_summary(rows: list) -> list:
    summary_rows = [row for row in rows if row["record_kind"] == "activity_summary"]
    return summary_rows or [row for row in rows if row["record_kind"] != "activity_summary"]


def _stand_hours(rows: list) -> float | None:
    numeric = [float(row["numeric_value"]) for row in rows if row["numeric_value"] is not None]
    if numeric:
        return _round(sum(numeric))
    stood = [row for row in rows if (row["text_value"] or "").endswith("Stood")]
    return float(len(stood)) if stood else None


def _sleep_summary(
    rows: list,
    window_start: datetime,
    window_end: datetime,
) -> dict[str, object]:
    stages: dict[str, float] = defaultdict(float)
    sources: set[str] = set()
    observed_starts: list[datetime] = []
    observed_ends: list[datetime] = []
    for row in rows:
        start = row["local_start_time"]
        end = row["local_end_time"]
        if not start or not end:
            continue
        try:
            parsed_start = max(datetime.fromisoformat(start), window_start)
            parsed_end = min(datetime.fromisoformat(end), window_end)
            minutes = (parsed_end - parsed_start).total_seconds() / 60.0
        except ValueError:
            continue
        if minutes <= 0:
            continue
        observed_starts.append(parsed_start)
        observed_ends.append(parsed_end)
        label = row["text_value"] or "unknown"
        short_label = label.replace("HKCategoryValueSleepAnalysis", "")
        stages[short_label] += minutes
        if row["source_app"]:
            sources.add(row["source_app"])

    asleep_keys = [key for key in stages if key.startswith("Asleep")]
    asleep_minutes = sum(stages[key] for key in asleep_keys)
    in_bed = sum(value for key, value in stages.items() if key == "InBed")
    awake = sum(value for key, value in stages.items() if key == "Awake")
    tracked_sleep_window = asleep_minutes + awake
    session_start = min(observed_starts) if observed_starts else None
    session_end = max(observed_ends) if observed_ends else None
    return {
        "attribution_rule": "night_start_date_18_to_next_day_12_v1",
        "window_start": window_start.isoformat(),
        "window_end": window_end.isoformat(),
        "session_start": session_start.isoformat() if session_start else None,
        "session_end": session_end.isoformat() if session_end else None,
        "session_elapsed_minutes": _round((session_end - session_start).total_seconds() / 60.0)
        if session_start and session_end
        else None,
        "total_sleep_minutes": _round(asleep_minutes) if asleep_keys else None,
        "in_bed_minutes": _round(in_bed) if in_bed else None,
        "awake_minutes": _round(awake) if awake else None,
        "sleep_efficiency_percentage": _round(asleep_minutes / tracked_sleep_window * 100.0)
        if tracked_sleep_window
        else None,
        "stages_minutes": {key: _round(value) for key, value in sorted(stages.items())},
        "sources": sorted(sources),
        "sample_count": len(rows),
        "missing_reason": None if rows else "no_sleep_samples_in_imported_data",
    }


def aggregate_day(day: str, db_path: str | Path = "data/health.db", timezone_name: str = "Asia/Shanghai") -> dict:
    date.fromisoformat(day)
    initialize(db_path)
    with closing(connect(db_path)) as connection:
        rows = _metric_rows(connection, day)
        sleep_window_start, sleep_window_end = _sleep_window(day, timezone_name)
        sleep_rows = _sleep_rows(connection, sleep_window_start, sleep_window_end)
        grouped: dict[str, list] = defaultdict(list)
        for row in rows:
            grouped[row["canonical_metric"]].append(row)

        for metric in ("activity.active_energy", "activity.exercise_minutes"):
            grouped[metric] = _prefer_activity_summary(grouped.get(metric, []))

        hr_values = _values(grouped, "cardiovascular.heart_rate")
        body: dict[str, object] = {}
        for key, metric in (
            ("weight_kg", "body.weight"),
            ("body_fat_percentage", "body.body_fat_percentage"),
            ("lean_body_mass_kg", "body.lean_body_mass"),
            ("height_m", "body.height"),
        ):
            metric_rows = grouped.get(metric, [])
            body[key] = _round(metric_rows[-1]["numeric_value"]) if metric_rows and metric_rows[-1]["numeric_value"] is not None else None

        workouts = []
        for row in rows:
            if row["record_kind"] != "workout":
                continue
            metadata = json.loads(row["metadata_json"] or "{}")
            workouts.append(
                {
                    "type": row["canonical_metric"].removeprefix("workout."),
                    "start_time": row["local_start_time"],
                    "end_time": row["local_end_time"],
                    "duration_minutes": _round(row["numeric_value"]),
                    "distance": _round(float(metadata["totalDistance"])) if metadata.get("totalDistance") else None,
                    "distance_unit": metadata.get("totalDistanceUnit"),
                    "energy": _round(float(metadata["totalEnergyBurned"])) if metadata.get("totalEnergyBurned") else None,
                    "energy_unit": metadata.get("totalEnergyBurnedUnit"),
                    "source": row["source_app"],
                }
            )

        has_sleep = bool(sleep_rows)
        has_activity = any(metric.startswith("activity.") and values for metric, values in grouped.items())
        has_heart = any(metric.startswith("cardiovascular.") and values for metric, values in grouped.items())
        available_domains = sum((has_sleep, has_activity, has_heart))
        status = "complete" if available_domains == 3 else "partial" if rows or sleep_rows else "missing"
        last_sync = connection.execute(
            "SELECT MAX(completed_at) AS value FROM health_import_batches WHERE status LIKE 'completed%'"
        ).fetchone()["value"]
        source_batches = sorted(
            {
                row["first_import_batch_id"]
                for row in [*rows, *sleep_rows]
                if row["first_import_batch_id"]
            }
        )

        summary = {
            "schema_version": "health_daily_summary_v1",
            "date": day,
            "timezone": timezone_name,
            "status": status,
            "coverage": {
                "wear_time_minutes": None,
                "sleep_data": "available" if has_sleep else "missing",
                "heart_data": "available" if has_heart else "missing",
                "activity_data": "available" if has_activity else "missing",
                "last_sync_at": last_sync,
                "limitations": [
                    "wear_time_not_yet_calculated",
                    "cross_source_overlap_resolution_v0.1",
                    "sleep_multi_source_dedup_not_enabled",
                ],
            },
            "sleep": _sleep_summary(sleep_rows, sleep_window_start, sleep_window_end),
            "activity": {
                "steps": _priority_count(grouped.get("activity.steps", [])),
                "distance_walking_running_m": _priority_sum(grouped.get("activity.distance_walking_running", [])),
                "active_energy_kcal": _sum(grouped, "activity.active_energy"),
                "basal_energy_kcal": _sum(grouped, "activity.basal_energy"),
                "exercise_minutes": _sum(grouped, "activity.exercise_minutes"),
                "stand_minutes": _sum(grouped, "activity.stand_minutes"),
                "stand_hours": _stand_hours(grouped.get("activity.stand_hours", [])),
                "flights_climbed": _sum(grouped, "activity.flights_climbed"),
                "distance_cycling_m": _sum(grouped, "activity.distance_cycling"),
                "physical_effort": _mean(grouped, "activity.physical_effort"),
                "missing_reason": None if has_activity else "no_activity_samples_in_imported_data",
            },
            "cardiovascular": {
                "heart_rate_bpm": {
                    "minimum": _round(min(hr_values)) if hr_values else None,
                    "average": _round(fmean(hr_values)) if hr_values else None,
                    "maximum": _round(max(hr_values)) if hr_values else None,
                    "sample_count": len(hr_values),
                },
                "resting_heart_rate_bpm": _mean(grouped, "cardiovascular.resting_heart_rate"),
                "walking_heart_rate_bpm": _mean(grouped, "cardiovascular.walking_heart_rate"),
                "hrv_sdnn_ms": _mean(grouped, "cardiovascular.hrv_sdnn"),
                "hrv_rmssd_ms": _mean(grouped, "cardiovascular.hrv_rmssd"),
                "vo2_max": _mean(grouped, "cardiovascular.vo2_max"),
                "missing_reason": None if has_heart else "no_cardiovascular_samples_in_imported_data",
            },
            "workouts": workouts,
            "body": body,
            "respiratory_and_other": {
                "respiratory_rate": _mean(grouped, "other.respiratory_rate"),
                "oxygen_saturation_percentage": _mean(grouped, "other.oxygen_saturation"),
                "sleeping_wrist_temperature_c": _mean(grouped, "other.sleeping_wrist_temperature"),
                "time_in_daylight_minutes": _sum(grouped, "other.time_in_daylight"),
                "mobility": {
                    "walking_speed_km_h": _mean(grouped, "mobility.walking_speed"),
                    "walking_step_length_cm": _mean(grouped, "mobility.walking_step_length"),
                    "walking_double_support_percentage": _mean(grouped, "mobility.walking_double_support_percentage"),
                    "walking_asymmetry_percentage": _mean(grouped, "mobility.walking_asymmetry_percentage"),
                    "walking_steadiness_percentage": _mean(grouped, "mobility.walking_steadiness"),
                    "stair_ascent_speed_m_s": _mean(grouped, "mobility.stair_ascent_speed"),
                    "stair_descent_speed_m_s": _mean(grouped, "mobility.stair_descent_speed"),
                },
                "hearing": {
                    "headphone_audio_exposure_dbaspl": _mean(grouped, "hearing.headphone_audio_exposure"),
                    "environmental_audio_exposure_dbaspl": _mean(grouped, "hearing.environmental_audio_exposure"),
                },
            },
            "baseline_comparison": {
                "status": "observation_only",
                "reason": "baseline_engine_not_enabled",
            },
            "anomaly_ids": [],
            "related_daily_report_id": None,
            "source_batch_ids": source_batches,
            "calculation_version": CALCULATION_VERSION,
            "generated_at": datetime.now().astimezone().isoformat(),
        }
        connection.execute(
            """
            INSERT INTO health_daily_summaries(date, timezone, status, summary_json, calculation_version)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(date) DO UPDATE SET
                timezone = excluded.timezone,
                status = excluded.status,
                summary_json = excluded.summary_json,
                calculation_version = excluded.calculation_version,
                generated_at = CURRENT_TIMESTAMP
            """,
            (day, timezone_name, status, json_dumps(summary), CALCULATION_VERSION),
        )
        connection.commit()
        return summary


def date_range(start: str, end: str):
    current = date.fromisoformat(start)
    final = date.fromisoformat(end)
    if current > final:
        raise ValueError("开始日期不能晚于结束日期")
    while current <= final:
        yield current.isoformat()
        current += timedelta(days=1)


def aggregate_range(start: str, end: str, db_path: str | Path = "data/health.db") -> list[dict]:
    return [aggregate_day(day, db_path=db_path) for day in date_range(start, end)]

