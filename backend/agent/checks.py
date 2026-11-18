"""Answer checks: every answer is checked in code before the user sees it.

1. numbers_from_tools: every number in the answer must match a number from a
   tool result (allowing for rounding), the question, or the agent's own rules.
2. early_patterns_flagged: if a pattern rests on fewer than 14 days, the answer
   must say it is early or uncertain.
3. no_causal_claims: no wording that turns a link into a cause ("busy days
   cause..."), unless it is negated ("not that busy days cause...").

The loop (agent/loop.py) gives the model one chance to fix a failed answer.
If it fails again, the answer is blocked.

These are simple text rules, so they can be wrong at the edges. They lean
strict: a blocked good answer costs a retry; an unsupported claim costs trust.
"""
import re
from dataclasses import asdict, dataclass, field

# ---------- shared ----------

MONTH = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?"
DATE_PATTERNS = [
    r"\b\d{4}-\d{2}-\d{2}\b",                                        # 2026-11-19
    rf"\b{MONTH}\s+\d{{1,2}}(?:st|nd|rd|th)?(?:\s*[–-]\s*\d{{1,2}}(?:st|nd|rd|th)?)?\b",  # Nov 19, Nov 9-15
    rf"\b\d{{1,2}}(?:st|nd|rd|th)?\s+(?:of\s+)?{MONTH}",              # 19th of November
    r"\b\d{1,2}/\d{1,2}\b",                                          # 11/19
]
LIST_MARKER = r"(?m)^\s*\d+[.)]\s"                                   # "1. " at the start of a line
CLOCK = re.compile(r"\b(\d{1,2}):(\d{2})\s*(am|pm|a\.m\.|p\.m\.)?|\b(\d{1,2})\s*(am|pm|a\.m\.|p\.m\.)", re.I)
DURATION = re.compile(r"\b(\d+)\s*h(?:ours?|rs?)?\s+(\d+)\s*m(?:in(?:utes?)?)?\b", re.I)
NUMBER = re.compile(r"(?<![\w.])([-−]?\d[\d,]*(?:\.\d+)?)\s*(%|k\b|min(?:ute)?s?\b|hours?\b|hrs?\b|h\b)?", re.I)

SMALL_COUNTS = {0, 1, 2}  # "one or two things", "1 day later": counting words, not statistics


@dataclass
class Check:
    name: str
    passed: bool
    problems: list[str] = field(default_factory=list)


@dataclass
class Report:
    checks: list[Check]

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks)

    def problems(self) -> list[str]:
        return [p for c in self.checks for p in c.problems]

    def to_list(self) -> list[dict]:
        return [asdict(c) for c in self.checks]


def check_answer(answer: str, steps: list, context: str = "") -> Report:
    """Run every check. `steps` are the run's Steps; `context` is the question and rules text."""
    return Report([
        check_numbers(answer, steps, context),
        check_early_patterns(answer, steps),
        check_causal_claims(answer),
    ])


def retry_message(report: Report) -> str:
    lines = "\n".join(f"- {p}" for p in report.problems())
    return ("Your answer did not pass the automatic checks:\n"
            f"{lines}\n"
            "Rewrite the full answer to fix these. Use only numbers exactly as the tools reported them "
            "(call a tool if you need another number), say when a pattern rests on under 14 days, "
            "and describe links, never causes.")


# ---------- 1. numbers ----------

def _strip_dates(text: str) -> str:
    for pattern in DATE_PATTERNS:
        text = re.sub(pattern, " ", text, flags=re.I)
    return re.sub(LIST_MARKER, " ", text)


def _minutes(hour: int, minute: int, suffix: str | None) -> list[int]:
    """Clock time as minutes after midnight. Without am/pm, both readings are possible."""
    suffix = (suffix or "").lower().replace(".", "")
    if suffix == "pm" and hour < 12:
        hour += 12
    if suffix == "am" and hour == 12:
        hour = 0
    options = [hour * 60 + minute]
    if not suffix and hour < 12:
        options.append((hour + 12) * 60 + minute)
    return options


def _clock_times(text: str) -> tuple[set[int], str]:
    """Find clock times (12:15, 4pm, 9:30 p.m.) and return them plus the text without them."""
    found: set[int] = set()

    def take(match):
        if match.group(1) is not None:
            hour, minute, suffix = int(match.group(1)), int(match.group(2)), match.group(3)
        else:
            hour, minute, suffix = int(match.group(4)), 0, match.group(5)
        found.update(_minutes(hour, minute, suffix))
        return " "
    return found, CLOCK.sub(take, text)


def _numbers(text: str) -> list[tuple[float, int, list[float]]]:
    """Each number as (value as written, decimals shown, values it could stand for)."""
    found = []

    def duration(match):  # "7h 14m" -> 7.23 hours
        hours = int(match.group(1)) + int(match.group(2)) / 60
        found.append((hours, 2, [hours, hours * 60]))
        return " "
    text = DURATION.sub(duration, text)

    for match in NUMBER.finditer(text):
        raw, unit = match.group(1).replace("−", "-").replace(",", ""), (match.group(2) or "").lower()
        value = float(raw)
        decimals = len(raw.split(".")[1]) if "." in raw else 0
        meanings = [value]  # a percentage must match a percentage a tool reported (e.g. percent_change)
        if unit == "k":
            meanings.append(value * 1000)
        elif unit.startswith("min"):
            meanings.append(value / 60)
        found.append((value, decimals, meanings))
    return found


def _collect(value, numbers: set[float], times: set[int]) -> None:
    """Every number and clock time inside a tool result or input."""
    if isinstance(value, bool):
        return
    if isinstance(value, (int, float)):
        numbers.add(float(value))
    elif isinstance(value, str):
        clock, rest = _clock_times(value)
        times.update(clock)
        numbers.update(float(n.replace(",", "")) for n in re.findall(r"\d[\d,]*(?:\.\d+)?", rest))
    elif isinstance(value, dict):
        for item in value.values():
            _collect(item, numbers, times)
    elif isinstance(value, list):
        for item in value:
            _collect(item, numbers, times)


def _close(written: float, decimals: int, meanings: list[float], known: set[float]) -> bool:
    tolerance = 0.5 * 10 ** -decimals + 1e-9
    if decimals == 0 and abs(written) >= 1000:  # "about 6,100 steps" rounds to the hundred
        zeros = len(str(int(abs(written)))) - len(str(int(abs(written))).rstrip("0"))
        tolerance = max(tolerance, 0.5 * 10 ** zeros)
    for meaning in meanings:
        scale = tolerance * abs(meaning / written) if written else tolerance
        if any(abs(abs(meaning) - abs(k)) <= scale for k in known):
            return True
    return False


def check_numbers(answer: str, steps: list, context: str = "") -> Check:
    known, known_times = set(), set()
    for step in steps:
        _collect(step.result, known, known_times)
        _collect(step.input, known, known_times)
    _collect(_strip_dates(context), known, known_times)

    times, rest = _clock_times(_strip_dates(answer))
    problems = [f"The time {t // 60:02d}:{t % 60:02d} does not come from any tool result."
                for t in sorted(times) if t not in known_times and (t + 720) % 1440 not in known_times]

    for written, decimals, meanings in _numbers(rest):
        if decimals == 0 and abs(written) in SMALL_COUNTS:
            continue
        if not _close(written, decimals, meanings, known):
            shown = f"{written:g}"
            problems.append(f"The number {shown} does not match any tool result.")
    return Check("numbers_from_tools", not problems, sorted(set(problems)))


# ---------- 2. early patterns ----------

HEDGES = re.compile(
    r"\b(early|uncertain|tentative|preliminary|limited data|small sample|not much data|"
    r"not enough data|too few|few days|only \d+ (?:paired )?days|too early|not yet clear)\b", re.I)


def check_early_patterns(answer: str, steps: list) -> Check:
    """A pattern only counts as early if every check of it (same x, y, lag) had under 14 days."""
    early, solid = set(), set()
    for step in steps:
        if not step.ok or step.tool not in {"compute_correlation", "forecast_week"}:
            continue
        key = (step.tool, step.input.get("x"), step.input.get("y"), step.input.get("lag_days", 0))
        notes = " ".join(step.result.get("notes", []))
        (early if "early and uncertain" in notes else solid).add(key)

    unhedged = early - solid
    if unhedged and not HEDGES.search(answer):
        return Check("early_patterns_flagged", False, [
            "A pattern you used rests on fewer than 14 days, but the answer does not say it is early or uncertain."])
    return Check("early_patterns_flagged", True)


# ---------- 3. causal wording ----------

CAUSAL = re.compile(
    r"\b(causes?|caused|causing|leads? to|led to|results? in|makes? you|made you|due to|because of|"
    r"is why|the reason (?:for|why)|improves? your|boosts? your|hurts? your|drives? your|ruins? your)\b", re.I)
NEGATION = re.compile(r"(?:\b(?:not|no|never|cannot|without)\b|n't\b)[^.!?]{0,40}$", re.I)


def check_causal_claims(answer: str) -> Check:
    problems = []
    for match in CAUSAL.finditer(answer):
        before = answer[max(0, match.start() - 60):match.start()]
        sentence_start = max(before.rfind("."), before.rfind("!"), before.rfind("?"), before.rfind("\n"))
        if NEGATION.search(before[sentence_start + 1:]):
            continue  # "not that busy days cause the dip" is the right way to say it
        problems.append(f"'{match.group(0)}' states a cause. Describe it as a link instead (e.g. 'tends to', 'is linked with').")
    return Check("no_causal_claims", not problems, sorted(set(problems)))
