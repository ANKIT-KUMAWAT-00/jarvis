"""
JARVIS macOS Application Control Tool
Enables launching, managing, and closing macOS applications and opening web URLs.
"""

import asyncio
import subprocess
import os
import shutil
from typing import Dict, Any, List, Optional
from .base import Tool, ToolResult, VerificationResult
from backend.security.permissions import ActionLevel


class AppControlTool(Tool):
    name = "app_control"
    description = (
        "Controls macOS applications and URLs. "
        "Actions: 'open_app' (launch an application by name like Calculator, Calendar, Safari, Notes, Mail, Spotify, Clock, Chrome), "
        "'open_url' (open any web URL in default browser), "
        "'close_app' (quit an application gracefully), "
        "'list_apps' (list running or available common macOS applications)."
    )
    permission_level = ActionLevel.LEVEL_1_SAFE_WRITE
    timeout_seconds = 15.0


    COMMON_APP_MAP = {
        "calculator": "Calculator",
        "calendar": "Calendar",
        "clock": "Clock",
        "mail": "Mail",
        "email": "Mail",
        "messages": "Messages",
        "imessage": "Messages",
        "notes": "Notes",
        "reminders": "Reminders",
        "safari": "Safari",
        "chrome": "Google Chrome",
        "google chrome": "Google Chrome",
        "terminal": "Terminal",
        "spotify": "Spotify",
        "slack": "Slack",
        "zoom": "zoom.us",
        "vscode": "Visual Studio Code",
        "code": "Visual Studio Code",
        "settings": "System Settings",
        "system settings": "System Settings",
        "preferences": "System Settings",
        "music": "Music",
        "photos": "Photos",
        "maps": "Maps",
        "facetime": "FaceTime",
        "textedit": "TextEdit"
    }

    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        action = params.get("action", "open_app")
        app_name = params.get("app_name") or params.get("name") or params.get("target", "")
        url = params.get("url", "")

        if action == "open_app":
            return await self._open_app(str(app_name).strip())
        elif action == "open_url":
            return await self._open_url(str(url or app_name).strip())
        elif action == "close_app":
            return await self._close_app(str(app_name).strip())
        elif action == "list_apps":
            return await self._list_apps()
        else:
            return ToolResult(
                success=False,
                output="",
                error=f"Unknown app_control action '{action}'. Supported: open_app, open_url, close_app, list_apps"
            )

    async def _open_app(self, raw_name: str) -> ToolResult:
        if not raw_name:
            return ToolResult(success=False, output="", error="app_name parameter is required.")

        normalized_name = self.COMMON_APP_MAP.get(raw_name.lower(), raw_name)

        try:
            # Use macOS native open -a
            proc = await asyncio.create_subprocess_exec(
                "open", "-a", normalized_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                err = stderr.decode().strip()
                # Fallback: try AppleScript
                as_cmd = f'tell application "{normalized_name}" to activate'
                proc2 = await asyncio.create_subprocess_exec(
                    "osascript", "-e", as_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                _, stderr2 = await proc2.communicate()
                if proc2.returncode != 0:
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Could not open application '{normalized_name}': {stderr2.decode().strip() or err}"
                    )

            # Brief pause to verify process launched
            await asyncio.sleep(0.5)
            return ToolResult(
                success=True,
                output=f"Successfully opened application: '{normalized_name}'.",
                raw_data={"app_name": normalized_name, "launched": True}
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Failed to open app '{raw_name}': {str(e)}")

    async def _open_url(self, url: str) -> ToolResult:
        if not url:
            return ToolResult(success=False, output="", error="url parameter is required.")

        if not (url.startswith("http://") or url.startswith("https://") or url.startswith("mailto:") or url.startswith("imessage:")):
            url = f"https://{url}"

        try:
            proc = await asyncio.create_subprocess_exec(
                "open", url,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode != 0:
                return ToolResult(success=False, output="", error=f"Could not open URL: {stderr.decode().strip()}")

            return ToolResult(
                success=True,
                output=f"Successfully launched URL in default browser: '{url}'.",
                raw_data={"url": url}
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Failed to open URL '{url}': {str(e)}")

    async def _close_app(self, raw_name: str) -> ToolResult:
        if not raw_name:
            return ToolResult(success=False, output="", error="app_name parameter is required.")

        normalized_name = self.COMMON_APP_MAP.get(raw_name.lower(), raw_name)
        as_cmd = f'tell application "{normalized_name}" to quit'
        try:
            proc = await asyncio.create_subprocess_exec(
                "osascript", "-e", as_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode != 0:
                return ToolResult(success=False, output="", error=f"Could not close application: {stderr.decode().strip()}")

            return ToolResult(
                success=True,
                output=f"Successfully closed application: '{normalized_name}'.",
                raw_data={"app_name": normalized_name, "closed": True}
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Failed to close app '{raw_name}': {str(e)}")

    async def _list_apps(self) -> ToolResult:
        try:
            # Query running applications with UI
            as_cmd = 'tell application "System Events" to get name of every application process whose visible is true'
            proc = await asyncio.create_subprocess_exec(
                "osascript", "-e", as_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            running = [app.strip() for app in stdout.decode().split(",") if app.strip()] if proc.returncode == 0 else []

            return ToolResult(
                success=True,
                output={"running_apps": running, "supported_common_apps": list(self.COMMON_APP_MAP.values())},
                raw_data={"running": running}
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Failed to list applications: {str(e)}")

    def verify(self, result: ToolResult, expectation: Dict[str, Any]) -> VerificationResult:
        if not result.success:
            return VerificationResult(
                verified=False,
                expected="Application or URL launched successfully",
                actual=f"Failure: {result.error}",
                message="App control action failed."
            )
        return VerificationResult(
            verified=True,
            expected="Application or URL active",
            actual=str(result.output),
            message="macOS application control verified."
        )
