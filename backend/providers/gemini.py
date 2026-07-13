"""
JARVIS Google Gemini Provider
High-performance asynchronous integration with official Google GenAI SDK.
Features sub-second latency tuning, true async calls (client.aio),
dead-key pruning, strict timeouts, and multi-key pooling with automatic failover.
"""

import os
import json
import base64
import logging
import asyncio
import time
from typing import List, Dict, Any, Optional, Type, Union
