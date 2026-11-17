"""Synthetic dataset: 60 days of fake history plus next week's calendar.

Used for development, demos and the agent's test questions. Nothing here is
real personal data. Every record gets `source="synthetic"`.

The demo "today" is Monday, Nov 16, 2026 (same as the frontend mock data).
History covers the 60 days before it (Sep 17 - Nov 15). Next week (Nov 16 - 22)
only has calendar events, so the agent has something to forecast.

Planted patterns (the agent should find these, and nothing stronger):
  1. Busy day (7h+ booked)   -> lower mood the NEXT day
  2. Busy day                 -> lower HRV / readiness the NEXT day
  3. Event ending 9:30pm+     -> less sleep that night
  4. Sleep under 6h           -> lower readiness the next morning
  5. Workout day              -> better mood the NEXT day
  6. Class day (Mon-Thu)      -> fewer steps
  Control: steps and HRV are unrelated (the agent should NOT report a pattern).

Generation is pure Python with a fixed seed, so the same seed always gives
the same data. `seed_synthetic` (management command) writes it to the database.
"""
import random
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Chicago")
SOURCE = "synthetic"

TODAY = date(2026, 11, 16)
HISTORY_DAYS = 60
FIRST_DAY = TODAY - timedelta(days=HISTORY_DAYS)  # Sep 17
NEXT_WEEK = [TODAY + timedelta(days=i) for i in range(7)]  # Nov 16 - 22

BUSY_HOURS = 7.0  # a day with at least this many hours booked counts as busy
LATE_END = time(21, 30)  # an event ending at or after this counts as late
SHORT_SLEEP_HOURS = 6.0


# ---------- record types (plain data, no Django) ----------

@dataclass
class Event:
    title: str
    category: str  # one of EventCategory: class, work, study, gym, social, other
    start: datetime  # timezone-aware, local time
    end: datetime

    @property
    def hours(self) -> float:
        return (self.end - self.start).total_seconds() / 3600


@dataclass
class Sleep:
    bedtime: datetime
    wake: datetime
    asleep_minutes: int
    in_bed_minutes: int


@dataclass
class Sample:
    metric: str
    value: float
    unit: str
    start: datetime
    end: datetime | None = None
    raw: dict = field(default_factory=dict)


@dataclass
class Day:
    """Everything generated for one local day. Sleep is the night that ENDS this morning."""

    date: date
    events: list[Event] = field(default_factory=list)
    sleep: Sleep | None = None
    samples: list[Sample] = field(default_factory=list)

    @property
    def booked_hours(self) -> float:
        return sum(e.hours for e in self.events)

    @property
    def is_busy(self) -> bool:
        return self.booked_hours >= BUSY_HOURS

    @property
    def has_late_event(self) -> bool:
        return any(e.end.time() >= LATE_END or e.end.date() > self.date for e in self.events)

    @property
    def is_class_day(self) -> bool:
        return any(e.category == "class" for e in self.events)

    def metric(self, name: str) -> float | None:
        for s in self.samples:
            if s.metric == name:
                return s.value
        return None


# ---------- readiness ----------

def readiness_score(hrv_ms: float, resting_hr: float, sleep_hours: float) -> float:
    """A simple 0-10 readiness score from last night's recovery signals.

    Apple Health has no readiness score, so we compute our own. The same
    formula should be used for real data, so synthetic and real line up.
    Baseline (HRV 50 ms, resting HR 58 bpm, 7h sleep) scores 6.
    """
    score = 6 + (hrv_ms - 50) / 8 - (resting_hr - 58) / 3 + 0.8 * (sleep_hours - 7)
    return round(min(10.0, max(0.0, score)), 1)


# ---------- mood labels (Apple "State of Mind" valence is -1 to 1) ----------

MOOD_LABELS = [
    (-0.71, "Very Unpleasant"),
    (-0.43, "Unpleasant"),
    (-0.14, "Slightly Unpleasant"),
    (0.14, "Neutral"),
    (0.43, "Slightly Pleasant"),
    (0.71, "Pleasant"),
    (1.01, "Very Pleasant"),
]


def mood_label(valence: float) -> str:
    for upper, label in MOOD_LABELS:
        if valence < upper:
            return label
    return MOOD_LABELS[-1][1]


# ---------- calendar ----------

def _at(day: date, hhmm: str) -> datetime:
    hours, minutes = map(int, hhmm.split(":"))
    return datetime.combine(day, time(hours, minutes), tzinfo=TZ)


# Fixed weekly schedule (weekday 0 = Monday): (title, start, end, category)
FIXED = {
    0: [("CS 4100 Lecture", "9:00", "10:15", "class"), ("MATH 3355 Lecture", "12:30", "14:45", "class")],
    1: [("PSYC 2000 Lecture", "11:00", "12:15", "class"), ("Library shift", "16:00", "20:00", "work")],
    2: [("CS 4100 Lecture", "9:00", "10:15", "class"), ("MATH 3355 Lecture", "12:30", "14:45", "class")],
    3: [("PSYC 2000 Lecture", "11:00", "12:15", "class"), ("Library shift", "16:00", "20:00", "work")],
    4: [("Library shift", "13:00", "17:00", "work")],
    5: [],
    6: [],
}

# Optional events per weekday: (title, start, end, category, probability).
# Slots on the same day never overlap.
OPTIONAL = {
    0: [("Study block", "10:30", "12:00", "study", 0.6), ("Gym", "17:30", "18:30", "gym", 0.5),
        ("Project work", "19:00", "21:00", "study", 0.4), ("Late study", "21:00", "22:30", "study", 0.2)],
    1: [("Gym", "7:00", "8:00", "gym", 0.3), ("Study block", "8:30", "10:30", "study", 0.5),
        ("Group project", "13:00", "15:30", "study", 0.35), ("Late study", "20:30", "22:30", "study", 0.25)],
    2: [("Study block", "10:30", "12:00", "study", 0.6), ("Gym", "17:30", "18:30", "gym", 0.5),
        ("Club meeting", "19:00", "21:00", "social", 0.4), ("Late study", "21:00", "22:30", "study", 0.2)],
    3: [("Gym", "7:00", "8:00", "gym", 0.3), ("Study block", "8:30", "10:30", "study", 0.5),
        ("Group project", "13:00", "15:30", "study", 0.35), ("Late study", "20:30", "22:30", "study", 0.25)],
    4: [("Study block", "9:30", "11:30", "study", 0.4), ("Gym", "17:30", "18:30", "gym", 0.5),
        ("Dinner with friends", "19:30", "22:30", "social", 0.5)],
    5: [("Gym", "10:00", "11:00", "gym", 0.5), ("Errands", "12:00", "14:00", "other", 0.4),
        ("Night out", "19:00", "23:00", "social", 0.5)],
    6: [("Brunch", "11:00", "13:00", "social", 0.4), ("Weekly review + study", "13:00", "16:00", "study", 0.5),
        ("Gym", "16:30", "17:30", "gym", 0.3)],
}

# Next week is fixed by hand so the forecast has a clear story:
# a late Wednesday followed by a heavy (8h+) Thursday.
NEXT_WEEK_PLAN = {
    0: ["Study block", "Gym"],
    1: ["Study block"],
    2: ["Study block", "Gym", "Late study"],
    3: ["Gym", "Study block"],
    4: ["Study block"],
    5: ["Gym"],
    6: ["Brunch"],
}


def _events_for(day: date, rng: random.Random, chosen: list[str] | None = None) -> list[Event]:
    weekday = day.weekday()
    events = [Event(t, c, _at(day, s), _at(day, e)) for t, s, e, c in FIXED[weekday]]
    for title, start, end, category, probability in OPTIONAL[weekday]:
        picked = title in chosen if chosen is not None else rng.random() < probability
        if picked:
            events.append(Event(title, category, _at(day, start), _at(day, end)))
    return sorted(events, key=lambda e: e.start)


# ---------- generation ----------

def generate(seed: int = 42) -> tuple[list[Day], list[Day]]:
    """Return (history, next_week). History has full data; next week has only events."""
    rng = random.Random(seed)

    history = [Day(FIRST_DAY + timedelta(days=i)) for i in range(HISTORY_DAYS)]
    for day in history:
        day.events = _events_for(day.date, rng)

    previous: Day | None = None
    for day in history:
        _fill_health(day, previous, rng)
        previous = day

    next_week = [Day(d, events=_events_for(d, rng, NEXT_WEEK_PLAN[d.weekday()])) for d in NEXT_WEEK]
    return history, next_week


def _fill_health(day: Day, prev: Day | None, rng: random.Random) -> None:
    busy_yesterday = prev is not None and prev.is_busy
    late_last_night = prev is not None and prev.has_late_event
    worked_out_yesterday = prev is not None and prev.metric("workout_minutes") is not None

    # Sleep: the night before this day. Late events cut it short (pattern 3).
    sleep_hours = rng.gauss(7.3, 0.55)
    if late_last_night:
        sleep_hours -= 0.9
    if busy_yesterday:
        sleep_hours -= 0.25
    sleep_hours = min(9.5, max(4.5, sleep_hours))
    asleep = round(sleep_hours * 60)
    in_bed = asleep + rng.randint(15, 45)
    bedtime_base = _at(day.date - timedelta(days=1), "23:15") + timedelta(minutes=rng.randint(-30, 30))
    if late_last_night:
        bedtime_base += timedelta(minutes=60)
    day.sleep = Sleep(bedtime_base, bedtime_base + timedelta(minutes=in_bed), asleep, in_bed)

    # Morning recovery signals (patterns 2 and 4).
    short_sleep = sleep_hours < SHORT_SLEEP_HOURS
    hrv = rng.gauss(52, 4) + 2 * (sleep_hours - 7) - 5 * short_sleep - 3 * busy_yesterday
    resting_hr = rng.gauss(58, 1.5) + 2 * short_sleep + 1 * busy_yesterday
    hrv, resting_hr = round(max(20, hrv), 1), round(resting_hr)
    readiness = readiness_score(hrv, resting_hr, sleep_hours)
    morning = _at(day.date, "7:00")

    # Workout: usually happens when the gym is booked, sometimes skipped.
    gym = next((e for e in day.events if e.category == "gym"), None)
    workout_minutes = None
    if gym and rng.random() < 0.85:
        workout_minutes = round(gym.hours * 60) - rng.randint(0, 10)
    elif not gym and day.date.weekday() >= 5 and rng.random() < 0.2:
        workout_minutes = rng.randint(25, 45)  # unplanned weekend run

    # Steps: lower on class days (pattern 6), higher on workout days. Unrelated to HRV (control).
    steps = rng.gauss(8600, 1300) - 2800 * day.is_class_day + 1800 * (workout_minutes is not None)
    steps = max(1500, round(steps))
    active_energy = round(steps * 0.045 + (workout_minutes or 0) * 7 + rng.gauss(0, 40))

    # Mood logged in the evening (patterns 1 and 5). About 1 in 10 days has no log.
    valence = (0.25 - 0.4 * busy_yesterday + 0.3 * worked_out_yesterday
               + 0.06 * (readiness - 6) + rng.gauss(0, 0.22))
    valence = round(min(1.0, max(-1.0, valence)), 2)
    log_mood = rng.random() > 0.1

    end_of_day = _at(day.date + timedelta(days=1), "0:00")
    day.samples = [
        Sample("heart_rate_variability", hrv, "ms", morning),
        Sample("resting_heart_rate", resting_hr, "bpm", morning),
        Sample("readiness", readiness, "score", morning, raw={"formula": "readiness_score(hrv, rhr, sleep)"}),
        Sample("step_count", steps, "count", _at(day.date, "0:00"), end_of_day, {"aggregation": "day"}),
        Sample("active_energy", active_energy, "kcal", _at(day.date, "0:00"), end_of_day, {"aggregation": "day"}),
    ]
    if workout_minutes is not None:
        start = gym.start if gym else _at(day.date, "9:00")
        kind = "Traditional Strength Training" if gym else "Running"
        day.samples.append(Sample("workout_minutes", workout_minutes, "min", start,
                                  start + timedelta(minutes=workout_minutes), {"workoutType": kind}))
    if log_mood:
        day.samples.append(Sample("state_of_mind_valence", valence, "valence",
                                  _at(day.date, "21:00") + timedelta(minutes=rng.randint(-60, 60)),
                                  raw={"kind": "dailyMood", "label": mood_label(valence)}))
