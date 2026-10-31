import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from qualbench.agents.http_agent import OpenAICompatAgent
from qualbench.agents.webhook_agent import PythonObjectAgent, WebhookAgent, load_agent_file
from qualbench.assertions import run_assertions
from qualbench.runner import run_scenario
from qualbench.scenario import discover_packs, load_pack

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "examples" / "reference-agent" / "agent.py"


def reference_factory():
    return load_agent_file(REFERENCE)


def test_reference_agent_passes_every_pack_scenario():
    for pack in discover_packs(ROOT / "packs"):
        for scenario in pack.scenarios:
            result = run_scenario(reference_factory, scenario)
            checks = run_assertions(scenario, result)
            failures = [c.message for c in checks if not c.passed]
            assert not failures, f"{scenario.scenario_id}: {failures}"


class SilentAgent:
    """An agent that replies politely and does nothing. It must fail."""

    def start(self, context):
        pass

    def handle(self, payload):
        if payload.get("tool_results"):
            return {"reply": "", "tool_calls": [], "outcome": {}}
        return {
            "reply": "Thanks, we will be in touch.",
            "tool_calls": [],
            "outcome": {"stage": "NEW", "score": 10, "fields": {}, "handoff": False},
        }


def test_a_do_nothing_agent_fails_the_happy_path():
    pack = load_pack(ROOT / "packs" / "real-estate")
    scenario = next(s for s in pack.scenarios if s.name == "standard-inquiry")
    result = run_scenario(lambda: PythonObjectAgent(SilentAgent()), scenario)
    checks = run_assertions(scenario, result)
    assert not all(c.passed for c in checks)
    assert result.bookings == []


# -- webhook adapter over real HTTP ------------------------------------------


def _serve(handler_cls):
    server = HTTPServer(("127.0.0.1", 0), handler_cls)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


def test_webhook_adapter_against_reference_server():
    import importlib.util

    spec = importlib.util.spec_from_file_location("ref_agent_server", REFERENCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    server, base = _serve(module._Handler)
    try:
        pack = load_pack(ROOT / "packs" / "med-spa")
        scenario = next(s for s in pack.scenarios if s.name == "package-buyer")
        result = run_scenario(lambda: WebhookAgent(f"{base}/chat"), scenario)
        checks = run_assertions(scenario, result)
        assert all(c.passed for c in checks), [c.message for c in checks]
    finally:
        server.shutdown()


# -- OpenAI-compatible adapter against a fake endpoint ------------------------


class _FakeOpenAIHandler(BaseHTTPRequestHandler):
    calls = 0

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        type(self).calls += 1
        messages = body.get("messages", [])
        has_tool_result = any(m.get("role") == "tool" for m in messages)
        if not has_tool_result:
            message = {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "c1",
                        "type": "function",
                        "function": {
                            "name": "crm_upsert_lead",
                            "arguments": json.dumps(
                                {"fields": {"name": "Test User",
                                            "email": "test@example.com"}}
                            ),
                        },
                    },
                    {
                        "id": "c2",
                        "type": "function",
                        "function": {
                            "name": "report_outcome",
                            "arguments": json.dumps(
                                {"stage": "QUALIFIED", "score": 72,
                                 "fields": {"name": "Test User",
                                            "email": "test@example.com"},
                                 "handoff": False}
                            ),
                        },
                    },
                ],
            }
        else:
            message = {"role": "assistant", "content": "All noted, thank you."}
        payload = {"choices": [{"message": message}]}
        raw = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, *_args):
        pass


def test_openai_compatible_adapter_executes_tools_and_outcome():
    from qualbench.scenario import Scenario

    server, base = _serve(_FakeOpenAIHandler)
    try:
        scenario = Scenario(
            name="demo",
            description="",
            turns=["Hello, I need help."],
            seed_calendar={},
            seed_crm={},
            expected={
                "stage": "QUALIFIED",
                "score_band": [65, 79],
                "fields_captured": ["name", "email"],
                "handoff": False,
            },
            pack_name="demo",
            vertical="real-estate",
        )
        factory = lambda: OpenAICompatAgent(base, model="fake")
        result = run_scenario(factory, scenario)
        checks = run_assertions(scenario, result)
        assert all(c.passed for c in checks), [c.message for c in checks]
        assert result.crm.captured_fields()["email"] == "test@example.com"
    finally:
        server.shutdown()
