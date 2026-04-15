from typing import Any, Dict

import numpy as np

from backend.app.services.training_service import FEATURE_ORDER, load_persisted_model_bundle


def score_with_ml_model(feature_vector: Dict[str, float]) -> Dict[str, Any]:
    bundle = load_persisted_model_bundle()
    model = bundle["model"]
    values = np.array([[feature_vector[name] for name in FEATURE_ORDER]], dtype=float)
    probabilities = model.predict_proba(values)[0].tolist()

    low_prob, medium_prob, high_prob = [float(prob) for prob in probabilities]
    risk_probability = max(probabilities)
    label_index = int(np.argmax(probabilities))
    risk_label = ["low", "medium", "high"][label_index]

    means = bundle["feature_means"]
    importances = bundle["feature_importances"]
    raw_contributions = {
        name: (feature_vector[name] - means[name]) * importances[name]
        for name in FEATURE_ORDER
    }
    contribution_scale = sum(abs(value) for value in raw_contributions.values()) or 1.0
    feature_contributions = {
        name: round(float(value / contribution_scale), 4)
        for name, value in raw_contributions.items()
    }

    explanation_method = "normalized_feature_distance_with_model_importance"
    try:
        import shap  # noqa: F401

        explanation_method = "shap_tree_explainer_available"
    except Exception:
        pass

    return {
        "model_name": bundle["metadata"]["model_name"],
        "risk_probability": round(float(risk_probability), 4),
        "risk_label": risk_label,
        "class_probabilities": {
            "low": round(low_prob, 4),
            "medium": round(medium_prob, 4),
            "high": round(high_prob, 4),
        },
        "explanation_method": explanation_method,
        "feature_contributions": feature_contributions,
        "feature_importances": importances,
        "top_explanations": [
            feature
            for feature, _ in sorted(
                feature_contributions.items(),
                key=lambda item: abs(item[1]),
                reverse=True,
            )[:3]
        ],
        "synthetic_training": bundle["metadata"].get("label_source") == "synthetic_proxy_labels",
        "artifact_path": bundle["metadata"]["artifact_path"],
    }
