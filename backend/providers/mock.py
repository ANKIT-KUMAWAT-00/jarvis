"""
JARVIS Mock LLM Provider
Deterministic, zero-cost high-fidelity provider for offline execution,
unit tests, preflight checks, and demonstrations without API keys.
"""

import json
import re
from typing import List, Dict, Any, Optional, Type
from pydantic import BaseModel
from .base import LLMProvider, PlanResult, PlanStep, TaskObject, TaskAction, TaskDependency


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

        # 0. Voice / Video Calls (e.g. "call Krishna", "call Krishna using WhatsApp")
        if any(w in ("call", "facetime", "ring") for w in words) and not any(w in ("meeting", "schedule") for w in words):
            recipient = "Someone"
            app = None
            if "using" in g_lower:
                parts = g_lower.split("using")
                before_using = parts[0]
                after_using = parts[1].strip()
                if "whatsapp" in after_using:
                    app = "whatsapp"
                elif "facetime" in after_using:
                    app = "facetime"
                # Extract recipient from before_using
                m_rec = re.search(r'(?:call|facetime|ring)\s+([a-zA-Z0-9_\s]+)', before_using)
                if m_rec:
                    recipient = m_rec.group(1).strip().capitalize()
            else:
                m_rec = re.search(r'(?:call|facetime|ring)\s+([a-zA-Z0-9_]+)', g_lower)
                if m_rec:
                    recipient = m_rec.group(1).strip().capitalize()

            step_params = {"recipient": recipient}
            if app:
                step_params["app"] = app

            task_obj = TaskObject(
                intent="make_call",
                target=recipient,
                actions=[TaskAction(type="make_call", target=recipient, parameters=step_params)],
                dependencies=[TaskDependency(type="application_installed", name=app.capitalize() if app else "FaceTime")],
                status="pending"
            )

            steps = [
                PlanStep(
                    step_id=1,
                    title=f"Initiate call to '{recipient}'{' via ' + app.capitalize() if app else ' via FaceTime'}",
                    tool_name="communication",
                    action="make_call",
                    parameters=step_params,
                    expected_outcome=f"Call initiated to '{recipient}'",
                    risk_level=1
                )
            ]
            return PlanResult(
                goal=actual_goal,
                intent="make_call",
                requires_tools=True,
                summary=f"Placing call to '{recipient}'{' using ' + app.capitalize() if app else ' using available communication service'}.",
                steps=steps,
                verification_criteria=f"Call to '{recipient}' dispatched.",
                task_object=task_obj
            )

        # 0.1. macOS System Settings Panes (e.g. "open system settings", "open accessibility settings")
        if "settings" in g_lower or "preferences" in g_lower:
            pane = "general"
            for p_key in ("accessibility", "automation", "screen_recording", "microphone", "camera", "full_disk", "bluetooth"):
                if p_key in g_lower:
                    pane = p_key
                    break
            
            task_obj = TaskObject(
                intent="system_settings",
                target=pane,
                actions=[TaskAction(type="open_settings", target=pane, parameters={"pane": pane})],
                status="pending"
            )
            steps = [
                PlanStep(
                    step_id=1,
                    title=f"Open macOS System Settings to '{pane.replace('_', ' ').capitalize()}'",
                    tool_name="app_control",
                    action="open_settings",
                    parameters={"pane": pane},
                    expected_outcome=f"Opened System Settings to {pane}",
                    risk_level=1
                )
            ]
            return PlanResult(
                goal=actual_goal,
                intent="system_settings",
                requires_tools=True,
                summary=f"Navigating to macOS System Settings: {pane}.",
                steps=steps,
                verification_criteria="System Settings pane launched.",
                task_object=task_obj
            )

        # 0.2. Explicit Playback Command: ONLY when user explicitly asks to "play" or "listen to"
        # Never trigger playback if user simply asks to "open youtube" or "open safari"
        is_play_request = any(w in ("play", "listen") for w in words)
        if is_play_request and any(w in g_lower for w in ("song", "music", "track", "video", "playlist", "youtube", "spotify")):
            browser = "Google Chrome" if "chrome" in g_lower else "Safari"
            # Extract user's exact query
            query = "music"
            m = re.search(r'(?:play|listen to)\s+([^,\.\n]+?)(?:\s+on\s+youtube|\s+in\s+spotify|\s+site|\s*$)', g_lower)
            if m:
                query = m.group(1).replace("youtube", "").replace("spotify", "").strip() or "music"

            task_obj = TaskObject(
                intent="play_music",
                target=query,
                actions=[
                    TaskAction(type="open_service", target="YouTube"),
                    TaskAction(type="search", query=query),
                    TaskAction(type="play", query=query)
                ],
                status="pending"
            )
            steps = [
                PlanStep(
                    step_id=1,
                    title=f"Search YouTube and play '{query}' in {browser}",
                    tool_name="app_control",
                    action="play_media",
                    parameters={"query": query, "browser": browser, "service": "youtube"},
                    expected_outcome=f"Playing '{query}' on YouTube in {browser}",
                    risk_level=1
                )
            ]
            return PlanResult(
                goal=actual_goal,
                intent="media_playback",
                requires_tools=True,
                summary=f"Searching YouTube for '{query}' and playing top result in {browser}.",
                steps=steps,
                verification_criteria="YouTube playback initiated in browser.",
                task_object=task_obj
            )

        # 0.3. YouTube Search without Autoplay (e.g. "open youtube and search for rajasthani songs")
        if "youtube" in g_lower and any(w in ("search", "find", "look up") for w in words) and not is_play_request:
            browser = "Google Chrome" if "chrome" in g_lower else "Safari"
            m_search = re.search(r'(?:search for|find|look up)\s+([^,\.\n]+?)(?:\s+on\s+youtube|\s+site|\s*$)', g_lower)
            query = m_search.group(1).strip() if m_search else "search"
            import urllib.parse
            url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
            task_obj = TaskObject(
                intent="search",
                target="YouTube",
                actions=[
                    TaskAction(type="open_service", target="YouTube"),
                    TaskAction(type="search", query=query, parameters={"url": url})
                ],
                status="pending"
            )
            steps = [
                PlanStep(
                    step_id=1,
                    title=f"Open YouTube search results for '{query}' in {browser}",
                    tool_name="app_control",
                    action="open_url",
                    parameters={"url": url, "browser": browser},
                    expected_outcome=f"YouTube search results for '{query}' loaded in {browser}",
                    risk_level=1
                )
            ]
            return PlanResult(
                goal=actual_goal,
                intent="browser_url",
                requires_tools=True,
                summary=f"Searching YouTube for '{query}' in {browser}.",
                steps=steps,
                verification_criteria=f"Opened YouTube search for '{query}'.",
                task_object=task_obj
            )

        # 0.4. Open Website / YouTube / URL without extra actions (e.g. "open youtube", "open safari", "open google")
        if "youtube" in g_lower and not is_play_request:
            browser = "Google Chrome" if "chrome" in g_lower else "Safari"
            url = "https://www.youtube.com"
            task_obj = TaskObject(
                intent="open_service",
                target="YouTube",
                actions=[TaskAction(type="open_service", target="YouTube", parameters={"url": url, "browser": browser})],
                status="pending"
            )
            steps = [
                PlanStep(
                    step_id=1,
                    title=f"Open YouTube ({url}) in {browser}",
                    tool_name="app_control",
                    action="open_url",
                    parameters={"url": url, "browser": browser},
                    expected_outcome=f"Opened YouTube in {browser}",
                    risk_level=1
                )
            ]
            return PlanResult(
                goal=actual_goal,
                intent="browser_url",
                requires_tools=True,
                summary=f"Opening YouTube homepage in {browser}.",
                steps=steps,
                verification_criteria=f"YouTube homepage opened in {browser}.",
                task_object=task_obj
            )

        # 0.5. Browser New Tab (open chrome new tab, safari new tab)
        if "new tab" in g_lower or ("tab" in words and any(w in ("open", "new", "create") for w in words)):
            browser = "Google Chrome" if "chrome" in g_lower else "Safari"
            task_obj = TaskObject(
                intent="browser_control",
                target=browser,
                actions=[TaskAction(type="open_new_tab", target=browser)],
                status="pending"
            )
            steps = [
                PlanStep(
                    step_id=1,
                    title=f"Open new tab in {browser}",
                    tool_name="app_control",
                    action="open_new_tab",
                    parameters={"browser": browser, "url": ""},
                    expected_outcome=f"New tab opened in {browser}",
                    risk_level=1
                )
            ]
            return PlanResult(
                goal=actual_goal,
                intent="browser_control",
                requires_tools=True,
                summary=f"Opening a new tab in {browser}.",
                steps=steps,
                verification_criteria=f"New tab launched in {browser}.",
                task_object=task_obj
            )

        # 0.6. Open Project (e.g. "open my ResumeIQ project", "open project ResumeIQ")
        if "project" in g_lower and any(w in ("open", "switch", "launch") for w in words):
            proj_name = "project"
            m_proj = re.search(r'(?:open\s+(?:my\s+)?|switch\s+to\s+(?:my\s+)?)?([a-zA-Z0-9_\-]+)\s+project', g_lower)
            if m_proj and m_proj.group(1).lower() not in ("the", "a", "my"):
                proj_name = m_proj.group(1).strip()
            else:
                m_proj2 = re.search(r'project\s+([a-zA-Z0-9_\-]+)', g_lower)
                if m_proj2:
                    proj_name = m_proj2.group(1).strip()
                else:
                    proj_name = "ResumeIQ" if "resumeiq" in g_lower else "workspace"

            task_obj = TaskObject(
                intent="open_project",
                target=proj_name,
                actions=[TaskAction(type="open_project", target=proj_name, parameters={"project_name": proj_name, "editor": "Visual Studio Code"})],
                dependencies=[TaskDependency(type="application_installed", name="Visual Studio Code")],
                status="pending"
            )
            steps = [
                PlanStep(
                    step_id=1,
                    title=f"Locate and open '{proj_name}' project in Visual Studio Code",
                    tool_name="app_control",
                    action="open_project",
                    parameters={"project_name": proj_name, "editor": "Visual Studio Code"},
                    expected_outcome=f"Project '{proj_name}' opened in Visual Studio Code",
                    risk_level=1
                )
            ]
            return PlanResult(
                goal=actual_goal,
                intent="project_open",
                requires_tools=True,
                summary=f"Locating and opening project '{proj_name}' in Visual Studio Code.",
                steps=steps,
                verification_criteria=f"Project '{proj_name}' opened in editor.",
                task_object=task_obj
            )

        # 0.7. App Store / Download from Store (e.g. "open the app store", "open app store and download whatsapp")
        if "app store" in g_lower or "appstore" in g_lower or ("store" in words and any(w in ("app", "download", "install", "get") for w in words)):
            app_to_download = None
            m_dl = re.search(r'(?:download|install|find|search for|get)\s+(?:the\s+)?([a-zA-Z0-9_\s]+)', g_lower)
            if m_dl:
                cand = m_dl.group(1).strip()
                if cand not in ("any app", "an app", "apps", "app", "application", "something", "anything"):
                    clean_cand = cand.split(" and ")[0].split(" then ")[0].strip().title()
                    if clean_cand and clean_cand.lower() not in ("any app", "an app", "app"):
                        app_to_download = clean_cand

            if app_to_download:
                task_obj = TaskObject(
                    intent="open_app_store",
                    target=app_to_download,
                    actions=[TaskAction(type="open_app_store", target=app_to_download, parameters={"app_name": app_to_download})],
                    status="pending"
                )
                steps = [
                    PlanStep(
                        step_id=1,
                        title=f"Open Mac App Store page for '{app_to_download}'",
                        tool_name="app_control",
                        action="open_app_store",
                        parameters={"app_name": app_to_download},
                        expected_outcome=f"Mac App Store navigated to '{app_to_download}'",
                        risk_level=1
                    )
                ]
                return PlanResult(
                    goal=actual_goal,
                    intent="open_app_store",
                    requires_tools=True,
                    summary=f"Opening Mac App Store page for '{app_to_download}'.",
                    steps=steps,
                    verification_criteria=f"App Store navigated to '{app_to_download}'.",
                    task_object=task_obj
                )
            else:
                task_obj = TaskObject(
                    intent="open_application",
                    target="App Store",
                    actions=[TaskAction(type="open_app", target="App Store", parameters={"app_name": "App Store"})],
                    status="pending"
                )
                steps = [
                    PlanStep(
                        step_id=1,
                        title="Launch App Store",
                        tool_name="app_control",
                        action="open_app",
                        parameters={"app_name": "App Store"},
                        expected_outcome="App Store opened",
                        risk_level=1
                    )
                ]
                return PlanResult(
                    goal=actual_goal,
                    intent="app_control",
                    requires_tools=True,
                    summary="Launching Mac App Store.",
                    steps=steps,
                    verification_criteria="App Store running.",
                    task_object=task_obj
                )

        # 1. App Control (open application, launch app, close app)
        is_close = any(w in ("close", "quit", "exit", "terminate", "kill", "stop") for w in words)
        is_open = any(w in ("open", "launch", "start") for w in words)

        if (is_open or is_close) and not any(w in g_lower for w in ("project file", "issue", "meeting", "calendar", "mail to", "message to")):
            target = None
            from backend.tools.app_control import AppControlTool
            sorted_apps = sorted(AppControlTool.COMMON_APP_MAP.keys(), key=lambda k: len(k), reverse=True)
            for cand in sorted_apps:
                if cand in g_lower:
                    target = AppControlTool.COMMON_APP_MAP[cand]
                    break

            # If explicit name given after open/launch/close/quit
            if not target:
                for i, w in enumerate(words):
                    if w in ("open", "launch", "start", "close", "quit") and i + 1 < len(words):
                        idx = i + 1
                        while idx < len(words) and words[idx] in ("the", "a", "an", "app", "application"):
                            idx += 1
                        if idx < len(words) and words[idx] not in ("app", "application", "something", "anything"):
                            target = words[idx].capitalize()
                            break

            if not target:
                target = "Safari"

            # If user specified a website or URL in the app (e.g. open google.com)
            if any(k in g_lower for k in ("http", ".com", ".org", ".io", ".net", "site")):
                m_url = re.search(r'(https?://[^\s]+|[a-zA-Z0-9_-]+\.(?:com|org|io|net))', actual_goal)
                url = m_url.group(0) if m_url else "https://google.com"
                if not url.startswith("http"):
                    url = f"https://{url}"
                task_obj = TaskObject(
                    intent="browser_url",
                    target=url,
                    actions=[TaskAction(type="open_url", target=url, parameters={"url": url, "browser": target})],
                    status="pending"
                )
                steps = [
                    PlanStep(
                        step_id=1,
                        title=f"Open {url} in {target}",
                        tool_name="app_control",
                        action="open_url",
                        parameters={"url": url, "browser": target},
                        expected_outcome=f"Opened {url} in {target}",
                        risk_level=1
                    )
                ]
                return PlanResult(
                    goal=actual_goal,
                    intent="browser_url",
                    requires_tools=True,
                    summary=f"Navigating to {url} in {target}.",
                    steps=steps,
                    verification_criteria=f"Opened {url} in {target}.",
                    task_object=task_obj
                )

            action = "close_app" if is_close and not is_open else "open_app"
            task_obj = TaskObject(
                intent="close_application" if action == "close_app" else "open_application",
                target=target,
                actions=[TaskAction(type=action, target=target, parameters={"app_name": target})],
                dependencies=[TaskDependency(type="application_installed", name=target)],
                status="pending"
            )
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
                verification_criteria=f"Application {target} state updated.",
                task_object=task_obj
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

            task_obj = TaskObject(
                intent="create_meeting",
                target=actual_goal,
                actions=[TaskAction(type="create_meeting", parameters={"title": actual_goal, "date": date_val, "time": time_val})],
                status="pending"
            )
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
                verification_criteria="Meeting link generated and calendar event created.",
                task_object=task_obj
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

            task_obj = TaskObject(
                intent="set_timer",
                target=f"{minutes_val} minutes",
                actions=[TaskAction(type="set_timer", parameters={"minutes": minutes_val, "label": actual_goal})],
                status="pending"
            )
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
                verification_criteria="Timer running in scheduler.",
                task_object=task_obj
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
            task_obj = TaskObject(
                intent=action,
                target=to_val,
                actions=[TaskAction(type=action, target=to_val, parameters=params)],
                status="pending"
            )
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
                verification_criteria="Client opened with draft/message.",
                task_object=task_obj
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
