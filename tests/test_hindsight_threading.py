"""P0 regression: the Hindsight SDK client must never be shared across threads.

The generated transport keeps one asyncio session bound to its creating loop,
so a long-lived client touched from a second worker thread raises
`RuntimeError: Timeout context manager should be used inside a task`.
The adapter therefore builds a fresh client per operation and closes it.
"""
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import Mock

import pytest

from app.memory import HindsightMemory


class _FixtureHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        assert self.path.startswith("/v1/default/banks/")
        body = json.dumps({"total": 0, "items": [], "limit": 1, "offset": 0}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


@pytest.fixture
def fixture_url():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _FixtureHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


def test_concurrent_operations_use_separate_closed_clients(monkeypatch):
    made = []
    real_new_client = HindsightMemory._new_client

    def counting_new_client(self):
        mock = Mock()
        mock.list_memories.return_value = Mock(total=0, items=[])
        made.append(mock)
        return mock

    monkeypatch.setattr(HindsightMemory, "_new_client", counting_new_client)
    memory = HindsightMemory.__new__(HindsightMemory)  # skip __init__; client factory is patched
    with ThreadPoolExecutor(max_workers=8) as pool:
        assert list(pool.map(lambda _: memory.count("deal-x"), range(8))) == [0] * 8
    assert len(made) == 8  # one client per operation, never shared
    assert all(m.close.call_count == 1 for m in made)  # and every client is closed


def test_real_client_survives_concurrent_threads(fixture_url):
    """True regression test: fails against a shared client (probe-verified
    RuntimeError), passes with per-operation clients."""
    memory = HindsightMemory(base_url=fixture_url)
    with ThreadPoolExecutor(max_workers=4) as pool:
        counts = list(pool.map(lambda _: memory.count("deal-x"), range(8)))
        listed = list(pool.map(lambda _: memory.list_memories("deal-x"), range(4)))
    assert counts == [0] * 8
    assert listed == [[]] * 4
