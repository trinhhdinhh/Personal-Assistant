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
| Apple Watch + Health app | Sleep, heart rate, HRV, readiness, steps, workouts, mood (State of Mind) | Health Auto Export app sends it automatically |

No other sources for now. Screen time was cut because it adds too much friction.

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

Screen time, manual check-ins, location, assignments, bank data, writing to the calendar, a separate mobile app, and Mac integrations (menu bar, widgets). The Claude app connector is planned for after the main agent works (see below).

## Timeline

| Dates | Goal |
|---|---|
| Nov 10–16 | Health and calendar data flowing in, plus the synthetic dataset |
| Nov 17–22 | The agent, its tools and the answer checks |
| Nov 23–25 | Connect the dashboard (Brief + Ask pages), run the tests, polish the demo |
| Nov 26 | Buffer |

## Use it from the Claude app, anywhere

Goal: open the Claude app on my phone, laptop or the web and ask things like *"how's my week looking?"* or *"show my weekly report"*, and get answers from this agent, wherever I am.

**How it works**
1. **The agent lives online, not on my Mac.** The backend and database are hosted in the cloud, so they're always reachable. This is needed early anyway: Health Auto Export on my phone has to send data to a public address.
2. **Data flows in on its own.** Health Auto Export sends my Watch data from my phone, and the server pulls my calendar link on a schedule. My Mac doesn't need to be on.
3. **Claude connects through a custom connector.** The project includes a small MCP server, hosted alongside the backend, that I add in Claude under Settings › Connectors. Because it's tied to my Claude account, it works in the Claude app on web, desktop and phone.
4. **A dashboard inside Claude.** A Claude artifact pinned to my sidebar shows the brief and weekly report by reading through the same connector.

**What the connector exposes**
- Read-only views: today's brief, the weekly report, the week-ahead forecast, recent trends
- `ask_agent`: passes my question to **this project's agent** and returns its answer and steps

**Rules**
- **This project's agent does the thinking.** The connector only passes questions and answers through. Claude's own chat must not replace the custom agent, because that's what gets graded.
- **Login required.** The connector holds my health and mood data, so it must use a proper sign-in (OAuth). Never an open, no-login connector.
- **Summaries only.** The connector returns daily summaries, never raw mood entries or raw health samples.
- **No writes.** The connector can't change my calendar or anything else. Suggestions still come as files I choose to add.

**Order**
1. Host the backend and database first (needed for the Health Auto Export data anyway).
2. Build the agent and get it working (the main project).
3. Add the MCP server, connect it in Claude, and test it on my phone.
4. Last, build the pinned dashboard in Claude.
