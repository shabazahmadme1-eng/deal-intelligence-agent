# Deal Intelligence Agent

A sales assistant that retains call notes, recalls deal history, and prepares pre-call briefs, follow-up drafts, and suggestions based on recorded wins from other deals.

**Current status:** a single-team local prototype. The default backend is an offline simulation, not Hindsight. Enable and verify real Hindsight before demonstrating it as a Hindsight-powered project. Sample companies, people, and metrics are synthetic.

## Run on Windows

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000. Load demo data, select Meridian, and click **Compare without memory**. This shows both responses without deleting stored notes. Select Kaveri and suggest tactics to see the recorded Meridian pilot outcome used as a candidate tactic. These are hypotheses to evaluate, not proof that a tactic will work for another customer.

`.env` is loaded from the project root; existing shell variables take precedence. Restart the server after changing settings. Local JSON files live in `data/` and are excluded from Git. Local writes use file locking and atomic replacement; malformed files fail visibly instead of silently losing data.

## Enable Hindsight

Set these values in `.env` (never commit the key):

```dotenv
MEMORY_BACKEND=hindsight
HINDSIGHT_BASE_URL=https://YOUR-INSTANCE-URL
HINDSIGHT_API_KEY=YOUR-API-KEY
HINDSIGHT_BANK_PREFIX=your-team-deal-
```

For a self-hosted instance, use its base URL, such as `http://localhost:8888`; authentication depends on its configuration. See the [official Python SDK documentation](https://hindsight.vectorize.io/sdks/python).

Run an actual provider check after configuring the instance:

```powershell
.\.venv\Scripts\python.exe scripts/verify_hindsight.py
```

This stores synthetic test data in a uniquely named verification bank, creates a second client to check persistence, and invokes recall and reflection. It consumes provider resources and leaves the verification bank for inspection. SDK contract tests alone do not prove that a server is working.

Hindsight performs its own generation for pre-call reflection. Optional `GROQ_API_KEY` and `GROQ_MODEL` settings enable generated follow-ups/tactics and baseline briefs. Without Groq, those outputs use labeled templates. Provider failures during Hindsight operations produce an error; the app does not silently replace Hindsight with local memory.

## Memory workflow

| Operation | Behavior |
|---|---|
| Retain | Split call notes into tagged source statements, with stable document IDs for retries. Hindsight extracts its own facts. |
| Recall | Retrieve evidence within the selected deal's bank. Include recent stored context in briefs. |
| Reflect | Hindsight generates a brief and returns supporting facts via `include_facts=True`. |
| Cross-deal suggestions | Retrieve explicitly recorded win patterns from other deals in this team's store. |
| Timeline / counts | List stored facts and read the provider's actual total, rather than pretending a search result count is a total. |

The local backend offers keyword retrieval and templates, not semantic memory or model learning. Stored evidence is visible but is not a claim-by-claim citation guarantee. Hindsight timestamps and metadata are preserved when supplied; absent scores/dates are not invented.

## Architecture

```text
Browser -> FastAPI -> agent.py -> memory.py -> Hindsight service
                          |          +-----> Local JSON simulation
                          +------> llm.py -> optional Groq / templates
```

`app/deals.py` contains the synthetic sample history. Demo seeding uses stable call IDs, so retries replay the prior receipt without touching the provider. Regular call logging uses a per-submission ID retained by the browser until success. A partially failed call may have saved some statements; retry the unchanged call to complete it. Resubmitting an ID with changed text returns HTTP 409; corrections are new calls linked with `supersedes_call_id`, and the earlier version is preserved. Hindsight SDK clients are created per operation and closed immediately — no client is shared across request threads.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts/seed_demo.py
.\.venv\Scripts\python.exe scripts/objection_lifecycle_demo.py
```

The terminal demos always use isolated temporary local memory. They are not Hindsight integration tests. Tests cover bank isolation, persistence and concurrent writes, provider response shapes, reflection invocation, API validation, duplicate seeding, retry handling, latest-call context, misleading win prevention, cross-thread client ownership, conflict/correction handling, provider-independent baselines, and cross-bank merge fairness.

## Limits and next work

- No login, tenant isolation, CRM integration, or production deployment. Keep the server on loopback. Cross-deal memory is intentional within the sample team only.
- Sentence tagging is heuristic; templates show objection history and progress without claiming automatic resolution of all contradictions. Review generated drafts before use.
- Timeline shows at most 100 stored facts. Long histories need pagination and stronger relevance/recency evaluation.
- Source text can contain malicious instructions; generation is instructed to treat it as data, but this is not a complete prompt-injection defense.
- The UI reports configured mode and actual generation path. It does not certify successful provider access until an operation succeeds.

See [docs/project-review.md](docs/project-review.md) for the assessment and outstanding submission requirements, and [demo_script.md](demo_script.md) for a nondestructive walkthrough.
