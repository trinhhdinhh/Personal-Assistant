"""POST /api/chat, with the fake model from test_loop (no API calls)."""
import pytest
from django.test import Client

from agent.tests.test_loop import fake, reply, text, tool_use  # noqa: F401  (fake is a fixture)


def post(body):
    return Client().post("/api/chat", body, content_type="application/json")


def test_chat_returns_answer_steps_checks_and_files(fake):
    fake(
        reply(tool_use("find_free_time", {"date": "2026-11-19"}), stop="tool_use"),
        reply(tool_use("make_ics_event", {"title": "Walk", "date": "2026-11-19", "start_time": "12:30",
                                          "duration_minutes": 20}, id="call_2"), stop="tool_use"),
        reply(text("You're free from 12:15 to 16:00. I made a calendar file for a walk at 12:30.")),
    )
    response = post({"question": "When can I walk Thursday?"})

    assert response.status_code == 200
    data = response.json()
    assert data["stop"] == "answered"
    assert [s["tool"] for s in data["steps"]] == ["find_free_time", "make_ics_event"]
    assert "result" not in data["steps"][0]  # raw tool results stay on the server
    assert all(c["passed"] for c in data["checks"])
    assert data["files"][0]["filename"].endswith(".ics") and "BEGIN:VEVENT" in data["files"][0]["ics"]


def test_blocked_answer_is_not_sent(fake):
    fake(
        reply(tool_use("find_free_time", {"date": "2026-11-19"}), stop="tool_use"),
        reply(text("You're free at 14:30.")),
        reply(text("You're free at 14:45.")),
    )
    data = post({"question": "When am I free Thursday?"}).json()
    assert data["stop"] == "blocked"
    assert "blocked_answer" not in data and "14:45" not in data["answer"]
    assert not data["checks"][0]["passed"]  # the user sees which check failed


def test_history_is_passed_to_the_model(fake):
    client = fake(reply(text("Sure.")))
    post({"question": "And Friday?", "history": [
        {"role": "user", "content": "When am I free Thursday?"},
        {"role": "assistant", "content": "From 12:15 to 16:00."},
    ]})
    sent = client.requests[0]["messages"]
    assert [m["role"] for m in sent] == ["user", "assistant", "user"]
    assert sent[-1]["content"] == "And Friday?"


@pytest.mark.parametrize("body", [{}, {"question": ""}, {"question": "x" * 1001},
                                  {"question": "Hi", "history": "nope"},
                                  {"question": "Hi", "history": [{"role": "system", "content": "x"}]}])
def test_bad_requests_are_rejected(db, body):
    assert post(body).status_code == 400


def test_get_is_not_allowed(db):
    assert Client().get("/api/chat").status_code == 405


def test_missing_key_is_a_clear_503(db, settings):
    from agent import llm
    llm.get_client.cache_clear()
    settings.OPENROUTER_API_KEY = ""
    response = post({"question": "Hi"})
    llm.get_client.cache_clear()
    assert response.status_code == 503 and "OPENROUTER_API_KEY" in response.json()["error"]
