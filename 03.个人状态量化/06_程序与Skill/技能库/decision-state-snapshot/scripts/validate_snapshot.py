#!/usr/bin/env python3
"""Validate state-snapshot-v1.0 and read legacy retrospective snapshots."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


FORBIDDEN_RESULT_KEYS = {
    "actual_choice",
    "immediate_outcome",
    "actual_result",
    "observed_outcome",
    "post_hoc_reflection",
}
LEGACY_REQUIRED = {
    "snapshot_id",
    "snapshot_type",
    "outcome_known_at_entry",
    "strict_backtest_eligible",
    "captured_at",
    "context",
    "internal_state",
    "goal_state",
    "option_states",
    "unknowns",
    "source_type",
}
V1_REQUIRED = (LEGACY_REQUIRED - {"strict_backtest_eligible"}) | {
    "schema_version",
    "subject_id",
    "event_date",
    "decision_id",
    "decision_time",
    "information_cutoff",
    "decision_question",
    "prediction_window",
    "choice_set",
    "field_evidence",
    "source_trace",
    "research_eligibility",
}


def extract_json(markdown: str) -> dict:
    match = re.search(r"```json\s*(.*?)```", markdown, re.DOTALL)
    if not match:
        raise ValueError("missing ```json block")
    return json.loads(match.group(1))


def walk_keys(value, path=""):
    if isinstance(value, dict):
        for key, nested in value.items():
            next_path = f"{path}.{key}" if path else key
            yield next_path, key
            yield from walk_keys(nested, next_path)
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            yield from walk_keys(nested, f"{path}[{index}]")


def scale_error(value, field: str) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 5:
        return f"{field} must be an integer 0-5 or null"
    return None


def validate(record: dict) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    legacy = record.get("schema_version") != "state-snapshot-v1.0"
    required = LEGACY_REQUIRED if legacy else V1_REQUIRED
    missing = required - record.keys()
    if missing:
        errors.append("missing required keys: " + ", ".join(sorted(missing)))

    if legacy:
        warnings.append("legacy schema: structural compatibility only")

    research = record.get("research_eligibility") if not legacy else None
    strict_eligible = (
        record.get("strict_backtest_eligible")
        if legacy
        else research.get("strict_backtest_eligible") if isinstance(research, dict) else None
    )

    kind = record.get("snapshot_type")
    if kind not in {"locked_prediction", "retrospective_reconstruction"}:
        errors.append("invalid snapshot_type")
    elif kind == "retrospective_reconstruction":
        if record.get("outcome_known_at_entry") is not True:
            errors.append("retrospective reconstruction requires outcome_known_at_entry: true")
        if strict_eligible is not False:
            errors.append("retrospective reconstruction requires strict_backtest_eligible: false")
    elif record.get("outcome_known_at_entry") is not False:
        errors.append("locked prediction requires outcome_known_at_entry: false")

    for key_path, key in walk_keys(record):
        if key in FORBIDDEN_RESULT_KEYS:
            errors.append(f"forbidden result key: {key_path}")

    options = record.get("option_states")
    if not isinstance(options, list) or not options:
        errors.append("option_states must contain at least one option")
    else:
        for index, option in enumerate(options):
            if not isinstance(option, dict):
                errors.append(f"option_states[{index}] must be an object")
                continue
            if option.get("available_now") not in {"yes", "no", "uncertain"}:
                errors.append(f"option_states[{index}].available_now is invalid")
            error = scale_error(option.get("start_friction_0_to_5"), f"option_states[{index}].start_friction_0_to_5")
            if error:
                errors.append(error)

    if not isinstance(record.get("unknowns"), list):
        errors.append("unknowns must be a list")

    internal = record.get("internal_state")
    if isinstance(internal, dict):
        for field in ("energy_0_to_5", "stress_load_0_to_5"):
            error = scale_error(internal.get(field), f"internal_state.{field}")
            if error:
                errors.append(error)

    if not legacy:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(record.get("event_date", ""))):
            errors.append("event_date must be YYYY-MM-DD")
        choice_set = record.get("choice_set")
        if not isinstance(choice_set, dict) or choice_set.get("mutually_exclusive") is not True:
            errors.append("choice_set.mutually_exclusive must be true")
        elif choice_set.get("completeness") not in {"complete", "partial"}:
            errors.append("choice_set.completeness must be complete or partial")
        elif not isinstance(choice_set.get("options"), list) or not choice_set.get("options"):
            errors.append("choice_set.options must contain at least one option")
        field_evidence = record.get("field_evidence")
        if not isinstance(field_evidence, list) or not field_evidence:
            errors.append("field_evidence must contain at least one evidence record")
        source_trace = record.get("source_trace")
        if not isinstance(source_trace, list) or not source_trace:
            errors.append("source_trace must contain at least one source record")
        if not isinstance(research, dict):
            errors.append("research_eligibility must be an object")
        else:
            for field in (
                "pattern_analysis_eligible",
                "strict_backtest_eligible",
                "causal_claim_eligible",
            ):
                if not isinstance(research.get(field), bool):
                    errors.append(f"research_eligibility.{field} must be boolean")
            if research.get("strict_backtest_eligible") is not False:
                errors.append("03 snapshot cannot grant strict backtest eligibility")
            if research.get("causal_claim_eligible") is not False:
                errors.append("03 snapshot cannot grant causal claim eligibility")
        if kind == "retrospective_reconstruction" and not record.get("reconstructed_at"):
            errors.append("retrospective reconstruction requires reconstructed_at")
        if kind == "locked_prediction" and record.get("reconstructed_at") is not None:
            errors.append("locked prediction requires reconstructed_at: null")

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("snapshot", type=Path)
    args = parser.parse_args()
    try:
        record = extract_json(args.snapshot.read_text(encoding="utf-8"))
        errors, warnings = validate(record)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"INVALID: {exc}")
        return 1
    if errors:
        print("INVALID:")
        for error in errors:
            print(f"- {error}")
        return 1
    label = "OK_LEGACY" if warnings else "OK"
    print(f"{label}: {args.snapshot.name}")
    for warning in warnings:
        print(f"- WARNING: {warning}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
