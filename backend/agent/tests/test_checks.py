"""Answer checks: supported answers pass, made-up numbers and causal claims are caught."""
from agent.checks import check_answer, check_causal_claims, check_early_patterns, check_numbers
from agent.loop import Step

CORRELATION = Step(
    tool="compute_correlation",
    input={"x": "busy_day", "y": "mood", "start_date": "2026-09-17", "end_date": "2026-11-15", "lag_days": 1},
    ok=True, summary="", ms=1,
    result={"paired_days": 56, "r": -0.63, "strength": "strong",
            "groups": {"busy_day_yes": {"days": 19, "average_mood": -0.13},
                       "busy_day_no": {"days": 37, "average_mood": 0.35},
                       "difference_yes_minus_no": -0.48},
            "notes": ["This shows the two move together, not that one causes the other."]},
)
FREE_TIME = Step(
    tool="find_free_time", input={"date": "2026-11-19"}, ok=True, summary="", ms=1,
    result={"date": "2026-11-19", "free_slots": [{"start": "12:15", "end": "16:00", "minutes": 225}]},
)
SLEEP = Step(
    tool="query_data", input={"start_date": "2026-11-09", "end_date": "2026-11-15", "metrics": ["sleep_hours"]},
    ok=True, summary="", ms=1, result={"averages": {"sleep_hours": 7.23}, "days_with_data": {"sleep_hours": 7}},
)
EARLY = Step(
    tool="compute_correlation",
    input={"x": "busy_day", "y": "mood", "start_date": "2026-11-05", "end_date": "2026-11-15", "lag_days": 1},
    ok=True, summary="", ms=1,
    result={"paired_days": 10, "notes": ["Only 10 paired days (under 14), so treat this as early and uncertain."]},
)

GOOD = ("Your mood tends to be lower the day after a busy day. Over 56 days, mood after busy days "
        "averaged −0.13 (19 days) vs 0.35 after other days (37 days), a gap of 0.48. "
        "This is a link, not proof that busy days cause it.")


def problems(check):
    return " ".join(check.problems)


# ---------- numbers ----------

def test_supported_answer_passes_every_check():
    report = check_answer(GOOD, [CORRELATION])
    assert report.passed, report.problems()


def test_made_up_number_is_caught():
    check = check_numbers("After busy days your mood drops by 35%.", [CORRELATION])
    assert not check.passed and "35" in problems(check)


def test_rounding_is_allowed_but_not_drift():
    assert check_numbers("Mood was about −0.1 after busy days.", [CORRELATION]).passed     # -0.13 rounded
    assert not check_numbers("Mood was −0.2 after busy days.", [CORRELATION]).passed      # not a rounding


def test_clock_times_and_unit_conversions():
    assert check_numbers("You're free from 12:15 to 4pm on Thursday.", [FREE_TIME]).passed
    assert check_numbers("You have a 225-minute gap.", [FREE_TIME]).passed
    assert not check_numbers("You're free at 2:30pm.", [FREE_TIME]).passed
    assert check_numbers("You slept 7h 14m on average last week.", [SLEEP]).passed  # 7.23 h
    assert check_numbers("You slept about 434 minutes a night.", [SLEEP]).passed


def test_dates_lists_and_rules_are_not_counted_as_stats():
    answer = "1. On Nov 19 (2026-11-19) you have 7h+ booked.\n2. Busy means 7 or more hours."
    assert check_numbers(answer, [FREE_TIME], context="A busy day has 7 or more hours booked.").passed


# ---------- early patterns ----------

def test_early_pattern_must_be_hedged():
    assert not check_early_patterns("After busy days your mood is lower.", [EARLY]).passed
    assert check_early_patterns("It's early, with only 10 days, but mood looks lower.", [EARLY]).passed


def test_early_check_is_fine_if_a_longer_check_backs_it():
    assert check_early_patterns("After busy days your mood is lower.", [EARLY, CORRELATION]).passed


# ---------- causal wording ----------

def test_causal_claims_are_caught():
    for claim in ["Busy days cause lower mood.", "Working out improves your mood.",
                  "Late events lead to less sleep.", "Your low readiness is due to short sleep."]:
        assert not check_causal_claims(claim).passed, claim


def test_negated_or_linking_language_passes():
    for ok in ["This is a link, not proof that busy days cause it.",
               "That doesn't mean workouts cause better mood.",
               "Mood tends to be lower after busy days.",
               "Short sleep is linked with lower readiness."]:
        assert check_causal_claims(ok).passed, ok
