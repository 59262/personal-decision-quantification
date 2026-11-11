from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
import zipfile
from contextlib import closing
from pathlib import Path

from health_layer.aggregate import aggregate_day
from health_layer.importer import import_apple_health
from health_layer.reporting import generate_report


FIXTURE = Path(__file__).parent / "fixtures" / "export.xml"


class PipelineTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.db = self.root / "health.db"

    def tearDown(self):
        self.temp.cleanup()

    def test_repeat_import_is_idempotent(self):
        first = import_apple_health(FIXTURE, self.db)
        second = import_apple_health(FIXTURE, self.db)

        self.assertEqual(first.status, "completed")
        self.assertGreater(first.inserted_records, 0)
        self.assertEqual(second.inserted_records, 0)
        self.assertEqual(second.duplicate_records, first.inserted_records)

        with closing(sqlite3.connect(self.db)) as connection:
            raw_count = connection.execute("SELECT COUNT(*) FROM health_raw_samples").fetchone()[0]
            batch_count = connection.execute("SELECT COUNT(*) FROM health_import_batches").fetchone()[0]
        self.assertEqual(raw_count, first.inserted_records)
        self.assertEqual(batch_count, 2)

    def test_daily_summary_and_report(self):
        imported = import_apple_health(FIXTURE, self.db)
        summary = aggregate_day("2026-10-13", self.db)

        self.assertEqual(summary["status"], "complete")
        self.assertEqual(summary["activity"]["steps"], 3000.0)
        self.assertEqual(summary["activity"]["active_energy_kcal"], 450.0)
        self.assertEqual(summary["sleep"]["total_sleep_minutes"], 480.0)
        self.assertEqual(summary["sleep"]["session_start"], "2026-10-13T23:00:00+08:00")
        self.assertEqual(summary["sleep"]["session_end"], "2026-10-14T07:00:00+08:00")
        self.assertEqual(summary["sleep"]["attribution_rule"], "night_start_date_18_to_next_day_12_v1")
        self.assertEqual(summary["cardiovascular"]["heart_rate_bpm"]["average"], 90.0)
        self.assertEqual(summary["respiratory_and_other"]["oxygen_saturation_percentage"], 98.0)
        self.assertEqual(summary["body"]["weight_kg"], 70.2)
        self.assertEqual(len(summary["workouts"]), 1)
        self.assertIn(imported.import_batch_id, summary["source_batch_ids"])

        report, json_path, markdown_path = generate_report(
            "2026-10-13",
            db_path=self.db,
            output_dir=self.root / "reports",
        )
        self.assertTrue(json_path.is_file())
        self.assertTrue(markdown_path.is_file())
        self.assertEqual(json.loads(json_path.read_text(encoding="utf-8"))["report_id"], report["report_id"])
        self.assertIn("不构成医学诊断", markdown_path.read_text(encoding="utf-8"))

    def test_missing_day_uses_null_not_zero(self):
        import_apple_health(FIXTURE, self.db)
        summary = aggregate_day("2026-10-14", self.db)
        self.assertEqual(summary["status"], "missing")
        self.assertIsNone(summary["activity"]["steps"])
        self.assertEqual(summary["activity"]["missing_reason"], "no_activity_samples_in_imported_data")

    def test_localized_export_filename_in_zip(self):
        archive_path = self.root / "导出.zip"
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("apple_health_export/export_cda.xml", "<ClinicalDocument />")
            archive.write(FIXTURE, "apple_health_export/导出.xml")

        result = import_apple_health(archive_path, self.db)
        self.assertEqual(result.status, "completed")
        self.assertGreater(result.inserted_records, 0)


if __name__ == "__main__":
    unittest.main()

