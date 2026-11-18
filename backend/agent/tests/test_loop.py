"""The agent loop, driven by a fake model so tests are free, fast and repeatable.

Each test scripts what the "model" replies, then checks what the loop did:
which tools ran, what went back to the model, and how the run ended.
"""
import json
from io import StringIO
from types import SimpleNamespace

import pytest
from django.core.management import call_command

from agent import llm
from agent.loop import FINAL_NUDGE, run_agent


# ---------- a fake model ----------

def text(value):
    return SimpleNamespace(type="text", text=value)


def tool_use(name, tool_input, id="call_1"):
    return SimpleNamespace(type="tool_use", name=name, input=tool_input, id=id)


def reply(*blocks, stop="end_turn"):
    return SimpleNamespace(content=list(blocks), stop_reason=stop,
                           usage=SimpleNamespace(input_tokens=100, output_tokens=20))


class FakeClient:
    """Returns scripted replies in order and records every request."""

    def __init__(self, replies):
        self.replies, self.requests = list(replies), []
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **request):
        self.requests.append({**request, "messages": list(request["messages"])})
        return self.replies.pop(0)


@pytest.fixture
def fake(monkeypatch, db, settings):
    settings.DEMO_TODAY = "2026-11-16"
    call_command("seed_synthetic", stdout=StringIO())

    def install(*replies):
        client = FakeClient(replies)
        monkeypatch.setattr(llm, "get_client", lambda: client)
        return client
    return install


# ---------- tests ----------

def test_runs_tools_in_a_row_then_answers(fake):
    client = fake(
        reply(tool_use("get_calendar", {"start_date": "2026-11-19", "end_date": "2026-11-19"}), stop="tool_use"),
        reply(tool_use("find_free_time", {"date": "2026-11-19"}, id="call_2"), stop="tool_use"),
        reply(text("You're free 12:15-16:00 on Thursday.")),
    )
    run = run_agent("When am I free Thursday?")

    assert run.stop == "answered"
    assert run.answer == "You're free 12:15-16:00 on Thursday."
    assert [s.tool for s in run.steps] == ["get_calendar", "find_free_time"]
    assert all(s.ok for s in run.steps)
    assert run.model_calls == 3 and run.input_tokens == 300

    # The second request carries the first tool's result, matched by id.
    tool_result = client.requests[1]["messages"][-1]["content"][0]
    assert tool_result["tool_use_id"] == "call_1" and not tool_result["is_error"]
    assert json.loads(tool_result["content"])["booked_hours_by_day"]["2026-11-19"] == 8.25


def test_parallel_tool_calls_go_back_in_one_message(fake):
    client = fake(
        reply(tool_use("find_free_time", {"date": "2026-11-18"}, id="a"),
              tool_use("find_free_time", {"date": "2026-11-19"}, id="b"), stop="tool_use"),
        reply(text("Done.")),
    )
    run_agent("Free time Wed and Thu?")
    results = client.requests[1]["messages"][-1]["content"]
    assert [r["tool_use_id"] for r in results] == ["a", "b"]


def test_tool_errors_go_back_to_the_model(fake):
    client = fake(
        reply(tool_use("query_data", {"start_date": "last week", "end_date": "2026-11-15", "metrics": ["mood"]}),
              stop="tool_use"),
        reply(text("Sorry, try again.")),
    )
    run = run_agent("How was my mood?")
    assert not run.steps[0].ok and run.steps[0].summary.startswith("Error:")
    assert client.requests[1]["messages"][-1]["content"][0]["is_error"] is True


def test_step_limit_forces_an_answer(fake):
    looping = [reply(tool_use("find_free_time", {"date": "2026-11-19"}, id=f"c{i}"), stop="tool_use") for i in range(2)]
    client = fake(*looping, reply(text("Here's what I found so far.")))
    run = run_agent("Keep checking", max_steps=3)

    assert run.stop == "step_limit" and run.model_calls == 3
    assert client.requests[-1]["tool_choice"] == {"type": "none"}
    assert client.requests[-1]["messages"][-1]["content"][-1] == {"type": "text", "text": FINAL_NUDGE}


def test_cut_off_reply_does_not_run_its_tools(fake):
    fake(reply(tool_use("save_suggestion", {"text": "half"}), stop="max_tokens"))
    run = run_agent("Suggest something")
    assert run.stop == "cut_off" and run.steps == []


def test_refusal_stops_the_run(fake):
    fake(reply(stop="refusal"))
    run = run_agent("Something it won't answer")
    assert run.stop == "declined" and run.answer


def test_requests_send_tools_system_prompt_and_date(fake):
    client = fake(reply(text("Hi.")))
    run_agent("Hello")
    request = client.requests[0]
    assert len(request["tools"]) == 9
    assert request["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert "2026-11-16" in request["system"][1]["text"]
