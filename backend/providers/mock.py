"""
JARVIS Mock LLM Provider
Deterministic, zero-cost high-fidelity provider for offline execution,
unit tests, preflight checks, and demonstrations without API keys.
"""

import json
import re
from typing import List, Dict, Any, Optional, Type
from pydantic import BaseModel
from .base import LLMProvider, PlanResult, PlanStep


class MockProvider(LLMProvider):
    """High-fidelity local mock provider honoring the JARVIS personality and structure."""
    
    def __init__(self, model_name: str = "mock-jarvis-v1"):
        self.model_name = model_name

    def get_model_name(self) -> str:
        return self.model_name

    def is_configured(self) -> bool:
        return True

    async def chat(
        self,
        messages: List[Dict[str, str]],
        system_instruction: Optional[str] = None,
        temperature: float = 0.7
    ) -> str:
        last_message = messages[-1]["content"] if messages else ""
        lower = last_message.lower()

        if any(w in lower for w in ("hello", "hi", "hey", "who are you", "who made you")):
            return "Good day, Sir. All systems are operational. I am JARVIS, your personal autonomous AI operating layer. I am currently running with the local offline engine. Add your GEMINI_API_KEY to .env to unlock full Gemini 2.5 Flash intelligence."


        if any(w in lower for w in ("status", "subsystems", "health", "metrics")):
            return "All local subsystems are green, Sir. Security boundaries active (Level 0-3), persistent memory store synchronized, tools ready. Currently in offline mode awaiting GEMINI_API_KEY."

        if any(w in lower for w in ("help", "what can you do", "commands", "features")):
            return "Sir, I can execute terminal commands, manage workspace files, capture screen vision, build projects, and store long-term memories. To enable autonomous reasoning and open conversation, configure your GEMINI_API_KEY in .env."

        if "thank" in lower:
            return "Always at your service, Sir."

        return (
            f"Sir, I received your instruction: '{last_message.strip()}'.\n\n"
            "However, all configured Gemini keys have reached their quota limits.\n"
            "Remember, Sir: you already lost Krishna... don't lose JARVIS too. Please top up credits or add a fresh API key in .env to restore dynamic reasoning."
        )


    async def plan(
        self,
        goal: str,
        context: Optional[str] = None,
        available_tools: Optional[List[Dict[str, Any]]] = None
    ) -> PlanResult:
        # Clean goal if forwarded from structured prompt wrapper
        actual_goal = goal
        if "User Goal:" in goal:
            actual_goal = goal.split("User Goal:")[1].split("\n")[0].strip()
        g_lower = actual_goal.lower()
        words = re.findall(r'\b[a-zA-Z0-9_-]+\b', g_lower)

        # 1. App Control (open application, launch app, close app)
        is_close = any(w in ("close", "quit", "exit", "terminate", "kill", "stop") for w in words)
        is_open = any(w in ("open", "launch", "start") for w in words)

        if (is_open or is_close) and not any(w in g_lower for w in ("project file", "issue", "meeting", "calendar", "mail to", "message to")):
            target = "Calculator"
            for candidate in ("calculator", "calendar", "safari", "chrome", "notes", "clock", "spotify", "mail", "messages", "terminal"):
                if candidate in g_lower:
                    target = candidate.capitalize()
                    break
            # If explicit name given after open/launch/close/quit
            for i, w in enumerate(words):
                if w in ("open", "launch", "start", "close", "quit") and i + 1 < len(words):
                    next_w = words[i + 1]
                    if next_w in ("the", "a", "an", "app", "application") and i + 2 < len(words):
                        target = words[i + 2].capitalize()
                        break
                    elif next_w not in ("the", "a", "an", "app", "application"):
                        target = next_w.capitalize()
                        break

            action = "close_app" if is_close and not is_open else "open_app"
            steps = [
                PlanStep(
                    step_id=1,
                    title=f"{'Close' if action == 'close_app' else 'Launch'} {target}",
                    tool_name="app_control",
                    action=action,
                    parameters={"app_name": target},
                    expected_outcome=f"Application {target} {'closed' if action == 'close_app' else 'launched'}",
                    risk_level=1
                )
            ]
            return PlanResult(
                goal=actual_goal,
                intent="app_control",
                requires_tools=True,
                summary=f"Managing macOS application: {target}.",
                steps=steps,
                verification_criteria=f"Application {target} state updated."
            )

        # 2. Meeting & Calendar Scheduling
        if any(w in ("meeting", "schedule", "calendar", "appointment") for w in words) or "fix a meeting" in g_lower:
            date_val = "Tomorrow"
            time_val = "10:00 AM"
            if "tomorrow" in g_lower:
                date_val = "Tomorrow"
            elif "today" in g_lower:
                date_val = "Today"
            elif "next week" in g_lower:
                date_val = "Next Week"
            
            time_match = re.search(r'\b(\d{1,2}(?::\d{2})?\s*(?:am|pm))\b', g_lower)
            if time_match:
                time_val = time_match.group(1).upper()

            steps = [
                PlanStep(
                    step_id=1,
                    title="Generate meeting credentials and schedule calendar event",
                    tool_name="meeting_scheduler",
                    action="create_meeting",
                    parameters={"title": actual_goal, "date": date_val, "time": time_val, "duration_minutes": 30},
                    expected_outcome="Meeting ID and Google Meet link generated and added to macOS Calendar",
                    risk_level=1
                )
            ]
            return PlanResult(
                goal=actual_goal,
                intent="meeting_scheduling",
                requires_tools=True,
                summary="Scheduling meeting, generating meeting ID and URL, and updating calendar.",
                steps=steps,
                verification_criteria="Meeting link generated and calendar event created."
            )

        # 3. Timer & Alarms
        if any(w in ("timer", "alarm", "countdown") for w in words):
            minutes_val = 10
            min_match = re.search(r'(\d+)\s*(?:min|minute)', g_lower)
            sec_match = re.search(r'(\d+)\s*(?:sec|second)', g_lower)
            if min_match:
                minutes_val = int(min_match.group(1))
            elif sec_match:
                minutes_val = max(1, int(sec_match.group(1)) // 60)

            steps = [
                PlanStep(
                    step_id=1,
                    title="Set system timer",
                    tool_name="meeting_scheduler",
                    action="set_timer",
                    parameters={"minutes": minutes_val, "label": actual_goal},
                    expected_outcome="Timer initialized and system alert scheduled",
                    risk_level=1
                )
            ]
            return PlanResult(
                goal=actual_goal,
                intent="timer",
                requires_tools=True,
                summary=f"Setting {minutes_val}-minute countdown timer on macOS.",
                steps=steps,
                verification_criteria="Timer running in scheduler."
            )

        # 4. Communication (Email & Message)
        if any(w in ("email", "mail", "message", "sms", "text", "imessage") for w in words):
            is_email = any(w in ("email", "mail") for w in words)
            action = "send_email" if is_email else "send_message"
            
            to_val = "recipient@example.com"
            email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', g_lower)
            if email_match:
                to_val = email_match.group(0)
            elif " to " in g_lower:
                after_to = g_lower.split(" to ")[1].split()[0]
                to_val = after_to

            subject_val = "Notification from JARVIS"
            subj_match = re.search(r'subject\s+([^,]+)', actual_goal, re.IGNORECASE)
            if subj_match:
                subject_val = subj_match.group(1).strip()

            params = {
                "to": to_val,
                "subject": subject_val,
                "body": actual_goal,
                "message": actual_goal
            }
            steps = [
                PlanStep(
                    step_id=1,
                    title=f"Prepare and dispatch {'email' if action == 'send_email' else 'message'}",
                    tool_name="communication",
                    action=action,
                    parameters=params,
                    expected_outcome=f"{'Email' if action == 'send_email' else 'Message'} prepared and opened in macOS client",
                    risk_level=1
                )
            ]
            return PlanResult(
                goal=actual_goal,
                intent="communication",
                requires_tools=True,
                summary=f"Dispatching {'email' if action == 'send_email' else 'message'} via macOS client.",
                steps=steps,
                verification_criteria="Client opened with draft/message."
            )

        # 5. Project Creation / Coding Request
        if any(w in g_lower for w in ("create", "react", "app", "nova", "build", "frontend")):
            steps = [
                PlanStep(
                    step_id=1,
                    title="Inspect workspace directory",
                    tool_name="filesystem",
                    action="list_dir",
                    parameters={"path": "."},
                    expected_outcome="Directory contents retrieved",
                    risk_level=0
                ),
                PlanStep(
                    step_id=2,
                    title="Create application structure",
                    tool_name="filesystem",
                    action="write_file",
                    parameters={"path": "nova_app.json", "content": json.dumps({"name": "Nova", "version": "1.0.0", "status": "active"})},
                    expected_outcome="File nova_app.json written to disk",
                    risk_level=1
                ),
                PlanStep(
                    step_id=3,
                    title="Verify project status",
                    tool_name="filesystem",
                    action="file_info",
                    parameters={"path": "nova_app.json"},
                    expected_outcome="Confirmed file exists with valid byte size",
                    risk_level=0
                )
            ]
            return PlanResult(
                goal=goal,
                intent="coding_task",
                requires_tools=True,
                summary="Plan formulated to inspect workspace, create project files, and verify output receipt.",
                steps=steps,
                verification_criteria="Project file verified on disk."
            )

        # 6. Terminal / Test execution
        if any(w in g_lower for w in ("test", "run", "lint", "check")):
            steps = [
                PlanStep(
                    step_id=1,
                    title="Run test suite command",
                    tool_name="terminal",
                    action="run_command",
                    parameters={"command": "echo 'JARVIS local tests: ALL PASS'"},
                    expected_outcome="Exit code 0 and pass indicator",
                    risk_level=1
                )
            ]
            return PlanResult(
                goal=goal,
                intent="terminal_execution",
                requires_tools=True,
                summary="Executing test command in controlled subprocess.",
                steps=steps,
                verification_criteria="Exit code 0"
            )

        # 7. Screen Vision
        if any(w in g_lower for w in ("screen", "looking at", "what do you see", "vision")):
            steps = [
                PlanStep(
                    step_id=1,
                    title="Capture live screen frame",
                    tool_name="screen",
                    action="execute",
                    parameters={},
                    expected_outcome="Live frame captured as base64 image",
                    risk_level=0
                )
            ]
            return PlanResult(
                goal=goal,
                intent="screen_query",
                requires_tools=True,
                summary="Capturing current display frame for visual telemetry.",
                steps=steps,
                verification_criteria="Non-empty base64 image received."
            )

        # 8. System Info Query
        if any(w in g_lower for w in ("system", "specs", "hardware", "diagnostic")):
            steps = [
                PlanStep(
                    step_id=1,
                    title="Retrieve system architecture telemetry",
                    tool_name="system_info",
                    action="execute",
                    parameters={},
                    expected_outcome="System telemetry retrieved",
                    risk_level=0
                )
            ]
            return PlanResult(
                goal=goal,
                intent="system_info",
                requires_tools=True,
                summary="Querying host system specifications and installed CLI tools.",
                steps=steps,
                verification_criteria="System metrics populated."
            )

        # 9. Workspace Filesystem Listing
        if any(w in g_lower for w in ("list files", "show files", "directory", "ls", "what files")):
            steps = [
                PlanStep(
                    step_id=1,
                    title="List directory contents",
                    tool_name="filesystem",
                    action="list_dir",
                    parameters={"path": "."},
                    expected_outcome="Directory contents retrieved",
                    risk_level=0
                )
            ]
            return PlanResult(
                goal=goal,
                intent="filesystem_inspection",
                requires_tools=True,
                summary="Inspecting workspace files.",
                steps=steps,
                verification_criteria="Files retrieved."
            )




        # Default conversational / informational plan
        return PlanResult(
            goal=goal,
            intent="conversation",
            requires_tools=False,
            summary="Direct response without external tool execution.",
            steps=[],
            verification_criteria="Response rendered."
        )

    async def generate_structured(
        self,
        prompt: str,
        schema_class: Type[BaseModel],
        system_instruction: Optional[str] = None
    ) -> BaseModel:
        # If schema is PlanResult, invoke plan()
        if schema_class == PlanResult:
            return await self.plan(prompt)

        # Provide a synthetic instance
        fields = schema_class.model_fields
        synth = {}
        for fname, finfo in fields.items():
            if finfo.annotation in (int, Optional[int]):
                synth[fname] = 1
            elif finfo.annotation in (bool, Optional[bool]):
                synth[fname] = True
            elif finfo.annotation in (float, Optional[float]):
                synth[fname] = 1.0
            elif finfo.annotation in (list, List[str]):
                synth[fname] = ["verified"]
            elif finfo.annotation in (dict, Dict[str, Any]):
                synth[fname] = {"status": "ok"}
            else:
                synth[fname] = f"Mock {fname}"
        return schema_class.model_validate(synth)

    async def analyze(
        self,
        content: str,
        instruction: str,
        is_untrusted: bool = True,
        image_base64: Optional[str] = None
    ) -> str:
        if image_base64:
            return (
                "Sir, I have analyzed your live screen capture. "
                "I observe your active desktop workspace running developer tooling and the JARVIS command console. "
                "Visual telemetry is sharp and clear."
            )
        return f"Analysis complete, Sir. Key takeaway regarding '{instruction}': {content[:100]}..."
