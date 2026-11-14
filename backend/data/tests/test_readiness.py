import pytest

from data.readiness import baseline, readiness, readiness_for_day


def test_normal_day_with_full_sleep_scores_79():
    assert readiness(hrv=50, hrv_normal=50, rhr=60, rhr_normal=60, sleep_hours=8) == 79


def test_rough_day_scores_61():
    # HRV 10% low, resting HR 3 bpm high, 6h sleep
    assert readiness(hrv=45, hrv_normal=50, rhr=63, rhr_normal=60, sleep_hours=6) == 61


def test_less_sleep_lowers_readiness():
    rested = readiness(hrv=50, hrv_normal=50, rhr=60, rhr_normal=60, sleep_hours=8)
    tired = readiness(hrv=50, hrv_normal=50, rhr=60, rhr_normal=60, sleep_hours=5.5)
    assert tired < rested


@pytest.mark.parametrize("hrv, rhr, sleep", [(500, 30, 14), (1, 120, 0)])
def test_readiness_stays_between_0_and_100(hrv, rhr, sleep):
    assert 0 <= readiness(hrv=hrv, hrv_normal=50, rhr=rhr, rhr_normal=60, sleep_hours=sleep) <= 100


def test_baseline_needs_7_days():
    assert baseline([50.0] * 6) is None
    assert baseline([50.0] * 7) == 50


def test_baseline_uses_only_last_28_days():
    assert baseline([100.0] * 10 + [50.0] * 28) == 50


def test_readiness_for_day_is_none_without_enough_history():
    assert readiness_for_day(hrv=50, rhr=60, sleep_hours=8, previous_hrv=[50] * 3, previous_rhr=[60] * 3) is None


def test_readiness_for_day_is_none_when_a_value_is_missing():
    assert readiness_for_day(hrv=None, rhr=60, sleep_hours=8, previous_hrv=[50] * 10, previous_rhr=[60] * 10) is None


def test_readiness_for_day_with_history():
    assert readiness_for_day(hrv=50, rhr=60, sleep_hours=8, previous_hrv=[50] * 10, previous_rhr=[60] * 10) == 79
