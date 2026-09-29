# Project assessment and submission readiness

Reviewed against the [official problem statement](https://docs.google.com/document/d/1A4ezag02em823ZzYF34DiUVHUNLWI5ztm70QvWidWoQ/edit) and [content guide](https://docs.google.com/document/d/1Spy4cclvZtWFI_ynXLcSDGBSVqb_Zjp2M1ffXqWeOXU/edit).

## Verdict

Keep the idea. The problem statement explicitly recommends a Deal Intelligence Agent: remember objections, competitors, stakeholders, pricing, and successful approaches across calls. The business workflow and memory fit are strong. The original implementation was an early prototype, with a simulated backend, templates, and several misleading claims. It was not ready to submit as a working Hindsight demonstration.

Innovation is the weak point: this is almost exactly an organizer-suggested idea, and innovation carries 30%. Differentiate through reliable handling of changed facts: an objection raised on call two, addressed on call four, and replaced by a remaining SLA concern on call five. Show the evidence and acknowledge unresolved uncertainty. That is a stronger story than merely retrieving more notes.

Memory carries 25%, technical implementation 20%, UX 15%, impact 10%. These are rubric weights, not predicted scores. No claim of guaranteed shortlisting is warranted.

## Implemented corrections

- Load `.env` and pass Hindsight authentication explicitly; pin the inspected SDK version.
- Use actual Hindsight reflection for populated briefs and display returned supporting facts.
- Preserve provider metadata/dates; do not invent scalar scores; use actual stored-fact totals.
- Make empty recall and fresh banks safe, and provider failure visible.
- Protect local JSON writes against concurrent instances and interrupted replacement; do not silently erase corrupt data.
- Deduplicate repeat seeding and unchanged call retries with stable document IDs.
- Validate blank/oversized input, known tones, and unknown deals.
- Prefer recent context, distinguish explicit resolution notes, and require explicitly tagged cross-deal wins.
- Remove invented email commitments and unsupported claim-by-claim citation promises.
- Add a nondestructive baseline comparison; prevent overlapping UI operations, refresh timelines, preserve per-deal drafts, label templates, and expose initialization errors.
- Restrict hosts and reject cross-origin writes for this loopback prototype.

## Still required before submission

- [ ] Configure a real Hindsight instance and run `scripts/verify_hindsight.py`. The local backend does not meet the mandatory technology requirement.
- [ ] Run and record the UI against Hindsight. Live browser validation was unavailable during this review because no browser surface was connected.
- [ ] Review generated content using the real observed demo, not assumed future functionality.
- [ ] Publish the clean repository and verify its URL. This directory had no `.git` repository during the review; a local folder is not a submitted GitHub repository.
- [ ] Record a public 2–5 minute YouTube demo at 1080p minimum. The content guide specifies one team video; the problem statement's wording about individual videos is broader, so clarify with organizers if needed.
- [ ] Every member publishes their own English article and social post. Include project screenshots and required Hindsight links. Do not mention “hackathon” in the article or social post, including hashtags.
- [ ] Article: publish publicly, then share a link post to one of the listed Reddit communities, respecting that community's rules.
- [ ] Social: include the actual project GitHub link in the main post, article link in a comment, and Hindsight GitHub link in a comment. Tag Code.in as requested by the content guide.
- [ ] Each member completes the profile review form.
- [ ] Submit the team's single final entry by 29 September. The supplied announcement does not specify the cutoff time or timezone; verify those with the organizers.

The existing content files are drafts for review, not completed published deliverables. No accounts, public posts, forms, or submissions were changed by this review.
