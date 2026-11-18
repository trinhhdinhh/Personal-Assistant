"""The grader: free tests with hand-built runs (no model calls)."""
import re

import pytest

from agent.evaluation import grade, load_questions, step_matches
from agent.loop import AgentRun, Step

QUESTIONS = {q["id"]: q for q in load_questions()}


def corr(x, y, lag, direction, strength="strong"):
    return Step("compute_correlation", {"x": x, "y": y, "start_date": "2026-09-17", "end_date": "2026-11-15",
                                        "lag_days": lag}, True, "", {"direction": direction, "strength": strength}, 1)


def run(answer, *steps, stop="answered"):
    return AgentRun(question="", answer=answer, steps=list(steps), stop=stop)


def test_questions_file_is_well_formed():
    assert sorted(QUESTIONS) == list(range(1, 11))
    for q in QUESTIONS.values():
        assert {"question", "expect", "must_use", "evidence", "must_say", "must_not"} <= set(q)
        for pattern in q["must_say"] + q["must_not"]:
            re.compile(pattern)


def test_a_good_answer_passes():
    answer = "Your mood tends to be lower the day after a busy day (56 days). It's a link, not a cause."
    result = grade(QUESTIONS[1], run(answer, corr("busy_day", "mood", 1, "negative")))
    assert result["passed"], result["criteria"]


def test_wrong_lag_is_not_evidence():
    answer = "Your mood tends to be lower the day after a busy day."
    result = grade(QUESTIONS[1], run(answer, corr("busy_day", "mood", 0, "none")))
    assert not result["criteria"]["evidence"]["passed"]


def test_banned_claim_fails():
    answer = "Mood is higher the next day. Working out improves your mood."
    result = grade(QUESTIONS[4], run(answer, corr("workout_day", "mood", 1, "positive")))
    assert not result["criteria"]["must_not"]["passed"]


def test_blocked_run_fails_and_skips_text_checks():
    result = grade(QUESTIONS[1], run("I couldn't back up my answer.", corr("busy_day", "mood", 1, "negative"), stop="blocked"))
    assert not result["passed"] and "must_say" not in result["criteria"]


def test_control_question_needs_a_weak_result_and_no_strong_claim():
    good = grade(QUESTIONS[6], run("There's no clear link between your steps and HRV.", corr("steps", "hrv", 0, "negative", "weak")))
    assert good["passed"], good["criteria"]
    bad = grade(QUESTIONS[6], run("There is a strong link.", corr("steps", "hrv", 0, "negative", "weak")))
    assert not bad["passed"]


def test_no_data_question_needs_no_tools():
    result = grade(QUESTIONS[10], run("I don't have any coffee or caffeine data, so I can't tell."))
    assert result["passed"], result["criteria"]


@pytest.mark.parametrize("metrics, ok", [(["steps", "class_day"], True), (["steps"], False)])
def test_list_inputs_must_contain_every_listed_value(metrics, ok):
    step = Step("query_data", {"start_date": "a", "end_date": "b", "metrics": metrics}, True, "", {}, 1)
    assert step_matches(step, QUESTIONS[5]["evidence"][1]) is ok


def test_negated_claim_is_not_a_banned_claim():
    answer = "Mood is lower the next day. This shows a link, not that busy days cause the dip."
    result = grade(QUESTIONS[1], run(answer, corr("busy_day", "mood", 1, "negative")))
    assert result["criteria"]["must_not"]["passed"], result["criteria"]
    banned = grade(QUESTIONS[1], run("Mood is lower the next day because busy days cause it.",
                                     corr("busy_day", "mood", 1, "negative")))
    assert not banned["criteria"]["must_not"]["passed"]
