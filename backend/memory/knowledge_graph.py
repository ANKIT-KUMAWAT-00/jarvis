"""
JARVIS Knowledge Graph & Notes Indexer
Indexes local notes (.md, .txt, .json), extracts semantic connections,
and builds node-link structures for interactive 3D/2D visualization.
"""

import os
import json
import re
from pathlib import Path
from typing import Dict, List, Any
from .store import MemoryStore


class KnowledgeGraphBuilder:
    def __init__(self, notes_dir: Path, store: MemoryStore):
        self.notes_dir = notes_dir
        self.store = store

    def index_notes(self) -> List[Dict[str, Any]]:
        """Index all markdown, text, and JSON documents in notes_dir."""
        documents = []
        if not self.notes_dir.exists():
            return documents

        for file_path in self.notes_dir.rglob("*"):
            if not file_path.is_file():
                continue
            suffix = file_path.suffix.lower()
            if suffix not in (".md", ".txt", ".json"):
                continue

            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")
                title = file_path.stem.replace("_", " ").title()
                
                # Check for frontmatter title or # Heading in markdown
                if suffix == ".md":
                    heading_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
                    if heading_match:
                        title = heading_match.group(1).strip()

                excerpt = content[:200].replace("\n", " ").strip()
                
                # Extract tags or concepts (#tag or [[wiki-link]])
                tags = re.findall(r"#([a-zA-Z0-9_\-]+)", content)
                wiki_links = re.findall(r"\[\[(.*?)\]\]", content)

                documents.append({
                    "id": f"note_{file_path.name}",
                    "title": title,
                    "path": str(file_path),
                    "filename": file_path.name,
                    "suffix": suffix,
                    "excerpt": excerpt,
                    "tags": list(set(tags)),
                    "links": wiki_links,
                    "char_count": len(content)
                })
            except Exception as e:
                pass
        return documents

    def build_graph(self) -> Dict[str, Any]:
        """
        Constructs nodes and links for interactive graph visualization.
        Integrates notes, active memories, and project milestones.
        """
        nodes = []
        links = []
        node_ids = set()

        # 1. Central Core Node
        core_id = "jarvis_core"
        nodes.append({
            "id": core_id,
            "label": "JARVIS Core",
            "type": "core",
            "size": 28,
            "color": "#00f0ff",
            "info": "Autonomous AI Agent Operating System"
        })
        node_ids.add(core_id)

        # 2. Add Project & Fact Memories
        memories = self.store.get_memories(limit=30)
        for mem in memories:
            m_id = f"mem_{mem.id}"
            category_color = {
                "project": "#7928ca",
                "preference": "#ff007f",
                "task": "#00df8f",
                "long_term": "#0070f3"
            }.get(mem.category, "#00a8ff")

            nodes.append({
                "id": m_id,
                "label": mem.content[:35] + ("..." if len(mem.content) > 35 else ""),
                "type": mem.category,
                "size": 16,
                "color": category_color,
                "info": f"[{mem.category.upper()}] {mem.content}"
            })
            node_ids.add(m_id)

            # Link memory to Core
            links.append({
                "source": core_id,
                "target": m_id,
                "relation": "remembers"
            })

        # 3. Add Notes
        notes = self.index_notes()
        for note in notes:
            n_id = note["id"]
            nodes.append({
                "id": n_id,
                "label": note["title"],
                "type": "note",
                "size": 18,
                "color": "#f5a623",
                "info": f"{note['title']}: {note['excerpt']}"
            })
            node_ids.add(n_id)

            # Link note to Core
            links.append({
                "source": core_id,
                "target": n_id,
                "relation": "indexed_note"
            })

            # Check wiki-links between notes
            for target_title in note["links"]:
                target_id = f"note_{target_title}.md"
                # If target node exists or will exist
                links.append({
                    "source": n_id,
                    "target": target_id,
                    "relation": "references"
                })

        return {
            "nodes": nodes,
            "links": [link for link in links if link["target"] in node_ids]
        }
