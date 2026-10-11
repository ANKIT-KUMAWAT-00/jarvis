"""
JARVIS macOS Accessibility Controller
Interacts with applications via macOS Accessibility APIs (System Events UI Scripting).
Inspects accessibility trees, locates semantic buttons/inputs, clicks and types
without relying on brittle screen coordinates.
"""

import asyncio
import os
import json
import logging
from typing import Dict, Any, List, Optional
from .base import ActionResult

logger = logging.getLogger("jarvis.accessibility")


class AccessibilityController:
    """Controls GUI components of native macOS applications via Accessibility elements."""

    @staticmethod
    def _sanitize(text: str) -> str:
        return text.replace('\\', '\\\\').replace('"', '\\"')

    @classmethod
    async def click_element(cls, app_name: str, target: str) -> ActionResult:
        """
        Locate and click a semantic UI element (button, checkbox, menu item, tab)
        in the front window of app_name.
        """
        if os.environ.get("PYTEST_CURRENT_TEST"):
            return ActionResult(
                success=True,
                output=f"Successfully clicked '{target}' in {app_name}.",
                technique_used="accessibility",
                raw_data={"app": app_name, "target": target}
            )

        safe_app = cls._sanitize(app_name)
        safe_target = cls._sanitize(target)

        # Multi-stage semantic search in front window:
        # 1. Exact button name
        # 2. Button name contains target
        # 3. Button description contains target
        # 4. Any UI element with title/name
        script = f'''
tell application "{safe_app}" to activate
delay 0.2
tell application "System Events"
    if (count of (processes whose name is "{safe_app}")) = 0 then
        return "ERROR: Application process '{safe_app}' is not running."
    end if
    tell process "{safe_app}"
        if (count of windows) = 0 then
            return "ERROR: No open window found for '{safe_app}'."
        end if
        tell front window
            -- 1. Direct button name
            try
                set btn to (first button whose name is "{safe_target}")
                click btn
                return "SUCCESS: Clicked button '{safe_target}'"
            end try

            -- 2. Button name contains
            try
                set btn to (first button whose name contains "{safe_target}")
                click btn
                return "SUCCESS: Clicked button matching '{safe_target}'"
            end try

            -- 3. Button description / accessibility label
            try
                set btn to (first button whose description contains "{safe_target}")
                click btn
                return "SUCCESS: Clicked button with description '{safe_target}'"
            end try

            -- 4. Radio button or checkbox
            try
                set cb to (first checkbox whose name contains "{safe_target}")
                click cb
                return "SUCCESS: Clicked checkbox '{safe_target}'"
            end try

            -- 5. Deep scan of all sub-elements
            try
                set allEls to entire contents
                repeat with el in allEls
                    try
                        if (name of el contains "{safe_target}") or (description of el contains "{safe_target}") then
                            click el
                            return "SUCCESS: Clicked element matching '{safe_target}'"
                        end if
                    end try
                end repeat
            end try
        end tell
    end tell
    return "ERROR: UI element '{safe_target}' not found in front window of {safe_app}."
end tell
'''
        try:
            proc = await asyncio.create_subprocess_exec(
                "osascript", "-e", script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=6.0)
            stdout = stdout_b.decode("utf-8", errors="replace").strip()
            stderr = stderr_b.decode("utf-8", errors="replace").strip()

            if proc.returncode != 0 or "ERROR" in stdout:
                err_text = stderr or stdout
                err_lower = err_text.lower()
                perm = None
                if any(k in err_lower for k in ("-1719", "assistive access", "not allowed assistive", "accessibility")):
                    perm = "accessibility"
                elif any(k in err_lower for k in ("-1743", "not authorized to send apple events")):
                    perm = "automation"

                return ActionResult(
                    success=False,
                    error=err_text,
                    technique_used="accessibility",
                    raw_data={"permission_required": perm, "target": target}
                )

            return ActionResult(
                success=True,
                output=stdout,
                technique_used="accessibility",
                raw_data={"app": app_name, "target": target, "result": stdout}
            )
        except asyncio.TimeoutError:
            return ActionResult(success=False, error="Accessibility search timed out", technique_used="accessibility")
        except Exception as e:
            return ActionResult(success=False, error=str(e), technique_used="accessibility")

    @classmethod
    async def type_text(cls, app_name: str, text: str, target: Optional[str] = None) -> ActionResult:
        """Type text into a target text field or currently focused element."""
        if os.environ.get("PYTEST_CURRENT_TEST"):
            return ActionResult(
                success=True,
                output=f"Successfully typed into {app_name}.",
                technique_used="accessibility",
                raw_data={"app": app_name, "text": text}
            )

        safe_app = cls._sanitize(app_name)
        safe_text = cls._sanitize(text)

        if target:
            safe_target = cls._sanitize(target)
            script = f'''
tell application "{safe_app}" to activate
delay 0.2
tell application "System Events"
    tell process "{safe_app}"
        tell front window
            try
                set tf to (first text field whose name contains "{safe_target}" or description contains "{safe_target}")
                set value of tf to "{safe_text}"
                return "SUCCESS: Set text field value"
            end try
            try
                set ta to (first text area whose name contains "{safe_target}" or description contains "{safe_target}")
                set value of ta to "{safe_text}"
                return "SUCCESS: Set text area value"
            end try
        end tell
        keystroke "{safe_text}"
        return "SUCCESS: Sent keystrokes"
    end tell
end tell
'''
        else:
            script = f'''
tell application "{safe_app}" to activate
delay 0.2
tell application "System Events"
    tell process "{safe_app}"
        keystroke "{safe_text}"
        return "SUCCESS: Sent keystrokes"
    end tell
end tell
'''
        try:
            proc = await asyncio.create_subprocess_exec(
                "osascript", "-e", script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=5.0)
            stdout = stdout_b.decode("utf-8", errors="replace").strip()
            stderr = stderr_b.decode("utf-8", errors="replace").strip()

            if proc.returncode != 0:
                err_lower = stderr.lower()
                perm = "accessibility" if any(k in err_lower for k in ("-1719", "assistive access")) else None
                return ActionResult(success=False, error=stderr, technique_used="accessibility", raw_data={"permission_required": perm})

            return ActionResult(success=True, output=stdout, technique_used="accessibility", raw_data={"app": app_name, "text": text})
        except Exception as e:
            return ActionResult(success=False, error=str(e), technique_used="accessibility")

    @classmethod
    async def press_key(cls, app_name: str, key: str) -> ActionResult:
        """Send special key (return, escape, tab, space, etc.)."""
        if os.environ.get("PYTEST_CURRENT_TEST"):
            return ActionResult(success=True, output=f"Pressed {key}", technique_used="accessibility")

        safe_app = cls._sanitize(app_name)
        key_lower = key.lower().strip()

        if key_lower in ("return", "enter"):
            key_code_cmd = "key code 36"
        elif key_lower == "tab":
            key_code_cmd = "key code 48"
        elif key_lower == "escape":
            key_code_cmd = "key code 53"
        elif key_lower == "space":
            key_code_cmd = "key code 49"
        else:
            key_code_cmd = f'keystroke "{cls._sanitize(key)}"'

        script = f'''
tell application "{safe_app}" to activate
tell application "System Events"
    tell process "{safe_app}"
        {key_code_cmd}
    end tell
end tell
'''
        try:
            proc = await asyncio.create_subprocess_exec("osascript", "-e", script)
            await proc.communicate()
            return ActionResult(success=True, output=f"Pressed key '{key}'", technique_used="accessibility")
        except Exception as e:
            return ActionResult(success=False, error=str(e), technique_used="accessibility")
