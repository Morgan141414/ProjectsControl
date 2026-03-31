from datetime import date, timedelta

from app.api.routes.ai_kpi import (
    _holt_linear_forecast,
    _isolation_forest_score_1d,
    _predict_next_score,
    _work_style_cluster,
)
from app.schemas.ai_score import AIScoreTrendPoint


def _trend(scores: list[int]) -> list[AIScoreTrendPoint]:
    start = date(2026, 1, 1)
    return [
        AIScoreTrendPoint(period_start=start + timedelta(days=i), score=s)
        for i, s in enumerate(scores)
    ]


def test_holt_linear_forecast_tracks_upward_series() -> None:
    pred = _holt_linear_forecast([40, 45, 50, 55, 60], alpha=0.45, beta=0.25, steps_ahead=1)
    assert pred is not None
    assert pred > 60


def test_predict_next_score_returns_ensemble_metadata() -> None:
    trend = _trend([62, 64, 66, 68, 71, 73, 75])
    current = {
        "fatigue_index": 0.25,
        "cognitive_load": 0.45,
        "recovery_quality": 0.75,
        "focus_quality": 0.42,
        "context_switches_per_hour": 18,
    }
    baseline = {"focus_quality": 0.30, "fatigue_index": 0.20}
    pred = _predict_next_score(trend, current, baseline)

    assert isinstance(pred.get("predicted_score"), int)
    assert pred["confidence"] in {"low", "medium", "high"}
    assert "confidence_interval" in pred
    assert pred["confidence_interval"]["min"] <= pred["predicted_score"] <= pred["confidence_interval"]["max"]
    assert "model_components" in pred
    assert {"linear_regression", "holt_linear", "ensemble_weight_holt"} <= set(pred["model_components"].keys())


def test_work_style_cluster_outputs_valid_style_and_confidence() -> None:
    style, conf, distances = _work_style_cluster(
        {
            "deep_work_ratio": 0.68,
            "communication_ratio": 0.12,
            "planning_ratio": 0.18,
            "context_switches_per_hour": 9,
        }
    )
    assert style in {"deep_worker", "multitasker", "communicator", "planner", "balanced"}
    assert 0.0 <= conf <= 1.0
    assert isinstance(distances, dict)
    assert style in distances


def test_isolation_score_flags_extreme_outlier_higher_than_normal_point() -> None:
    population = [62, 64, 63, 65, 66, 64, 63, 65, 64, 62, 66, 63]
    normal_score = _isolation_forest_score_1d(64, population)
    outlier_score = _isolation_forest_score_1d(20, population)

    assert 0.0 <= normal_score <= 1.0
    assert 0.0 <= outlier_score <= 1.0
    assert outlier_score > normal_score

