import logging
import re
from .client import generate  # Uses the centralized Gemini client

logger = logging.getLogger("Surgeon")

SYSTEM_PROMPT = """You are an expert in Grammatical Framework (GF).
Your task is to FIX a broken GF file based on a compiler error.
OUTPUT ONLY THE FIXED CODE. NO MARKDOWN. NO COMMENTS.
"""

def attempt_repair(broken_code, error_log):
    """
    Analyzing the error log to patch the GF code.
    """
    prompt = f"""
    {SYSTEM_PROMPT}
    
    --- BROKEN CODE ---
    {broken_code}
    
    --- COMPILER ERROR ---
    {error_log}
    
    --- TASK ---
    Fix the code to resolve the error. 
    If the error is 'unknown function', replace it with a standard RGL function or a string stub.
    """
    
    try:
        logger.info("🧠 Surgeon analyzing error pattern...")
        fixed_code = generate(prompt)
        
        # Strip markdown if the AI added it despite instructions
        fixed_code = re.sub(r"```gf\n", "", fixed_code)
        fixed_code = re.sub(r"```", "", fixed_code)
        
        return fixed_code.strip()
    except Exception as e:
        logger.error(f"Surgeon failed: {e}")
        return None
