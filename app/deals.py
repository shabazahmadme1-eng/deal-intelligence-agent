"""Deal store + realistic seed data for the demo."""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class Deal:
    id: str
    company: str
    contact: str
    contact_title: str
    value: str
    stage: str
    competitors: list[str] = field(default_factory=list)
    product: str = "our logistics-automation platform"


DEFAULT_DEALS = [
    Deal(
        id="meridian",
        company="Meridian Logistics",
        contact="Priya Nair",
        contact_title="VP Operations",
        value="$48,000 / year",
        stage="Negotiation",
        competitors=["FleetTrack", "RouteWise"],
    ),
    Deal(
        id="kaveri",
        company="Kaveri Fintech",
        contact="Arjun Rao",
        contact_title="CTO",
        value="₹35,00,000 / year",
        stage="Evaluation",
        competitors=["LedgerPro"],
        product="our payment-reconciliation platform",
    ),
    Deal(
        id="northwind",
        company="Northwind Retail",
        contact="Sarah D'Souza",
        contact_title="Head of Procurement",
        value="$72,000 / year",
        stage="Proposal",
        competitors=["ShopFlow"],
        product="our retail replenishment platform",
    ),
]

# Staged call history for the learning-curve demo (deal: meridian).
# Interaction 1 is generic; by interaction 5 the agent knows objections,
# stakeholders, pricing limits, and what tactics worked.
SEED_CALLS: dict[str, list[dict]] = {
    "meridian": [
        {
            "notes": "Intro call with Priya Nair (VP Operations). They run 40 delivery hubs. "
            "Pain: manual dispatch planning takes 6 hours daily. Asked for a ballpark price. "
            "Next step: send pricing one-pager.",
            "outcome": "Interested, wants pricing",
        },
        {
            "notes": "Objection: Priya says our $48k quote is 20% over budget. They are also "
            "evaluating FleetTrack, which quoted lower. Concerned about migration effort "
            "from their Excel-based dispatch sheets. Next step: ROI breakdown.",
            "outcome": "Price objection raised",
        },
        {
            "notes": "Met Rohan Iyer (Head of Dispatch) — new stakeholder. He worries drivers "
            "won't adopt a new app. Liked our Hindi/Telugu driver UI when shown. Priya asked "
            "whether training is included in the quote. Next step: pilot proposal for 3 hubs.",
            "outcome": "New stakeholder, pilot requested",
        },
        {
            "notes": "Objection handled: showed ROI model — 6 hrs/day dispatch savings = ~$60k/yr, "
            "so payback in 9 months. Priya accepted the math but needs CFO sign-off. "
            "Competitor update: RouteWise dropped out, only FleetTrack left. "
            "Next step: security questionnaire + CFO call.",
            "outcome": "ROI accepted, CFO call pending",
        },
        {
            "notes": "WIN PATTERN: Priya confirmed the 2-week pilot at 3 hubs is what convinced "
            "the ops team — on-time dispatch improved 18% during the pilot. CFO asked for "
            "annual vs quarterly billing options. Only open item: support SLA for night shifts. "
            "Next step: final proposal with SLA appendix.",
            "outcome": "Pilot won over ops team, closing on SLA",
        },
    ],
    "kaveri": [
        {
            "notes": "Intro call with Arjun Rao (CTO). 12-person eng team, processing 2M UPI "
            "transactions/day. Pain: reconciliation breaks every festival sale. Evaluating "
            "us vs LedgerPro. Next step: technical deep-dive.",
            "outcome": "Technical evaluation started",
        },
        {
            "notes": "Objection: Arjun requires SOC 2 Type II report and data residency in India "
            "before any paid pilot. Their compliance head, Meera Krishnan, must approve. "
            "Next step: share SOC 2 + architecture doc.",
            "outcome": "Blocked on compliance review",
        },
        {
            "notes": "WIN PATTERN: Sharing the SOC 2 report and an India data-residency diagram before the review helped Meera approve the technical evaluation. Next step: scope a paid pilot; no contract signed yet.",
            "outcome": "Compliance review passed; pilot scope pending",
        },
    ],
    "northwind": [
        {
            "notes": "Intro call with Sarah D'Souza (Head of Procurement). 90 stores, replenishment "
            "planned manually per store. Also talking to ShopFlow. Price-sensitive: asked for "
            "volume discount tiers upfront. Next step: volume pricing proposal.",
            "outcome": "Wants volume pricing",
        },
    ],
}


class DealStore:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path or os.environ.get("DEALS_PATH", str(Path(__file__).resolve().parent.parent / "data/deals.json")))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            try:
                raw = json.loads(self.path.read_text(encoding="utf-8"))
                self._deals = {d["id"]: Deal(**d) for d in raw}
            except (json.JSONDecodeError, TypeError, KeyError) as exc:
                raise RuntimeError(f"Invalid deals file: {self.path}; restore a backup.") from exc
        else:
            self.reset()

    def reset(self) -> None:
        self._deals = {d.id: d for d in DEFAULT_DEALS}
        self._save()

    def _save(self) -> None:
        self.path.write_text(
            json.dumps([asdict(d) for d in self._deals.values()], indent=2), encoding="utf-8"
        )

    def list(self) -> list[Deal]:
        return list(self._deals.values())

    def get(self, deal_id: str) -> Deal | None:
        return self._deals.get(deal_id)
