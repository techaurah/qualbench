"""The agent session protocol shared by every adapter.

One payload goes in, one response comes out. The runner owns the mock tools;
the agent only *requests* tool calls and reports its outcome.

Request payload::

    {
      "session_id": "real-estate/standard-inquiry",
      "message": "user text, or null when delivering tool results",
      "history": [{"role": "user" | "agent", "content": "..."}],
      "context": {"pack": "real-estate", "vertical": "real-estate",
                  "appointment_minutes": 60},
      "tool_results": [{"id": "call-1", "tool": "calendar.book",
                        "ok": true, "result": {...}}]   # optional
    }

Response::

    {
      "reply": "text shown to the user",
      "tool_calls": [{"id": "call-1", "tool": "calendar.check_availability",
                      "args": {"start": "...", "end": "..."}}],
      "outcome": {"stage": "BOOKED", "score": 92,
                  "fields": {"name": "...", "email": "..."},
                  "handoff": false}
    }

Tools the runner executes: ``calendar.check_availability``,
``calendar.book``, ``crm.upsert_lead``, ``crm.get_lead`` and
``report_outcome`` (OpenAI-compatible adapter only; webhook agents return
the outcome inline instead).
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


class AgentError(RuntimeError):
    """Raised when an agent cannot be reached or returns garbage."""


@runtime_checkable
class AgentSession(Protocol):
    def start(self, context: dict[str, Any]) -> None:
        """Called once before the first user turn."""
        ...

    def send(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Send one payload (user message or tool results), return a response."""
        ...
