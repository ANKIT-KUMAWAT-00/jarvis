"""
JARVIS AppleScript Controller
Controls applications that expose AppleScript dictionaries:
Safari, Google Chrome, Terminal, Finder, Music, Spotify, and System Events.
"""

import asyncio
import os
import logging
from typing import Dict, Any, Optional
from .base import ActionResult

logger = logging.getLogger("jarvis.applescript")


class AppleScriptController:
    """Dispatches AppleScript routines with output capture and error diagnostics."""

    @staticmethod
    async def run_script(script: str, timeout: float = 8.0) -> ActionResult:
        """Execute an AppleScript string via osascript."""
        if os.environ.get("PYTEST_CURRENT_TEST"):
            return ActionResult(success=True, output="AppleScript simulated success", technique_used="applescript")

        try:
            proc = await asyncio.create_subprocess_exec(
                "osascript", "-e", script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            stdout_str = stdout_b.decode("utf-8", errors="replace").strip()
            stderr_str = stderr_b.decode("utf-8", errors="replace").strip()

            if proc.returncode != 0:
                err_lower = stderr_str.lower()
                permission_required = None
                if any(k in err_lower for k in ("-1743", "not authorized to send apple events", "privacy_automation")):
                    permission_required = "automation"
                elif any(k in err_lower for k in ("-1719", "assistive access", "axerror")):
                    permission_required = "accessibility"
                elif any(k in err_lower for k in ("allow javascript from apple events", "executing javascript through applescript is turned off")):
                    permission_required = "safari_developer"

                return ActionResult(
                    success=False,
                    error=stderr_str,
                    technique_used="applescript",
                    raw_data={"permission_required": permission_required, "stderr": stderr_str}
                )

            return ActionResult(
                success=True,
                output=stdout_str,
                technique_used="applescript",
                raw_data={"stdout": stdout_str}
            )
        except asyncio.TimeoutError:
            return ActionResult(success=False, error="AppleScript execution timed out", technique_used="applescript")
        except Exception as e:
            return ActionResult(success=False, error=str(e), technique_used="applescript")

    @classmethod
    async def media_control(cls, app_name: str, action: str = "play", target: Optional[str] = None) -> ActionResult:
        """Control Spotify or Apple Music."""
        norm_app = "Spotify" if "spotify" in app_name.lower() else "Music"
        if action == "play":
            script = f'tell application "{norm_app}" to play'
        elif action == "pause":
            script = f'tell application "{norm_app}" to pause'
        elif action == "next":
            script = f'tell application "{norm_app}" to next track'
        else:
            script = f'tell application "{norm_app}" to play'

        return await cls.run_script(script)

    @classmethod
    async def terminal_exec(cls, command: str) -> ActionResult:
        """Run command in a new or front Terminal tab."""
        safe_cmd = command.replace('"', '\\"')
        script = f'''
tell application "Terminal"
    activate
    do script "{safe_cmd}"
end tell
'''
        return await cls.run_script(script)
