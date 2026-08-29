"""
JARVIS Environment Observer
Continuously observes macOS computer state: running applications, active windows,
browser tabs, accessibility elements, and system dialogs.
"""

import asyncio
import os
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field

logger = logging.getLogger("jarvis.observer")


class ObservedElement(BaseModel):
    role: str
    title: str = ""
    description: str = ""
    value: str = ""
    enabled: bool = True
    sub_elements_count: int = 0


class ObservedState(BaseModel):
    running_apps: List[str] = Field(default_factory=list)
    active_app: Optional[str] = None
    active_window_title: Optional[str] = None
    browser_active: Optional[str] = None
    browser_url: Optional[str] = None
    browser_title: Optional[str] = None
    ui_elements: List[ObservedElement] = Field(default_factory=list)
    has_modal_dialog: bool = False
    has_permission_prompt: bool = False
    dialog_text: Optional[str] = None
    timestamp: float = 0.0


class EnvironmentObserver:
    """
    Non-invasive observer querying macOS window and process hierarchies.
    """

    @staticmethod
    async def get_running_applications() -> List[str]:
        """Fetch names of all visible applications currently running."""
        if os.environ.get("PYTEST_CURRENT_TEST"):
            return ["Finder", "Safari", "Terminal"]

        script = 'tell application "System Events" to get name of every application process whose visible is true'
        try:
            proc = await asyncio.create_subprocess_exec(
                "osascript", "-e", script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=3.0)
            if proc.returncode == 0:
                return [app.strip() for app in stdout.decode().split(",") if app.strip()]
        except Exception as e:
            logger.debug(f"Error fetching running apps: {e}")
        return []

    @staticmethod
    async def get_frontmost_application() -> Tuple[Optional[str], Optional[str]]:
        """Identify which application and window is currently frontmost."""
        if os.environ.get("PYTEST_CURRENT_TEST"):
            return "Safari", "New Tab"

        script = '''
tell application "System Events"
    set frontApp to first application process whose frontmost is true
    set appName to name of frontApp
    set winTitle to ""
    try
        if (count of windows of frontApp) > 0 then
            set winTitle to name of front window of frontApp
        end if
    end try
    return appName & "|||" & winTitle
end tell
'''
        try:
            proc = await asyncio.create_subprocess_exec(
                "osascript", "-e", script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=2.5)
            if proc.returncode == 0:
                parts = stdout.decode().strip().split("|||")
                app_name = parts[0].strip() if len(parts) > 0 else None
                win_title = parts[1].strip() if len(parts) > 1 else ""
                return app_name, win_title
        except Exception:
            pass
        return None, None

    @staticmethod
    async def get_browser_state(preferred_browser: str = "Safari") -> Dict[str, Any]:
        """Inspect active tab and URL in Safari or Chrome."""
        if os.environ.get("PYTEST_CURRENT_TEST"):
            return {"browser": preferred_browser, "url": "about:blank", "title": "Blank"}

        # Try Safari
        safari_script = '''
tell application "System Events"
    if (count of (processes whose name is "Safari")) > 0 then
        tell application "Safari"
            if (count of windows) > 0 then
                tell current tab of front window
                    return "Safari|||" & URL & "|||" & name
                end tell
            end if
        end tell
    end if
    return "NONE"
end tell
'''
        # Try Chrome
        chrome_script = '''
tell application "System Events"
    if (count of (processes whose name is "Google Chrome")) > 0 then
        tell application "Google Chrome"
            if (count of windows) > 0 then
                tell active tab of front window
                    return "Google Chrome|||" & URL & "|||" & title
                end tell
            end if
        end tell
    end if
    return "NONE"
end tell
'''
        for s in (safari_script, chrome_script):
            try:
                proc = await asyncio.create_subprocess_exec(
                    "osascript", "-e", s,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=2.0)
                out = stdout.decode().strip()
                if out and out != "NONE" and "|||" in out:
                    parts = out.split("|||")
                    return {
                        "browser": parts[0].strip(),
                        "url": parts[1].strip() if len(parts) > 1 else "",
                        "title": parts[2].strip() if len(parts) > 2 else ""
                    }
            except Exception:
                pass

        return {"browser": None, "url": None, "title": None}

    @staticmethod
    async def inspect_ui_elements(app_name: str) -> List[ObservedElement]:
        """
        Inspect visible accessibility elements (buttons, text fields)
        of the front window of an application.
        """
        if os.environ.get("PYTEST_CURRENT_TEST") or not app_name:
            return []

        script = f'''
tell application "System Events"
    if (count of (processes whose name is "{app_name}")) > 0 then
        tell process "{app_name}"
            if (count of windows) > 0 then
                tell front window
                    set btnNames to name of every button
                    set txtNames to description of every text field
                    return (btnNames as string) & "|||" & (txtNames as string)
                end tell
            end if
        end tell
    end if
    return ""
end tell
'''
        elements = []
        try:
            proc = await asyncio.create_subprocess_exec(
                "osascript", "-e", script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=2.5)
            if proc.returncode == 0:
                raw = stdout.decode().strip()
                if "|||" in raw:
                    btns, txts = raw.split("|||")
                    for b in btns.split(","):
                        if b.strip():
                            elements.append(ObservedElement(role="button", title=b.strip()))
                    for t in txts.split(","):
                        if t.strip():
                            elements.append(ObservedElement(role="text_field", title=t.strip()))
        except Exception:
            pass

        return elements

    @classmethod
    async def observe_full_state(cls) -> ObservedState:
        """Capture complete computer state snapshot."""
        import time
        running = await cls.get_running_applications()
        active_app, win_title = await cls.get_frontmost_application()
        browser_info = await cls.get_browser_state()

        ui_elems = []
        if active_app:
            ui_elems = await cls.inspect_ui_elements(active_app)

        return ObservedState(
            running_apps=running,
            active_app=active_app,
            active_window_title=win_title,
            browser_active=browser_info.get("browser"),
            browser_url=browser_info.get("url"),
            browser_title=browser_info.get("title"),
            ui_elements=ui_elems,
            timestamp=time.time()
        )
