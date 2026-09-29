# Hindsight integration research

Reviewed 29 September 2026. Scope: `app/memory.py`, `app/agent.py`, `app/main.py`, installed `hindsight-client==0.10.1`, and first-party documentation/source. This is a design review, not a live cloud integration certification. No implementation changes were made for this report.

## Recommendation

Keep FastAPI, the plain browser UI, and Hindsight. The urgent work is a reliable memory boundary, not an agent-framework rewrite. Demonstrate one deal across successive calls, including an objection becoming resolved, and show the actual reflection evidence. Keep per-deal banks for this deadline; revisit organization-wide retrieval after the demo works.

## Findings

### 1. The global synchronous client has an event-loop ownership risk

The installed SDK's `_run_async` obtains or creates the calling thread's event loop and invokes `run_until_complete`. Its generated REST client lazily creates and retains one `aiohttp.ClientSession`. `app/main.py` creates one global memory adapter, then invokes it from synchronous route handlers. FastAPI executes ordinary `def` handlers in an external thread pool. Therefore separate workers can use the same session from different loops. [SDK v0.10.1](https://raw.githubusercontent.com/vectorize-io/hindsight/v0.10.1/hindsight-clients/python/hindsight_client/hindsight_client.py), [FastAPI concurrency](https://fastapi.tiangolo.com/async/), [aiohttp loop ownership FAQ](https://docs.aiohttp.org/en/stable/faq.html#why-is-creating-a-clientsession-outside-of-an-event-loop-dangerous).

The coordinating review reproduced this using the installed client and an isolated local `ThreadingHTTPServer`, without cloud access: one shared Hindsight instance successfully listed an empty bank from its owning thread; a second distinct thread then raised `RuntimeError: Timeout context manager should be used inside a task`. The first loop was kept alive and the client closed in its owning thread. This confirms cross-thread transport incompatibility, not that every request fails; reuse within one worker can appear healthy.

The local evidence is `.venv/Lib/site-packages/hindsight_client_api/rest.py`, especially `_ensure_session`. There is also no application shutdown cleanup, although the SDK provides `close()` and `aclose()`. Give the adapter a consistent client/loop lifetime. A dedicated execution thread owning one client is compatible with the present synchronous domain code; an application-lifespan async client is a larger alternative. Simply adding a lock does not establish loop ownership.

### 2. Stable document IDs mean replacement, not silently ignoring edits

Official retain documentation describes a bank-scoped document upsert; omitting the ID permits duplicate documents. Local `retain` instead returns immediately whenever the ID exists, even when content changes. This hides corrected-content bugs during offline tests. [Retain API](https://hindsight.vectorize.io/developer/api/retain).

Do not overstate the documentation's simplified “delete/reprocess” description as a guarantee of fresh extraction on identical retries. The tagged v0.10.1 orchestrator classifies unchanged/changed/new/removed chunks. Its delta path preserves unchanged content and can perform metadata-only updates when every chunk matches; its streaming path also has matching-hash recovery. Changed content is not generally ignored. Whether a particular deployment takes the optimized path depends on server implementation/configuration. [v0.10.1 retain orchestrator, delta and recovery code](https://raw.githubusercontent.com/vectorize-io/hindsight/v0.10.1/hindsight-api-slim/hindsight_api/engine/retain/orchestrator.py).

Project consequence: `call_id-index` identifies sentences by position. Retrying a shortened or edited call can leave obsolete trailing documents remotely; locally even retained positions keep old text. Prefer one stable document per complete call, with explicitly defined update semantics. Test identical retries, changed content, shorter edits, and a failure followed by retry.

### 3. Retain complete calls to preserve meaning

Hindsight extracts facts from supplied content and supports full conversation documents; the server already chunks documents and can return source chunks on recall. [Document API](https://hindsight.vectorize.io/developer/api/documents).

The project's regex splits “The CTO rejected the price. She accepted it after the pilot.” into isolated extraction requests. My inference: this loses local pronoun/causal context and multiplies remote calls. Retain notes plus outcome together, with a call timestamp and source metadata. Let the local mock present sentence-like display entries if useful, but do not require the real backend to use that storage representation. Batch independent complete calls for seeding; batch transport alone does not repair disconnected sentence context. Preserve explicit win annotations separately or in call metadata so the existing tactics filter remains meaningful.

### 4. Async submission is not ingestion completion

Current operations documentation defines `pending`, `processing`, `completed`, `failed`, and `cancelled`. An accepted asynchronous retain returns an operation identifier; the application must poll or otherwise observe terminal status before claiming the memories are ready. Caller-supplied async operation IDs enable safe resubmission after a lost acknowledgement. The installed client explicitly warns that this identifier is ignored for synchronous retain. [Operations](https://hindsight.vectorize.io/developer/api/operations), [Retain source documentation](https://github.com/vectorize-io/hindsight/blob/main/hindsight-docs/docs/developer/api/retain.mdx).

The current adapter deliberately uses `retain_async=False`; keep that honest completed-write contract for a small demo. Switching a boolean to async without representing operation state would be a regression. A timeout can still mean an unknown remote outcome, so replay the same document identity and inspect the result.

### 5. Reflect already retrieves; preserve its actual evidence

Reflect runs its own retrieval loop. `include_facts=True` returns `based_on` sources, including memories and potentially mental models/directives. The project correctly replaces preliminary recall hits with returned memory evidence, but omits the other source categories. Its four preliminary recalls plus list call add latency and inject selected facts into a prompt before a second retrieval process. [Reflect API](https://hindsight.vectorize.io/developer/api/reflect).

For Hindsight, pass deal context and the desired briefing task directly to reflect, retaining its returned evidence. Keep explicit retrieval for the local/template path. Do not gate reflection on whether an unrelated preliminary selection was nonempty. Installed `ReflectFact` includes ID, text, type, context, and event times, but no document ID or application `kind` metadata; design evidence rendering around that actual schema instead of assuming recall and reflection payloads are interchangeable.

### 6. Memory lists are pages of facts, not a complete call history

Current Cloud documentation defines `limit`/`offset`, a total, and default descending `mentioned_at` then `created_at` ordering. Explicit time-window axes can change ordering. The installed SDK exposes pagination and time-field parameters. [List memory units](https://docs.hindsight.vectorize.io/api-reference/list-memories/).

The adapter requests only a single page of 100. Sorting that page by `occurred_start` locally cannot recover excluded facts. Worse, the UI's single timestamp combines an event date with mention time, which obscures when a new report revised older information. Keep event time and recorded time distinct. Label bounded lists honestly, expose pagination when required, and use call records as the source of a genuine call timeline. Counts of local sentences and Hindsight extracted facts are not semantically equal.

### 7. Bank isolation is reasonable; cross-bank ranking is not

Recall searches a specified bank and produces a ranked list using multiple retrieval strategies. Tags can scope data within a bank, but default inclusive modes also include untagged/global data; strict modes are needed when that is inappropriate. [Recall API](https://hindsight.vectorize.io/developer/api/recall).

Per-deal banks fit the current demo. The project deliberately fans out across banks for tactics, then assigns every Hindsight hit `score=None`; sorting those as zero means the first banks dominate the final limit. It is not a global relevance ranking. Use bounded per-bank candidates with a fair merge or explicit secondary ranking. For growth, consider one organization bank with deal tags and enforced access policy, or a separate curated win-pattern bank. That is a future architecture decision, not a deadline prerequisite. Metadata `kind` currently is application annotation, not a Hindsight tag or an access-control rule.

## Version and verification boundaries

Installed package metadata confirms 0.10.1. Tagged 0.10.1 SDK/server sources are linked where inspected; unversioned official pages and `main` documentation describe current behavior, not proof of the configured server version. The actual remote server version, credentials, enabled optimizations, latency, retention outcomes, and evidence fidelity still require a real integration run. Do not infer these from local tests.

Deadline order: fix client ownership; use a coherent complete-call retain contract; simplify real reflection; run real retain/recall/reflect checks; then record the three-call objection-resolution demo. Defer async job UI, bank migration, and framework changes.
