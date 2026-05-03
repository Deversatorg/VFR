"""Evaluation metrics and report writers for measurement regressor runs."""

from __future__ import annotations

import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from vfr_ai_engine.runtime.measurements.anthropometry import infer_measurement_targets
from vfr_ai_engine.non_runtime.training.data import RegressorDataset
from vfr_ai_engine.runtime.measurements.regressor_schema import OUTPUT_MEASUREMENTS


def heuristic_predictions_for_dataset(dataset: RegressorDataset) -> list[dict[str, float]]:
    predictions: list[dict[str, float]] = []
    for record in dataset.records:
        profile = record.profile
        targets, _, _ = infer_measurement_targets(
            height_cm=float(profile["height_cm"]),
            weight_kg=float(profile["weight_kg"]),
            body_type=str(profile["body_type"]),
            gender=str(profile["gender"]),
            muscularity=None,
            body_fat_percentage=None,
            overrides=None,
            hints=None,
        )
        predictions.append(targets)
    return predictions


def build_prediction_rows(
    *,
    dataset: RegressorDataset,
    predictions_cm: np.ndarray,
    split_by_index: dict[int, str],
    heuristic_predictions: list[dict[str, float]] | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row_index, record in enumerate(dataset.records):
        for output_index, measurement_name in enumerate(OUTPUT_MEASUREMENTS):
            if dataset.target_mask[row_index, output_index] <= 0:
                continue
            actual = float(dataset.targets[row_index, output_index])
            predicted = float(predictions_cm[row_index, output_index])
            heuristic = None
            if heuristic_predictions is not None:
                heuristic = heuristic_predictions[row_index].get(measurement_name)
            regressor_error = predicted - actual
            heuristic_error = None if heuristic is None else float(heuristic) - actual
            rows.append(
                {
                    "record_id": record.record_id,
                    "split": split_by_index.get(row_index, "unknown"),
                    "gender": record.metadata.get("gender", ""),
                    "body_type": record.metadata.get("body_type", ""),
                    "bmi_bucket": record.metadata.get("bmi_bucket", ""),
                    "measurement_mode": record.metadata.get("measurement_mode", ""),
                    "measurement": measurement_name,
                    "actual_cm": round(actual, 4),
                    "predicted_cm": round(predicted, 4),
                    "heuristic_cm": None if heuristic is None else round(float(heuristic), 4),
                    "regressor_error_cm": round(regressor_error, 4),
                    "heuristic_error_cm": None if heuristic_error is None else round(heuristic_error, 4),
                    "regressor_abs_error_cm": round(abs(regressor_error), 4),
                    "heuristic_abs_error_cm": None if heuristic_error is None else round(abs(heuristic_error), 4),
                }
            )
    return rows


def summarize_prediction_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "overall": _summarize_group(rows),
        "by_measurement": _group_summary(rows, "measurement"),
        "by_gender": _group_summary(rows, "gender"),
        "by_body_type": _group_summary(rows, "body_type"),
        "by_bmi_bucket": _group_summary(rows, "bmi_bucket"),
        "by_measurement_mode": _group_summary(rows, "measurement_mode"),
        "by_split": _group_summary(rows, "split"),
        "worst_regressor_rows": sorted(
            rows,
            key=lambda row: float(row["regressor_abs_error_cm"]),
            reverse=True,
        )[:20],
    }


def write_predictions_csv(path: str | Path, rows: list[dict[str, Any]]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "record_id",
        "split",
        "gender",
        "body_type",
        "bmi_bucket",
        "measurement_mode",
        "measurement",
        "actual_cm",
        "predicted_cm",
        "heuristic_cm",
        "regressor_error_cm",
        "heuristic_error_cm",
        "regressor_abs_error_cm",
        "heuristic_abs_error_cm",
    ]
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: str | Path, payload: Any) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def append_metrics_ndjson(path: str | Path, payload: dict[str, Any]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def write_markdown_report(path: str | Path, summary: dict[str, Any], *, title: str) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# {title}",
        "",
        "## Overall",
        "",
        _format_summary_table({"all": summary["overall"]}),
        "",
        "## By Measurement",
        "",
        _format_summary_table(summary["by_measurement"]),
        "",
        "## By Gender",
        "",
        _format_summary_table(summary["by_gender"]),
        "",
        "## By Body Type",
        "",
        _format_summary_table(summary["by_body_type"]),
        "",
        "## By BMI Bucket",
        "",
        _format_summary_table(summary["by_bmi_bucket"]),
        "",
        "## Worst Regressor Rows",
        "",
        "| record | split | measurement | actual | predicted | error | heuristic error |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for row in summary["worst_regressor_rows"][:12]:
        lines.append(
            "| {record_id} | {split} | {measurement} | {actual_cm:.2f} | {predicted_cm:.2f} | "
            "{regressor_error_cm:.2f} | {heuristic_error} |".format(
                **row,
                heuristic_error=_format_optional_number(row.get("heuristic_error_cm")),
            )
        )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _group_summary(rows: list[dict[str, Any]], field: str) -> dict[str, dict[str, float]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = str(row.get(field) or "unknown")
        grouped[key].append(row)
    return {key: _summarize_group(group_rows) for key, group_rows in sorted(grouped.items())}


def _summarize_group(rows: list[dict[str, Any]]) -> dict[str, float]:
    regressor_errors = [float(row["regressor_error_cm"]) for row in rows]
    heuristic_errors = [
        float(row["heuristic_error_cm"])
        for row in rows
        if row.get("heuristic_error_cm") is not None
    ]
    result = _error_stats(regressor_errors)
    result = {f"regressor_{key}": value for key, value in result.items()}
    result["count"] = float(len(rows))
    if heuristic_errors:
        result.update({f"heuristic_{key}": value for key, value in _error_stats(heuristic_errors).items()})
    return result


def _error_stats(errors: list[float]) -> dict[str, float]:
    if not errors:
        return {"mae_cm": 0.0, "mean_signed_error_cm": 0.0, "max_abs_error_cm": 0.0}
    return {
        "mae_cm": round(statistics.fmean(abs(error) for error in errors), 4),
        "mean_signed_error_cm": round(statistics.fmean(errors), 4),
        "max_abs_error_cm": round(max(abs(error) for error in errors), 4),
    }


def _format_summary_table(summary: dict[str, dict[str, float]]) -> str:
    lines = [
        "| group | count | regressor MAE | regressor bias | regressor max | heuristic MAE | heuristic bias |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for group, metrics in summary.items():
        lines.append(
            "| {group} | {count:.0f} | {reg_mae} | {reg_bias} | {reg_max} | {heur_mae} | {heur_bias} |".format(
                group=group or "unknown",
                count=metrics.get("count", 0.0),
                reg_mae=_format_optional_number(metrics.get("regressor_mae_cm")),
                reg_bias=_format_optional_number(metrics.get("regressor_mean_signed_error_cm")),
                reg_max=_format_optional_number(metrics.get("regressor_max_abs_error_cm")),
                heur_mae=_format_optional_number(metrics.get("heuristic_mae_cm")),
                heur_bias=_format_optional_number(metrics.get("heuristic_mean_signed_error_cm")),
            )
        )
    return "\n".join(lines)


def _format_optional_number(value: Any) -> str:
    if value is None:
        return ""
    return f"{float(value):.2f}"
