"""
JARVIS Context Manager
Maintains conversational state, active task context, window/application awareness,
entity tracking, and multi-turn reference resolution.
"""

import time
import re
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class EntityReference(BaseModel):
    category: str  # person, file, project, app, website, playlist, query, contact
    value: str
    context_source: str = ""
    timestamp: float = Field(default_factory=time.time)


class ConversationContext(BaseModel):
    current_app: Optional[str] = None
    current_browser: str = "Safari"
    current_website: Optional[str] = None
    current_window: Optional[str] = None
    current_tab: Optional[str] = None
    active_chat: Optional[str] = None
    active_project: Optional[str] = None
    active_file: Optional[str] = None
    recent_people: List[str] = Field(default_factory=list)
    recent_files: List[str] = Field(default_factory=list)
    recent_projects: List[str] = Field(default_factory=list)
    recent_apps: List[str] = Field(default_factory=list)
    recent_results: List[str] = Field(default_factory=list)
    completed_actions: List[str] = Field(default_factory=list)
    pending_actions: List[str] = Field(default_factory=list)
    failed_actions: List[str] = Field(default_factory=list)
    active_permissions_required: List[str] = Field(default_factory=list)
    active_installations_required: List[str] = Field(default_factory=list)


class ContextManager:
    """
    Central repository for situational awareness, dialogue history, and
    co-reference resolution across multi-turn interactions.
    """

    def __init__(self, max_history: int = 30):
        self.max_history = max_history
        self.conversation_history: List[Dict[str, str]] = []
        self.recent_commands: List[str] = []
        self.context = ConversationContext()
        self.entities: Dict[str, EntityReference] = {}
        self.active_task: Optional[Dict[str, Any]] = None
        self.previous_tasks: List[Dict[str, Any]] = []

    def record_user_message(self, text: str):
        """Record user input and dynamically extract contextual entities."""
        clean = text.strip()
        self.conversation_history.append({"role": "user", "content": clean})
        self.recent_commands.append(clean)
        if len(self.conversation_history) > self.max_history:
            self.conversation_history = self.conversation_history[-self.max_history:]
        if len(self.recent_commands) > 15:
            self.recent_commands = self.recent_commands[-15:]

        self._extract_entities_from_text(clean)

    def record_assistant_message(self, text: str):
        """Record assistant reply."""
        clean = text.strip()
        self.conversation_history.append({"role": "assistant", "content": clean})
        if len(self.conversation_history) > self.max_history:
            self.conversation_history = self.conversation_history[-self.max_history:]

    def _extract_entities_from_text(self, text: str):
        """Heuristically extract salient nouns, applications, people, projects, and websites."""
        t_lower = text.lower()

        # Known Applications & Websites
        apps_keywords = {
            "whatsapp": ("app", "WhatsApp"),
            "telegram": ("app", "Telegram"),
            "safari": ("app", "Safari"),
            "chrome": ("app", "Google Chrome"),
            "google chrome": ("app", "Google Chrome"),
            "spotify": ("app", "Spotify"),
            "vs code": ("app", "Visual Studio Code"),
            "vscode": ("app", "Visual Studio Code"),
            "visual studio code": ("app", "Visual Studio Code"),
            "terminal": ("app", "Terminal"),
            "finder": ("app", "Finder"),
            "gmail": ("website", "Gmail"),
            "youtube": ("website", "YouTube"),
            "notes": ("app", "Notes"),
            "calendar": ("app", "Calendar"),
            "mail": ("app", "Mail"),
            "messages": ("app", "Messages"),
            "slack": ("app", "Slack")
        }

        for k, (cat, val) in apps_keywords.items():
            if k in t_lower:
                self.entities[cat] = EntityReference(category=cat, value=val, context_source=text)
                if cat == "app":
                    self.set_current_app(val)
                elif cat == "website":
                    self.context.current_website = val

        # People extraction (e.g., "Krishna", "Dee bhai", "Alice")
        call_msg_patterns = [
            r'(?:call|message|text|email|chat with|contact|send to)\s+([A-Za-z0-9_\s]+?)(?:\s+(?:on|using|in|that|about)|$|\.)',
            r"([A-Za-z0-9_]+)'s\s+chat",
            r"(?:to|with)\s+([A-Za-z0-9_\s]+?)(?:\s+on|\s+in|$|\.)"
        ]
        for pat in call_msg_patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                person = m.group(1).strip()
                # filter common stop words, pronouns, and time adverbs
                stop_words = (
                    "whatsapp", "telegram", "safari", "chrome", "spotify", "her", "him", "them",
                    "the app", "someone", "recipient", "later", "soon", "now", "today", "tomorrow",
                    "yesterday", "back", "again", "this", "that", "it", "me", "you", "us", "here", "there"
                )
                if person.lower() not in stop_words:
                    self.entities["person"] = EntityReference(category="person", value=person, context_source=text)
                    if person not in self.context.recent_people:
                        self.context.recent_people.append(person)
                    self.context.active_chat = person
                    break

        # Project extraction (e.g., "ResumeIQ", "jarvis")
        proj_pattern = r'(?:open|run|build|test|switch to)\s+(?:my\s+)?([a-zA-Z0-9_-]+)\s+project'
        m_proj = re.search(proj_pattern, text, re.IGNORECASE)
        if m_proj:
            proj = m_proj.group(1).strip()
            self.entities["project"] = EntityReference(category="project", value=proj, context_source=text)
            self.context.active_project = proj
            if proj not in self.context.recent_projects:
                self.context.recent_projects.append(proj)

        # File extraction (e.g., "notes.txt", "main.py", "resume.pdf")
        m_file = re.search(r'\b([a-zA-Z0-9_\-]+\.[a-zA-Z0-9]{1,5})\b', text)
        if m_file:
            fname = m_file.group(1)
            self.entities["file"] = EntityReference(category="file", value=fname, context_source=text)
            self.context.active_file = fname
            if fname not in self.context.recent_files:
                self.context.recent_files.append(fname)

        # Playlist / Media extraction
        m_playlist = re.search(r'(?:play|open)\s+(?:my\s+)?([a-zA-Z0-9_\s]+?)\s+playlist', text, re.IGNORECASE)
        if m_playlist:
            plist = m_playlist.group(1).strip()
            self.entities["playlist"] = EntityReference(category="playlist", value=plist, context_source=text)

    def set_current_app(self, app_name: str):
        """Update active application and recent app queue."""
        clean = app_name.strip()
        self.context.current_app = clean
        if clean not in self.context.recent_apps:
            self.context.recent_apps.append(clean)
        if len(self.context.recent_apps) > 5:
            self.context.recent_apps.pop(0)

    def set_recent_results(self, results: List[str]):
        """Save numbered list of items (e.g. search hits, playlists) for ordinal resolution."""
        self.context.recent_results = list(results)

    def resolve_references(self, prompt: str) -> Dict[str, Any]:
        """
        Resolves pronouns and anaphoric references:
        - 'it', 'this', 'that' -> active project, active file, or target app
        - 'him', 'her', 'them' -> recent person
        - 'there', 'here' -> current app or website
        - 'the app' -> current application
        - 'the chat' -> current chat / person
        - 'the first one', 'the second one' -> recent results
        - 'continue' -> resume pending task
        """
        p_clean = prompt.strip()
        p_lower = p_clean.lower()
        resolved_entities: Dict[str, Any] = {}
        augmented_prompt = p_clean

        # Check for continuation command
        is_continuation = p_lower in ("continue", "resume", "carry on", "keep going", "proceed") or p_lower.startswith("continue ")
        resolved_entities["is_continuation"] = is_continuation

        # 1. Resolve pronouns for people: "her", "him", "them"
        if re.search(r'\b(her|him|them)\b', p_lower):
            if self.context.recent_people:
                person = self.context.recent_people[-1]
                resolved_entities["recipient"] = person
                # Expand prompt for downstream planners
                augmented_prompt = re.sub(r'\b(her|him|them)\b', person, augmented_prompt, flags=re.IGNORECASE)
            elif "person" in self.entities:
                person = self.entities["person"].value
                resolved_entities["recipient"] = person
                augmented_prompt = re.sub(r'\b(her|him|them)\b', person, augmented_prompt, flags=re.IGNORECASE)

        # 2. Resolve "it", "this", "that"
        if re.search(r'\b(it|this|that)\b', p_lower):
            # If prompt is "run it", "test it", "build it" -> project
            if any(verb in p_lower for verb in ("run", "build", "test", "compile", "open", "deploy", "start")):
                if self.context.active_project:
                    proj = self.context.active_project
                    resolved_entities["project"] = proj
                    augmented_prompt = re.sub(r'\b(it|this|that)\b', f"the {proj} project", augmented_prompt, flags=re.IGNORECASE)
                elif self.context.active_file:
                    f = self.context.active_file
                    resolved_entities["file"] = f
                    augmented_prompt = re.sub(r'\b(it|this|that)\b', f"file {f}", augmented_prompt, flags=re.IGNORECASE)
            # If prompt is "play it" -> song / playlist
            elif "play" in p_lower:
                if "playlist" in self.entities:
                    plist = self.entities["playlist"].value
                    resolved_entities["playlist"] = plist
                    augmented_prompt = re.sub(r'\b(it|this|that)\b', f"{plist} playlist", augmented_prompt, flags=re.IGNORECASE)

        # 3. Resolve "the app", "the application"
        if re.search(r'\b(the app|the application)\b', p_lower):
            if self.context.current_app:
                app = self.context.current_app
                resolved_entities["app"] = app
                augmented_prompt = re.sub(r'\b(the app|the application)\b', app, augmented_prompt, flags=re.IGNORECASE)

        # 4. Resolve "the chat", "the message"
        if re.search(r'\b(the chat|the conversation)\b', p_lower):
            if self.context.active_chat:
                chat = self.context.active_chat
                resolved_entities["chat"] = chat
                augmented_prompt = re.sub(r'\b(the chat|the conversation)\b', f"{chat}'s chat", augmented_prompt, flags=re.IGNORECASE)

        # 5. Resolve ordinals: "first one", "second one", "previous one"
        ordinal_map = {
            "first": 0, "second": 1, "third": 2, "fourth": 3, "fifth": 4,
            "1st": 0, "2nd": 1, "3rd": 2, "last": -1, "previous": -1
        }
        for ord_word, idx in ordinal_map.items():
            if f"{ord_word} one" in p_lower or f"{ord_word} result" in p_lower or f"{ord_word} playlist" in p_lower:
                if self.context.recent_results and (idx < len(self.context.recent_results) or idx == -1):
                    item = self.context.recent_results[idx]
                    resolved_entities["selected_item"] = item
                    augmented_prompt = re.sub(rf'\bthe {ord_word} (one|result|playlist)\b', f"'{item}'", augmented_prompt, flags=re.IGNORECASE)
                break

        # 6. Resolve implicit application context
        # e.g. "Play my workout playlist" -> if Spotify is active or recent, attach Spotify
        if "app" not in resolved_entities and self.context.current_app:
            resolved_entities["inferred_app"] = self.context.current_app

        return {
            "original_prompt": prompt,
            "resolved_prompt": augmented_prompt,
            "resolved_entities": resolved_entities,
            "current_app": self.context.current_app,
            "current_browser": self.context.current_browser,
            "active_project": self.context.active_project,
            "active_chat": self.context.active_chat,
            "is_continuation": is_continuation
        }

    def format_context_for_planner(self) -> str:
        """Construct comprehensive prompt section containing conversational & computer state."""
        lines = ["[CONVERSATION & ENVIRONMENT CONTEXT]"]
        if self.context.current_app:
            lines.append(f"- Active Application: {self.context.current_app}")
        if self.context.current_browser:
            lines.append(f"- Active Browser: {self.context.current_browser}")
        if self.context.current_website:
            lines.append(f"- Current Website: {self.context.current_website}")
        if self.context.active_project:
            lines.append(f"- Current Project: {self.context.active_project}")
        if self.context.active_chat:
            lines.append(f"- Active Chat / Contact: {self.context.active_chat}")
        if self.context.recent_people:
            lines.append(f"- Recently Mentioned People: {', '.join(self.context.recent_people[-3:])}")
        if self.context.recent_files:
            lines.append(f"- Recently Mentioned Files: {', '.join(self.context.recent_files[-3:])}")
        if self.context.recent_apps:
            lines.append(f"- Recently Used Applications: {', '.join(self.context.recent_apps[-3:])}")
        if self.context.recent_results:
            lines.append(f"- Recent Results / Options: {', '.join(self.context.recent_results[:5])}")

        if self.active_task:
            lines.append(f"- Active Ongoing Task: {self.active_task.get('goal', 'unknown')}")
            lines.append(f"- Active Task Status: {self.active_task.get('status', 'in_progress')}")
        elif self.previous_tasks:
            last = self.previous_tasks[-1]
            lines.append(f"- Previous Task: {last.get('goal', '')} (Outcome: {last.get('state', 'completed')})")

        return "\n".join(lines)

    def update_from_observation(self, obs: Any):
        """Update active environment context from an ObservedState or dict."""
        if hasattr(obs, "active_app") and obs.active_app:
            self.set_current_app(obs.active_app)
        elif isinstance(obs, dict) and obs.get("active_app"):
            self.set_current_app(obs["active_app"])

        if hasattr(obs, "active_window_title") and obs.active_window_title:
            self.context.current_window = obs.active_window_title
        elif isinstance(obs, dict) and obs.get("active_window_title"):
            self.context.current_window = obs["active_window_title"]

        if hasattr(obs, "browser_active") and obs.browser_active:
            self.context.current_browser = obs.browser_active
        elif isinstance(obs, dict) and obs.get("browser_active"):
            self.context.current_browser = obs["browser_active"]

        if hasattr(obs, "browser_url") and obs.browser_url:
            self.context.current_website = obs.browser_url
        elif isinstance(obs, dict) and obs.get("browser_url"):
            self.context.current_website = obs["browser_url"]

