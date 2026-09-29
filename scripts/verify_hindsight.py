"""Opt-in live provider check; writes only synthetic data to a unique bank."""
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.memory import HindsightMemory, bank_id_for


def main():
    import os
    if os.environ.get("MEMORY_BACKEND") != "hindsight":
        raise SystemExit("Configure MEMORY_BACKEND=hindsight and your provider settings in .env first.")
    bank = bank_id_for("verification-" + uuid.uuid4().hex[:12])
    first = HindsightMemory()
    second = None
    try:
        first.retain(bank, "Synthetic verification: customer Cedar requested quarterly billing after a two-week pilot.",
                     {"kind": "pricing"}, document_id="verification-call")
        second = HindsightMemory()
        hits = second.recall(bank, "What billing schedule did Cedar request?")
        if not hits or second.count(bank) < 1:
            raise RuntimeError("No persisted facts recalled; inspect the provider bank.")
        answer, facts = second.reflect_with_evidence(bank, "What billing schedule did Cedar request? Use stored facts only.")
        if not answer or not facts:
            raise RuntimeError("Reflection returned no answer or supporting facts.")
        print("PASS: retain, new-client recall, count, and reflection with evidence.")
        print("Verification bank:", bank)
        print(answer)
    finally:
        first.client.close()
        if second:
            second.client.close()


if __name__ == "__main__":
    main()
