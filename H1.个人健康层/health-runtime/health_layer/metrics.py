from __future__ import annotations

from dataclasses import dataclass


NORMALIZATION_VERSION = "health-normalize-v0.3"


@dataclass(frozen=True)
class MetricDefinition:
    canonical_metric: str
    canonical_unit: str | None
    aggregation: str
    domain: str


METRICS: dict[str, MetricDefinition] = {
    "HKQuantityTypeIdentifierStepCount": MetricDefinition("activity.steps", "count", "sum", "activity"),
    "HKQuantityTypeIdentifierDistanceWalkingRunning": MetricDefinition("activity.distance_walking_running", "m", "sum", "activity"),
    "HKQuantityTypeIdentifierActiveEnergyBurned": MetricDefinition("activity.active_energy", "kcal", "sum", "activity"),
    "HKQuantityTypeIdentifierBasalEnergyBurned": MetricDefinition("activity.basal_energy", "kcal", "sum", "activity"),
    "HKQuantityTypeIdentifierAppleExerciseTime": MetricDefinition("activity.exercise_minutes", "min", "sum", "activity"),
    "HKQuantityTypeIdentifierAppleStandTime": MetricDefinition("activity.stand_minutes", "min", "sum", "activity"),
    "HKQuantityTypeIdentifierAppleStandHour": MetricDefinition("activity.stand_hours", "count", "sum", "activity"),
    "HKCategoryTypeIdentifierAppleStandHour": MetricDefinition("activity.stand_hours", "count", "count", "activity"),
    "HKQuantityTypeIdentifierFlightsClimbed": MetricDefinition("activity.flights_climbed", "count", "sum", "activity"),
    "HKQuantityTypeIdentifierDistanceCycling": MetricDefinition("activity.distance_cycling", "m", "sum", "activity"),
    "HKQuantityTypeIdentifierPhysicalEffort": MetricDefinition("activity.physical_effort", "kcal/hr·kg", "mean", "activity"),
    "HKQuantityTypeIdentifierHeartRate": MetricDefinition("cardiovascular.heart_rate", "count/min", "distribution", "cardiovascular"),
    "HKQuantityTypeIdentifierRestingHeartRate": MetricDefinition("cardiovascular.resting_heart_rate", "count/min", "mean", "cardiovascular"),
    "HKQuantityTypeIdentifierWalkingHeartRateAverage": MetricDefinition("cardiovascular.walking_heart_rate", "count/min", "mean", "cardiovascular"),
    "HKQuantityTypeIdentifierHeartRateVariabilitySDNN": MetricDefinition("cardiovascular.hrv_sdnn", "ms", "mean", "cardiovascular"),
    "HKQuantityTypeIdentifierHeartRateVariabilityRMSSD": MetricDefinition("cardiovascular.hrv_rmssd", "ms", "mean", "cardiovascular"),
    "HKQuantityTypeIdentifierVO2Max": MetricDefinition("cardiovascular.vo2_max", "mL/min·kg", "mean", "cardiovascular"),
    "HKQuantityTypeIdentifierBodyMass": MetricDefinition("body.weight", "kg", "latest", "body"),
    "HKQuantityTypeIdentifierBodyFatPercentage": MetricDefinition("body.body_fat_percentage", "%", "latest", "body"),
    "HKQuantityTypeIdentifierLeanBodyMass": MetricDefinition("body.lean_body_mass", "kg", "latest", "body"),
    "HKQuantityTypeIdentifierHeight": MetricDefinition("body.height", "m", "latest", "body"),
    "HKQuantityTypeIdentifierRespiratoryRate": MetricDefinition("other.respiratory_rate", "count/min", "mean", "other"),
    "HKQuantityTypeIdentifierOxygenSaturation": MetricDefinition("other.oxygen_saturation", "%", "mean", "other"),
    "HKQuantityTypeIdentifierAppleSleepingWristTemperature": MetricDefinition("other.sleeping_wrist_temperature", "degC", "mean", "other"),
    "HKQuantityTypeIdentifierTimeInDaylight": MetricDefinition("other.time_in_daylight", "min", "sum", "other"),
    "HKQuantityTypeIdentifierWalkingSpeed": MetricDefinition("mobility.walking_speed", "km/hr", "mean", "mobility"),
    "HKQuantityTypeIdentifierWalkingStepLength": MetricDefinition("mobility.walking_step_length", "cm", "mean", "mobility"),
    "HKQuantityTypeIdentifierWalkingDoubleSupportPercentage": MetricDefinition("mobility.walking_double_support_percentage", "%", "mean", "mobility"),
    "HKQuantityTypeIdentifierWalkingAsymmetryPercentage": MetricDefinition("mobility.walking_asymmetry_percentage", "%", "mean", "mobility"),
    "HKQuantityTypeIdentifierAppleWalkingSteadiness": MetricDefinition("mobility.walking_steadiness", "%", "mean", "mobility"),
    "HKQuantityTypeIdentifierStairDescentSpeed": MetricDefinition("mobility.stair_descent_speed", "m/s", "mean", "mobility"),
    "HKQuantityTypeIdentifierStairAscentSpeed": MetricDefinition("mobility.stair_ascent_speed", "m/s", "mean", "mobility"),
    "HKQuantityTypeIdentifierHeadphoneAudioExposure": MetricDefinition("hearing.headphone_audio_exposure", "dBASPL", "mean", "hearing"),
    "HKQuantityTypeIdentifierEnvironmentalAudioExposure": MetricDefinition("hearing.environmental_audio_exposure", "dBASPL", "mean", "hearing"),
    "HKCategoryTypeIdentifierHeadphoneAudioExposureEvent": MetricDefinition("hearing.headphone_audio_exposure_event", None, "count", "hearing"),
    "HKQuantityTypeIdentifierEstimatedWorkoutEffortScore": MetricDefinition("workout.estimated_effort_score", "appleEffortScore", "mean", "workout"),
    "HKDataTypeSleepDurationGoal": MetricDefinition("sleep.duration_goal", "hr", "latest", "sleep"),
    "HKCategoryTypeIdentifierSleepAnalysis": MetricDefinition("sleep.stage", None, "duration", "sleep"),
    "HKCategoryTypeIdentifierMindfulSession": MetricDefinition("other.mindful_session", "min", "duration", "other"),
}


UNIT_FACTORS: dict[tuple[str, str], float] = {
    ("km", "m"): 1000.0,
    ("mi", "m"): 1609.344,
    ("ft", "m"): 0.3048,
    ("cm", "m"): 0.01,
    ("lb", "kg"): 0.45359237,
    ("g", "kg"): 0.001,
    ("kJ", "kcal"): 0.239005736,
    ("J", "kcal"): 0.000239005736,
    ("h", "min"): 60.0,
    ("s", "min"): 1.0 / 60.0,
}


def simplify_type(metric_type: str) -> str:
    for prefix in (
        "HKQuantityTypeIdentifier",
        "HKCategoryTypeIdentifier",
        "HKWorkoutActivityType",
    ):
        if metric_type.startswith(prefix):
            return metric_type[len(prefix):]
    return metric_type


def convert_value(value: float | None, unit: str | None, target_unit: str | None) -> float | None:
    if value is None or target_unit is None or unit is None or unit == target_unit:
        if target_unit == "%" and unit == "%" and 0 <= value <= 1:
            return value * 100.0
        return value
    if target_unit == "%" and unit in {"count", "%"}:
        return value * 100.0 if 0 <= value <= 1 else value
    factor = UNIT_FACTORS.get((unit, target_unit))
    return value * factor if factor is not None else value

