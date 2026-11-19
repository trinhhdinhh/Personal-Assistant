# CLAUDE.md

Read this before making changes.

## What this is

**Personal Life Agent:** an AI agent that looks at my **schedule** and **Apple Watch health data** (sleep, heart rate/HRV, readiness, steps, workouts and logged moods) and gives me suggestions to improve, backed by my own data.

It's a university course project (LSU, agentic systems option). The grader wants:
- **Real agentic behavior:** the agent plans and uses several tools in a row, not a single LLM call
- **Concrete tools** the agent chooses between
- **Clear novelty** compared with apps like Apple Health, Bearable, Exist.io and Motion

**The novelty:** the agent **looks ahead** (it predicts how next week will go based on my own history) and **checks its own advice** (it follows up on whether its suggestions actually helped).


## What it does

1. **Week-ahead forecast:** reads next week's calendar, compares it with my history, and warns me about rough days. *"Thursday has 8h booked. After days like that your mood dips and your readiness drops about 2 points. Consider moving the 7pm block."*
2. **Weekly life report:** a Sunday summary of sleep, recovery, mood and activity vs last week, where my time went, and the biggest changes, with charts.
3. **Smart suggestions in free time:** finds real gaps in my schedule ("you're free 3:00–3:45, take a walk") and creates a calendar file I can tap to add.
4. **Suggestion follow-up:** remembers what it suggested and checks a week later whether it helped.
5. **Ask anything:** I can ask questions about my life ("why was last week rough?") and get answers with numbers, charts and the steps the agent took.

## Data sources

| Source | What it gives | How it arrives |
|---|---|---|
| iCloud Calendar | Events, how busy each day is | Private calendar share link (.ics) |
| Apple Watch + Health app | Sleep, heart rate, HRV, readiness, steps, workouts, mood (State of Mind) | Health Auto Export app |

For demo day the app uses the synthetic dataset, which has the same shape as these sources. Importing my real data comes later. No other sources for now. Screen time was cut because it adds too much friction.

## The agent's tools

| Tool | What it does |
|---|---|
| `query_data` | Gets health and schedule numbers for a date range |
| `get_calendar` | Gets events for a date range |
| `compare_periods` | Compares a metric between two periods (e.g. this week vs last) |
| `compute_correlation` | Checks whether two things move together (e.g. busy days → next-day mood) |
| `forecast_week` | Predicts how next week's days will go based on similar past days |
| `find_free_time` | Finds open gaps in the schedule |
| `make_ics_event` | Creates a calendar file for a suggestion |
| `save_suggestion` | Records a suggestion so it can be checked later |
| `evaluate_suggestion` | Checks whether a past suggestion improved the metric |

## Rules

**The agent**
- Build the agent loop myself. **No LangChain, LlamaIndex, CrewAI or similar frameworks.** The custom agent is what gets graded.
- Every answer is checked before I see it:
  - every number must come from a tool result (no made-up stats)
  - patterns need at least 14 days of data, or they're stated as early or uncertain
  - correlation is never stated as causation
- The agent never changes my calendar or sends anything on its own. It only suggests, and I decide.

**Privacy**
- Never commit real personal data, exports or secrets.
- Mood and health data are sensitive. The AI model sees daily summaries, never raw entries.
- Demos and screenshots use synthetic (fake) data.

**Keep it simple**
- Prefer simple, readable code. It gets presented and explained to a grader.
- Work on one thing at a time and make sure it works before moving on.

## Testing

A synthetic 60-day dataset with planted patterns (e.g. busy days lower next-day mood, short sleep lowers readiness) and about 10 test questions with known answers. Success means the agent finds the planted patterns, picks sensible tools, and the checks block unsupported claims.

## Out of scope (for now)

Screen time, manual check-ins, location, assignments, bank data, writing to the calendar, a separate mobile app, Mac integrations (menu bar, widgets), hosting or deploying the app, and using it from the Claude app (connector). Real data import comes after demo day.

## Timeline

| Dates | Goal |
|---|---|
| Nov 10–16 | Health and calendar data flowing in, plus the synthetic dataset |
| Nov 17–22 | The agent, its tools and the answer checks |
| Nov 23–25 | Connect the dashboard (Brief + Ask pages), run the tests, polish the demo |
| Nov 26 | Buffer |

## How it runs (demo day)

Everything runs **locally on my Mac**. There is no hosting or deployment.

- **Backend:** Django + Postgres (docker-compose), started with `runserver`.
- **Frontend:** the Next.js dashboard (Today, Week, Report, Ask pages) at localhost:3000.
- **Data:** the synthetic 60-day dataset, with `DEMO_TODAY` pinning "today" to the dataset's Monday.
- **Model:** my OpenRouter key in the git-ignored `.env`.

The goal for demo day is that this runs reliably end to end and the agent's steps and answer checks are visible on the Ask page.
