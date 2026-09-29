"""Agent behavior: generic when fresh, specific after memory accumulates."""
import os

import pytest

from app import agent
from app.deals import DealStore
from app.memory import LocalMemory


@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "")  # template mode for determinism
    store = DealStore(path=tmp_path / "deals.json")
    memory = LocalMemory(path=tmp_path / "memory.json")
    return store, memory


def test_brief_is_generic_on_fresh_deal(setup):
    store, memory = setup
    result = agent.brief(store, memory, "meridian")
    assert result["memories_used"] == []
    assert "no calls logged yet" in result["brief"].lower()


def test_brief_recalls_logged_objection(setup):
    store, memory = setup
    agent.log_call(store, memory, "meridian", "Objection: Priya says $48k is over budget.", "Price objection")
    result = agent.brief(store, memory, "meridian")
    assert result["memories_used"], "brief should use recalled memories"
    assert "budget" in result["brief"].lower()


def test_log_call_tags_sentences_by_kind(setup):
    store, memory = setup
    result = agent.log_call(
        store, memory, "meridian",
        "Objection: migration effort worries Rohan. Next step: send the pilot proposal.",
        "Pilot requested",
    )
    kinds = {r["kind"] for r in result["retained"]}
    assert {"objection", "next_step", "outcome"} <= kinds


def test_followup_names_the_contact(setup):
    store, memory = setup
    agent.log_call(store, memory, "meridian", "Priya wants training included in the quote.")
    result = agent.draft_followup(store, memory, "meridian")
    assert "Priya" in result["email"]


def test_tactics_borrow_from_other_deals(setup):
    store, memory = setup
    agent.log_call(store, memory, "kaveri", "WIN PATTERN: sharing the SOC 2 report unblocked compliance.")
    result = agent.suggest_tactics(store, memory, "meridian")
    assert "kaveri" in result["tactics"].lower() or "soc 2" in result["tactics"].lower()


def test_unknown_deal_raises_key_error(setup):
    store, memory = setup
    with pytest.raises(KeyError):
        agent.brief(store, memory, "nonexistent")
