"""CLI for training, evaluating, and using the VFR measurement regressor."""

from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch

from vfr_ai_engine.non_runtime.training.data import (
    fit_input_scaler,
    fit_output_scaler,
    load_regressor_dataset,
    split_dataset,
    transform_targets,
)
from vfr_ai_engine.runtime.measurements.regressor_model import (
    MeasurementMLP,
    MeasurementRegressorPredictor,
    StandardScaler,
    checkpoint_metadata,
    load_checkpoint,
    make_data_loader,
    masked_mse_loss,
    predict_array,
    save_checkpoint,
    transform_inputs,
)
from vfr_ai_engine.non_runtime.training.reporting import (
    append_metrics_ndjson,
    build_prediction_rows,
    heuristic_predictions_for_dataset,
    summarize_prediction_rows,
    write_json,
    write_markdown_report,
    write_predictions_csv,
)
from vfr_ai_engine.runtime.measurements.regressor_schema import MODEL_INPUT_FIELDS, OUTPUT_MEASUREMENTS


def main() -> None:
    args = _parse_args()
    if args.command == "train":
        train(args)
    elif args.command == "evaluate":
        evaluate(args)
    elif args.command == "predict":
        predict(args)
    else:
        raise ValueError(f"Unknown command: {args.command}")


def train(args: argparse.Namespace) -> dict[str, Any]:
    _set_seed(args.seed)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = output_dir / "metrics.ndjson"
    if metrics_path.exists() and not args.resume:
        metrics_path.unlink()

    dataset = load_regressor_dataset(args.dataset, mapping_path=args.mapping, require_targets=True)
    splits = split_dataset(
        dataset,
        seed=args.seed,
        validation_fraction=args.validation_fraction,
        test_fraction=args.test_fraction,
    )
    input_scaler = fit_input_scaler(dataset, splits.train)
    output_scaler = fit_output_scaler(dataset, splits.train)

    scaled_inputs = transform_inputs(dataset.inputs, input_scaler)
    scaled_targets = transform_targets(dataset.targets, output_scaler)

    metadata = checkpoint_metadata(
        input_scaler=input_scaler,
        output_scaler=output_scaler,
        hidden_size=args.hidden_size,
        training_args={
            "dataset": str(args.dataset),
            "mapping": str(args.mapping or ""),
            "seed": args.seed,
            "epochs": args.epochs,
            "batch_size": args.batch_size,
            "learning_rate": args.learning_rate,
        },
    )
    model = MeasurementMLP(
        input_size=len(MODEL_INPUT_FIELDS),
        output_size=len(OUTPUT_MEASUREMENTS),
        hidden_size=args.hidden_size,
    )
    optimizer = torch.optim.Adam(model.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay)
    start_epoch = 0
    best_validation_loss = math.inf
    best_epoch = 0

    latest_checkpoint = output_dir / "measurement-regressor-latest.pt"
    best_checkpoint = output_dir / "measurement-regressor-best.pt"
    if args.resume and latest_checkpoint.exists():
        loaded_model, loaded_metadata, checkpoint = load_checkpoint(latest_checkpoint)
        model.load_state_dict(loaded_model.state_dict())
        metadata = loaded_metadata
        start_epoch = int(checkpoint.get("epoch", 0)) + 1
        best_validation_loss = float((checkpoint.get("metrics") or {}).get("validation_loss", math.inf))

    train_loader = make_data_loader(
        scaled_inputs,
        scaled_targets,
        dataset.target_mask,
        splits.train,
        batch_size=args.batch_size,
        shuffle=True,
        seed=args.seed,
    )
    started_at = time.monotonic()
    stale_epochs = 0

    for epoch in range(start_epoch, args.epochs):
        model.train()
        epoch_losses = []
        for batch_inputs, batch_targets, batch_mask in train_loader:
            optimizer.zero_grad()
            batch_predictions = model(batch_inputs)
            loss = masked_mse_loss(batch_predictions, batch_targets, batch_mask)
            loss.backward()
            optimizer.step()
            epoch_losses.append(float(loss.detach().cpu().item()))

        train_loss = float(np.mean(epoch_losses)) if epoch_losses else 0.0
        validation_loss = _evaluate_loss(model, scaled_inputs, scaled_targets, dataset.target_mask, splits.validation)
        epoch_metrics = {
            "epoch": epoch,
            "train_loss": round(train_loss, 6),
            "validation_loss": round(validation_loss, 6),
        }
        append_metrics_ndjson(metrics_path, epoch_metrics)

        save_checkpoint(latest_checkpoint, model, metadata=metadata, epoch=epoch, metrics=epoch_metrics)
        if validation_loss < best_validation_loss - 1e-7:
            best_validation_loss = validation_loss
            best_epoch = epoch
            stale_epochs = 0
            save_checkpoint(best_checkpoint, model, metadata=metadata, epoch=epoch, metrics=epoch_metrics)
        else:
            stale_epochs += 1

        if (epoch + 1) % args.checkpoint_interval == 0:
            save_checkpoint(
                output_dir / f"measurement-regressor-epoch-{epoch + 1:04d}.pt",
                model,
                metadata=metadata,
                epoch=epoch,
                metrics=epoch_metrics,
            )

        if args.early_stopping_patience > 0 and stale_epochs >= args.early_stopping_patience:
            break
        if args.max_hours > 0 and (time.monotonic() - started_at) >= args.max_hours * 3600.0:
            break

    if best_checkpoint.exists():
        model, metadata, _ = load_checkpoint(best_checkpoint)
    final_summary = _write_evaluation_artifacts(
        output_dir=output_dir,
        dataset=dataset,
        model=model,
        metadata=metadata,
        split_by_index=_split_lookup(splits),
        title="Measurement Regressor Training Report",
    )
    write_json(
        output_dir / "metadata.json",
        {
            **metadata,
            "dataset_size": len(dataset.records),
            "splits": {
                "train": len(splits.train),
                "validation": len(splits.validation),
                "test": len(splits.test),
            },
            "best_epoch": best_epoch,
            "summary": final_summary,
        },
    )
    return final_summary


def evaluate(args: argparse.Namespace) -> dict[str, Any]:
    model, metadata, _ = load_checkpoint(args.model)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    dataset = load_regressor_dataset(args.dataset, mapping_path=args.mapping, require_targets=True)
    split_by_index = {index: "evaluation" for index in range(len(dataset.records))}
    return _write_evaluation_artifacts(
        output_dir=output_dir,
        dataset=dataset,
        model=model,
        metadata=metadata,
        split_by_index=split_by_index,
        title="Measurement Regressor Evaluation Report",
    )


def predict(args: argparse.Namespace) -> None:
    predictor = MeasurementRegressorPredictor.from_checkpoint(args.model)
    dataset = load_regressor_dataset(args.input, mapping_path=args.mapping, require_targets=False)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for record in dataset.records:
            payload = {
                "record_id": record.record_id,
                "profile": record.profile,
                "predictions": predictor.predict_profile(record.profile),
            }
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _write_evaluation_artifacts(
    *,
    output_dir: Path,
    dataset,
    model,
    metadata: dict[str, Any],
    split_by_index: dict[int, str],
    title: str,
) -> dict[str, Any]:
    input_scaler = metadata["input_scaler"]
    output_scaler = metadata["output_scaler"]
    scaled_inputs = transform_inputs(dataset.inputs, StandardScaler.from_dict(input_scaler))
    scaled_predictions = predict_array(model, scaled_inputs)
    predictions_cm = StandardScaler.from_dict(output_scaler).inverse_transform(scaled_predictions)
    heuristic_predictions = heuristic_predictions_for_dataset(dataset)
    rows = build_prediction_rows(
        dataset=dataset,
        predictions_cm=predictions_cm,
        split_by_index=split_by_index,
        heuristic_predictions=heuristic_predictions,
    )
    summary = summarize_prediction_rows(rows)
    write_predictions_csv(output_dir / "predictions.csv", rows)
    write_json(output_dir / "summary.json", summary)
    write_markdown_report(output_dir / "measurement-regressor-report.md", summary, title=title)
    return summary


def _evaluate_loss(
    model: MeasurementMLP,
    inputs: np.ndarray,
    targets: np.ndarray,
    target_mask: np.ndarray,
    indices: list[int],
) -> float:
    if not indices:
        return 0.0
    model.eval()
    with torch.no_grad():
        predictions = model(torch.tensor(inputs[indices], dtype=torch.float32))
        loss = masked_mse_loss(
            predictions,
            torch.tensor(targets[indices], dtype=torch.float32),
            torch.tensor(target_mask[indices], dtype=torch.float32),
        )
    return float(loss.detach().cpu().item())


def _split_lookup(splits) -> dict[int, str]:
    lookup: dict[int, str] = {}
    lookup.update({index: "train" for index in splits.train})
    lookup.update({index: "validation" for index in splits.validation})
    lookup.update({index: "test" for index in splits.test})
    return lookup


def _set_seed(seed: int) -> None:
    np.random.seed(seed)
    torch.manual_seed(seed)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train and evaluate the VFR body measurement regressor.")
    subcommands = parser.add_subparsers(dest="command", required=True)

    train_parser = subcommands.add_parser("train")
    _add_dataset_args(train_parser)
    train_parser.add_argument("--output-dir", required=True)
    train_parser.add_argument("--epochs", type=int, default=100)
    train_parser.add_argument("--batch-size", type=int, default=32)
    train_parser.add_argument("--learning-rate", type=float, default=1e-3)
    train_parser.add_argument("--weight-decay", type=float, default=1e-5)
    train_parser.add_argument("--hidden-size", type=int, default=64)
    train_parser.add_argument("--seed", type=int, default=20260430)
    train_parser.add_argument("--validation-fraction", type=float, default=0.15)
    train_parser.add_argument("--test-fraction", type=float, default=0.15)
    train_parser.add_argument("--max-hours", type=float, default=0.0)
    train_parser.add_argument("--checkpoint-interval", type=int, default=10)
    train_parser.add_argument("--early-stopping-patience", type=int, default=20)
    train_parser.add_argument("--resume", action="store_true")

    evaluate_parser = subcommands.add_parser("evaluate")
    _add_dataset_args(evaluate_parser)
    evaluate_parser.add_argument("--model", required=True)
    evaluate_parser.add_argument("--output-dir", required=True)

    predict_parser = subcommands.add_parser("predict")
    predict_parser.add_argument("--model", required=True)
    predict_parser.add_argument("--input", required=True)
    predict_parser.add_argument("--mapping")
    predict_parser.add_argument("--output", required=True)

    return parser.parse_args()


def _add_dataset_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--mapping")


if __name__ == "__main__":
    main()
