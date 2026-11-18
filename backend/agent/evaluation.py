"""Grading the agent against the synthetic test questions (data/synthetic_questions.json).

Every criterion is checked in code, from the run's recorded steps and its
final answer, so the score is the same every time for the same run:

- answered:  the run ended with an answer that passed the answer checks
- must_use:  every listed tool was called
- evidence:  at least one tool call matches one of the listed specs, which
             proves the agent ran the right analysis and found the pattern
- must_say:  the answer matches every listed pattern
- must_not:  the answer matches none of the listed patterns
"""
import json
import re
from pathlib import Path

from agent.checks import NEGATION
from agent.loop import AgentRun, Step

QUESTIONS_FILE = Path(__file__).resolve().parent.parent / "data" / "synthetic_questions.json"


def load_questions() -> list[dict]:
    return json.loads(QUESTIONS_FILE.read_text())["questions"]


def step_matches(step: Step, spec: dict) -> bool:
    """Does one tool call fit a spec like
    {"tool": "compute_correlation", "input": {"x": ["busy_day"], "lag_days": [1]}, "result": {"direction": ["negative"]}}?
    A list-valued input (like query_data metrics) must contain every listed value.
    """
    if step.tool != spec["tool"] or not step.ok:
        return False
    for key, allowed in spec.get("input", {}).items():
        value = step.input.get(key, 0 if key == "lag_days" else None)
        if isinstance(value, list):
            if not set(allowed) <= set(value):
                return False
        elif value not in allowed:
            return False
    for key, allowed in spec.get("result", {}).items():
        if not isinstance(step.result, dict) or step.result.get(key) not in allowed:
            return False
    return True


def _said(pattern: str, answer: str) -> bool:
    """True if the answer makes the claim, ignoring negated uses like
    "not that busy days cause the dip" (same rule as the answer checks)."""
    for match in re.finditer(pattern, answer, re.I):
        sentence = re.split(r"[.!?\n]", answer[:match.start()])[-1]
        if not NEGATION.search(sentence[-60:]):
            return True
    return False


def grade(question: dict, run: AgentRun) -> dict:
    """Score one run. Returns each criterion as {"passed": bool, "detail": str}."""
    answer = run.answer
    used = [s.tool for s in run.steps]
    criteria = {}

    criteria["answered"] = {
        "passed": run.stop == "answered",
        "detail": run.stop if run.stop != "answered" else f"passed checks ({run.retries} rewrites)",
    }

    missing = [t for t in question["must_use"] if t not in used]
    criteria["must_use"] = {"passed": not missing, "detail": f"missing {missing}" if missing else "all used"}

    if question["evidence"]:
        found = any(step_matches(s, spec) for s in run.steps for spec in question["evidence"])
        criteria["evidence"] = {"passed": found, "detail": "found" if found else "no tool call showed the expected finding"}

    if run.stop == "answered":  # a blocked or failed answer has nothing to read
        unsaid = [p for p in question["must_say"] if not re.search(p, answer, re.I)]
        criteria["must_say"] = {"passed": not unsaid, "detail": f"did not say {unsaid}" if unsaid else "ok"}
        said = [p for p in question["must_not"] if _said(p, answer)]
        criteria["must_not"] = {"passed": not said, "detail": f"said {said}" if said else "ok"}

    return {
        "id": question["id"],
        "question": question["question"],
        "passed": all(c["passed"] for c in criteria.values()),
        "criteria": criteria,
        "tools_used": used,
        "answer": answer,
        "stop": run.stop,
        "retries": run.retries,
        "checks": run.checks,
        "model_calls": run.model_calls,
        "tokens": run.input_tokens + run.output_tokens,
    }
