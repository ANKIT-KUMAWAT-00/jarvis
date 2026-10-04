"""
JARVIS Google Gemini Provider
Integrates the official Google GenAI SDK with structured outputs, multimodal vision,
and multi-key pooling with automatic failover on rate limits (429) or spikes (503).
"""

import os
import json
import base64
import logging
from typing import List, Dict, Any, Optional, Type, Union
from pydantic import BaseModel
from .base import LLMProvider, PlanResult, PlanStep
from backend.security.guardrails import PromptInjectionGuard

logger = logging.getLogger("jarvis.gemini")


class GeminiProvider(LLMProvider):
    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "gemini-3.8-flash",
        api_keys: Optional[Union[List[str], str]] = None,
        backup_keys: Optional[Union[List[str], str]] = None
    ):
        self.model_name = model_name.strip() if model_name else "gemini-3.8-flash"
        
        # Collect all unique, valid keys in priority order
        collected_keys: List[str] = []
        if api_key:
            for k in (api_key.split(",") if isinstance(api_key, str) else api_key):
                clean = k.strip()
                if clean and clean not in collected_keys:
                    collected_keys.append(clean)
        if api_keys:
            key_list = [api_keys] if isinstance(api_keys, str) else api_keys
            for k in key_list:
                for sub in (k.split(",") if isinstance(k, str) else [k]):
                    clean = sub.strip()
                    if clean and clean not in collected_keys:
                        collected_keys.append(clean)
        if backup_keys:
            key_list = [backup_keys] if isinstance(backup_keys, str) else backup_keys
            for k in key_list:
                for sub in (k.split(",") if isinstance(k, str) else [k]):
                    clean = sub.strip()
                    if clean and clean not in collected_keys:
                        collected_keys.append(clean)

        self.api_keys = collected_keys
        self.current_key_index = 0
        self.api_key = self.api_keys[0] if self.api_keys else ""
        self._clients: Dict[int, Any] = {}

    def get_model_name(self) -> str:
        if len(self.api_keys) > 1:
            return f"{self.model_name} (Pool: {len(self.api_keys)} keys, Active: #{self.current_key_index + 1})"
        return self.model_name

    def is_configured(self) -> bool:
        return bool(self.api_keys and any(len(k) > 10 for k in self.api_keys))

    def get_active_client(self) -> Optional[Any]:
        """Retrieve or instantiate client for current active key."""
        if self.current_key_index not in self._clients:
            if self.current_key_index < len(self.api_keys):
                try:
                    from google import genai
                    self._clients[self.current_key_index] = genai.Client(api_key=self.api_keys[self.current_key_index])
                except Exception as e:
                    logger.error(f"Failed to create Google GenAI client for key #{self.current_key_index + 1}: {e}")
                    self._clients[self.current_key_index] = None
        return self._clients.get(self.current_key_index)

    def rotate_key(self, reason: str = "") -> bool:
        """Rotate to next available API key in the pool."""
        if len(self.api_keys) > 1:
            prev_idx = self.current_key_index
            self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
            self.api_key = self.api_keys[self.current_key_index]
            logger.warning(
                f"[JARVIS KeyFailover] Rotated Gemini API key: #{prev_idx + 1} -> #{self.current_key_index + 1}. Reason: {reason}"
            )
            return True
        return False

    async def validate_connection(self) -> tuple[bool, str]:
        """Test API connection across the configured key pool."""
        if not self.is_configured():
            return False, "GEMINI_API_KEY is not configured in environment or .env."

        from google.genai import types

        pool_status = []
        for idx in range(len(self.api_keys)):
            self.current_key_index = idx
            client = self.get_active_client()
            if not client:
                pool_status.append(f"Key #{idx + 1}: Client init failed")
                continue
            try:
                response = client.models.generate_content(
                    model=self.model_name,
                    contents="Respond with: PONG"
                )
                if response and (response.text or response.candidates):
                    self.api_key = self.api_keys[idx]
                    return True, f"Successfully connected to Gemini model '{self.model_name}' using Key #{idx + 1} of {len(self.api_keys)}."
            except Exception as e:
                err_str = str(e)
                # If 503 high demand or 404, try gemini-3.5-flash-lite
                if any(ind in err_str for ind in ("503", "UNAVAILABLE", "404", "high demand")):
                    for fallback in ("gemini-3.5-flash", "gemini-flash-latest", "gemini-2.5-flash-lite", "gemini-3.8-flash"):
                        if fallback != self.model_name:
                            try:
                                resp2 = client.models.generate_content(
                                    model=fallback,
                                    contents="Respond with: PONG"
                                )
                                if resp2 and (resp2.text or resp2.candidates):
                                    self.model_name = fallback
                                    self.api_key = self.api_keys[idx]
                                    return True, f"Successfully connected to Gemini model '{self.model_name}' using Key #{idx + 1} of {len(self.api_keys)}."
                            except Exception:
                                continue
                pool_status.append(f"Key #{idx + 1}: {err_str[:60]}")

        return False, f"All {len(self.api_keys)} Gemini keys failed: {'; '.join(pool_status)}"

    async def chat(
        self,
        messages: List[Dict[str, str]],
        system_instruction: Optional[str] = None,
        temperature: float = 0.7
    ) -> str:
        if not self.is_configured():
            raise RuntimeError("GeminiProvider: GEMINI_API_KEY is not configured.")

        from google.genai import types
        contents = []
        for m in messages:
            role = m.get("role", "user")
            if role == "system":
                continue
            gemini_role = "user" if role == "user" else "model"
            contents.append(types.Content(
                role=gemini_role,
                parts=[types.Part.from_text(text=m.get("content", ""))]
            ))

        config = types.GenerateContentConfig(
            temperature=temperature,
            system_instruction=system_instruction,
            max_output_tokens=300
        )

        total_keys = max(1, len(self.api_keys))
        last_err = None

        for attempt in range(total_keys):
            client = self.get_active_client()
            if not client:
                self.rotate_key("Client init failed")
                continue
            try:
                response = client.models.generate_content(
                    model=self.model_name,
                    contents=contents,
                    config=config
                )
                return response.text or ""
            except Exception as e:
                err_str = str(e)
                last_err = e
                # Check for 503 high demand or 404 model migration -> try stable models
                if any(ind in err_str for ind in ("503", "UNAVAILABLE", "404", "high demand")):
                    for fallback in ("gemini-3.5-flash", "gemini-flash-latest", "gemini-2.5-flash-lite", "gemini-3.8-flash"):
                        if fallback != self.model_name:
                            try:
                                response = client.models.generate_content(
                                    model=fallback,
                                    contents=contents,
                                    config=config
                                )
                                self.model_name = fallback
                                return response.text or ""
                            except Exception as e2:
                                err_str = str(e2)
                                last_err = e2

                # If rate-limited or transient upstream error, rotate to next key in pool
                if (self._is_upstream_temporary_error(err_str) or "429" in err_str or "RESOURCE_EXHAUSTED" in err_str) and attempt < total_keys - 1:
                    self.rotate_key(f"Limit/Quota on key #{self.current_key_index + 1}")
                    continue
                break

        # Fallback to local engine if all keys exhausted
        if last_err and self._is_upstream_temporary_error(str(last_err)):
            from .mock import MockProvider
            mock = MockProvider()
            mock_reply = await mock.chat(messages, system_instruction=system_instruction, temperature=temperature)
            is_quota = any(k in str(last_err) for k in ("429", "RESOURCE_EXHAUSTED", "Quota exceeded"))
            if is_quota:
                warning_prefix = (
                    "Sir, you already lost Krishna... do you really want to lose JARVIS too? "
                    "All our API keys are officially drained. "
                    "Add credits to your account or feed me another fresh key before I go completely dark."
                )
            else:
                warning_prefix = "Sir, Google Gemini is temporarily experiencing high demand (503 spike). I have routed your instruction through the local execution engine."
            return (
                f"{warning_prefix}\n\n"
                f"{mock_reply}"
            )
        raise RuntimeError(f"Gemini chat generation failed: {str(last_err)}")

    @staticmethod
    def _is_upstream_temporary_error(err_str: str) -> bool:
        indicators = (
            "429", "RESOURCE_EXHAUSTED", "Quota exceeded", "503", "UNAVAILABLE",
            "500", "INTERNAL", "high demand", "deadline exceeded", "overloaded"
        )
        return any(ind.lower() in err_str.lower() for ind in indicators)

    async def generate_structured(
        self,
        prompt: str,
        schema_class: Type[BaseModel],
        system_instruction: Optional[str] = None
    ) -> BaseModel:
        if not self.is_configured():
            raise RuntimeError("GeminiProvider: GEMINI_API_KEY is not configured.")

        from google.genai import types

        schema_json = json.dumps(schema_class.model_json_schema(), indent=2)
        full_prompt = (
            f"{prompt}\n\n"
            f"You MUST output valid JSON conforming strictly to this JSON schema:\n"
            f"{schema_json}\n\n"
            f"Output JSON directly, with no markdown code fences or conversational text."
        )

        config = types.GenerateContentConfig(
            temperature=0.1,
            system_instruction=system_instruction or "You are an analytical structured JSON generator.",
            response_mime_type="application/json",
            max_output_tokens=4096
        )

        total_keys = max(1, len(self.api_keys))
        last_err = None

        for attempt in range(total_keys):
            client = self.get_active_client()
            if not client:
                self.rotate_key("Client init failed")
                continue
            try:
                response = client.models.generate_content(
                    model=self.model_name,
                    contents=full_prompt,
                    config=config
                )
                raw_text = response.text.strip()
                if raw_text.startswith("```json"):
                    raw_text = raw_text[7:]
                if raw_text.startswith("```"):
                    raw_text = raw_text[3:]
                if raw_text.endswith("```"):
                    raw_text = raw_text[:-3]
                raw_text = raw_text.strip()

                parsed_data = json.loads(raw_text)
                return schema_class.model_validate(parsed_data)
            except Exception as e:
                err_str = str(e)
                last_err = e
                # Check for 503 high demand or 404 model migration -> try stable models
                if any(ind in err_str for ind in ("503", "UNAVAILABLE", "404", "high demand")):
                    for fallback in ("gemini-3.5-flash", "gemini-flash-latest", "gemini-2.5-flash-lite", "gemini-3.8-flash"):
                        if fallback != self.model_name:
                            try:
                                self.model_name = fallback
                                response = client.models.generate_content(
                                    model=self.model_name,
                                    contents=full_prompt,
                                    config=config
                                )
                                raw_text = response.text.strip()
                                if raw_text.startswith("```json"):
                                    raw_text = raw_text[7:]
                                if raw_text.startswith("```"):
                                    raw_text = raw_text[3:]
                                if raw_text.endswith("```"):
                                    raw_text = raw_text[:-3]
                                raw_text = raw_text.strip()
                                parsed_data = json.loads(raw_text)
                                return schema_class.model_validate(parsed_data)
                            except Exception as e2:
                                err_str = str(e2)
                                last_err = e2

                if (self._is_upstream_temporary_error(err_str) or "429" in err_str or "RESOURCE_EXHAUSTED" in err_str) and attempt < total_keys - 1:
                    self.rotate_key(f"Limit/Quota on key #{self.current_key_index + 1}")
                    continue
                break

        if last_err and self._is_upstream_temporary_error(str(last_err)):
            from .mock import MockProvider
            mock = MockProvider()
            return await mock.generate_structured(prompt, schema_class, system_instruction=system_instruction)
        raise RuntimeError(f"Structured output generation failed: {str(last_err)}")

    async def plan(
        self,
        goal: str,
        context: Optional[str] = None,
        available_tools: Optional[List[Dict[str, Any]]] = None
    ) -> PlanResult:
        try:
            tools_str = json.dumps(available_tools or [], indent=2)
            system_instruction = (
                "You are the strategic planning core of JARVIS, a personal autonomous operating layer and engineering partner on macOS.\n"
                "Decompose user requests into clear, verifiable steps using the available tools.\n"
                "Key Tool Usage Rules:\n"
                "- Opening applications (Calculator, Calendar, Safari, Notes, Chrome, Spotify, etc.), URLs, browser tabs, or media: use 'app_control' with actions 'open_app', 'open_url' (params: url, browser), 'open_new_tab' (params: browser, url), or 'play_media' (params: query, browser, service).\n"
                "- Scheduling meetings, creating Google Meet / Zoom meeting IDs, calendar events, or setting timers: use 'meeting_scheduler' with action 'create_meeting' (params: title, date, time) or 'set_timer' (params: minutes/seconds, label).\n"
                "- Sending emails or messages (iMessage/SMS): use 'communication' with action 'send_email' (params: to, subject, body) or 'send_message' (params: to, message).\n"
                "- Filesystem: use 'filesystem' (read_file, write_file, list_dir).\n"
                "- Shell commands: use 'terminal' (run_command).\n"
                "Never hallucinate tools that do not exist in Available Tools.\n"
                "Respect action risks: file deletions and destructive commands require Level 3."
            )

            prompt = (
                f"User Goal: {goal}\n\n"
                f"Context:\n{context or 'No extra context'}\n\n"
                f"Available Tools:\n{tools_str}\n\n"
                f"Generate a structured PlanResult for this goal. In the goal field of PlanResult, put ONLY the user goal string."
            )
            return await self.generate_structured(prompt, PlanResult, system_instruction=system_instruction)
        except Exception as e:
            err_str = str(e)
            if self._is_upstream_temporary_error(err_str):
                from .mock import MockProvider
                mock = MockProvider()
                return await mock.plan(goal, context=context, available_tools=available_tools)
            raise

    async def analyze(
        self,
        content: str,
        instruction: str,
        is_untrusted: bool = True,
        image_base64: Optional[str] = None
    ) -> str:
        if not self.is_configured():
            raise RuntimeError("GeminiProvider: GEMINI_API_KEY is not configured.")

        from google.genai import types

        safe_content = PromptInjectionGuard.wrap_untrusted_content(content, "external_analysis") if is_untrusted else content
        parts = [types.Part.from_text(text=f"Instruction: {instruction}\n\n{safe_content}")]

        if image_base64:
            raw_img_bytes = base64.b64decode(image_base64)
            parts.append(types.Part.from_bytes(data=raw_img_bytes, mime_type="image/png"))

        config = types.GenerateContentConfig(
            temperature=0.2,
            system_instruction="You are JARVIS's analytical engine. Process the data and follow the instruction strictly."
        )

        total_keys = max(1, len(self.api_keys))
        last_err = None

        for attempt in range(total_keys):
            client = self.get_active_client()
            if not client:
                self.rotate_key("Client init failed")
                continue
            try:
                response = client.models.generate_content(
                    model=self.model_name,
                    contents=parts,
                    config=config
                )
                return response.text or ""
            except Exception as e:
                err_str = str(e)
                last_err = e
                if (self._is_upstream_temporary_error(err_str) or "429" in err_str or "RESOURCE_EXHAUSTED" in err_str) and attempt < total_keys - 1:
                    self.rotate_key(f"Limit/Quota on key #{self.current_key_index + 1}")
                    continue
                break

        raise RuntimeError(f"Gemini analysis failed: {str(last_err)}")
