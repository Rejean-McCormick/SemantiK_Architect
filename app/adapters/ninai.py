# app/adapters/ninai.py
import logging
from typing import Any, Dict, List, Optional, Union
from pydantic import ValidationError

from app.core.domain.frame import BioFrame, EventFrame, RelationalFrame
from app.shared.config import settings
from app.shared.lexicon import lexicon  # <--- NEW: Import the Memory Bank

# Logger setup
logger = logging.getLogger(settings.OTEL_SERVICE_NAME)

# --- CONSTANTS: The Ninai Protocol Ledger ---
CONSTRUCTOR_STATEMENT = "ninai.constructors.Statement"
CONSTRUCTOR_ENTITY = "ninai.constructors.Entity"
CONSTRUCTOR_LIST = "ninai.constructors.List"
TYPE_BIO = "ninai.types.Bio"
TYPE_EVENT = "ninai.types.Event"

class NinaiAdapter:
    """
    The Bridge between the external Ninai Protocol (Recursive JSON Objects)
    and the internal Abstract Wiki Architect Domain (Flat Pydantic Frames).
    v2.0 Upgrade: Integrates LexiconRuntime for Entity Grounding.
    """

    def parse(self, ninai_payload: Dict[str, Any], target_lang: str = "eng") -> Union[BioFrame, EventFrame, RelationalFrame]:
        """
        Main entry point. Recursively parses the input JSON tree.
        Now accepts 'target_lang' to resolve QIDs using the Lexicon.
        """
        # 0. Load Lexicon for this language (Lazy Load)
        lexicon.load_language(target_lang)

        # 1. Validate Root Structure
        func = ninai_payload.get("function")
        if func != CONSTRUCTOR_STATEMENT:
            raise ValueError(f"Invalid Root: Expected '{CONSTRUCTOR_STATEMENT}', got '{func}'")

        args = ninai_payload.get("args", [])
        if not args:
            raise ValueError("Invalid Statement: 'args' list is empty.")

        # 2. Extract Intent
        intent_obj = args[0]
        # CRITICAL FIX: Ninai stores the type in the 'function' key
        intent_type = intent_obj.get("function") 

        # 3. Route to specific handler
        if intent_type == TYPE_BIO:
            return self._parse_bio(args, target_lang)
        elif intent_type == TYPE_EVENT:
            return self._parse_event(args, target_lang)
        else:
            raise ValueError(f"Unsupported Ninai Type: {intent_type}")

    def _parse_bio(self, args: List[Dict[str, Any]], lang: str) -> BioFrame:
        """
        Parses a Biographical Statement.
        Enriches Entity data using the Lexicon (Zone B).
        """
        try:
            # --- Subject (Arg 1) ---
            subject_node = args[1]
            subject_qid = self._extract_qid(subject_node)
            
            # Lookup in Lexicon (Enrichment)
            # If Ninai sends "Unknown", we use the Lexicon's lemma (e.g., "Douglas Adams")
            subj_entry = lexicon.lookup(subject_qid, lang) if subject_qid else None
            
            subject_name = self._extract_label(subject_node)
            if subject_name == "Unknown" and subj_entry:
                subject_name = subj_entry.lemma

            # --- Profession (Arg 2) ---
            prof_node = args[2]
            prof_qid = self._extract_qid(prof_node)
            prof_entry = lexicon.lookup(prof_qid, lang) if prof_qid else None
            
            # Use GF Function if available (e.g. 'physicist_N'), else raw string
            if prof_entry and prof_entry.gf_fun:
                profession_key = prof_entry.gf_fun
            else:
                profession_key = self._extract_value(prof_node)

            # --- Nationality (Arg 3) ---
            nationality_key = None
            if len(args) > 3:
                nat_node = args[3]
                nat_qid = self._extract_qid(nat_node)
                nat_entry = lexicon.lookup(nat_qid, lang) if nat_qid else None
                
                if nat_entry and nat_entry.gf_fun:
                    nationality_key = nat_entry.gf_fun
                else:
                    nationality_key = self._extract_value(nat_node)

            # --- Construct Frame ---
            # We inject the concrete GF function into 'meta' for the Engine to use
            meta_data = {}
            if subj_entry:
                meta_data["subject_gf"] = subj_entry.gf_fun

            return BioFrame(
                frame_type="bio",
                subject={
                    "name": subject_name,
                    "qid": subject_qid,
                    "profession": profession_key,
                    "nationality": nationality_key,
                    "gender": "n" 
                },
                context_id=subject_qid,
                meta=meta_data 
            )
        except IndexError:
            raise ValueError("Malformed BioFrame: Missing required arguments.")
        except ValidationError as e:
            raise ValueError(f"Validation Error in BioFrame: {e}")

    def _parse_event(self, args: List[Dict[str, Any]], lang: str) -> EventFrame:
        """
        Parses an Event Statement.
        """
        try:
            # Subject
            subject_node = args[1]
            subject_qid = self._extract_qid(subject_node)
            subject_name = self._extract_label(subject_node)
            
            # Lexicon Lookup
            subj_entry = lexicon.lookup(subject_qid, lang) if subject_qid else None
            if subject_name == "Unknown" and subj_entry:
                subject_name = subj_entry.lemma

            # Event Object
            event_node = args[2]
            event_name = self._extract_label(event_node)

            meta_data = {}
            if subj_entry:
                meta_data["subject_gf"] = subj_entry.gf_fun

            return EventFrame(
                frame_type="event",
                subject={
                    "name": subject_name,
                    "qid": subject_qid
                },
                event_object=event_name,
                context_id=subject_qid,
                meta=meta_data
            )
        except IndexError:
            raise ValueError("Malformed EventFrame: Missing required arguments.")
        except ValidationError as e:
            raise ValueError(f"Validation Error in EventFrame: {e}")

    # --- Helper: Recursive Tree Walkers ---

    def _extract_label(self, node: Dict[str, Any]) -> str:
        """Extracts human-readable label or 'Unknown'."""
        if node.get("function") == CONSTRUCTOR_ENTITY:
            if len(node.get("args", [])) > 1:
                return node["args"][1]
        return "Unknown"

    def _extract_qid(self, node: Dict[str, Any]) -> Optional[str]:
        """Extracts the Wikidata ID (QID)."""
        if node.get("function") == CONSTRUCTOR_ENTITY:
            if len(node.get("args", [])) > 0:
                return node["args"][0]
        return None

    def _extract_value(self, node: Dict[str, Any]) -> str:
        """Extracts a raw string value, handling wrappers."""
        if isinstance(node, str):
            return node
            
        if "value" in node:
            return node["value"]
            
        # Fallback for Entity wrappers used as values
        if node.get("function") == CONSTRUCTOR_ENTITY:
             if len(node.get("args", [])) > 1:
                 return node["args"][1].lower()
             
        return str(node)

# Global Singleton
ninai_adapter = NinaiAdapter()