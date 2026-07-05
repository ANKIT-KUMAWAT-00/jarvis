"""
JARVIS Knowledge Graph & Notes Indexer
Indexes local notes (.md, .txt, .json), extracts semantic connections,
and builds node-link structures for interactive 3D/2D visualization.
"""

import os
import json
import re
from pathlib import Path
