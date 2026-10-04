"""
JARVIS Planning & Intent Classification Engine
Decodes user goals into structured action hierarchies with verification constraints.
"""

import re
from typing import Dict, Any, Optional
from backend.providers.base import LLMProvider, PlanResult, PlanStep


class IntentClassifier:
    """Fast local intent classification with heuristic accelerators."""

    @staticmethod
    def classify(prompt: str) -> str:
        p_lower = prompt.lower().strip()

        # Remember / Memory command
        if p_lower.startswith(("remember that", "remember:", "remember ", "note down", "keep in mind")):
            return "REMEMBER_FACT"

        # Screen vision query
        if any(phrase in p_lower for phrase in ("what am i looking at", "look at my screen", "inspect my screen", "what's on my screen", "analyze screen")):
            return "SCREEN_QUERY"

        # Briefing
        if "morning briefing" in p_lower or "daily briefing" in p_lower:
            return "MORNING_BRIEFING"

        # Project switching / status
        if p_lower.startswith(("switch to ", "open the ")) and "project" in p_lower:
            return "PROJECT_SWITCH"

        # Schedule / Reminder
        if p_lower.startswith(("remind me ", "set a reminder", "schedule task")):
            return "ACTIONABLE_COMMAND"

        # Apps & System control (open, launch, start, close, quit)
        if any(w in p_lower for w in ("open app", "launch app", "open ", "launch ", "close app", "quit app", "close ")):
            return "ACTIONABLE_COMMAND"

        # Meetings & Calendar (schedule, fix meeting, calendar event, meet)
        if any(w in p_lower for w in ("meeting", "schedule", "calendar", "appointment", "fix a meeting", "create meeting", "set a meeting")):
            return "ACTIONABLE_COMMAND"

        # Timers & Alarms
        if any(w in p_lower for w in ("timer", "alarm", "countdown")):
            return "ACTIONABLE_COMMAND"

        # Communications (email, message, text, sms, mail)
        if any(w in p_lower for w in ("send email", "send an email", "send message", "send a message", "email to", "mail to", "message to", "text to", "imessage")):
            return "ACTIONABLE_COMMAND"

        # Coding / Terminal / Engineering / Filesystem
        if any(w in p_lower for w in ("create", "build", "run", "fix", "test", "inspect", "compile", "install", "refactor", "commit", "delete", "write", "list files", "show files", "execute")):
            return "ENGINEERING_ACTION"

        # Imperative action verbs starting sentence
        first_word = p_lower.split()[0] if p_lower.split() else ""
        if first_word in ("open", "launch", "start", "close", "quit", "set", "send", "fix", "schedule", "create", "make", "show", "list", "run"):
            return "ACTIONABLE_COMMAND"

        return "GENERAL_CONVERSATION"


class Planner:
    def __init__(self, provider: LLMProvider):
        self.provider = provider

    async def create_plan(
        self,
        goal: str,
        context: Optional[str] = None,
        available_tools: Optional[list] = None
    ) -> PlanResult:
        """Formulate a structured execution plan. Uses fast local rules first to conserve API quota."""
        # Fast local heuristic check for routine system commands (zero API token cost)
        try:
            from backend.providers.mock import MockProvider
            local_mock = MockProvider()
            fast_plan = await local_mock.plan(goal, context=context, available_tools=available_tools)
            if fast_plan.intent in ("app_control", "meeting_scheduling", "timer", "communication") and fast_plan.steps:
                return fast_plan
        except Exception:
            pass

        return await self.provider.plan(goal, context=context, available_tools=available_tools)

