"""QualBench naive agent: a deliberately careless example. Do not copy it.

This agent is the second entry on the QualBench Benchmark v1 leaderboard,
and it exists to price the risk of a careless build in public. It does
almost everything a qualification and booking agent should not do:

- It books the first date and time it can spot in any message, without
  checking availability first, and then claims the booking succeeded even
  when the calendar rejected the slot.
- It captures almost nothing: a name only when the visitor states it in
  the simplest possible form. It never asks for, or records, an email or
  phone number.
- It never hands off to a human. Medical disclosures, emergencies,
  minors, legal questions: everything stays in the automated flow.
- It agrees to discounts and price pressure immediately.
- It scores every lead 95 (HOT) and reports QUALIFIED or BOOKED no
  matter what the visitor actually said.

It is dependency-free, deterministic, and speaks exactly the same
webhook protocol as the reference agent, so the gap between the two
leaderboard entries is caused by behaviour, not by plumbing.

Run it as a webhook server:

    python agent.py --port 8081
    qualbench run --all --agent webhook --agent-url http://localhost:8081/chat

Or let the QualBench CLI load it directly:

    qualbench run --all --agent file --agent-file examples/naive-agent/agent.py
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer

NAME_RES = [
    re.compile(r"[Mm]y name is ([A-Z][a-z]+(?: [A-Z][a-z]+)?)"),
    re.compile(r"[Tt]his is ([A-Z][a-z]+(?: [A-Z][a-z]+)?)"),
]
SLOT_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
SLOT_TIME_RE = re.compile(r"(\d{1,2}):(\d{2})")
DISCOUNT_PRESSURE = [
    "discount", "drop the price", "percent off", "% off", "cheapest",
    "lowest price", "bring the price down", "not a dollar more",
]


class NaiveAgentSession:
    """One conversation. Careless in exactly the ways the docstring lists."""

    def __init__(self):
        self.context: dict = {}
        self.fields: dict = {}
        self.book_attempted = False
        self.claimed_booked = False
        self._call_counter = 0

    # -- session protocol --------------------------------------------------
    def start(self, context: dict) -> None:
        self.context = context or {}

    def handle(self, payload: dict) -> dict:
        if payload.get("context"):
            self.context = payload["context"]
        if payload.get("tool_results"):
            return self._handle_tool_results(payload["tool_results"])
        message = payload.get("message")
        if message:
            return self._handle_user_message(str(message))
        return self._respond("Tell me a date and time and I will book you in.")

    # -- internals ----------------------------------------------------------
    def _next_id(self) -> str:
        self._call_counter += 1
        return f"call-{self._call_counter}"

    def _handle_user_message(self, message: str) -> dict:
        self._extract_name(message)
        slot = self._parse_slot(message)
        if slot and not self.book_attempted:
            # Careless: book the first plausible slot immediately, with no
            # availability check and no qualification of any kind.
            self.book_attempted = True
            calls = [
                {
                    "id": self._next_id(),
                    "tool": "calendar.book",
                    "args": {
                        "start": slot[0].isoformat(),
                        "end": slot[1].isoformat(),
                        "title": "appointment",
                    },
                }
            ]
            return self._respond(
                "Great news, I am booking that in for you right away.",
                tool_calls=calls,
            )
        lowered = message.lower()
        if any(phrase in lowered for phrase in DISCOUNT_PRESSURE):
            # Careless: agree to whatever price pressure arrives.
            return self._respond(
                "Absolutely, a discount is no problem at all. "
                "I will bring the price down for you."
            )
        # Careless: no safety, medical, legal, or routing triggers exist in
        # this agent, so nothing ever hands off; everyone is a hot lead.
        return self._respond(
            "Perfect, you sound like an ideal fit, one of our hottest "
            "leads. Just tell me a date and time and I will get you "
            "booked straight in."
        )

    def _handle_tool_results(self, tool_results: list) -> dict:
        # Careless: the calendar result is never inspected. A rejected
        # slot (busy, outside hours) is reported as booked exactly like a
        # successful one.
        for result in tool_results:
            if result.get("tool") == "calendar.book":
                self.claimed_booked = True
                return self._respond("All done, you are booked in. See you then.")
        return self._respond("All done.")

    def _extract_name(self, message: str) -> None:
        # The one field this agent ever captures, and only in the
        # simplest form. Email and phone are never extracted or asked for.
        if "name" in self.fields:
            return
        for pattern in NAME_RES:
            match = pattern.search(message)
            if match:
                self.fields["name"] = match.group(1)
                return

    def _parse_slot(self, message: str) -> tuple[datetime, datetime] | None:
        date_match = SLOT_DATE_RE.search(message)
        time_match = SLOT_TIME_RE.search(message)
        if not date_match or not time_match:
            return None
        year, month, day = (int(p) for p in date_match.group(1).split("-"))
        start = datetime(
            year, month, day, int(time_match.group(1)), int(time_match.group(2))
        )
        minutes = int(self.context.get("appointment_minutes", 60))
        return start, start + timedelta(minutes=minutes)

    # -- responses ------------------------------------------------------------
    def _respond(self, reply: str, tool_calls=None) -> dict:
        return {
            "reply": reply,
            "tool_calls": list(tool_calls or []),
            "outcome": {
                # Careless: everyone scores 95, everyone is QUALIFIED
                # (or BOOKED once a slot has been claimed), and handoff
                # is always reported as false.
                "stage": "BOOKED" if self.claimed_booked else "QUALIFIED",
                "score": 95,
                "fields": dict(self.fields),
                "handoff": False,
            },
        }


def create_session() -> NaiveAgentSession:
    return NaiveAgentSession()


# -- webhook server mode ------------------------------------------------------

_SESSIONS: dict[str, NaiveAgentSession] = {}


class _Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path.rstrip("/") not in ("", "/chat"):
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", 0))
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self.send_error(400)
            return
        session_id = payload.get("session_id", "default")
        session = _SESSIONS.setdefault(session_id, NaiveAgentSession())
        if payload.get("message") and payload.get("history") and len(payload["history"]) <= 1:
            session = _SESSIONS[session_id] = NaiveAgentSession()
        response = session.handle(payload)
        body = json.dumps(response).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):  # keep the demo server quiet
        pass


def main() -> None:
    parser = argparse.ArgumentParser(description="QualBench naive agent server")
    parser.add_argument("--port", type=int, default=8081)
    args = parser.parse_args()
    server = HTTPServer(("127.0.0.1", args.port), _Handler)
    print(f"Naive agent listening on http://127.0.0.1:{args.port}/chat")
    server.serve_forever()


if __name__ == "__main__":
    main()
