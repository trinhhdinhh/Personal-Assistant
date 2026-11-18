"""The agent loop, written by hand (no agent frameworks).

    question -> model -> tool calls? -> run tools -> results back -> model -> ... -> answer

Each turn:
1. Send the conversation and the tool definitions to the model.
2. If the model asks for tools, run every requested tool, send all results
   back in one message, and go again.
3. If the model answers instead, stop.

Safety limits:
- At most MAX_STEPS model calls. On the last one, tools are switched off and
  the model must answer with what it has.
- A tool failure becomes an error result the model can read; it never
  crashes the loop.
- If the model is cut off or declines, we stop and say so.

Every tool call is recorded as a Step, so the user can see how the answer
was reached, and so the answer checks can compare numbers with tool results.

Answer checks (agent/checks.py) run on every final answer. If one fails, the
model gets one retry with the problems listed; if it fails again, the answer
is blocked and the user sees why instead.
"""
import json
import logging
import time
from dataclasses import asdict, dataclass, field

import anthropic
from django.conf import settings

from agent import llm
from agent.checks import check_answer, retry_message
from agent.prompts import SYSTEM_PROMPT, today_note
from agent.registry import run_tool, tool_definitions
from data.timeutils import today

logger = logging.getLogger(__name__)

MAX_STEPS = 10        # model calls per question
MAX_TOKENS = 16000    # per model call
MAX_RETRIES = 1       # chances to fix an answer that failed the checks
FINAL_NUDGE = "You have used all your tool calls. Answer now using only the results above."
BLOCKED = ("I couldn't back up my answer with your data, so I'm not showing it. "
           "Try asking a narrower question.")


@dataclass
class Step:
    """One tool call the agent made."""
    tool: str
    input: dict
    ok: bool
    summary: str               # one line for the UI
    result: dict | str         # what the model saw (parsed JSON, or the error text)
    ms: int                    # how long the tool took


@dataclass
class AgentRun:
    question: str
    answer: str = ""
    steps: list[Step] = field(default_factory=list)
    stop: str = ""             # answered | step_limit | blocked | cut_off | declined | error
    checks: list[dict] = field(default_factory=list)  # results of the last answer check
    retries: int = 0           # times the model rewrote its answer after failing a check
    blocked_answer: str = ""   # the answer that was held back, kept for debugging
    model_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# ---------- the loop ----------

READ_ONLY_NOTE = ("This conversation is read-only: you cannot save suggestions, so skip save_suggestion. "
                  "You can still make calendar files with make_ics_event for the user to add.")


def run_agent(question: str, history: list[dict] | None = None, max_steps: int = MAX_STEPS,
              allow_writes: bool = True) -> AgentRun:
    """Answer one question. `history` is earlier turns as [{"role", "content"}] text messages.

    With `allow_writes=False` (the Claude connector) the agent cannot use tools that change
    stored data: they are left out of the tool list and refused if called anyway.
    """
    run = AgentRun(question=question, model=settings.AGENT_MODEL)
    tools = tool_definitions(allow_writes)
    allowed = {t["name"] for t in tools}
    messages = [*(history or []), {"role": "user", "content": question}]
    date_line = today_note(today())
    system = [
        {"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": date_line if allow_writes else f"{date_line}\n{READ_ONLY_NOTE}"},
    ]
    # Numbers the answer may use besides tool results: the conversation and the agent's own rules.
    context = "\n".join([SYSTEM_PROMPT, date_line, *(str(m["content"]) for m in messages)])

    while True:
        last_call = run.model_calls + 1 >= max_steps
        try:
            response = llm.get_client().messages.create(
                model=settings.AGENT_MODEL,
                max_tokens=MAX_TOKENS,
                system=system,
                tools=tools,
                tool_choice={"type": "none"} if last_call else {"type": "auto"},
                messages=messages,
            )
        except (anthropic.APIStatusError, anthropic.APIConnectionError) as error:
            logger.warning("Model call failed: %s", type(error).__name__)
            return _finish(run, "error", "Sorry, I couldn't reach the model just now. Please try again.")

        run.model_calls += 1
        run.input_tokens += response.usage.input_tokens
        run.output_tokens += response.usage.output_tokens
        text = _text(response)

        if response.stop_reason == "refusal":
            return _finish(run, "declined", text or "The model declined to answer this question.")
        if response.stop_reason == "max_tokens":
            # A cut-off reply may hold a half-written tool call, so never run its tools.
            return _finish(run, "cut_off", text or "The answer was cut off. Try a narrower question.")
        if response.stop_reason != "tool_use":
            report = check_answer(text, run.steps, context)
            run.checks = report.to_list()
            if report.passed:
                return _finish(run, "step_limit" if last_call else "answered", text)
            if run.retries < MAX_RETRIES and not last_call:
                run.retries += 1
                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": retry_message(report)})
                continue
            run.blocked_answer = text
            return _finish(run, "blocked", BLOCKED)

        # The model wants tools: keep its whole reply (thinking blocks included), run the tools,
        # and send every result back in ONE user message.
        messages.append({"role": "assistant", "content": response.content})
        results = [_call_tool(block, run, allowed) for block in response.content if block.type == "tool_use"]
        if run.model_calls + 1 >= max_steps:
            results.append({"type": "text", "text": FINAL_NUDGE})
        messages.append({"role": "user", "content": results})


def _call_tool(block, run: AgentRun, allowed: set[str]) -> dict:
    started = time.monotonic()
    content, is_error = run_tool(block.name, block.input, allowed)
    ms = round((time.monotonic() - started) * 1000)

    result = content if is_error else json.loads(content)
    run.steps.append(Step(block.name, dict(block.input), not is_error, _summary(block.name, result, is_error), result, ms))
    logger.info("tool %s ok=%s %sms", block.name, not is_error, ms)  # names only, never health values

    return {"type": "tool_result", "tool_use_id": block.id, "content": content, "is_error": is_error}


def _text(response) -> str:
    return "\n".join(b.text for b in response.content if b.type == "text").strip()


def _finish(run: AgentRun, stop: str, answer: str) -> AgentRun:
    run.stop, run.answer = stop, answer
    return run


# ---------- one-line step summaries for the UI ----------

def _summary(tool: str, result, is_error: bool) -> str:
    if is_error:
        return f"Error: {result}"[:160]
    if tool == "query_data":
        return f"{len(result['days'])} days of {', '.join(result['days_with_data'])}"
    if tool == "get_calendar":
        return f"{len(result['events'])} events, {result['start_date']} to {result['end_date']}"
    if tool == "compare_periods":
        return f"{result['metric']}: {result['period_a']['average']} vs {result['period_b']['average']}"
    if tool == "compute_correlation":
        return f"{result['meaning']}: {result['strength'] or 'n/a'} link over {result['paired_days']} days"
    if tool == "forecast_week":
        rough = [d["weekday"] for d in result["days"] if d["risk"] != "low"]
        return f"Week of {result['start_date']}: watch {', '.join(rough) or 'nothing'}"
    if tool == "find_free_time":
        return f"{len(result['free_slots'])} free slots on {result['weekday']} {result['date']}"
    if tool == "make_ics_event":
        return f"Calendar file: {result['summary']}"
    if tool == "save_suggestion":
        return f"Saved suggestion #{result['suggestion_id']}, check on {result['check_on']}"
    if tool == "evaluate_suggestion":
        return f"Checked {len(result['results'])} suggestion(s)"
    return tool
