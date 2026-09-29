import pytest

from app.backend.schemas import Preferences
from app.memory.long_term import LongTermMemory, MemoryValidationError, facts_from_preferences, validate_fact
from app.memory.manager import MemoryManager
from app.memory.short_term import ShortTermMemory
from app.schemas.memory import ConversationTurn as T
from app.schemas.memory import MemoryKey
from tests.fakes import TOKEN_A


def test_short_term_window_keeps_recent_turns_in_order():
    history = [T(role="user" if i % 2 == 0 else "assistant", content=f"m{i}") for i in range(20)]
    msgs = ShortTermMemory(max_messages=6).to_messages(history)
    assert [m["content"] for m in msgs] == ["m14", "m15", "m16", "m17", "m18", "m19"]
    assert msgs[0]["role"] == "user" and msgs[-1]["role"] == "assistant"


def test_short_term_window_enforces_alternation_and_budget():
    history = [T(role="assistant", content="welcome"), T(role="user", content="a"), T(role="user", content="b"),
               T(role="assistant", content="c"), T(role="system", content="ignored"), T(role="user", content="dangling")]
    msgs = ShortTermMemory().to_messages(history)
    assert msgs == [{"role": "user", "content": "a\n\nb"}, {"role": "assistant", "content": "c"}]
    long = [T(role="user", content="x" * 3000), T(role="assistant", content="y" * 3000)] * 10
    kept = ShortTermMemory(max_messages=20, max_chars=7000).window(long)
    assert sum(len(t.content) for t in kept) <= 7000


def test_short_term_disabled():
    assert ShortTermMemory(max_messages=0).to_messages([T(role="user", content="a"), T(role="assistant", content="b")]) == []


def test_long_term_only_accepts_whitelisted_valid_facts():
    assert validate_fact(MemoryKey.PREFERRED_STUDY_START, "18:30") == "18:30"
    assert validate_fact(MemoryKey.DAILY_STUDY_GOAL_MINUTES, "90") == 90
    assert validate_fact(MemoryKey.TIMEZONE, "Asia/Kolkata") == "Asia/Kolkata"
    for key, bad in [(MemoryKey.PREFERRED_STUDY_START, "evening"), (MemoryKey.DEFAULT_REMINDER_TIME, "25:00"),
                     (MemoryKey.DAILY_STUDY_GOAL_MINUTES, 5000), (MemoryKey.TIMEZONE, "Mars/Olympus")]:
        with pytest.raises(MemoryValidationError):
            validate_fact(key, bad)
    with pytest.raises(ValueError):
        MemoryKey("favourite_food")


def test_facts_come_from_backend_preferences():
    facts = facts_from_preferences(Preferences(preferred_study_start="18:00", timezone="UTC", default_reminder_time=None))
    assert {f.key: f.value for f in facts} == {MemoryKey.PREFERRED_STUDY_START: "18:00", MemoryKey.TIMEZONE: "UTC"}


async def test_manager_fetches_history_from_backend_when_not_supplied(harness):
    harness.fake.messages["conv-1"] = [{"role": "user", "content": "hello"}, {"role": "assistant", "content": "hi!"}]
    manager = MemoryManager(ShortTermMemory(), LongTermMemory())
    async with harness.client(TOKEN_A) as backend:
        snap = await manager.load(backend, conversation_id="conv-1", history=None)
        supplied = await manager.load(backend, conversation_id="conv-1", history=[T(role="user", content="x"), T(role="assistant", content="y")])
    assert [m["content"] for m in snap.history_messages] == ["hello", "hi!"]
    assert snap.facts_as_dict()["preferred_study_start"] == "18:00" and snap.currency == "INR"
    assert [m["content"] for m in supplied.history_messages] == ["x", "y"]


async def test_conversation_messages_are_never_saved_as_long_term_memory(harness):
    """Running the agent must not write preferences unless remember_preference is called."""
    before = dict(harness.fake.prefs["11111111-1111-1111-1111-111111111111"])
    await harness.run("I usually study late at night and I love pizza. What are my tasks?")
    assert harness.fake.prefs["11111111-1111-1111-1111-111111111111"] == before
    assert not any(m == "PATCH" for m, _ in harness.fake.calls)
