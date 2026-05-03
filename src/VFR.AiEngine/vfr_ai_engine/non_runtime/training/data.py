"""Dataset loading, normalization, scaling, and splitting for measurement training."""

from __future__ import annotations

import csv
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from vfr_ai_engine.runtime.measurements.regressor_model import StandardScaler, transform_inputs
from vfr_ai_engine.runtime.measurements.regressor_schema import (
    FIELD_ALIASES,
    MEASUREMENT_ALIASES,
    NUMERIC_INPUT_FIELDS,
    OUTPUT_MEASUREMENTS,
    bmi_bucket,
    derive_bmi,
    encode_profile_features,
    normalize_body_type,
    normalize_gender,
    parse_float,
)


@dataclass
class MeasurementRecord:
    record_id: str
    profile: dict[str, Any]
    targets: dict[str, float]
    metadata: dict[str, Any]


@dataclass
class RegressorDataset:
    records: list[MeasurementRecord]
    inputs: np.ndarray
    targets: np.ndarray
    target_mask: np.ndarray


@dataclass
class DatasetSplits:
    train: list[int]
    validation: list[int]
    test: list[int]


def load_column_mapping(path: str | Path | None) -> dict[str, Any]:
    if not path:
        return {}
    mapping_path = Path(path)
    with mapping_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if isinstance(payload, dict) and "columns" in payload:
        return dict(payload["columns"])
    if not isinstance(payload, dict):
        raise ValueError("Column mapping must be a JSON object.")
    return dict(payload)


def load_regressor_dataset(
    dataset_path: str | Path,
    *,
    mapping_path: str | Path | None = None,
    require_targets: bool = True,
) -> RegressorDataset:
    mapping = load_column_mapping(mapping_path)
    raw_records = _read_dataset_records(Path(dataset_path))
    records = [
        record
        for index, raw_record in enumerate(raw_records)
        if (record := _normalize_record(raw_record, index, mapping, require_targets=require_targets)) is not None
    ]
    if not records:
        raise ValueError("Dataset did not contain any usable anthropometric rows.")
    return build_dataset_from_records(records)


def build_dataset_from_records(records: list[MeasurementRecord]) -> RegressorDataset:
    inputs = np.asarray([encode_profile_features(record.profile) for record in records], dtype=np.float32)
    targets = np.zeros((len(records), len(OUTPUT_MEASUREMENTS)), dtype=np.float32)
    target_mask = np.zeros_like(targets)

    for row_index, record in enumerate(records):
        for column_index, measurement_name in enumerate(OUTPUT_MEASUREMENTS):
            value = record.targets.get(measurement_name)
            if value is None:
                continue
            targets[row_index, column_index] = float(value)
            target_mask[row_index, column_index] = 1.0

    return RegressorDataset(records=records, inputs=inputs, targets=targets, target_mask=target_mask)


def split_dataset(
    dataset: RegressorDataset,
    *,
    seed: int,
    validation_fraction: float = 0.15,
    test_fraction: float = 0.15,
) -> DatasetSplits:
    indices = list(range(len(dataset.records)))
    rng = random.Random(seed)
    rng.shuffle(indices)

    if len(indices) < 3:
        return DatasetSplits(train=indices, validation=indices, test=indices)

    test_count = max(1, int(round(len(indices) * test_fraction)))
    validation_count = max(1, int(round(len(indices) * validation_fraction)))
    if test_count + validation_count >= len(indices):
        test_count = 1
        validation_count = 1

    test = indices[:test_count]
    validation = indices[test_count : test_count + validation_count]
    train = indices[test_count + validation_count :]
    return DatasetSplits(train=train, validation=validation, test=test)


def fit_input_scaler(dataset: RegressorDataset, indices: list[int]) -> StandardScaler:
    numeric_values = dataset.inputs[indices, : len(NUMERIC_INPUT_FIELDS)]
    return StandardScaler.fit(NUMERIC_INPUT_FIELDS, numeric_values)


def fit_output_scaler(dataset: RegressorDataset, indices: list[int]) -> StandardScaler:
    return StandardScaler.fit_masked(
        OUTPUT_MEASUREMENTS,
        dataset.targets[indices],
        dataset.target_mask[indices],
    )


def transform_targets(targets: np.ndarray, scaler: StandardScaler) -> np.ndarray:
    return scaler.transform(targets)


def _read_dataset_records(path: Path) -> list[dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))
    if suffix == ".jsonl":
        records = []
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records
    if suffix == ".json":
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if isinstance(payload, dict) and isinstance(payload.get("cases"), list):
            return list(payload["cases"])
        if isinstance(payload, list):
            return payload
    raise ValueError(f"Unsupported dataset format: {path}. Use CSV, JSONL, or JSON.")


def _normalize_record(
    raw_record: Mapping[str, Any],
    index: int,
    mapping: Mapping[str, Any],
    *,
    require_targets: bool,
) -> MeasurementRecord | None:
    flattened = _flatten_record(raw_record)
    height_cm = _extract_numeric(flattened, "height_cm", mapping)
    weight_kg = _extract_numeric(flattened, "weight_kg", mapping)
    bmi = derive_bmi(height_cm, weight_kg, _extract_numeric(flattened, "bmi", mapping))
    if height_cm is None or weight_kg is None or bmi is None:
        return None

    gender = normalize_gender(_extract_raw(flattened, "gender", mapping))
    body_type = normalize_body_type(_extract_raw(flattened, "body_type", mapping), bmi)
    profile = {
        "height_cm": height_cm,
        "weight_kg": weight_kg,
        "bmi": bmi,
        "gender": gender,
        "body_type": body_type,
        "muscularity": _extract_numeric(flattened, "muscularity", mapping) or 0.0,
        "body_fat_percentage": _extract_numeric(flattened, "body_fat_percentage", mapping) or 0.0,
    }

    targets: dict[str, float] = {}
    for measurement_name in OUTPUT_MEASUREMENTS:
        value = _extract_measurement(flattened, measurement_name, mapping)
        if value is not None and value > 0:
            targets[measurement_name] = value

    if require_targets and not targets:
        return None

    record_id = str(
        flattened.get("name")
        or flattened.get("id")
        or flattened.get("record_id")
        or f"row_{index:05d}"
    )
    metadata = {
        "record_id": record_id,
        "source": flattened.get("source", ""),
        "measurement_mode": _extract_raw(flattened, "measurement_mode", mapping) or "",
        "gender": gender,
        "body_type": body_type,
        "bmi": bmi,
        "bmi_bucket": bmi_bucket(bmi),
    }
    return MeasurementRecord(record_id=record_id, profile=profile, targets=targets, metadata=metadata)


def _flatten_record(record: Mapping[str, Any]) -> dict[str, Any]:
    flattened = dict(record)
    measurements = record.get("measurements")
    if isinstance(measurements, Mapping):
        for key, value in measurements.items():
            flattened.setdefault(str(key), value)
    return flattened


def _extract_raw(row: Mapping[str, Any], canonical_name: str, mapping: Mapping[str, Any]) -> Any:
    spec = mapping.get(canonical_name)
    if spec is not None:
        value = _extract_by_spec(row, spec)
        if value is not None:
            return value
    for alias in FIELD_ALIASES.get(canonical_name, (canonical_name,)):
        if alias in row:
            return row[alias]
    return None


def _extract_numeric(row: Mapping[str, Any], canonical_name: str, mapping: Mapping[str, Any]) -> float | None:
    return parse_float(_extract_raw(row, canonical_name, mapping))


def _extract_measurement(row: Mapping[str, Any], measurement_name: str, mapping: Mapping[str, Any]) -> float | None:
    spec = mapping.get(measurement_name)
    if spec is not None:
        value = _extract_by_spec(row, spec)
        return parse_float(value)
    for alias in MEASUREMENT_ALIASES.get(measurement_name, (measurement_name,)):
        if alias in row:
            return parse_float(row[alias])
    return None


def _extract_by_spec(row: Mapping[str, Any], spec: Any) -> Any:
    if isinstance(spec, str):
        return row.get(spec)
    if isinstance(spec, list):
        for column_name in spec:
            if column_name in row and row[column_name] not in (None, ""):
                return row[column_name]
        return None
    if isinstance(spec, Mapping):
        columns = spec.get("columns") or spec.get("column")
        if isinstance(columns, str):
            raw_value = row.get(columns)
        elif isinstance(columns, list):
            raw_value = None
            for column_name in columns:
                if column_name in row and row[column_name] not in (None, ""):
                    raw_value = row[column_name]
                    break
        else:
            raw_value = None
        numeric = parse_float(raw_value)
        if numeric is None:
            return raw_value
        scale = parse_float(spec.get("scale")) if "scale" in spec else None
        offset = parse_float(spec.get("offset")) if "offset" in spec else None
        if scale is not None:
            numeric *= scale
        if offset is not None:
            numeric += offset
        return numeric
    raise ValueError(f"Unsupported mapping spec: {spec!r}")
