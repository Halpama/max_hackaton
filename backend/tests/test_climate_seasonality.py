"""Climate → seasonality scoring (no network)."""

from app.clients.climate import comfort_raw, scores_from_monthly


def test_comfort_prefers_mild_over_freezing():
    mild = comfort_raw(18.0, 45.0)
    freeze = comfort_raw(-12.0, 30.0)
    assert mild > freeze


def test_scores_from_monthly_span_1_to_5():
    months = [
        {"temp": -10.0, "precip": 40.0},
        {"temp": -8.0, "precip": 35.0},
        {"temp": 0.0, "precip": 40.0},
        {"temp": 8.0, "precip": 45.0},
        {"temp": 15.0, "precip": 50.0},
        {"temp": 20.0, "precip": 55.0},
        {"temp": 22.0, "precip": 60.0},
        {"temp": 20.0, "precip": 55.0},
        {"temp": 14.0, "precip": 50.0},
        {"temp": 6.0, "precip": 45.0},
        {"temp": -2.0, "precip": 40.0},
        {"temp": -8.0, "precip": 35.0},
    ]
    scores = scores_from_monthly(months)
    assert len(scores) == 12
    assert min(scores) == 1
    assert max(scores) == 5
    # July warmer than January
    assert scores[6] > scores[0]
