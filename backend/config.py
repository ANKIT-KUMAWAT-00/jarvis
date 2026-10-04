"""
JARVIS System Configuration Module
Handles environment variables, default paths, and system settings.
"""

import os
from typing import List, Optional
from pathlib import Path
from pydantic import BaseModel, Field

# Base Directory paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
FRONTEND_DIR = PROJECT_ROOT / "frontend"
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"
DEFAULT_NOTES_DIR = DATA_DIR / "notes"

# Ensure runtime directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_NOTES_DIR.mkdir(parents=True, exist_ok=True)


class JarvisConfig(BaseModel):
    """Configuration schema for JARVIS."""
    app_env: str = Field(default="development", description="Application environment")
    jarvis_name: str = Field(default="JARVIS", description="Assistant persona name")
    
    # Gemini Brain Configuration
    gemini_api_key: str = Field(default="", description="Primary Google Gemini API key")
    gemini_backup_api_key: str = Field(default="", description="Backup Google Gemini API key")
    gemini_backup_api_key_2: str = Field(default="", description="Tertiary Google Gemini API key")
    gemini_backup_api_key_3: str = Field(default="", description="Backup Google Gemini API key #4")
    gemini_backup_api_key_4: str = Field(default="", description="Backup Google Gemini API key #5")
    gemini_backup_api_key_5: str = Field(default="", description="Backup Google Gemini API key #6")
    gemini_backup_api_key_6: str = Field(default="", description="Backup Google Gemini API key #7")
    gemini_backup_api_key_7: str = Field(default="", description="Backup Google Gemini API key #8")
    gemini_backup_api_key_8: str = Field(default="", description="Backup Google Gemini API key #9")
    gemini_model: str = Field(default="gemini-3.5-flash", description="Configured Gemini model")
    
    # Workspace & Filesystem Boundaries
    workspace_root: Path = Field(default=PROJECT_ROOT, description="Primary safe workspace boundary")
    notes_dir: Path = Field(default=DEFAULT_NOTES_DIR, description="Local knowledge notes directory")
    
    # Execution & Self-Correction Limits
    max_agent_steps: int = Field(default=20, description="Maximum iterative steps per goal")
    max_repair_attempts: int = Field(default=3, description="Maximum automated self-repair attempts")
    
    # Feature Flags
    voice_enabled: bool = Field(default=True, description="Voice interaction active")
    screen_enabled: bool = Field(default=True, description="Screen capture & vision active")
    telegram_enabled: bool = Field(default=False, description="Telegram bot integration active")
    phone_enabled: bool = Field(default=False, description="Telephony integration active")
    memory_enabled: bool = Field(default=True, description="Persistent SQLite memory active")
    
    # Server & Networking
    host: str = Field(default="127.0.0.1", description="Server host (localhost for security)")
    port: int = Field(default=8010, description="Server port")
    
    # Voice Buffer Parameters
    voice_finish_ms: int = Field(default=900, description="Speech end detection window in milliseconds")
    
    # Database
    db_path: Path = Field(default=DATA_DIR / "jarvis_memory.db", description="SQLite database path")

    @property
    def all_gemini_keys(self) -> list[str]:
        """Return list of distinct configured Gemini API keys in priority order."""
        keys = []
        raw_sources = [
            self.gemini_api_key,
            self.gemini_backup_api_key,
            self.gemini_backup_api_key_2,
            self.gemini_backup_api_key_3,
            self.gemini_backup_api_key_4,
            self.gemini_backup_api_key_5,
            self.gemini_backup_api_key_6,
            self.gemini_backup_api_key_7,
            self.gemini_backup_api_key_8,
        ]
        # Also pick up any GEMINI_API_KEY* or GEMINI_BACKUP_API_KEY* from environment dynamically
        for env_k, env_v in sorted(os.environ.items()):
            if (env_k.startswith("GEMINI_API_KEY") or env_k.startswith("GEMINI_BACKUP_API_KEY")) and env_v:
                raw_sources.append(env_v)

        for raw in raw_sources:
            if raw:
                for k in raw.split(","):
                    clean = k.strip()
                    if clean and clean not in keys:
                        keys.append(clean)
        return keys

    @classmethod
    def load_from_env(cls) -> "JarvisConfig":
        """Load configuration from environment variables and .env file."""
        # Check for .env file in project root
        env_file = PROJECT_ROOT / ".env"
        if env_file.exists():
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, val = line.split("=", 1)
                        key = key.strip()
                        val = val.strip().strip("\"'")
                        # Set in environ if not set or previously empty
                        if key not in os.environ or not os.environ[key]:
                            os.environ[key] = val
                        elif val:
                            # Prefer explicit value from .env
                            os.environ[key] = val

        raw_workspace = os.getenv("WORKSPACE_ROOT")
        workspace = Path(raw_workspace).resolve() if raw_workspace else PROJECT_ROOT

        raw_notes = os.getenv("NOTES_DIR")
        notes = Path(raw_notes).resolve() if raw_notes else DEFAULT_NOTES_DIR

        return cls(
            app_env=os.getenv("APP_ENV", "development"),
            jarvis_name=os.getenv("JARVIS_NAME", "JARVIS"),
            gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
            gemini_backup_api_key=os.getenv("GEMINI_BACKUP_API_KEY", ""),
            gemini_backup_api_key_2=os.getenv("GEMINI_BACKUP_API_KEY_2", ""),
            gemini_backup_api_key_3=os.getenv("GEMINI_BACKUP_API_KEY_3", ""),
            gemini_backup_api_key_4=os.getenv("GEMINI_BACKUP_API_KEY_4", ""),
            gemini_backup_api_key_5=os.getenv("GEMINI_BACKUP_API_KEY_5", ""),
            gemini_backup_api_key_6=os.getenv("GEMINI_BACKUP_API_KEY_6", ""),
            gemini_backup_api_key_7=os.getenv("GEMINI_BACKUP_API_KEY_7", ""),
            gemini_backup_api_key_8=os.getenv("GEMINI_BACKUP_API_KEY_8", ""),
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash"),
            workspace_root=workspace,
            notes_dir=notes,
            max_agent_steps=int(os.getenv("MAX_AGENT_STEPS", "20")),
            max_repair_attempts=int(os.getenv("MAX_REPAIR_ATTEMPTS", "3")),
            voice_enabled=os.getenv("VOICE_ENABLED", "true").lower() in ("true", "1", "yes"),
            screen_enabled=os.getenv("SCREEN_ENABLED", "true").lower() in ("true", "1", "yes"),
            telegram_enabled=os.getenv("TELEGRAM_ENABLED", "false").lower() in ("true", "1", "yes"),
            phone_enabled=os.getenv("PHONE_ENABLED", "false").lower() in ("true", "1", "yes"),
            memory_enabled=os.getenv("MEMORY_ENABLED", "true").lower() in ("true", "1", "yes"),
            host=os.getenv("HOST", "127.0.0.1"),
            port=int(os.getenv("PORT", "8010")),
            voice_finish_ms=int(os.getenv("VOICE_FINISH_MS", "900")),
            db_path=DATA_DIR / "jarvis_memory.db",
        )

    def reload(self):
        """Reload configuration from disk."""
        updated = JarvisConfig.load_from_env()
        for field, val in updated.__dict__.items():
            setattr(self, field, val)

    @staticmethod
    def persist_api_key(api_key: str, backup_key: Optional[str] = None):
        """Write GEMINI_API_KEY and optional GEMINI_BACKUP_API_KEY directly to .env."""
        clean_key = api_key.strip()
        clean_backup = backup_key.strip() if backup_key else None
        env_file = PROJECT_ROOT / ".env"
        lines = []
        key_found = False
        backup_found = False
        if env_file.exists():
            with open(env_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
        
        new_lines = []
        for line in lines:
            if line.strip().startswith("GEMINI_API_KEY="):
                new_lines.append(f"GEMINI_API_KEY={clean_key}\n")
                key_found = True
            elif clean_backup is not None and line.strip().startswith("GEMINI_BACKUP_API_KEY="):
                new_lines.append(f"GEMINI_BACKUP_API_KEY={clean_backup}\n")
                backup_found = True
            else:
                new_lines.append(line)
        if not key_found:
            new_lines.append(f"GEMINI_API_KEY={clean_key}\n")
        if clean_backup is not None and not backup_found:
            new_lines.append(f"GEMINI_BACKUP_API_KEY={clean_backup}\n")

        with open(env_file, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        os.environ["GEMINI_API_KEY"] = clean_key
        if clean_backup is not None:
            os.environ["GEMINI_BACKUP_API_KEY"] = clean_backup


# Global singleton instance
config = JarvisConfig.load_from_env()

