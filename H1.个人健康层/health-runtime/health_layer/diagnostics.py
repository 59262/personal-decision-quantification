from __future__ import annotations

from contextlib import closing
from datetime import date, timedelta
from pathlib import Path

from .database import connect, initialize


def source_contributions(
    day: str,
    canonical_metric: str,
    db_path: str | Path = "data/health.db",
) -> list[dict]:
    next_day = (date.fromisoformat(day) + timedelta(days=1)).isoformat()
    initialize(db_path)
    with closing(connect(db_path)) as connection:
        rows = connection.execute(
            """
            SELECT COALESCE(r.source_app, 'unknown') AS source_app,
                   CASE
                     WHEN r.source_device LIKE '%Watch%' THEN 'watch'
                     WHEN r.source_device LIKE '%iPhone%' THEN 'iphone'
                     ELSE 'other'
                   END AS device_kind,
                   COUNT(*) AS sample_count,
                   ROUND(SUM(n.numeric_value), 3) AS numeric_total,
                   MIN(n.local_start_time) AS first_sample,
                   MAX(n.local_end_time) AS last_sample
            FROM health_normalized_samples n
            JOIN health_raw_samples r ON r.sample_id = n.sample_id
            WHERE n.canonical_metric = ?
              AND n.local_start_time >= ?
              AND n.local_start_time < ?
            GROUP BY source_app, device_kind
            ORDER BY numeric_total DESC
            """,
            (canonical_metric, f"{day}T00:00:00", f"{next_day}T00:00:00"),
        ).fetchall()
        return [dict(row) for row in rows]

