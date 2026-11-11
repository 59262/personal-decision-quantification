from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
import zipfile
from contextlib import closing, contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import BinaryIO, Iterator
from xml.etree import ElementTree

from .database import connect, initialize, json_dumps
from .metrics import METRICS, NORMALIZATION_VERSION, convert_value, simplify_type


IMPORTER_VERSION = "apple-health-xml-v0.1"


@dataclass
class ParsedSample:
    record_kind: str
    metric_type: str
    start_time: str | None
    end_time: str | None
    value_text: str | None
    value_num: float | None
    unit: str | None
    source_device: str | None
    source_app: str | None
    source_record_id: str | None
    timezone: str | None
    metadata: dict[str, str]
    raw_payload: dict[str, object]


@dataclass
class ImportResult:
    import_batch_id: str
    file_hash: str
    status: str
    total_records: int
    inserted_records: int
    duplicate_records: int
    skipped_records: int
    error_records: int
    min_date: str | None
    max_date: str | None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalize_time(value: str | None) -> tuple[str | None, str | None]:
    if not value:
        return None, None
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d %H:%M:%S %z")
        return parsed.isoformat(), parsed.strftime("%z")
    except ValueError:
        try:
            parsed = datetime.fromisoformat(value.replace(" ", "T"))
            offset = parsed.strftime("%z") if parsed.tzinfo else None
            return parsed.isoformat(), offset
        except ValueError:
            return value, None


def _as_float(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _duration_minutes(start: str | None, end: str | None) -> float | None:
    if not start or not end:
        return None
    try:
        return (datetime.fromisoformat(end) - datetime.fromisoformat(start)).total_seconds() / 60.0
    except ValueError:
        return None


def _metadata(element: ElementTree.Element) -> dict[str, str]:
    result: dict[str, str] = {}
    for child in element:
        if child.tag == "MetadataEntry" and child.attrib.get("key"):
            result[child.attrib["key"]] = child.attrib.get("value", "")
    return result


def _record_sample(element: ElementTree.Element) -> ParsedSample:
    attrs = dict(element.attrib)
    start_time, tz = _normalize_time(attrs.get("startDate"))
    end_time, end_tz = _normalize_time(attrs.get("endDate"))
    value_text = attrs.get("value")
    return ParsedSample(
        record_kind="record",
        metric_type=attrs.get("type", "unknown"),
        start_time=start_time,
        end_time=end_time,
        value_text=value_text,
        value_num=_as_float(value_text),
        unit=attrs.get("unit"),
        source_device=attrs.get("device"),
        source_app=attrs.get("sourceName"),
        source_record_id=attrs.get("uuid"),
        timezone=tz or end_tz,
        metadata=_metadata(element),
        raw_payload=attrs,
    )


def _workout_sample(element: ElementTree.Element) -> ParsedSample:
    attrs = dict(element.attrib)
    start_time, tz = _normalize_time(attrs.get("startDate"))
    end_time, end_tz = _normalize_time(attrs.get("endDate"))
    duration = _as_float(attrs.get("duration"))
    duration_unit = attrs.get("durationUnit") or "min"
    if duration is None:
        duration = _duration_minutes(start_time, end_time)
        duration_unit = "min"
    metadata = _metadata(element)
    for key in ("totalDistance", "totalDistanceUnit", "totalEnergyBurned", "totalEnergyBurnedUnit"):
        if attrs.get(key) is not None:
            metadata[key] = attrs[key]
    return ParsedSample(
        record_kind="workout",
        metric_type=attrs.get("workoutActivityType", "HKWorkoutActivityTypeOther"),
        start_time=start_time,
        end_time=end_time,
        value_text=str(duration) if duration is not None else None,
        value_num=duration,
        unit=duration_unit,
        source_device=attrs.get("device"),
        source_app=attrs.get("sourceName"),
        source_record_id=attrs.get("uuid"),
        timezone=tz or end_tz,
        metadata=metadata,
        raw_payload=attrs,
    )


def _activity_samples(element: ElementTree.Element) -> list[ParsedSample]:
    attrs = dict(element.attrib)
    date = attrs.get("dateComponents")
    start_time = f"{date}T00:00:00" if date else None
    definitions = (
        ("HKQuantityTypeIdentifierActiveEnergyBurned", "activeEnergyBurned", "activeEnergyBurnedUnit"),
        ("HKQuantityTypeIdentifierAppleExerciseTime", "appleExerciseTime", "appleExerciseTimeUnit"),
        ("HKQuantityTypeIdentifierAppleStandHour", "appleStandHours", None),
    )
    samples: list[ParsedSample] = []
    for metric_type, value_key, unit_key in definitions:
        if attrs.get(value_key) is None:
            continue
        value = attrs[value_key]
        samples.append(
            ParsedSample(
                record_kind="activity_summary",
                metric_type=metric_type,
                start_time=start_time,
                end_time=start_time,
                value_text=value,
                value_num=_as_float(value),
                unit=attrs.get(unit_key) if unit_key else "count",
                source_device=None,
                source_app="Apple Health ActivitySummary",
                source_record_id=f"{date}:{value_key}",
                timezone=None,
                metadata={},
                raw_payload=attrs,
            )
        )
    return samples


@contextmanager
def open_export(path: Path) -> Iterator[BinaryIO]:
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            xml_entries = [info for info in archive.infolist() if info.filename.lower().endswith(".xml")]
            exact = [info for info in xml_entries if Path(info.filename).name.lower() == "export.xml"]
            localized = [
                info
                for info in xml_entries
                if "cda" not in Path(info.filename).name.lower()
            ]
            candidates = exact or localized
            if not candidates:
                raise ValueError("压缩包中未找到 Apple 健康主 XML 文件")
            selected = max(candidates, key=lambda info: info.file_size)
            with archive.open(selected, "r") as stream:
                yield stream
    else:
        with path.open("rb") as stream:
            yield stream


def iter_samples(path: Path) -> Iterator[ParsedSample]:
    with open_export(path) as stream:
        for _event, element in ElementTree.iterparse(stream, events=("end",)):
            if element.tag == "Record":
                yield _record_sample(element)
                element.clear()
            elif element.tag == "Workout":
                yield _workout_sample(element)
                element.clear()
            elif element.tag == "ActivitySummary":
                yield from _activity_samples(element)
                element.clear()
            elif element.tag in {"Me", "ExportDate", "Correlation", "ClinicalRecord"}:
                element.clear()


def sample_id(sample: ParsedSample) -> str:
    if sample.source_record_id:
        identity = [sample.record_kind, sample.metric_type, sample.source_record_id]
    else:
        identity = [
            sample.record_kind,
            sample.metric_type,
            sample.start_time,
            sample.end_time,
            sample.value_text,
            sample.unit,
            sample.source_app,
            sample.source_device,
            sample.metadata,
        ]
    return hashlib.sha256(json_dumps(identity).encode("utf-8")).hexdigest()


def _source_id(sample: ParsedSample) -> str:
    identity = f"{sample.source_app or ''}|{sample.source_device or ''}"
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]


def _normalize(sample: ParsedSample) -> tuple[str, float | None, str | None, str | None, str, list[str]]:
    if sample.record_kind == "workout":
        canonical = f"workout.{simplify_type(sample.metric_type)}"
        value = convert_value(sample.value_num, sample.unit, "min")
        return canonical, value, sample.value_text, "min", "accepted", []

    definition = METRICS.get(sample.metric_type)
    if not definition:
        return (
            f"unmapped.{simplify_type(sample.metric_type)}",
            sample.value_num,
            sample.value_text,
            sample.unit,
            "unmapped",
            ["metric_not_in_dictionary"],
        )

    value = convert_value(sample.value_num, sample.unit, definition.canonical_unit)
    notes: list[str] = []
    if sample.value_num is not None and sample.unit and definition.canonical_unit:
        if sample.unit != definition.canonical_unit and value == sample.value_num:
            notes.append(f"unit_not_converted:{sample.unit}->{definition.canonical_unit}")
    return (
        definition.canonical_metric,
        value,
        sample.value_text,
        definition.canonical_unit,
        "accepted" if not notes else "review",
        notes,
    )


def _insert_sample(
    connection: sqlite3.Connection,
    sample: ParsedSample,
    import_batch_id: str,
    source_hash: str,
) -> bool:
    sid = sample_id(sample)
    cursor = connection.execute(
        """
        INSERT OR IGNORE INTO health_raw_samples(
            sample_id, record_kind, metric_type, start_time, end_time,
            value_text, value_num, unit, source_device, source_app,
            source_record_id, timezone, metadata_json, raw_payload_json,
            first_import_batch_id, source_file_hash
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            sid,
            sample.record_kind,
            sample.metric_type,
            sample.start_time,
            sample.end_time,
            sample.value_text,
            sample.value_num,
            sample.unit,
            sample.source_device,
            sample.source_app,
            sample.source_record_id,
            sample.timezone,
            json_dumps(sample.metadata),
            json_dumps(sample.raw_payload),
            import_batch_id,
            source_hash,
        ),
    )
    inserted = cursor.rowcount == 1
    connection.execute(
        "INSERT OR IGNORE INTO health_import_memberships(import_batch_id, sample_id, outcome) VALUES (?, ?, ?)",
        (import_batch_id, sid, "inserted" if inserted else "duplicate"),
    )
    if inserted:
        canonical, numeric, text, unit, quality, notes = _normalize(sample)
        connection.execute(
            """
            INSERT INTO health_normalized_samples(
                sample_id, canonical_metric, numeric_value, text_value,
                canonical_unit, local_start_time, local_end_time, timezone,
                quality_status, quality_notes_json, normalization_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sid,
                canonical,
                numeric,
                text,
                unit,
                sample.start_time,
                sample.end_time,
                sample.timezone,
                quality,
                json_dumps(notes),
                NORMALIZATION_VERSION,
            ),
        )

    source_id = _source_id(sample)
    connection.execute(
        """
        INSERT INTO health_sources(
            source_id, source_name, source_device, source_app, first_sample_at, last_sample_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(source_id) DO UPDATE SET
            first_sample_at = CASE
                WHEN excluded.first_sample_at IS NULL THEN health_sources.first_sample_at
                WHEN health_sources.first_sample_at IS NULL THEN excluded.first_sample_at
                ELSE MIN(health_sources.first_sample_at, excluded.first_sample_at)
            END,
            last_sample_at = CASE
                WHEN excluded.last_sample_at IS NULL THEN health_sources.last_sample_at
                WHEN health_sources.last_sample_at IS NULL THEN excluded.last_sample_at
                ELSE MAX(health_sources.last_sample_at, excluded.last_sample_at)
            END,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            source_id,
            sample.source_app or sample.source_device or "unknown",
            sample.source_device,
            sample.source_app,
            sample.start_time,
            sample.end_time or sample.start_time,
        ),
    )
    return inserted


def import_apple_health(path: str | Path, db_path: str | Path = "data/health.db") -> ImportResult:
    source_path = Path(path).resolve()
    if not source_path.is_file():
        raise FileNotFoundError(f"找不到导入文件：{source_path}")
    source_hash = file_sha256(source_path)
    batch_id = str(uuid.uuid4())
    started_at = utc_now()
    initialize(db_path)
    errors: list[dict[str, object]] = []
    total = inserted = duplicates = skipped = 0
    min_date: str | None = None
    max_date: str | None = None

    with closing(connect(db_path)) as connection:
        connection.execute(
            """
            INSERT INTO health_import_batches(
                import_batch_id, source_filename, source_file_hash, source_file_size,
                importer_version, started_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, 'running')
            """,
            (batch_id, source_path.name, source_hash, source_path.stat().st_size, IMPORTER_VERSION, started_at),
        )
        connection.commit()
        try:
            for sample in iter_samples(source_path):
                total += 1
                was_inserted = _insert_sample(connection, sample, batch_id, source_hash)
                inserted += int(was_inserted)
                duplicates += int(not was_inserted)
                if sample.start_time:
                    date = sample.start_time[:10]
                    min_date = date if min_date is None or date < min_date else min_date
                    max_date = date if max_date is None or date > max_date else max_date
                if total % 5000 == 0:
                    connection.commit()
            connection.commit()
            status = "completed"
        except Exception as exc:
            connection.rollback()
            status = "failed"
            errors.append({"record": total, "type": type(exc).__name__, "message": str(exc)})
            committed = connection.execute(
                """
                SELECT outcome, COUNT(*) AS count
                FROM health_import_memberships
                WHERE import_batch_id = ?
                GROUP BY outcome
                """,
                (batch_id,),
            ).fetchall()
            committed_counts = {row["outcome"]: row["count"] for row in committed}
            inserted = committed_counts.get("inserted", 0)
            duplicates = committed_counts.get("duplicate", 0)

        connection.execute(
            """
            UPDATE health_import_batches SET
                completed_at = ?, status = ?, total_records = ?, inserted_records = ?,
                duplicate_records = ?, skipped_records = ?, error_records = ?, error_log_json = ?
            WHERE import_batch_id = ?
            """,
            (
                utc_now(),
                status,
                total,
                inserted,
                duplicates,
                skipped,
                len(errors),
                json_dumps(errors),
                batch_id,
            ),
        )
        connection.commit()

    return ImportResult(
        import_batch_id=batch_id,
        file_hash=source_hash,
        status=status,
        total_records=total,
        inserted_records=inserted,
        duplicate_records=duplicates,
        skipped_records=skipped,
        error_records=len(errors),
        min_date=min_date,
        max_date=max_date,
    )


def renormalize_all(db_path: str | Path = "data/health.db") -> dict[str, int | str]:
    """Rebuild the derivative normalization layer without changing raw samples."""
    initialize(db_path)
    updated = 0
    with closing(connect(db_path)) as connection:
        cursor = connection.execute(
            """
            SELECT sample_id, record_kind, metric_type, start_time, end_time,
                   value_text, value_num, unit, source_device, source_app,
                   source_record_id, timezone, metadata_json, raw_payload_json
            FROM health_raw_samples
            ORDER BY rowid
            """
        )
        while True:
            rows = cursor.fetchmany(5000)
            if not rows:
                break
            for row in rows:
                sample = ParsedSample(
                    record_kind=row["record_kind"],
                    metric_type=row["metric_type"],
                    start_time=row["start_time"],
                    end_time=row["end_time"],
                    value_text=row["value_text"],
                    value_num=row["value_num"],
                    unit=row["unit"],
                    source_device=row["source_device"],
                    source_app=row["source_app"],
                    source_record_id=row["source_record_id"],
                    timezone=row["timezone"],
                    metadata=json.loads(row["metadata_json"] or "{}"),
                    raw_payload=json.loads(row["raw_payload_json"] or "{}"),
                )
                canonical, numeric, text_value, unit, quality, notes = _normalize(sample)
                connection.execute(
                    """
                    UPDATE health_normalized_samples SET
                        canonical_metric = ?, numeric_value = ?, text_value = ?,
                        canonical_unit = ?, quality_status = ?, quality_notes_json = ?,
                        normalization_version = ?, normalized_at = CURRENT_TIMESTAMP
                    WHERE sample_id = ?
                    """,
                    (
                        canonical,
                        numeric,
                        text_value,
                        unit,
                        quality,
                        json_dumps(notes),
                        NORMALIZATION_VERSION,
                        row["sample_id"],
                    ),
                )
                updated += 1
            connection.commit()
    return {"updated": updated, "normalization_version": NORMALIZATION_VERSION}

