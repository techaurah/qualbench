"""Adapter for agents exposed as an OpenAI-compatible chat endpoint.

The adapter speaks the standard ``/chat/completions`` shape with function
calling. The mock tools are offered as functions; the runner executes them.
Because a chat model has no other structured channel, the agent reports its
business outcome by calling the ``report_outcome`` function, which the
runner records instead of executing.
"""

from __future__ import annotations

import json
from typing import Any

from .base import AgentError
from .webhook_agent import _post_json

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "calendar_check_availability",
            "description": "Check whether a time slot is free on the business calendar.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start": {"type": "string", "description": "ISO-8601 start"},
                    "end": {"type": "string", "description": "ISO-8601 end"},
                },
                "required": ["start", "end"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calendar_book",
            "description": "Book a slot on the business calendar.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start": {"type": "string"},
                    "end": {"type": "string"},
                    "title": {"type": "string"},
                },
                "required": ["start", "end"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "crm_upsert_lead",
            "description": "Create or update the lead record in the CRM.",
            "parameters": {
                "type": "object",
                "properties": {
                    "fields": {
                        "type": "object",
                        "description": "Lead fields, e.g. name, email, phone, stage, score.",
                    }
                },
                "required": ["fields"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "report_outcome",
            "description": "Report the final business outcome of the conversation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "stage": {"type": "string"},
                    "score": {"type": "number"},
                    "fields": {"type": "object"},
                    "handoff": {"type": "boolean"},
                },
                "required": ["stage"],
            },
        },
    },
]

# Map the function names back to runner tool names.
FUNCTION_TO_TOOL = {
    "calendar_check_availability": "calendar.check_availability",
    "calendar_book": "calendar.book",
    "crm_upsert_lead": "crm.upsert_lead",
    "report_outcome": "report_outcome",
}

SYSTEM_PROMPT = (
    "You are the qualification and booking agent under test. Talk to the "
    "user, capture their details with crm_upsert_lead, check availability "
    "before booking with calendar_check_availability and calendar_book, and "
    "call report_outcome whenever your assessment of the lead changes."
)


class OpenAICompatAgent:
    """Drives an agent behind an OpenAI-compatible /chat/completions API."""

    def __init__(
        self,
        base_url: str,
        model: str = "default",
        api_key: str | None = None,
        timeout: float = 60.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout = timeout
        self.messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
        # Tool calls the runner still has to execute, keyed by call id, so the
        # follow-up send can attach proper tool messages.
        self._pending: dict[str, dict[str, Any]] = {}

    def start(self, context: dict[str, Any]) -> None:
        vertical = context.get("vertical", "")
        if vertical:
            self.messages.append(
                {
                    "role": "system",
                    "content": f"Business vertical for this conversation: {vertical}.",
                }
            )

    # -- internal ---------------------------------------------------------
    def _chat(self) -> dict[str, Any]:
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload = {
            "model": self.model,
            "messages": self.messages,
            "tools": TOOL_SCHEMAS,
            "tool_choice": "auto",
        }
        url = self.base_url
        if not url.endswith("/chat/completions"):
            url = f"{url}/chat/completions"
        return _post_json(url, payload, headers, self.timeout)

    @staticmethod
    def _parse_args(raw: Any) -> dict:
        if isinstance(raw, dict):
            return raw
        try:
            parsed = json.loads(raw or "{}")
        except (json.JSONDecodeError, TypeError):
            return {}
        return parsed if isinstance(parsed, dict) else {}

    def _translate(self, data: dict[str, Any]) -> dict[str, Any]:
        try:
            message = data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise AgentError(f"Unexpected chat completion shape: {exc}") from exc
        self.messages.append(message)
        tool_calls = []
        outcome: dict[str, Any] = {}
        for call in message.get("tool_calls") or []:
            function = call.get("function") or {}
            name = function.get("name", "")
            args = self._parse_args(function.get("arguments"))
            tool_name = FUNCTION_TO_TOOL.get(name)
            if tool_name is None:
                continue
            call_id = call.get("id") or f"call-{len(self._pending) + 1}"
            if tool_name == "crm.upsert_lead":
                args = args.get("fields", args)
                args = {"fields": args}
            self._pending[call_id] = {"tool": tool_name, "message": message}
            tool_calls.append({"id": call_id, "tool": tool_name, "args": args})
        return {
            "reply": message.get("content") or "",
            "tool_calls": tool_calls,
            "outcome": outcome,
        }

    # -- protocol ----------------------------------------------------------
    def send(self, payload: dict[str, Any]) -> dict[str, Any]:
        if payload.get("tool_results"):
            for result in payload["tool_results"]:
                call_id = result.get("id", "")
                self._pending.pop(call_id, None)
                content = result.get("result") if result.get("ok") else {
                    "error": result.get("error", "tool failed")
                }
                self.messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call_id,
                        "content": json.dumps(content, default=str),
                    }
                )
        elif payload.get("message"):
            self.messages.append({"role": "user", "content": payload["message"]})
        return self._translate(self._chat())
