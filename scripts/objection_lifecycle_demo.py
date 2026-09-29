"""Objection lifecycle demo: watch one objection go open -> resolved with evidence.

Usage:
    python scripts/objection_lifecycle_demo.py

Runs against throwaway temp storage (your data/ directory is untouched).
Each transition is asserted, so this doubles as a behavior check.
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import agent  # noqa: E402
from app.deals import DealStore  # noqa: E402
from app.memory import LocalMemory, bank_id_for  # noqa: E402

tmp = tempfile.mkdtemp(prefix="dealintel-lifecycle-")
store = DealStore(path=os.path.join(tmp, "deals.json"))
memory = LocalMemory(path=os.path.join(tmp, "memory.json"))
DEAL = "meridian"


def show(title, result):
    print("=" * 70)
    print(title)
    print("=" * 70)
    print(result["brief"])
    print("\nEvidence cited:")
    for mem in result["memories_used"][:6]:
        print(f"  [{mem['metadata'].get('kind', 'general')}] {mem['text']}")
    print()


agent.log_call(store, memory, DEAL,
               "Objection: Priya says the $48k quote is 20% over budget. Next step: send an ROI breakdown.",
               "Price objection raised", call_id="lifecycle-1")
first = agent.brief(store, memory, DEAL)
show("CALL 1 LOGGED -- objection is OPEN", first)
assert "Objection history" in first["brief"], "open objection should be listed"
assert "Progress / resolved" not in first["brief"], "nothing resolved yet"

agent.log_call(store, memory, DEAL,
               "Objection handled: the ROI model shows payback in 9 months and Priya accepted the math. "
               "Only open item: support SLA for night shifts. Next step: final proposal with SLA appendix.",
               "ROI accepted, closing on SLA", call_id="lifecycle-2")
second = agent.brief(store, memory, DEAL)
show("CALL 2 LOGGED -- objection RESOLVED, new thread open", second)
assert "Progress / resolved" in second["brief"], "resolution should appear"
assert "SLA" in second["brief"], "new open thread should appear"
texts = [m["text"] for m in second["memories_used"]]
assert any("over budget" in t for t in texts), "original objection still cited"
assert any("accepted the math" in t for t in texts), "resolution cited"

print("Follow-up draft after resolution:")
print(agent.draft_followup(store, memory, DEAL)["email"])
print()
print(f"Stored facts for {DEAL}: {memory.count(bank_id_for(DEAL))}")
print("LIFECYCLE OK: open -> resolved, every claim backed by cited source calls.")
