"""Learning-curve demo: show the agent generic on call 1, sharp by call 5.

Usage:
    python scripts/seed_demo.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import agent
from app.deals import SEED_CALLS, DealStore
from app.memory import LocalMemory

tmp = tempfile.mkdtemp(prefix="dealintel-demo-")
store = DealStore(path=os.path.join(tmp, "deals.json"))
memory = LocalMemory(path=os.path.join(tmp, "memory.json"))

deal_id = "meridian"
print("=" * 70)
print("INTERACTION 1 — fresh deal, no memory (generic brief)")
print("=" * 70)
first = agent.brief(store, memory, deal_id)
print(first["brief"])
print(f"\n[memories used: {len(first['memories_used'])}]")

for i, call in enumerate(SEED_CALLS[deal_id], start=1):
    agent.log_call(store, memory, deal_id, call["notes"], call.get("outcome", ""))
    print(f"\n--- logged call {i}: {call.get('outcome', '')} ---")

print()
print("=" * 70)
print("INTERACTION 6 — after 5 calls (personalized brief)")
print("=" * 70)
later = agent.brief(store, memory, deal_id)
print(later["brief"])
print(f"\n[memories used: {len(later['memories_used'])}]")

print()
print("=" * 70)
print("FOLLOW-UP EMAIL (references remembered details)")
print("=" * 70)
print(agent.draft_followup(store, memory, deal_id)["email"])

print()
print("=" * 70)
print("TACTICS (borrows win patterns from past deals)")
print("=" * 70)
print(agent.suggest_tactics(store, memory, deal_id)["tactics"])
