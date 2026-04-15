from typing import Any, Dict

from backend.app.services.training_service import FEATURE_ORDER, load_persisted_model_bundle


def build_explainability_record(feature_vector: Dict[str, float]) -> Dict[str, Any]:
    bundle = load_persisted_model_bundle()
    shap_values: Dict[str, float]
    method = "feature_importance_proxy"
    means = bundle["feature_means"]
    feature_importances = bundle["feature_importances"]

    proxy_values = {
        name: round(float((feature_vector[name] - means[name]) * feature_importances[name]), 4)
        for name in FEATURE_ORDER
    }

    try:
        import numpy as np
        import shap

        explainer = shap.Explainer(bundle["model"])
        explanation = explainer(np.array([[feature_vector[name] for name in FEATURE_ORDER]], dtype=float))
        values = explanation.values[0]
        if hasattr(values, "tolist"):
            values = values.tolist()
        if isinstance(values[0], list):
            values = values[0]
        shap_values = {
            name: round(float(value), 4)
            for name, value in zip(FEATURE_ORDER, values)
        }
        method = "shap_explainer"
    except Exception:
        shap_values = proxy_values

    if sum(abs(value) for value in shap_values.values()) < 0.0001:
        shap_values = proxy_values
        method = "proxy_fallback_from_feature_distance"

    sorted_features = sorted(shap_values.items(), key=lambda item: item[1], reverse=True)
    top_positive = [name for name, value in sorted_features[:3] if value >= 0]
    top_negative = [name for name, value in sorted(sorted_features, key=lambda item: item[1])[:3] if value <= 0]

    return {
        "method": method,
        "feature_values": {name: round(float(feature_vector[name]), 4) for name in FEATURE_ORDER},
        "shap_values": shap_values,
        "top_positive_drivers": top_positive,
        "top_negative_drivers": top_negative,
        "summary_plot_data": {name: abs(value) for name, value in shap_values.items()},
    }
