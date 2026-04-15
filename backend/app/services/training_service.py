import csv
import json
import os
import pickle
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from backend.app.services.feature_service import build_model_feature_vector
from backend.app.services.ingestion_service import get_environment_bundle, search_locations

ARTIFACT_DIR = Path(__file__).resolve().parents[3] / "data" / "processed" / "artifacts"
DATASET_PATH = ARTIFACT_DIR / "training_dataset.json"
MODEL_PATH = ARTIFACT_DIR / "risk_model.pkl"
METADATA_PATH = ARTIFACT_DIR / "risk_model_metadata.json"
HFID_ENV_CACHE_PATH = ARTIFACT_DIR / "hfid_environment_cache.json"
REAL_LABELS_PATH = Path(__file__).resolve().parents[3] / "data" / "raw" / "training_labels.csv"
HFID_PATH = Path(__file__).resolve().parents[3] / "data" / "raw" / "hfid_hv1.csv"
HFID_MAX_TRAINING_ROWS = int(os.getenv("HFID_MAX_TRAINING_ROWS", "120"))

FEATURE_ORDER = [
    "avg_temperature_c",
    "avg_precipitation_mm",
    "precip_trend_last_30d",
    "vegetation_anomaly",
    "soil_moisture_percentile",
    "drought_index",
    "crop_sensitivity",
]


def _synthetic_training_rows() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    temperatures = [21.0, 26.0, 30.0, 34.0, 38.0]
    precipitations = [0.8, 2.5, 5.0, 9.0, 14.0]
    trends = [-10.0, -4.0, 0.0, 3.0]
    vegetation = [-0.35, -0.2, -0.05, 0.1]
    soil = [0.15, 0.3, 0.5, 0.7]
    drought = [0.25, 0.45, 0.65, 0.85]
    sensitivity = [0.35, 0.55, 0.75]

    for temp in temperatures:
        for rain in precipitations:
            for trend in trends:
                for ndvi in vegetation:
                    soil_value = soil[(int(temp + rain) + int(abs(trend))) % len(soil)]
                    drought_value = drought[(int(abs(ndvi) * 100) + int(rain)) % len(drought)]
                    sensitivity_value = sensitivity[(int(temp) + int(abs(ndvi) * 100)) % len(sensitivity)]
                    score = float(
                        0.22 * np.clip((temp - 24) / 14, 0, 1)
                        + 0.18 * np.clip((8 - rain) / 8, 0, 1)
                        + 0.12 * np.clip((-trend) / 10, 0, 1)
                        + 0.18 * np.clip((-ndvi) / 0.4, 0, 1)
                        + 0.12 * np.clip((0.5 - soil_value) / 0.5, 0, 1)
                        + 0.10 * np.clip(drought_value, 0, 1)
                        + 0.08 * np.clip(sensitivity_value, 0, 1)
                    )
                    label = "high" if score >= 0.72 else "medium" if score >= 0.40 else "low"
                    rows.append(
                        {
                            "avg_temperature_c": temp,
                            "avg_precipitation_mm": rain,
                            "precip_trend_last_30d": trend,
                            "vegetation_anomaly": ndvi,
                            "soil_moisture_percentile": soil_value,
                            "drought_index": drought_value,
                            "crop_sensitivity": sensitivity_value,
                            "label": label,
                        }
                    )
    return rows


def _safe_float(value: Any) -> Optional[float]:
    if value in (None, "", "nan", "NaN"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _coalesce_phase(row: Dict[str, Any]) -> Optional[float]:
    return _safe_float(row.get("ipc_phase_ipcch")) or _safe_float(row.get("ipc_phase_fews"))


def _phase_to_label(phase: Optional[float]) -> Optional[str]:
    if phase is None:
        return None
    if phase >= 4:
        return "high"
    if phase >= 3:
        return "medium"
    if phase >= 1:
        return "low"
    return None


def _admin_key(country: str, admin1: str, admin2: str) -> Tuple[str, str, str]:
    return (country.strip().lower(), admin1.strip().lower(), admin2.strip().lower())


def _read_hfid_latest_rows() -> List[Dict[str, Any]]:
    if not HFID_PATH.exists():
        return []

    latest_rows: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    with HFID_PATH.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            phase = _coalesce_phase(row)
            label = _phase_to_label(phase)
            if label is None:
                continue

            country = (row.get("ADMIN0") or "").strip()
            admin1 = (row.get("ADMIN1") or "").strip()
            admin2 = (row.get("ADMIN2") or "").strip()
            if not country or not admin1:
                continue

            key = _admin_key(country, admin1, admin2)
            current = latest_rows.get(key)
            current_month = current.get("year_month", "") if current else ""
            next_month = row.get("year_month", "") or ""
            if current is None or next_month >= current_month:
                latest_rows[key] = {
                    **row,
                    "_selected_phase": phase,
                    "_derived_label": label,
                }

    return list(latest_rows.values())


def load_hfid_latest_labels() -> List[Dict[str, Any]]:
    rows = _read_hfid_latest_rows()
    normalized: List[Dict[str, Any]] = []
    for row in rows:
        normalized.append(
            {
                "year_month": row.get("year_month"),
                "country": row.get("ADMIN0", ""),
                "admin1": row.get("ADMIN1", ""),
                "admin2": row.get("ADMIN2", ""),
                "phase": row.get("_selected_phase"),
                "label": row.get("_derived_label"),
                "ha_fews": _safe_float(row.get("ha_fews")),
                "ha_ipcch": _safe_float(row.get("ha_ipcch")),
                "fcs_lit": _safe_float(row.get("fcs_lit")),
                "rcsi_lit": _safe_float(row.get("rcsi_lit")),
                "iso3": row.get("iso3"),
            }
        )
    return normalized


def ensure_artifact_dir() -> None:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)


def _load_environment_cache() -> Dict[str, Dict[str, Any]]:
    if not HFID_ENV_CACHE_PATH.exists():
        return {}
    try:
        return json.loads(HFID_ENV_CACHE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_environment_cache(cache: Dict[str, Dict[str, Any]]) -> None:
    HFID_ENV_CACHE_PATH.write_text(json.dumps(cache, indent=2), encoding="utf-8")


def _build_location_query(country: str, admin1: str, admin2: str) -> str:
    parts = [part for part in [admin2, admin1, country] if part]
    return ", ".join(parts)


def _resolve_environment_for_hfid_row(row: Dict[str, Any], cache: Dict[str, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    key = "|".join([row.get("ADMIN0", ""), row.get("ADMIN1", ""), row.get("ADMIN2", "")]).strip().lower()
    if key in cache:
        return cache[key]

    query = _build_location_query(
        country=row.get("ADMIN0", ""),
        admin1=row.get("ADMIN1", ""),
        admin2=row.get("ADMIN2", ""),
    )
    if not query:
        return None

    matches = search_locations(query=query, limit=1)
    if not matches:
        return None

    match = matches[0]
    environment = get_environment_bundle(match["latitude"], match["longitude"])
    cached = {
        "query": query,
        "name": match["name"],
        "country": match["country"],
        "latitude": match["latitude"],
        "longitude": match["longitude"],
        "environment": environment,
    }
    cache[key] = cached
    return cached


def _build_hfid_training_rows(max_rows: int = HFID_MAX_TRAINING_ROWS) -> List[Dict[str, Any]]:
    rows = _read_hfid_latest_rows()
    if not rows:
        return []

    cache = _load_environment_cache()
    dataset: List[Dict[str, Any]] = []

    for row in rows[:max_rows]:
        resolved = _resolve_environment_for_hfid_row(row, cache)
        if not resolved:
            continue

        feature_row = build_model_feature_vector(resolved["environment"])
        if all(value == 0.0 for value in feature_row.values()):
            continue

        dataset.append(
            {
                **feature_row,
                "label": row["_derived_label"],
                "source_country": row.get("ADMIN0", ""),
                "source_admin1": row.get("ADMIN1", ""),
                "source_admin2": row.get("ADMIN2", ""),
                "source_month": row.get("year_month", ""),
                "ipc_phase": row.get("_selected_phase"),
                "hfid_fcs_lit": _safe_float(row.get("fcs_lit")),
                "hfid_rcsi_lit": _safe_float(row.get("rcsi_lit")),
            }
        )

    _save_environment_cache(cache)
    return dataset


def ensure_training_dataset(force_rebuild: bool = False) -> List[Dict[str, Any]]:
    ensure_artifact_dir()

    if REAL_LABELS_PATH.exists():
        with REAL_LABELS_PATH.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            rows = []
            for row in reader:
                rows.append(
                    {
                        **{feature: float(row[feature]) for feature in FEATURE_ORDER},
                        "label": row["label"],
                    }
                )
        DATASET_PATH.write_text(json.dumps(rows, indent=2), encoding="utf-8")
        return rows

    if not force_rebuild and DATASET_PATH.exists():
        return json.loads(DATASET_PATH.read_text(encoding="utf-8"))

    if HFID_PATH.exists():
        dataset = _build_hfid_training_rows()
        if dataset:
            DATASET_PATH.write_text(json.dumps(dataset, indent=2), encoding="utf-8")
            return dataset

    dataset = _synthetic_training_rows()
    DATASET_PATH.write_text(json.dumps(dataset, indent=2), encoding="utf-8")
    return dataset


def train_and_persist_model() -> Dict[str, Any]:
    ensure_artifact_dir()
    dataset = ensure_training_dataset(force_rebuild=True)

    features = np.array([[float(row[name]) for name in FEATURE_ORDER] for row in dataset], dtype=float)
    labels = np.array([0 if row["label"] == "low" else 1 if row["label"] == "medium" else 2 for row in dataset], dtype=int)

    try:
        from xgboost import XGBClassifier

        model = XGBClassifier(
            n_estimators=50,
            max_depth=4,
            learning_rate=0.1,
            subsample=0.9,
            colsample_bytree=0.9,
            objective="multi:softprob",
            num_class=3,
            eval_metric="mlogloss",
        )
        model_name = "xgboost_classifier"
    except Exception:
        from sklearn.ensemble import GradientBoostingClassifier

        model = GradientBoostingClassifier(random_state=42)
        model_name = "gradient_boosting_classifier"

    model.fit(features, labels)

    with MODEL_PATH.open("wb") as handle:
        pickle.dump(model, handle)

    label_source = "synthetic_proxy_labels"
    if REAL_LABELS_PATH.exists():
        label_source = "csv_real_labels"
    elif HFID_PATH.exists() and dataset:
        label_source = "hfid_latest_labels_live_api_features"

    metadata = {
        "model_name": model_name,
        "feature_order": FEATURE_ORDER,
        "artifact_path": str(MODEL_PATH),
        "dataset_path": str(DATASET_PATH),
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "row_count": len(dataset),
        "label_source": label_source,
    }
    METADATA_PATH.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    load_persisted_model_bundle.cache_clear()
    return metadata


@lru_cache(maxsize=1)
def load_persisted_model_bundle() -> Dict[str, Any]:
    if not MODEL_PATH.exists() or not METADATA_PATH.exists():
        metadata = train_and_persist_model()
    else:
        metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))

    with MODEL_PATH.open("rb") as handle:
        model = pickle.load(handle)

    dataset = ensure_training_dataset()
    feature_matrix = np.array([[float(row[name]) for name in FEATURE_ORDER] for row in dataset], dtype=float)
    feature_means = {
        name: round(float(value), 4)
        for name, value in zip(FEATURE_ORDER, feature_matrix.mean(axis=0).tolist())
    }

    importances = getattr(model, "feature_importances_", np.ones(len(FEATURE_ORDER)) / len(FEATURE_ORDER))
    if np.sum(importances) == 0:
        importances = np.ones(len(FEATURE_ORDER)) / len(FEATURE_ORDER)
    normalized_importances = np.array(importances, dtype=float) / np.sum(importances)

    return {
        "model": model,
        "metadata": metadata,
        "feature_means": feature_means,
        "feature_importances": {
            name: round(float(weight), 4)
            for name, weight in zip(FEATURE_ORDER, normalized_importances.tolist())
        },
        "dataset_rows": len(dataset),
    }


def build_training_row_from_environment(environment: Dict[str, Any], label: str) -> Dict[str, Any]:
    row = build_model_feature_vector(environment)
    row["label"] = label
    return row
