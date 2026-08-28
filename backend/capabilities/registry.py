"""
JARVIS Capability Registry
Universal registry of application capabilities, supported automation interfaces,
and dynamic fallback routing (Native -> AppleScript -> Accessibility -> Browser -> App Store).
"""

import os
import subprocess
import urllib.parse
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field


class AppCapabilityProfile(BaseModel):
    name: str
    display_name: str
    bundle_id: Optional[str] = None
    capabilities: List[str] = Field(default_factory=lambda: ["open", "close", "focus"])
    interfaces: List[str] = Field(default_factory=lambda: ["native_api", "accessibility"])
    web_fallback_url: Optional[str] = None
    app_store_search: Optional[str] = None
    is_scriptable: bool = False
    requires_permissions: List[str] = Field(default_factory=list)


class CapabilityRegistry:
    """
    Maintains application capability metadata and selects the optimal
    execution interface for any task without hardcoding static commands.
    """

    def __init__(self):
        self._profiles: Dict[str, AppCapabilityProfile] = {}
        self._initialize_standard_profiles()

    def _initialize_standard_profiles(self):
        standard = [
            AppCapabilityProfile(
                name="safari",
                display_name="Safari",
                bundle_id="com.apple.Safari",
                capabilities=["open", "close", "navigate", "search", "click", "type", "read", "scroll"],
                interfaces=["applescript", "browser", "accessibility", "native_api"],
                is_scriptable=True
            ),
            AppCapabilityProfile(
                name="chrome",
                display_name="Google Chrome",
                bundle_id="com.google.Chrome",
                capabilities=["open", "close", "navigate", "search", "click", "type", "read", "scroll"],
                interfaces=["applescript", "browser", "accessibility", "native_api"],
                is_scriptable=True
            ),
            AppCapabilityProfile(
                name="whatsapp",
                display_name="WhatsApp",
                bundle_id="net.whatsapp.WhatsApp",
                capabilities=["open", "close", "search", "send", "click", "type", "read"],
                interfaces=["accessibility", "browser", "native_api"],
                web_fallback_url="https://web.whatsapp.com",
                app_store_search="WhatsApp",
                requires_permissions=["accessibility"]
            ),
            AppCapabilityProfile(
                name="telegram",
                display_name="Telegram",
                bundle_id="ru.keepcoder.Telegram",
                capabilities=["open", "close", "search", "send", "click", "type", "read"],
                interfaces=["accessibility", "browser", "native_api"],
                web_fallback_url="https://web.telegram.org",
                app_store_search="Telegram",
                requires_permissions=["accessibility"]
            ),
            AppCapabilityProfile(
                name="spotify",
                display_name="Spotify",
                bundle_id="com.spotify.client",
                capabilities=["open", "close", "play", "pause", "search", "select", "click"],
                interfaces=["applescript", "accessibility", "browser", "native_api"],
                web_fallback_url="https://open.spotify.com",
                app_store_search="Spotify",
                is_scriptable=True
            ),
            AppCapabilityProfile(
                name="vscode",
                display_name="Visual Studio Code",
                bundle_id="com.microsoft.VSCode",
                capabilities=["open", "close", "open_project", "run", "edit", "terminal"],
                interfaces=["native_api", "accessibility"],
                app_store_search="Visual Studio Code"
            ),
            AppCapabilityProfile(
                name="terminal",
                display_name="Terminal",
                bundle_id="com.apple.Terminal",
                capabilities=["open", "close", "run", "execute"],
                interfaces=["applescript", "native_api"],
                is_scriptable=True
            ),
            AppCapabilityProfile(
                name="finder",
                display_name="Finder",
                bundle_id="com.apple.finder",
                capabilities=["open", "reveal", "search", "select"],
                interfaces=["applescript", "native_api"],
                is_scriptable=True
            ),
            AppCapabilityProfile(
                name="mail",
                display_name="Mail",
                bundle_id="com.apple.mail",
                capabilities=["open", "close", "send", "read", "search"],
                interfaces=["applescript", "accessibility", "native_api"],
                is_scriptable=True
            ),
            AppCapabilityProfile(
                name="gmail",
                display_name="Gmail",
                capabilities=["open", "send", "read", "search"],
                interfaces=["browser"],
                web_fallback_url="https://mail.google.com"
            ),
            AppCapabilityProfile(
                name="youtube",
                display_name="YouTube",
                capabilities=["open", "search", "play", "watch"],
                interfaces=["browser"],
                web_fallback_url="https://www.youtube.com"
            ),
            AppCapabilityProfile(
                name="notes",
                display_name="Notes",
                bundle_id="com.apple.Notes",
                capabilities=["open", "close", "read", "type", "create"],
                interfaces=["applescript", "accessibility", "native_api"],
                is_scriptable=True
            ),
            AppCapabilityProfile(
                name="music",
                display_name="Music",
                bundle_id="com.apple.Music",
                capabilities=["open", "close", "play", "pause", "search"],
                interfaces=["applescript", "accessibility", "native_api"],
                is_scriptable=True
            ),
            AppCapabilityProfile(
                name="settings",
                display_name="System Settings",
                bundle_id="com.apple.systempreferences",
                capabilities=["open", "configure", "inspect"],
                interfaces=["native_api", "applescript"]
            )
        ]

        for p in standard:
            self._profiles[p.name.lower()] = p

    def get_profile(self, app_name: str) -> AppCapabilityProfile:
        """Retrieve profile or dynamically generate generic profile for any unknown application."""
        clean = app_name.lower().strip()
        # Aliases
        aliases = {
            "google chrome": "chrome",
            "vs code": "vscode",
            "visual studio code": "vscode",
            "code": "vscode",
            "apple music": "music",
            "preferences": "settings",
            "system settings": "settings",
            "app store": "app store",
            "mac app store": "app store"
        }
        mapped = aliases.get(clean, clean)
        if mapped in self._profiles:
            return self._profiles[mapped]

        # Dynamically synthesize generic profile for unfamiliar applications
        display = app_name.strip().title()
        return AppCapabilityProfile(
            name=clean,
            display_name=display,
            capabilities=["open", "close", "focus", "click", "type", "search", "read", "select"],
            interfaces=["native_api", "accessibility"],
            app_store_search=display
        )

    def register_profile(self, profile: AppCapabilityProfile):
        """Add or update an application capability profile."""
        self._profiles[profile.name.lower()] = profile

    def discover_execution_method(
        self,
        app_name: str,
        desired_action: str = "open"
    ) -> Dict[str, Any]:
        """
        Dynamically determine the optimal execution method for a given application:
        1. Check if application is installed locally.
        2. If installed -> choose between Native API, AppleScript, or Accessibility API.
        3. If not installed -> check if browser fallback URL is available.
        4. If not installed and no browser fallback -> route to Mac App Store.
        """
        profile = self.get_profile(app_name)
        installed, app_path = self.check_app_installed(profile.display_name)

        if installed:
            # Determine preferred interface
            if desired_action in ("open", "close", "focus", "launch"):
                method = "native_api"
            elif profile.is_scriptable and desired_action in ("search", "play", "navigate", "run", "read"):
                method = "applescript"
            else:
                method = "accessibility"

            return {
                "available": True,
                "execution_type": "native",
                "method": method,
                "app_name": profile.display_name,
                "path": app_path,
                "capabilities": profile.capabilities
            }

        # Not installed natively: Check if browser fallback is appropriate
        if profile.web_fallback_url:
            return {
                "available": True,
                "execution_type": "browser_fallback",
                "method": "browser",
                "app_name": profile.display_name,
                "web_url": profile.web_fallback_url,
                "capabilities": profile.capabilities
            }

        # Installation required: Mac App Store
        encoded_query = urllib.parse.quote(profile.app_store_search or profile.display_name)
        store_url = f"macappstore://showSearchResults?q={encoded_query}"
        return {
            "available": False,
            "execution_type": "install_required",
            "method": "app_store",
            "app_name": profile.display_name,
            "store_url": store_url,
            "capabilities": profile.capabilities
        }

    def discover_app(self, app_name: str, desired_action: str = "open") -> Dict[str, Any]:
        """Discover profile and optimal execution method for application."""
        return self.discover_execution_method(app_name, desired_action=desired_action)

    @staticmethod
    def check_app_installed(app_name: str) -> Tuple[bool, Optional[str]]:
        """Check filesystem and Spotlight to detect installed .app bundles."""
        from backend.tools.app_control import AppControlTool
        return AppControlTool.check_app_installed(app_name)

