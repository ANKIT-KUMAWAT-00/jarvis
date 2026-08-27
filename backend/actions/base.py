"""
JARVIS Action Abstraction Layer - Base Types
High-level action interfaces decouples intent from underlying OS controllers.
"""

from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class ActionType(str, Enum):
    LAUNCH_APP = "launch_app"
    FOCUS_APP = "focus_app"
    CLOSE_APP = "close_app"
    NAVIGATE = "navigate"
    SEARCH = "search"
    FIND_ELEMENT = "find_element"
    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    TYPE_TEXT = "type_text"
    PRESS_KEY = "press_key"
    SCROLL = "scroll"
    SELECT = "select"
    READ = "read"
    PLAY_MEDIA = "play_media"
    OPEN_SETTINGS = "open_settings"
    OPEN_PROJECT = "open_project"
    OPEN_APP_STORE = "open_app_store"
    WAIT = "wait"
    TAKE_SCREENSHOT = "take_screenshot"
    OBSERVE = "observe"
    VERIFY = "verify"


class ActionCommand(BaseModel):
    action_type: ActionType
    app: Optional[str] = None
    target: Optional[str] = None
    text: Optional[str] = None
    query: Optional[str] = None
    url: Optional[str] = None
    browser: Optional[str] = None
    selector: Optional[str] = None
    key: Optional[str] = None
    direction: Optional[str] = "down"
    pane: Optional[str] = None
    project_name: Optional[str] = None
    editor: Optional[str] = "Visual Studio Code"
    expected_outcome: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)


class ActionResult(BaseModel):
    success: bool
    output: Any = ""
    error: Optional[str] = None
    technique_used: str = "native"  # native, applescript, accessibility, browser, vision
    raw_data: Dict[str, Any] = Field(default_factory=dict)
    execution_time_ms: int = 0
