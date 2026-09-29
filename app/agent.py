"""Deal Intelligence Agent: brief, log, follow-up, and tactics.

Every function recalls deal memory first and returns the memories it used,
so the UI can show *why* the agent said what it said — memory is the star.
"""
from __future__ import annotations

import json
import os
import re
import tempfile
import time
import uuid
from pathlib import Path

from filelock import FileLock

from . import llm
from .deals import Deal, DealStore
from .memory import (
    DocumentConflictError,
    LocalMemory,
    MemoryAdapter,
    MemoryHit,
    bank_id_for,
    short_hash,
)

SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")

# Keyword tagging so logged calls become structured, recallable facts.
# Explicit intent markers ("Objection:", "Next step:") rank first so they beat
# content keywords ("pilot", "pricing") inside the same sentence.
TAG_RULES: list[tuple[str, list[str]]] = [
    ("objection", ["objection", "concern", "worried", "worry", "blocker", "blocked", "too expensive", "over budget", "won't", "requires"]),
    ("next_step", ["next step", "follow-up", "follow up", "pending", "send ", "share ", "call"]),
    ("competitor", ["fleet", "routewise", "ledgerpro", "shopflow", "competitor", "evaluating", "quoted"]),
    ("pricing", ["price", "pricing", "$", "₹", "budget", "quote", "discount", "billing", "payback", "roi"]),
    ("stakeholder", ["vp", "cto", "cfo", "head of", "met ", "stakeholder", "sign-off", "approve", "compliance"]),
    ("win", ["win pattern"]),
]


def tag_sentence(sentence: str) -> str:
    lowered = sentence.lower()
    if lowered.startswith("win pattern:"):
        return "win"
    if lowered.startswith(("objection handled:", "resolved:")):
        return "resolved"
    if "only open item" in lowered:
        return "objection"
    for tag, keywords in TAG_RULES:
        if any(k in lowered for k in keywords):
            return tag
    return "general"


def _best_effort_count(memory: MemoryAdapter, bank: str) -> int | None:
    """Counts are informational: a completed read/write must not fail just
    because the incidental count lookup did."""
    try:
        return memory.count(bank)
    except Exception:
        return None


class ReceiptStore:
    """Application-level idempotency journal for call submissions.

    Same call ID + same payload replays the prior receipt without touching
    the provider (safe retries, cheap reseeds). Same call ID + different
    payload is a conflict: corrections must arrive as a new call that
    supersedes the earlier one. Works identically for every memory backend,
    with no provider read-before-write.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = FileLock(str(self.path) + ".lock")

    def _load(self) -> dict:
        if self.path.exists():
            try:
                return json.loads(self.path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                return {}
        return {}

    def get(self, call_id: str) -> dict | None:
        with self.lock:
            return self._load().get(call_id)

    def put(self, call_id: str, receipt: dict) -> None:
        with self.lock:
            data = self._load()
            data[call_id] = receipt
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.path.parent, delete=False) as f:
                temp = Path(f.name)
                json.dump(data, f, indent=2)
            try:
                os.replace(temp, self.path)
            finally:
                temp.unlink(missing_ok=True)

    def reset(self) -> None:
        with self.lock:
            data: dict = {}
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.path.parent, delete=False) as f:
                temp = Path(f.name)
                json.dump(data, f, indent=2)
            try:
                os.replace(temp, self.path)
            finally:
                temp.unlink(missing_ok=True)


def receipts_for(memory: MemoryAdapter) -> ReceiptStore:
    """Receipts live next to the local store (tests stay isolated); the remote
    backend uses RECEIPTS_PATH so retries stay idempotent there too."""
    if isinstance(memory, LocalMemory):
        return ReceiptStore(memory.path.parent / "receipts.json")
    default = Path(__file__).resolve().parent.parent / "data" / "receipts.json"
    return ReceiptStore(os.environ.get("RECEIPTS_PATH", str(default)))


def reset_call_receipts(memory: MemoryAdapter) -> None:
    receipts_for(memory).reset()


def brief(store: DealStore, memory: MemoryAdapter, deal_id: str, use_memory: bool = True) -> dict:
    deal = _require_deal(store, deal_id)
    bank = bank_id_for(deal_id)
    queries = [
        "objections concerns blockers raised",
        "stakeholders people involved decisions",
        "pricing budget quote billing",
        "next steps pending follow-ups",
    ]
    hits: list[MemoryHit] = []
    seen: set[str] = set()
    for query in queries if use_memory else []:
        for hit in memory.recall(bank, query, top_k=3):
            if hit.text not in seen:
                seen.add(hit.text)
                hits.append(hit)
    # Reserve room for both relevant historical facts and the latest context.
    if use_memory:
        recent = sorted(memory.list_memories(bank, limit=100), key=lambda h: h.timestamp or 0, reverse=True)[:12]
        for hit in recent:
            if hit.text not in seen:
                seen.add(hit.text)
                hits.append(hit)
    hits.sort(key=lambda h: h.timestamp or 0, reverse=True)
    top = hits[:24]

    context = "\n".join(f"- {h.text} [{h.metadata.get('kind', 'general')}]" for h in top)
    prompt = (
        f"Deal: {deal.company} ({deal.value}, stage: {deal.stage}). "
        f"Main contact: {deal.contact}, {deal.contact_title}. "
        f"Competitors: {', '.join(deal.competitors)}.\n"
        f"Past call memories:\n{context or '(no prior calls logged)'}\n\n"
        "Separate historical objections from resolved ones; prioritize the latest next step. Write a 60-second pre-call brief for the sales rep: 1) deal state in one line, "
        "2) open objections/risks, 3) suggested talk track for this call. Be concrete."
    )
    generation = "template"
    if use_memory and top and memory.server_reflection:
        text, top = memory.reflect_with_evidence(bank, prompt)
        generated = text
        generation = "hindsight-reflect"
    else:
        generated = llm.complete(prompt, system="You are a sales coach briefing a rep before a call.")
        text = generated or _template_brief(deal, top)
        if generated:
            generation = "groq"
    if not use_memory:
        text = text.replace("no calls logged yet", "prior call memory disabled for this comparison")
    return {
        "deal_id": deal_id,
        "brief": text,
        "memories_used": [h.to_dict() for h in top],
        # The memory-free baseline must not depend on the provider at all.
        "memory_count": _best_effort_count(memory, bank) if use_memory else None,
        "generation": generation,
        "llm": bool(generated),
    }


def _template_brief(deal: Deal, hits: list[MemoryHit]) -> str:
    if not hits:
        return (
            f"**{deal.company}** ({deal.value}, {deal.stage}) — no calls logged yet.\n\n"
            f"Main contact: {deal.contact} ({deal.contact_title}). "
            f"Known competitors: {', '.join(deal.competitors)}.\n\n"
            "Talk track: run discovery — pain, timeline, decision process. "
            "Log the call afterwards and this brief gets smarter every time."
        )
    by_kind: dict[str, list[str]] = {}
    for hit in hits:
        by_kind.setdefault(hit.metadata.get("kind", "general"), []).append(hit.text)
    lines = [f"**{deal.company}** ({deal.value}, {deal.stage}) — {len(hits)} memories recalled."]
    if by_kind.get("objection"):
        lines.append("\n**Objection history (check current status):**")
        lines.extend(f"- {t}" for t in by_kind["objection"][:3])
    if by_kind.get("resolved"):
        lines.append("\n**Progress / resolved objections:**")
        lines.extend(f"- {t}" for t in by_kind["resolved"][:3])
    if by_kind.get("win"):
        lines.append("\n**Recorded wins:**")
        lines.extend(f"- {t}" for t in by_kind["win"][:2])
    if by_kind.get("stakeholder"):
        lines.append("\n**People to remember:**")
        lines.extend(f"- {t}" for t in by_kind["stakeholder"][:2])
    if by_kind.get("pricing"):
        lines.append("\n**Pricing threads:**")
        lines.extend(f"- {t}" for t in by_kind["pricing"][:2])
    if by_kind.get("competitor"):
        lines.append("\n**Competitor history:**")
        lines.extend(f"- {t}" for t in by_kind["competitor"][:2])
    if by_kind.get("next_step"):
        lines.append("\n**Suggested talk track:** close the loop on:")
        lines.extend(f"- {t}" for t in by_kind["next_step"][:1])
    if by_kind.get("general"):
        lines.append("\n**Other recorded context:**")
        lines.extend(f"- {t}" for t in by_kind["general"][:3])
    return "\n".join(lines)


def log_call(
    store: DealStore,
    memory: MemoryAdapter,
    deal_id: str,
    notes: str,
    outcome: str = "",
    call_id: str | None = None,
    supersedes: str | None = None,
) -> dict:
    deal = _require_deal(store, deal_id)
    bank = bank_id_for(deal_id)
    call_id = call_id or uuid.uuid4().hex
    if len(notes.strip()) < 3:
        raise ValueError("Call notes must contain at least 3 non-whitespace characters")
    payload_hash = short_hash(notes.strip() + "\n" + outcome.strip())
    receipts = receipts_for(memory)
    prior = receipts.get(call_id)
    if prior:
        if prior["hash"] == payload_hash:
            return {
                "deal_id": deal_id,
                "retained": prior["retained"],
                "memory_count": _best_effort_count(memory, bank),
                "duplicate": True,
            }
        raise DocumentConflictError(call_id, prior["hash"], payload_hash)
    sentences = [s.strip() for s in SENTENCE_SPLIT.split(notes.strip()) if s.strip()]
    retained: list[dict] = []
    for index, sentence in enumerate(sentences):
        kind = tag_sentence(sentence)
        metadata: dict = {"kind": kind, "deal": deal.company, "call_id": call_id}
        if supersedes:
            metadata["supersedes"] = supersedes
        mem_id = memory.retain(bank, sentence, metadata=metadata, document_id=f"{call_id}-{index}")
        retained.append({"id": mem_id, "kind": kind, "text": sentence})
    if outcome:
        metadata = {"kind": "outcome", "deal": deal.company, "call_id": call_id}
        if supersedes:
            metadata["supersedes"] = supersedes
        mem_id = memory.retain(bank, f"Call outcome: {outcome}", metadata=metadata, document_id=f"{call_id}-outcome")
        retained.append({"id": mem_id, "kind": "outcome", "text": f"Call outcome: {outcome}"})
    receipts.put(call_id, {
        "hash": payload_hash,
        "retained": retained,
        "deal_id": deal_id,
        "supersedes": supersedes,
        "timestamp": time.time(),
    })
    return {"deal_id": deal_id, "retained": retained, "memory_count": _best_effort_count(memory, bank), "duplicate": False}


def draft_followup(store: DealStore, memory: MemoryAdapter, deal_id: str, tone: str = "professional") -> dict:
    deal = _require_deal(store, deal_id)
    bank = bank_id_for(deal_id)
    hits = memory.recall(bank, "objections next steps open items commitments", top_k=6)
    recent = memory.list_memories(bank, limit=20)
    seen = {h.text for h in hits}
    hits.extend(h for h in recent if h.text not in seen)
    hits.sort(key=lambda h: h.timestamp or 0, reverse=True)
    hits = hits[:8]
    context = "\n".join(f"- {h.text}" for h in hits)
    prompt = (
        f"Write a {tone} follow-up email from the sales rep to {deal.contact} "
        f"({deal.contact_title}, {deal.company}) after a sales call about {deal.product}.\n"
        f"Deal value {deal.value}, stage {deal.stage}.\n"
        f"What we remember from past calls:\n{context or '(first touch — keep it short)'}\n\n"
        "Reference a remembered detail only if evidence exists; otherwise draft a first-touch email. Do not imply work has been done or files attached. Keep it under 150 words. "
        "End with one clear next step."
    )
    generated = llm.complete(prompt, system="You write crisp B2B sales follow-up emails.")
    text = generated or _template_followup(deal, hits)
    return {
        "deal_id": deal_id,
        "email": text,
        "memories_used": [h.to_dict() for h in hits],
        "llm": llm.is_configured() and generated is not None,
    }


def _template_followup(deal: Deal, hits: list[MemoryHit]) -> str:
    relevant = next((h for h in hits if h.metadata.get("kind") == "next_step"), hits[0] if hits else None)
    detail = f'Following up on this recorded point: "{relevant.text}"' if relevant else f"I'd like to learn more about {deal.company}'s priorities."
    return (
        f"Subject: Next step for {deal.company}\n\nHi {deal.contact.split()[0]},\n\n"
        f"{detail}\n\nWould a 30-minute working session help us confirm the open questions "
        "and agree on next steps? Please suggest a time that works for you.\n\nBest,\nYour sales rep"
    )


def suggest_tactics(store: DealStore, memory: MemoryAdapter, deal_id: str) -> dict:
    """Mine win patterns across ALL deals — memory compounds over time."""
    deal = _require_deal(store, deal_id)
    banks = [bank_id_for(d.id) for d in store.list() if d.id != deal_id]
    wins = memory.recall_many(banks, "win pattern what worked convinced accepted pilot", top_k=50)
    wins = [w for w in wins if w.metadata.get("kind") == "win" or w.text.lower().startswith("win pattern:")]
    # Prefer memories explicitly tagged as wins over token-overlap lookalikes.
    wins.sort(key=lambda w: 0 if w.metadata.get("kind") == "win" else 1)
    objections = memory.recall(bank_id_for(deal_id), "objections concerns blockers", top_k=4)
    context_wins = "\n".join(f"- [{w.metadata.get('bank_id', '?')}] {w.text}" for w in wins)
    context_obj = "\n".join(f"- {h.text}" for h in objections)
    prompt = (
        f"Current deal: {deal.company} ({deal.value}, {deal.stage}).\n"
        f"Current objections:\n{context_obj or '(none logged yet)'}\n\n"
        f"Tactics that worked in past deals:\n{context_wins or '(no win patterns stored yet)'}\n\n"
        "Suggest 3 concrete tactics for this deal, each citing which past deal it borrows from. "
        "If no past wins exist, say what to try first and what to log."
    )
    generated = llm.complete(prompt, system="You are a sales strategist who learns from win/loss history.")
    text = generated or _template_tactics(deal, wins, objections)
    return {
        "deal_id": deal_id,
        "tactics": text,
        "memories_used": [h.to_dict() for h in (wins + objections)],
        "llm": llm.is_configured() and generated is not None,
    }


def _template_tactics(deal: Deal, wins: list[MemoryHit], objections: list[MemoryHit]) -> str:
    if not wins:
        return (
            f"No win patterns stored yet. For **{deal.company}**: run the call, log what worked, "
            "and future deals will borrow from it. That compounding is the whole point."
        )
    lines = [f"Tactics for **{deal.company}**, borrowed from past wins:"]
    for win in wins[:3]:
        src = win.metadata.get("bank_id", "?")
        lines.append(f"- Try what worked in `{src}`: \"{win.text}\"")
    objection = next(
        (h for h in objections if h.metadata.get("kind") == "objection"),
        objections[0] if objections else None,
    )
    if objection:
        lines.append(f"\nApply them against the open objection: \"{objection.text}\"")
    return "\n".join(lines)


def timeline(store: DealStore, memory: MemoryAdapter, deal_id: str) -> dict:
    deal = _require_deal(store, deal_id)
    bank = bank_id_for(deal_id)
    hits = memory.list_memories(bank, limit=100)
    hits.sort(key=lambda h: h.timestamp or 0)
    return {
        "deal_id": deal_id,
        "company": deal.company,
        "count": _best_effort_count(memory, bank),
        "shown": len(hits),
        "memories": [h.to_dict() for h in hits],
    }


def _require_deal(store: DealStore, deal_id: str) -> Deal:
    deal = store.get(deal_id)
    if deal is None:
        raise KeyError(f"Unknown deal: {deal_id}")
    return deal
