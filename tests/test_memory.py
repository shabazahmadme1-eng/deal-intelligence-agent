"""Memory adapter contract: retain -> recall roundtrip."""
import os

import pytest

from app.memory import LocalMemory, MemoryHit


@pytest.fixture
def memory(tmp_path):
    return LocalMemory(path=tmp_path / "memory.json")


def test_retain_recall_roundtrip(memory):
    memory.retain("deal-a", "Priya objected to the $48k price", {"kind": "objection"})
    memory.retain("deal-a", "Rohan likes the driver app UI", {"kind": "stakeholder"})
    hits = memory.recall("deal-a", "price objection budget", top_k=2)
    assert hits, "expected recalled memories"
    assert all(isinstance(h, MemoryHit) for h in hits)
    assert "price" in hits[0].text  # most relevant ranks first


def test_banks_are_isolated(memory):
    memory.retain("deal-a", "Meridian price objection $48k")
    memory.retain("deal-b", "Kaveri needs SOC 2 report")
    hits = memory.recall("deal-b", "price objection", top_k=5)
    assert all("Kaveri" in h.text for h in hits)


def test_reflect_handles_empty_bank(memory):
    assert "No relevant memories" in memory.reflect("deal-empty", "anything")


def test_recall_many_searches_across_banks(memory):
    memory.retain("deal-a", "WIN PATTERN: 2-week pilot convinced the ops team")
    memory.retain("deal-b", "WIN PATTERN: ROI model closed the CFO")
    hits = memory.recall_many(["deal-a", "deal-b"], "win pattern pilot", top_k=5)
    assert len(hits) == 2
    assert {h.metadata["bank_id"] for h in hits} == {"deal-a", "deal-b"}


def test_count_tracks_retained_memories(memory):
    assert memory.count("deal-a") == 0
    memory.retain("deal-a", "first call logged")
    memory.retain("deal-a", "second call logged")
    assert memory.count("deal-a") == 2
