import logging
import re
import os
import sys
import json
import argparse
import time
from typing import Optional, Dict
from pathlib import Path

# Add project root to path if running as script
if __name__ == "__main__":
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# NEW SDK (google-genai)
from google import genai
from google.genai import types

from app.shared.config import settings
from ai_services.prompts import ARCHITECT_SYSTEM_PROMPT, SURGEON_SYSTEM_PROMPT

# Logger setup
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("architect")

# Constants
PROJECT_ROOT = Path(__file__).parents[1]
MATRIX_PATH = PROJECT_ROOT / "data" / "indices" / "everything_matrix.json"

# [FIX] Point directly to the main GF source folder so 'manage.py build' finds the files automatically
GENERATED_SRC_DIR = PROJECT_ROOT / "gf"

TOPOLOGY_CONFIG = PROJECT_ROOT / "data" / "config" / "topology_weights.json"
# [NEW] Load the mapping configuration for ISO -> RGL codes
ISO_MAP_PATH = PROJECT_ROOT / "data" / "config" / "iso_to_wiki.json"


class ArchitectAgent:
    """
    The AI Agent responsible for writing and fixing GF grammars.
    Acts as the 'Human-in-the-loop' replacement for Tier 3 languages.
    """

    def __init__(self):
        self.api_key = settings.GOOGLE_API_KEY
        # [FIX] Use available model from diagnostic
        self.model_name = "gemini-2.0-flash"
        self._client = None

        # [NEW] Load RGL Mapping Cache (e.g. zho -> Chi)
        self.iso_to_rgl = self._load_rgl_mapping()

        if self.api_key:
            try:
                # google-genai client
                self._client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.error(f"❌ Failed to initialize google-genai client: {e}")
                self._client = None
        else:
            logger.warning("⚠️ GOOGLE_API_KEY not found. The Architect Agent is disabled.")

    def _load_rgl_mapping(self) -> Dict[str, str]:
        """Loads the ISO -> RGL Code mapping (e.g. zho -> Chi)."""
        mapping = {}
        if ISO_MAP_PATH.exists():
            try:
                with open(ISO_MAP_PATH, "r") as f:
                    data = json.load(f)
                    for k, v in data.items():
                        # We map the ISO code (key) to the 'wiki' code (RGL code)
                        if isinstance(v, dict) and "wiki" in v:
                            mapping[k.lower()] = v["wiki"]
            except Exception as e:
                logger.error(f"⚠️ Failed to load ISO map: {e}")
        return mapping

    def get_rgl_code(self, iso_code: str) -> str:
        """Returns the GF-compatible RGL code (e.g. 'Chi') for an ISO code ('zho')."""
        return self.iso_to_rgl.get(iso_code.lower(), iso_code.capitalize())

    def generate_grammar(self, lang_code: str, lang_name: str, topology: str = "SVO") -> Optional[str]:
        """
        Generates a fresh Concrete Grammar (*.gf) for a missing language.
        """
        if not self._client:
            return None

        rgl_code = self.get_rgl_code(lang_code)
        module_name = f"Wiki{rgl_code}"

        logger.info(
            f"🏗️  The Architect is designing {lang_name} ({lang_code} -> {module_name}) [Topology: {topology}]..."
        )

        try:
            user_prompt = f"""
            Act as a Grammatical Framework (GF) expert.
            Write the concrete grammar file '{module_name}.gf' for Language: {lang_name} (ISO: {lang_code}).

            # Use this Skeleton EXACTLY:
            concrete {module_name} of SemantikArchitect = open Syntax{rgl_code}, Paradigms{rgl_code} in {{
              lincat
                Fact = S ;
                Entity = NP ;
                Predicate = VP ; -- Fixed: Use VP (Verb Phrase), not VPS
              lin
                mkFact s p = mkS (mkCl s p) ;
                -- Implement other linearizations here
            }}

            # Constraints
            1. Output ONLY the code.
            2. Do NOT inherit from 'WikiI' or 'Wiki'. Use the 'open' syntax above.
            3. The abstract syntax 'SemantikArchitect' defines:
               cat Fact; Entity; Predicate;
               fun mkFact : Entity -> Predicate -> Fact;
            """

            contents = [
                {
                    "role": "user",
                    "parts": [ARCHITECT_SYSTEM_PROMPT + "\n\n" + user_prompt],
                }
            ]

            resp = self._client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=types.GenerateContentConfig(temperature=0.1),
            )

            return self._sanitize_output(getattr(resp, "text", "") or "", module_name)

        except Exception as e:
            logger.error(f"❌ Architect generation failed for {lang_code}: {e}")
            return None

    def repair_grammar(self, broken_code: str, error_log: str) -> Optional[str]:
        """
        The Surgeon: Patches a broken grammar file based on compiler logs.
        """
        if not self._client:
            return None

        logger.info("🚑 The Surgeon is operating on broken grammar...")

        try:
            user_prompt = f"""
            **BROKEN CODE:**
            {broken_code}

            **COMPILER ERROR:**
            {error_log}
            """

            contents = [
                {
                    "role": "user",
                    "parts": [SURGEON_SYSTEM_PROMPT + "\n\n" + user_prompt],
                }
            ]

            resp = self._client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=types.GenerateContentConfig(temperature=0.1),
            )

            return self._sanitize_output(getattr(resp, "text", "") or "")

        except Exception as e:
            logger.error(f"❌ Surgeon repair failed: {e}")
            return None

    def _sanitize_output(self, text: str, module_name: str = "Wiki") -> str:
        """
        Cleans LLM output to ensure only valid GF code remains.
        """
        clean = re.sub(r"```(gf)?", "", text)
        clean = clean.strip()

        if not any(clean.startswith(k) for k in ["concrete", "resource", "interface"]):
            match = re.search(r"(concrete|resource|interface)\s+" + module_name, clean)
            if match:
                clean = clean[match.start() :]
            else:
                match = re.search(r"(concrete|resource|interface)\s+Wiki", clean)
                if match:
                    clean = clean[match.start() :]

        clean = re.sub(r"\bof\s+Wiki\b", "of SemantikArchitect", clean)

        if "= WikiI" in clean or "= Wiki" in clean:
            clean = re.sub(r"=\s*WikiI?\s*(with\s*\([^)]+\))?\s*(\*\*)?", "=", clean)
            if "open" not in clean:
                clean = clean.replace("=", "= open")

        return clean

# ... (le reste du fichier inchangé)
