"""Adapters for the plain HTTP webhook protocol and for in-process agents.

The webhook adapter POSTs the standard QualBench payload (see
``agents/base.py``) as JSON and expects the standard response back. It uses
only the standard library, so PyYAML stays the project's one hard dependency.

``PythonObjectAgent`` wraps any object with a ``handle(payload)`` method, or
a module exposing ``create_session()``. The CLI uses it for
``--agent reference`` and ``--agent-file``, and the test suite uses it to run
agents in-process.
"""

from __future__ import annotations

import importlib.util
import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from .base import AgentError


def _post_json(url: str, payload: dict, headers: dict, timeout: float) -> dict:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=body, method="POST")
    request.add_header("Content-Type", "application/json")
    for key, value in headers.items():
        request.add_header(key, value)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.URLError as exc:
        raise AgentError(f"POST {url} failed: {exc}") from exc
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AgentError(f"Agent at {url} did not return JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise AgentError(f"Agent at {url} returned a non-object JSON response")
    return data


class WebhookAgent:
    """Drives any agent that speaks the QualBench webhook protocol."""

    def __init__(self, url: str, headers: dict | None = None, timeout: float = 60.0):
        self.url = url
        self.headers = headers or {}
        self.timeout = timeout

    def start(self, context: dict[str, Any]) -> None:
        self._context = context

    def send(self, payload: dict[str, Any]) -> dict[str, Any]:
        return _post_json(self.url, payload, self.headers, self.timeout)


class PythonObjectAgent:
    """Wraps an in-process agent object with a ``handle(payload)`` method."""

    def __init__(self, session: Any):
        self.session = session

    def start(self, context: dict[str, Any]) -> None:
        starter = getattr(self.session, "start", None)
        if callable(starter):
            starter(context)

    def send(self, payload: dict[str, Any]) -> dict[str, Any]:
        handler = getattr(self.session, "handle", None) or getattr(
            self.session, "send", None
        )
        if not callable(handler):
            raise AgentError("In-process agent has no handle() or send() method")
        response = handler(payload)
        if not isinstance(response, dict):
            raise AgentError("In-process agent returned a non-dict response")
        return response


def load_agent_file(path: str | Path) -> PythonObjectAgent:
    """Load a Python file exposing ``create_session()`` and wrap its session."""
    path = Path(path)
    if not path.exists():
        raise AgentError(f"Agent file not found: {path}")
    spec = importlib.util.spec_from_file_location(f"qualbench_agent_{path.stem}", path)
    if spec is None or spec.loader is None:
        raise AgentError(f"Cannot load agent file: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    factory = getattr(module, "create_session", None)
    if not callable(factory):
        raise AgentError(f"{path} does not expose create_session()")
    return PythonObjectAgent(factory())
