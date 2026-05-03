"""PyTorch model, loss, checkpoint, and inference helpers for measurement regression."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from vfr_ai_engine.runtime.measurements.regressor_schema import (
    MODEL_INPUT_FIELDS,
    NUMERIC_INPUT_FIELDS,
    OUTPUT_MEASUREMENTS,
    encode_profile_features,
)


class StandardScaler:
    def __init__(self, fields: Iterable[str], mean: Iterable[float], std: Iterable[float]) -> None:
        self.fields = tuple(fields)
        self.mean = np.asarray(list(mean), dtype=np.float32)
        self.std = np.asarray(list(std), dtype=np.float32)

    @classmethod
    def fit(cls, fields: Iterable[str], values: np.ndarray) -> "StandardScaler":
        mean = values.mean(axis=0)
        std = values.std(axis=0)
        std = np.where(std < 1e-6, 1.0, std)
        return cls(tuple(fields), mean.tolist(), std.tolist())

    @classmethod
    def fit_masked(cls, fields: Iterable[str], values: np.ndarray, mask: np.ndarray) -> "StandardScaler":
        means = []
        stds = []
        for index in range(values.shape[1]):
            observed = values[mask[:, index] > 0, index]
            if observed.size == 0:
                means.append(0.0)
                stds.append(1.0)
                continue
            std = float(observed.std())
            means.append(float(observed.mean()))
            stds.append(std if std >= 1e-6 else 1.0)
        return cls(tuple(fields), means, stds)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "StandardScaler":
        return cls(payload["fields"], payload["mean"], payload["std"])

    def to_dict(self) -> dict[str, Any]:
        return {
            "fields": list(self.fields),
            "mean": self.mean.astype(float).tolist(),
            "std": self.std.astype(float).tolist(),
        }

    def transform(self, values: np.ndarray) -> np.ndarray:
        return ((values - self.mean) / self.std).astype(np.float32)

    def inverse_transform(self, values: np.ndarray) -> np.ndarray:
        return (values * self.std + self.mean).astype(np.float32)


def transform_inputs(inputs: np.ndarray, scaler: StandardScaler) -> np.ndarray:
    transformed = inputs.copy().astype(np.float32)
    numeric_count = len(NUMERIC_INPUT_FIELDS)
    transformed[:, :numeric_count] = scaler.transform(transformed[:, :numeric_count])
    return transformed


class MeasurementMLP(nn.Module):
    """Small tabular multi-output regressor for body measurement targets."""

    def __init__(self, input_size: int, output_size: int, hidden_size: int = 64) -> None:
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(input_size, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, output_size),
        )

    def forward(self, features: torch.Tensor) -> torch.Tensor:
        return self.network(features)


def masked_mse_loss(predictions: torch.Tensor, targets: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    squared_error = (predictions - targets).pow(2) * mask
    denominator = mask.sum().clamp_min(1.0)
    return squared_error.sum() / denominator


def make_data_loader(
    inputs: np.ndarray,
    targets: np.ndarray,
    target_mask: np.ndarray,
    indices: list[int],
    *,
    batch_size: int,
    shuffle: bool,
    seed: int,
) -> DataLoader:
    generator = torch.Generator()
    generator.manual_seed(seed)
    tensors = TensorDataset(
        torch.tensor(inputs[indices], dtype=torch.float32),
        torch.tensor(targets[indices], dtype=torch.float32),
        torch.tensor(target_mask[indices], dtype=torch.float32),
    )
    return DataLoader(tensors, batch_size=batch_size, shuffle=shuffle, generator=generator)


def predict_array(model: MeasurementMLP, inputs: np.ndarray, *, batch_size: int = 256) -> np.ndarray:
    model.eval()
    predictions: list[np.ndarray] = []
    with torch.no_grad():
        for start in range(0, len(inputs), batch_size):
            batch = torch.tensor(inputs[start : start + batch_size], dtype=torch.float32)
            predictions.append(model(batch).detach().cpu().numpy())
    return np.vstack(predictions).astype(np.float32)


def checkpoint_metadata(
    *,
    input_scaler: StandardScaler,
    output_scaler: StandardScaler,
    hidden_size: int,
    training_args: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "version": 1,
        "model": {
            "input_size": len(MODEL_INPUT_FIELDS),
            "hidden_size": hidden_size,
            "output_size": len(OUTPUT_MEASUREMENTS),
        },
        "input_fields": list(MODEL_INPUT_FIELDS),
        "output_measurements": list(OUTPUT_MEASUREMENTS),
        "input_scaler": input_scaler.to_dict(),
        "output_scaler": output_scaler.to_dict(),
        "training_args": training_args or {},
    }


def save_checkpoint(
    path: str | Path,
    model: MeasurementMLP,
    *,
    metadata: dict[str, Any],
    epoch: int,
    metrics: dict[str, Any] | None = None,
) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "state_dict": model.state_dict(),
            "metadata": metadata,
            "epoch": epoch,
            "metrics": metrics or {},
        },
        path,
    )


def load_checkpoint(path: str | Path) -> tuple[MeasurementMLP, dict[str, Any], dict[str, Any]]:
    checkpoint = torch.load(path, map_location="cpu")
    metadata = checkpoint.get("metadata")
    if not isinstance(metadata, dict):
        raise RuntimeError(f"Measurement regressor checkpoint is missing metadata: {path}")
    model_config = metadata.get("model") or {}
    model = MeasurementMLP(
        input_size=int(model_config.get("input_size", len(MODEL_INPUT_FIELDS))),
        output_size=int(model_config.get("output_size", len(OUTPUT_MEASUREMENTS))),
        hidden_size=int(model_config.get("hidden_size", 64)),
    )
    model.load_state_dict(checkpoint["state_dict"])
    model.eval()
    return model, metadata, checkpoint


class MeasurementRegressorPredictor:
    def __init__(self, model: MeasurementMLP, metadata: dict[str, Any]) -> None:
        self.model = model
        self.metadata = metadata
        self.input_scaler = StandardScaler.from_dict(metadata["input_scaler"])
        self.output_scaler = StandardScaler.from_dict(metadata["output_scaler"])
        self.output_measurements = tuple(metadata.get("output_measurements", OUTPUT_MEASUREMENTS))

    @classmethod
    def from_checkpoint(cls, path: str | Path) -> "MeasurementRegressorPredictor":
        model, metadata, _ = load_checkpoint(path)
        return cls(model, metadata)

    def predict_profile(self, profile: dict[str, Any]) -> dict[str, float]:
        features = np.asarray([encode_profile_features(profile)], dtype=np.float32)
        scaled_inputs = transform_inputs(features, self.input_scaler)
        scaled_outputs = predict_array(self.model, scaled_inputs, batch_size=1)
        outputs = self.output_scaler.inverse_transform(scaled_outputs)[0]
        return {
            measurement_name: round(float(value), 2)
            for measurement_name, value in zip(self.output_measurements, outputs)
            if np.isfinite(value) and value > 0
        }
