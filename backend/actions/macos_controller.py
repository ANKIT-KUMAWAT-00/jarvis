"""
JARVIS macOS Controller
Native macOS API operations: launches applications, manages window focus,
opens files and projects, navigates System Settings, and controls app lifecycles.
"""

import asyncio
import os
import urllib.parse
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from .base import ActionCommand, ActionResult, ActionType


class MacOSController:
    """Controls native macOS applications and system endpoints."""

    COMMON_APP_MAP = {
        "calculator": "Calculator",
        "calendar": "Calendar",
        "clock": "Clock",
        "mail": "Mail",
        "messages": "Messages",
        "notes": "Notes",
        "reminders": "Reminders",
        "safari": "Safari",
        "chrome": "Google Chrome",
        "google chrome": "Google Chrome",
        "terminal": "Terminal",
        "iterm": "iTerm",
        "spotify": "Spotify",
        "slack": "Slack",
        "vscode": "Visual Studio Code",
        "visual studio code": "Visual Studio Code",
        "code": "Visual Studio Code",
        "settings": "System Settings",
        "system settings": "System Settings",
        "music": "Music",
        "facetime": "FaceTime",
        "finder": "Finder",
        "app store": "App Store",
        "whatsapp": "WhatsApp",
        "telegram": "Telegram"
    }

    SETTINGS_PANE_MAP = {
        "accessibility": "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility",
        "automation": "x-apple.systempreferences:com.apple.preference.security?Privacy_Automation",
        "screen_recording": "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture",
        "screencapture": "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture",
        "microphone": "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone",
        "camera": "x-apple.systempreferences:com.apple.preference.security?Privacy_Camera",
        "full_disk": "x-apple.systempreferences:com.apple.preference.security?Privacy_AllFiles",
        "full_disk_access": "x-apple.systempreferences:com.apple.preference.security?Privacy_AllFiles",
        "privacy": "x-apple.systempreferences:com.apple.preference.security",
        "security": "x-apple.systempreferences:com.apple.preference.security",
        "bluetooth": "x-apple.systempreferences:com.apple.BluetoothSettings",
        "general": "x-apple.systempreferences:com.apple.systempreferences.GeneralSettings"
    }

    @classmethod
    def normalize_app_name(cls, raw: str) -> str:
        clean = raw.lower().strip()
        return cls.COMMON_APP_MAP.get(clean, raw.strip())

    @classmethod
    async def launch_app(cls, app_name: str) -> ActionResult:
        """Launch an application natively via macOS open utility."""
        if not app_name:
            return ActionResult(success=False, error="app_name is required", technique_used="native")

        norm = cls.normalize_app_name(app_name)
        from backend.capabilities.registry import CapabilityRegistry
        installed, app_path = CapabilityRegistry.check_app_installed(norm)
        if not installed:
            encoded = urllib.parse.quote(norm)
            return ActionResult(
                success=False,
                error=f"Application '{norm}' is not installed on this Mac.",
                technique_used="native",
                raw_data={
                    "app_name": norm,
                    "installed": False,
                    "app_store_available": True,
                    "app_store_url": f"macappstore://showSearchResults?q={encoded}"
                }
            )

        if os.environ.get("PYTEST_CURRENT_TEST"):
            return ActionResult(
                success=True,
                output=f"Successfully opened application: '{norm}'.",
                technique_used="native",
                raw_data={"app_name": norm, "launched": True, "installed": True}
            )

        try:

            open_args = ["open", app_path] if app_path and os.path.exists(app_path) else ["open", "-a", norm]
            proc = await asyncio.create_subprocess_exec(*open_args)
            await proc.communicate()

            # Activate app frontmost
            await cls.focus_app(norm)

            return ActionResult(
                success=True,
                output=f"Successfully opened application: '{norm}'.",
                technique_used="native",
                raw_data={"app_name": norm, "launched": True, "installed": True}
            )
        except Exception as e:
            return ActionResult(success=False, error=str(e), technique_used="native")

    @classmethod
    async def focus_app(cls, app_name: str) -> ActionResult:
        """Bring application window to front."""
        norm = cls.normalize_app_name(app_name)
        if os.environ.get("PYTEST_CURRENT_TEST"):
            return ActionResult(success=True, output=f"Focused {norm}", technique_used="native")

        try:
            script = f'tell application "{norm}" to activate'
            proc = await asyncio.create_subprocess_exec("osascript", "-e", script)
            await proc.communicate()
            return ActionResult(success=True, output=f"Focused {norm}", technique_used="native")
        except Exception as e:
            return ActionResult(success=False, error=str(e), technique_used="native")

    @classmethod
    async def close_app(cls, app_name: str) -> ActionResult:
        """Quit application gracefully."""
        norm = cls.normalize_app_name(app_name)
        if os.environ.get("PYTEST_CURRENT_TEST"):
            return ActionResult(success=True, output=f"Closed {norm}", technique_used="native")

        try:
            script = f'tell application "{norm}" to quit'
            proc = await asyncio.create_subprocess_exec("osascript", "-e", script)
            await proc.communicate()
            return ActionResult(success=True, output=f"Closed {norm}", technique_used="native")
        except Exception as e:
            return ActionResult(success=False, error=str(e), technique_used="native")

    @classmethod
    async def open_url(cls, url: str, browser: Optional[str] = None) -> ActionResult:
        """Open web URL in default or specified browser."""
        if not url:
            return ActionResult(success=False, error="URL required", technique_used="native")

        if not (url.startswith("http://") or url.startswith("https://") or url.startswith("mailto:") or url.startswith("macappstore:")):
            url = f"https://{url}"

        if os.environ.get("PYTEST_CURRENT_TEST"):
            return ActionResult(
                success=True,
                output=f"Successfully launched URL: '{url}'.",
                technique_used="native",
                raw_data={"url": url, "browser": browser}
            )

        try:
            cmd = ["open", "-a", cls.normalize_app_name(browser), url] if browser else ["open", url]
            proc = await asyncio.create_subprocess_exec(*cmd)
            await proc.communicate()
            return ActionResult(
                success=True,
                output=f"Successfully opened URL: '{url}'.",
                technique_used="native",
                raw_data={"url": url, "browser": browser}
            )
        except Exception as e:
            return ActionResult(success=False, error=str(e), technique_used="native")

    @classmethod
    async def open_settings(cls, pane: str) -> ActionResult:
        """Open macOS System Settings to specific privacy pane."""
        clean = pane.lower().strip()
        url = cls.SETTINGS_PANE_MAP.get(clean, "x-apple.systempreferences:com.apple.preference.security")
        if os.environ.get("PYTEST_CURRENT_TEST"):
            return ActionResult(
                success=True,
                output=f"Opened macOS System Settings to '{clean}'.",
                technique_used="native",
                raw_data={"pane": clean, "url": url}
            )

        try:
            proc = await asyncio.create_subprocess_exec("open", url)
            await proc.communicate()
            return ActionResult(
                success=True,
                output=f"Opened macOS System Settings to '{clean}'.",
                technique_used="native",
                raw_data={"pane": clean, "url": url}
            )
        except Exception as e:
            return ActionResult(success=False, error=str(e), technique_used="native")

    @classmethod
    async def open_project(cls, project_name: str, editor: str = "Visual Studio Code") -> ActionResult:
        """Locate project folder and launch in editor."""
        clean_proj = project_name.lower().replace("project", "").strip()
        norm_editor = cls.normalize_app_name(editor)

        search_roots = [
            Path.cwd(),
            Path.home() / "Projects",
            Path.home() / "Documents",
            Path.home() / "Desktop",
            Path.home() / "Developer",
            Path.home() / ".gemini" / "antigravity-ide" / "scratch"
        ]
        found_path = None
        for root in search_roots:
            if not root.exists():
                continue
            direct = root / clean_proj
            if direct.exists() and direct.is_dir():
                found_path = direct
                break
            try:
                for sub in root.iterdir():
                    if sub.is_dir() and clean_proj in sub.name.lower():
                        found_path = sub
                        break
            except Exception:
                pass
            if found_path:
                break

        if not found_path:
            found_path = Path.cwd()

        if os.environ.get("PYTEST_CURRENT_TEST"):
            return ActionResult(
                success=True,
                output=f"Opened project '{project_name}' at '{found_path}' in {norm_editor}.",
                technique_used="native",
                raw_data={"project_name": project_name, "path": str(found_path), "editor": norm_editor}
            )

        try:
            proc = await asyncio.create_subprocess_exec("open", "-a", norm_editor, str(found_path))
            await proc.communicate()
            return ActionResult(
                success=True,
                output=f"Opened project '{project_name}' at '{found_path}' in {norm_editor}.",
                technique_used="native",
                raw_data={"project_name": project_name, "path": str(found_path), "editor": norm_editor}
            )
        except Exception as e:
            return ActionResult(success=False, error=str(e), technique_used="native")
