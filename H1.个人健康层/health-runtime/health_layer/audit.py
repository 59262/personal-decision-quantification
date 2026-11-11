from __future__ import annotations

from contextlib import closing
from pathlib import Path

from .database import connect, initialize


def audit_database(db_path: str | Path = "data/health.db") -> dict:
    initialize(db_path)
    with closing(connect(db_path)) as connection:
        raw_count = connection.execute("SELECT COUNT(*) AS count FROM health_raw_samples").fetchone()["count"]
        normalized_count = connection.execute("SELECT COUNT(*) AS count FROM health_normalized_samples").fetchone()["count"]
        date_bounds = connection.execute(
            "SELECT MIN(substr(start_time, 1, 10)) AS min_date, MAX(substr(start_time, 1, 10)) AS max_date FROM health_raw_samples"
        ).fetchone()
        source_count = connection.execute("SELECT COUNT(*) AS count FROM health_sources").fetchone()["count"]
        import_batches = [
            dict(row)
            for row in connection.execute(
                """
                SELECT import_batch_id, source_filename, source_file_hash, status,
                       total_records, inserted_records, duplicate_records,
                       skipped_records, error_records, started_at, completed_at
                FROM health_import_batches
                ORDER BY started_at
                """
            )
        ]
        record_kinds = {
            row["record_kind"]: row["count"]
            for row in connection.execute(
                "SELECT record_kind, COUNT(*) AS count FROM health_raw_samples GROUP BY record_kind ORDER BY count DESC"
            )
        }
        quality_statuses = {
            row["quality_status"]: row["count"]
            for row in connection.execute(
                "SELECT quality_status, COUNT(*) AS count FROM health_normalized_samples GROUP BY quality_status ORDER BY count DESC"
            )
        }
        unmapped = [
            {
                "metric": row["canonical_metric"],
                "count": row["count"],
                "units": (row["units"] or "").split(","),
            }
            for row in connection.execute(
                """
                SELECT n.canonical_metric, COUNT(*) AS count,
                       GROUP_CONCAT(DISTINCT COALESCE(r.unit, '(none)')) AS units
                FROM health_normalized_samples n
                JOIN health_raw_samples r ON r.sample_id = n.sample_id
                WHERE n.quality_status = 'unmapped'
                GROUP BY n.canonical_metric
                ORDER BY count DESC, canonical_metric
                LIMIT 50
                """
            )
        ]
        null_time_count = connection.execute(
            "SELECT COUNT(*) AS count FROM health_raw_samples WHERE start_time IS NULL"
        ).fetchone()["count"]
        distinct_dates = connection.execute(
            "SELECT COUNT(DISTINCT substr(start_time, 1, 10)) AS count FROM health_raw_samples WHERE start_time IS NOT NULL"
        ).fetchone()["count"]
        metric_coverage = [
            {
                "metric": row["canonical_metric"],
                "samples": row["samples"],
                "effective_days": row["effective_days"],
                "from": row["min_date"],
                "to": row["max_date"],
            }
            for row in connection.execute(
                """
                SELECT canonical_metric, COUNT(*) AS samples,
                       COUNT(DISTINCT substr(local_start_time, 1, 10)) AS effective_days,
                       MIN(substr(local_start_time, 1, 10)) AS min_date,
                       MAX(substr(local_start_time, 1, 10)) AS max_date
                FROM health_normalized_samples
                GROUP BY canonical_metric
                ORDER BY samples DESC, canonical_metric
                """
            )
        ]
        daily_statuses = {
            row["status"]: row["count"]
            for row in connection.execute(
                "SELECT status, COUNT(*) AS count FROM health_daily_summaries GROUP BY status ORDER BY status"
            )
        }
        return {
            "database": str(Path(db_path).resolve()),
            "raw_samples": raw_count,
            "normalized_samples": normalized_count,
            "raw_normalized_match": raw_count == normalized_count,
            "date_range": {"from": date_bounds["min_date"], "to": date_bounds["max_date"]},
            "distinct_dates_with_data": distinct_dates,
            "source_count": source_count,
            "record_kinds": record_kinds,
            "quality_statuses": quality_statuses,
            "unmapped_metrics": unmapped,
            "metric_coverage": metric_coverage,
            "daily_summary_statuses": daily_statuses,
            "null_start_time_records": null_time_count,
            "import_batches": import_batches,
        }

