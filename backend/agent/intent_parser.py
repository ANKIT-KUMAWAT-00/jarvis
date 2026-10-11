"""
JARVIS Intent & Goal Parser
Extracts goals, target applications, entities, and actions from natural language,
resolving pronouns and conversational references.
"""

import re
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class ParsedGoal(BaseModel):
    raw_prompt: str
    resolved_prompt: str
    intent_category: str  # APP_INTERACTION, MEDIA_PLAYBACK, COMMUNICATION, BROWSER_SEARCH, ENGINEERING, SYSTEM_SETTING, REMEMBER, SCREEN_QUERY, CONVERSATION, CONTINUATION
    primary_application: Optional[str] = None
    target_entity: Optional[str] = None
    action: Optional[str] = None
    query_or_message: Optional[str] = None
    recipient: Optional[str] = None
    is_multi_turn_continuation: bool = False
    requires_browser: bool = False
    dependencies: List[str] = Field(default_factory=list)


class IntentParser:
    """NLU parser translating conversational requests into structured goal objects."""

    @classmethod
    def parse(cls, prompt: str, context_manager: Optional[Any] = None) -> ParsedGoal:
        p_clean = prompt.strip()
        p_lower = p_clean.lower()

        # Step 1: Resolve co-references if context manager is provided
        resolved_info = {}
        augmented_prompt = p_clean
        if context_manager and hasattr(context_manager, "resolve_references"):
            resolved_info = context_manager.resolve_references(p_clean)
            augmented_prompt = resolved_info.get("resolved_prompt", p_clean)
            p_lower = augmented_prompt.lower()

        # Fast continuation check
        is_continuation = resolved_info.get("is_continuation", False) or p_lower in (
            "continue", "resume", "carry on", "keep going", "proceed", "go ahead",
            "just go for it", "do it", "just do it"
        )
        if is_continuation:
            return ParsedGoal(
                raw_prompt=p_clean,
                resolved_prompt=augmented_prompt,
                intent_category="CONTINUATION",
                is_multi_turn_continuation=True
            )

        # Step 2: Detect Primary Application
        known_apps = {
            "whatsapp": "WhatsApp",
            "telegram": "Telegram",
            "safari": "Safari",
            "chrome": "Google Chrome",
            "google chrome": "Google Chrome",
            "spotify": "Spotify",
            "vs code": "Visual Studio Code",
            "vscode": "Visual Studio Code",
            "visual studio code": "Visual Studio Code",
            "terminal": "Terminal",
            "finder": "Finder",
            "gmail": "Gmail",
            "youtube": "YouTube",
            "mail": "Mail",
            "messages": "Messages",
            "facetime": "FaceTime",
            "notes": "Notes",
            "settings": "System Settings",
            "system settings": "System Settings",
            "app store": "App Store"
        }

        detected_app = None
        for k, v in known_apps.items():
            if k in p_lower:
                detected_app = v
                break

        if not detected_app and context_manager and hasattr(context_manager, "context"):
            detected_app = context_manager.context.current_app

        # Step 3: Classify Intent Category
        intent_cat = "CONVERSATION"

        # Media Playback
        if any(w in p_lower for w in ("play ", "listen to ", "stream ", "watch ")) or (
            any(w in p_lower for w in ("song", "music", "playlist", "track", "album"))
            and any(w in p_lower for w in ("play", "listen", "start", "open"))
        ):
            intent_cat = "MEDIA_PLAYBACK"
            if not detected_app:
                detected_app = "Spotify" if "spotify" in p_lower else "YouTube"

        # Communications (call, message, email, chat)
        elif any(w in p_lower for w in ("call ", "facetime ", "ring ", "make a call", "send email", "send an email", "send message", "send a message", "message ", "chat with")):
            intent_cat = "COMMUNICATION"

        # Web & Browser Search
        elif any(w in p_lower for w in ("search ", "search for ", "google ", "look up ", "in safari", "in chrome", "browse")):
            intent_cat = "BROWSER_SEARCH"
            if not detected_app:
                detected_app = "Safari"

        # Engineering / Code / Terminal
        elif any(w in p_lower for w in ("create", "build", "run", "fix", "test", "compile", "refactor", "commit", "execute", "project")):
            intent_cat = "ENGINEERING"
            if not detected_app:
                detected_app = "Visual Studio Code" if "project" in p_lower else "Terminal"

        # System Settings
        elif any(w in p_lower for w in ("settings", "permission", "pane", "preferences")):
            intent_cat = "SYSTEM_SETTING"
            detected_app = "System Settings"

        # App Interaction (open, click, type, navigate)
        elif any(w in p_lower for w in ("open", "launch", "close", "quit", "click", "type", "navigate", "select", "switch to")):
            intent_cat = "APP_INTERACTION"

        # Step 4: Extract recipient / message / query
        recipient = None
        m_rec = re.search(r'(?:call|message|chat with|to)\s+([A-Z][a-zA-Z0-9_\s]+?)(?:\s+(?:on|using|in|that|about)|$|\.)', augmented_prompt)
        if m_rec:
            recipient = m_rec.group(1).strip()
            if recipient.lower() in ("whatsapp", "telegram", "safari", "chrome", "spotify", "her", "him", "the app"):
                recipient = None

        if not recipient and resolved_info.get("resolved_entities", {}).get("recipient"):
            recipient = resolved_info["resolved_entities"]["recipient"]

        query_or_msg = None
        m_msg = re.search(r'(?:that|message:?|saying:?)\s+["\']?([^"\']+)["\']?$', augmented_prompt, re.IGNORECASE)
        if m_msg:
            query_or_msg = m_msg.group(1).strip()

        return ParsedGoal(
            raw_prompt=p_clean,
            resolved_prompt=augmented_prompt,
            intent_category=intent_cat,
            primary_application=detected_app,
            recipient=recipient,
            query_or_message=query_or_msg,
            requires_browser=detected_app in ("Safari", "Google Chrome", "Gmail", "YouTube") or "browser" in p_lower
        )
