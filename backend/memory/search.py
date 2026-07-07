"""
JARVIS Memory Retrieval & Epistemic Reasoning
Ranks memories by relevance and organizes context into strict epistemic categories:
KNOWN, OBSERVED, REMEMBERED, INFERRED, UNKNOWN.
"""

import re
import math
from typing import List, Dict, Any, Tuple
from .store import MemoryStore, MemoryItem


class MemoryRetriever:
    def __init__(self, store: MemoryStore):
        self.store = store

    def _tokenize(self, text: str) -> List[str]:
        """Normalize text into lowercase alphanumeric tokens."""
        return re.findall(r"\b[a-zA-Z0-9_-]{2,}\b", text.lower())

    def search_relevant(self, query: str, limit: int = 5, min_score: float = 0.1) -> List[Tuple[MemoryItem, float]]:
        """
        Retrieves memories scored by term frequency relevance.
        Returns list of (MemoryItem, relevance_score).
        """
        all_memories = self.store.get_memories(limit=200)
        query_tokens = set(self._tokenize(query))
        if not query_tokens:
            return [(m, 1.0) for m in all_memories[:limit]]

        scored = []
        for mem in all_memories:
            content_tokens = self._tokenize(mem.content)
            if not content_tokens:
                continue

            # Calculate token intersection and simple length normalization
            matches = sum(1 for t in query_tokens if t in content_tokens)
            if matches > 0:
                score = matches / (math.sqrt(len(content_tokens)) + 1.0)
                # Boost explicit user preferences
                if mem.category == "preference":
                    score *= 1.3
                if score >= min_score:
                    scored.append((mem, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:limit]

    def build_epistemic_context(
        self,
        query: str,
        observed_facts: List[str] | None = None,
        system_knowns: List[str] | None = None,
        recent_tasks: List[Dict[str, Any]] | None = None
    ) -> Dict[str, List[str]]:
        """
        Constructs context strictly segregated by epistemic certainty:
        - KNOWN: Confirmed system facts and verified local state
        - REMEMBERED: Facts retrieved from memory database
        - LEARNED_CORRECTIONS: Prior user corrections and mistake lessons
        - RECENT_ACTIONS: Tasks and operations recently executed
        - OBSERVED: Immediate execution outputs from current turn
        - INFERRED: Logical deductions made during reasoning
        - UNKNOWN: Missing information that must NOT be hallucinated
        """
        relevant_memories = self.search_relevant(query, limit=5)
        
        remembered = [
            f"[{m.category.upper()}] {m.content} (Confidence: {m.confidence})"
            for m, _ in relevant_memories
        ]

        # Fetch past corrections & mistake lessons
        correction_memories = self.store.get_memories(category="correction", limit=5)
        learned_corrections = [
            f"{m.content}" for m in correction_memories
        ]

        # Format recent tasks & outputs
        recent_actions = []
        if recent_tasks:
            for t in recent_tasks[-5:]:
                goal_text = t.get("goal", "")
                state = t.get("state", "COMPLETED")
                summary = t.get("summary", "")
                resp = t.get("response", "")
                receipts = t.get("receipts", [])
                rec_str = f"Task: '{goal_text}' | Status: {state}"
                if summary:
                    rec_str += f" | Action: {summary}"
                elif resp:
                    rec_str += f" | Output: {resp[:120]}"
                if receipts:
                    rec_str += f" | Detail: {receipts[-1][:120]}"
                recent_actions.append(rec_str)

        context = {
            "KNOWN": system_knowns or [],
            "REMEMBERED": remembered,
            "LEARNED_CORRECTIONS": learned_corrections,
            "RECENT_ACTIONS": recent_actions,
            "OBSERVED": observed_facts or [],
            "INFERRED": [],
            "UNKNOWN": []
        }
        return context

    def format_context_for_prompt(self, context: Dict[str, List[str]]) -> str:
        """Format the epistemic context block for LLM prompts."""
        lines = ["[EPISTEMIC STATE CONTEXT]"]
        for category, items in context.items():
            lines.append(f"--- {category} ---")
            if items:
                for it in items:
                    lines.append(f"• {it}")
            else:
                lines.append("• None recorded")
        lines.append("[END EPISTEMIC STATE]")
        return "\n".join(lines)
