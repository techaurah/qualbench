"""Agent adapters: how the runner talks to the agent under test."""

from .base import AgentError, AgentSession
from .http_agent import OpenAICompatAgent
from .webhook_agent import PythonObjectAgent, WebhookAgent

__all__ = [
    "AgentError",
    "AgentSession",
    "OpenAICompatAgent",
    "PythonObjectAgent",
    "WebhookAgent",
]
