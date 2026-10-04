"""
JARVIS Browser & Webpage Inspection Tool
Fetches web content, cleans HTML to semantic text, and strictly wraps results
in PromptInjectionGuard untrusted data boundaries.
"""

import time
import re
import urllib.request
import urllib.parse
from typing import Dict, Any, Optional
from .base import Tool, ToolResult, VerificationResult
from backend.security.permissions import ActionLevel
from backend.security.guardrails import PromptInjectionGuard


class BrowserTool(Tool):
    name: str = "browser"
    description: str = "Fetch and inspect website contents safely, extracting text and structural data as untrusted content."
    permission_level: ActionLevel = ActionLevel.LEVEL_0_READ

    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        start_time = time.time()
        url = params.get("url", "").strip()

        if not url:
            return ToolResult(success=False, output="", error="URL is required for browser tool.")

        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"

        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) JARVIS-AI-Agent/1.0"}
            )
            with urllib.request.urlopen(req, timeout=10.0) as response:
                content_type = response.headers.get("Content-Type", "")
                raw_bytes = response.read(1024 * 512) # Cap at 512KB for security & memory
                html = raw_bytes.decode("utf-8", errors="replace")

            # Clean HTML to readable text
            # 1. Remove script, style, head, noscript
            cleaned = re.sub(r"<(script|style|head|noscript)[^>]*>[\s\S]*?</\1>", " ", html, flags=re.IGNORECASE)
            # 2. Convert links and headings
            cleaned = re.sub(r"<h[1-6][^>]*>(.*?)</h[1-6]>", r"\n### \1\n", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"<p[^>]*>(.*?)</p>", r"\n\1\n", cleaned, flags=re.IGNORECASE)
            # 3. Strip remaining tags
            text = re.sub(r"<[^>]+>", " ", cleaned)
            # 4. Collapse extra whitespace
            text = re.sub(r"\s+", " ", text).strip()
            # 5. Extract page title
            title_match = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.IGNORECASE)
            page_title = title_match.group(1).strip() if title_match else url

            # Wrap strictly in untrusted boundaries
            safe_payload = PromptInjectionGuard.wrap_untrusted_content(
                content=f"Title: {page_title}\nURL: {url}\n\nContent:\n{text[:4000]}",
                origin=url
            )

            return ToolResult(
                success=True,
                output=safe_payload,
                raw_data={"url": url, "title": page_title, "content_type": content_type},
                execution_time_ms=int((time.time() - start_time) * 1000)
            )

        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Web fetch error for {url}: {str(e)}",
                execution_time_ms=int((time.time() - start_time) * 1000)
            )

    def verify(self, result: ToolResult, expectation: Dict[str, Any]) -> VerificationResult:
        if result.success and result.raw_data and "title" in result.raw_data:
            return VerificationResult(
                verified=True,
                expected=f"HTTP fetch of {expectation.get('url', 'target')}",
                actual=f"Received: {result.raw_data.get('title')}",
                message="Browser page retrieval verified."
            )
        return VerificationResult(
            verified=False,
            expected="Successful HTTP response",
            actual=f"Error: {result.error}",
            message="Browser verification failed."
        )
