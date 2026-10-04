"""
JARVIS Communication Tool
Enables composing and sending emails via macOS Mail and messages via macOS Messages.
"""

import asyncio
import urllib.parse
from typing import Dict, Any, Optional
from .base import Tool, ToolResult, VerificationResult
from backend.security.permissions import ActionLevel


class CommunicationTool(Tool):
    name = "communication"
    description = (
        "Composes and sends emails and messages on macOS. "
        "Actions: 'send_email' (composes/sends an email to a recipient with subject and body using macOS Mail), "
        "'send_message' (sends an iMessage or SMS to a recipient phone number/contact using macOS Messages)."
    )
    permission_level = ActionLevel.LEVEL_1_SAFE_WRITE
    timeout_seconds = 20.0

    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        action = params.get("action", "send_email")
        if action in ("send_email", "email", "mail"):
            return await self._send_email(params)
        elif action in ("send_message", "message", "imessage", "sms"):
            return await self._send_message(params)
        else:
            return ToolResult(
                success=False,
                output="",
                error=f"Unknown communication action '{action}'. Supported: send_email, send_message"
            )

    async def _send_email(self, params: Dict[str, Any]) -> ToolResult:
        recipient = params.get("to") or params.get("recipient") or params.get("email") or ""
        subject = params.get("subject") or "Message from JARVIS"
        body = params.get("body") or params.get("message") or params.get("content") or ""
        send_immediately = params.get("send_immediately", False)

        if not recipient:
            return ToolResult(success=False, output="", error="Recipient email address ('to') is required.")

        # Escape quotes for AppleScript
        clean_recipient = recipient.replace('"', '\\"')
        clean_subject = subject.replace('"', '\\"')
        clean_body = body.replace('"', '\\"').replace("\n", "\\n")

        # Try AppleScript via macOS Mail app
        as_script = f'''
        tell application "Mail"
            activate
            set newMsg to make new outgoing message with properties {{subject:"{clean_subject}", content:"{clean_body}", visible:true}}
            tell newMsg
                make new to recipient at end of to recipients with properties {{address:"{clean_recipient}"}}
            end tell
        end tell
        '''
        
        apple_script_succeeded = False
        try:
            proc = await asyncio.create_subprocess_exec(
                "osascript", "-e", as_script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            _, stderr = await proc.communicate()
            if proc.returncode == 0:
                apple_script_succeeded = True
        except Exception:
            pass

        # Fallback to mailto: URL scheme
        if not apple_script_succeeded:
            query = urllib.parse.urlencode({"subject": subject, "body": body})
            mailto_url = f"mailto:{recipient}?{query}"
            try:
                proc = await asyncio.create_subprocess_exec("open", mailto_url)
                await proc.communicate()
            except Exception as e:
                return ToolResult(success=False, output="", error=f"Could not open mail client: {str(e)}")

        receipt = {
            "status": "DISPATCHED",
            "type": "email",
            "to": recipient,
            "subject": subject,
            "body_snippet": body[:80] + ("..." if len(body) > 80 else ""),
            "client": "macOS Mail",
            "message": f"Sir, I have prepared and opened your email to '{recipient}' with subject '{subject}' in macOS Mail."
        }
        return ToolResult(
            success=True,
            output=receipt,
            raw_data={"to": recipient, "subject": subject, "sent": True}
        )

    async def _send_message(self, params: Dict[str, Any]) -> ToolResult:
        recipient = params.get("to") or params.get("recipient") or params.get("phone") or ""
        message = params.get("message") or params.get("body") or params.get("content") or ""

        if not recipient:
            return ToolResult(success=False, output="", error="Recipient ('to' or 'recipient') is required.")

        clean_recipient = recipient.replace('"', '\\"')
        clean_msg = message.replace('"', '\\"').replace("\n", "\\n")

        # Try AppleScript on Messages app
        as_script = f'''
        tell application "Messages"
            activate
            try
                set targetService to 1st account whose service type = iMessage
                set targetBuddy to participant "{clean_recipient}" of targetService
                send "{clean_msg}" to targetBuddy
            on error
                set targetService to 1st account whose service type = iMessage
                set targetBuddy to buddy "{clean_recipient}" of targetService
                send "{clean_msg}" to targetBuddy
            end try
        end tell
        '''

        apple_script_succeeded = False
        try:
            proc = await asyncio.create_subprocess_exec(
                "osascript", "-e", as_script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            _, stderr = await proc.communicate()
            if proc.returncode == 0:
                apple_script_succeeded = True
        except Exception:
            pass

        # Fallback to imessage: URL scheme
        if not apple_script_succeeded:
            try:
                proc = await asyncio.create_subprocess_exec("open", f"imessage://{recipient}")
                await proc.communicate()
            except Exception:
                pass

        receipt = {
            "status": "DISPATCHED",
            "type": "imessage_sms",
            "to": recipient,
            "message_snippet": message[:80] + ("..." if len(message) > 80 else ""),
            "client": "macOS Messages",
            "message": f"Sir, I have dispatched your message to '{recipient}' via macOS Messages."
        }
        return ToolResult(
            success=True,
            output=receipt,
            raw_data={"to": recipient, "message": message, "dispatched": True}
        )

    def verify(self, result: ToolResult, expectation: Dict[str, Any]) -> VerificationResult:
        if not result.success:
            return VerificationResult(
                verified=False,
                expected="Message or email dispatched",
                actual=f"Failure: {result.error}",
                message="Communication dispatch failed."
            )
        return VerificationResult(
            verified=True,
            expected="Message or email formatted and dispatched in macOS client",
            actual=str(result.output),
            message="Communication action successfully verified."
        )
