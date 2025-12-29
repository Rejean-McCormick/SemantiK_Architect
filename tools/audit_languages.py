# audit_languages.py
import os
import subprocess
import glob
import sys
import json
import hashlib
import time
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict

# -----------------------------------------------------------------------------
# CONFIGURATION
# -----------------------------------------------------------------------------
GF_DIR = "gf"
RGL_DIR = "gf-rgl/src"
CACHE_FILE = "data/indices/audit_cache.json"
REPORT_FILE = "data/reports/audit_report.json"

# Include ALL RGL folders to ensure we don't fail on missing shared paths
RGL_FOLDERS = [
    "api", "abstract", "common", "prelude",
    "romance", "germanic", "scandinavian", "slavic", "uralic", "hindustani", "semitic",
    "afrikaans", "amharic", "arabic", "basque", "bulgarian", "catalan", 
    "chinese", "danish", "dutch", "english", "estonian", "finnish", "french", 
    "german", "greek", "hebrew", "hindi", "hungarian", "icelandic", 
    "indonesian", "italian", "japanese", "korean", "latin", "latvian", 
    "lithuanian", "maltese", "mongolian", "nepali", "norwegian", "persian", 
    "polish", "portuguese", "punjabi", "romanian", "russian", "sindhi", 
    "slovenian", "somali", "spanish", "swahili", "swedish", "thai", "turkish", 
    "urdu", "vietnamese", "xhosa", "yoruba", "zulu"
]

@dataclass
class AuditResult:
    lang: str
    filename: str
    status: str  # VALID, BROKEN, SKIPPED
    error: Optional[str] = None
    duration: float = 0.0
    file_hash: str = ""

class LanguageAuditor:
    def __init__(self, use_cache: bool = False):
        self.abs_rgl = os.path.abspath(RGL_DIR)
        self.paths = [os.path.join(self.abs_rgl, f) for f in RGL_FOLDERS]
        self.path_str = ":".join(self.paths)
        self.use_cache = use_cache
        self.cache = self._load_cache()

    def _load_cache(self) -> Dict:
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, 'r') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _get_file_hash(self, filepath: str) -> str:
        """Calculates SHA-256 hash of the file content for caching."""
        hasher = hashlib.sha256()
        try:
            with open(filepath, 'rb') as f:
                buf = f.read()
                hasher.update(buf)
            return hasher.hexdigest()
        except FileNotFoundError:
            return ""

    def check_language(self, file_path: str) -> AuditResult:
        """Audits a single language file."""
        filename = os.path.basename(file_path)
        lang = filename.replace("Wiki", "").replace(".gf", "")
        current_hash = self._get_file_hash(file_path)
        
        # 1. Cache Check (Fast Path)
        if self.use_cache:
            cached_data = self.cache.get(filename)
            if cached_data and cached_data.get("hash") == current_hash:
                if cached_data.get("status") == "VALID":
                    return AuditResult(
                        lang=lang, filename=filename, status="SKIPPED", 
                        file_hash=current_hash
                    )

        # 2. Compile Check (Slow Path)
        start_time = time.time()
        cmd = ["gf", "-make", "-path", self.path_str, filename]
        
        try:
            result = subprocess.run(
                cmd, 
                cwd=GF_DIR, 
                capture_output=True, 
                text=True
            )
            duration = time.time() - start_time
            
            if result.returncode == 0:
                return AuditResult(lang, filename, "VALID", duration=duration, file_hash=current_hash)
            else:
                # Parse Error
                error_msg = self._extract_error(result.stderr or result.stdout)
                return AuditResult(lang, filename, "BROKEN", error=error_msg, duration=duration, file_hash=current_hash)

        except Exception as e:
            return AuditResult(lang, filename, "BROKEN", error=str(e), file_hash=current_hash)

    def _extract_error(self, text: str) -> str:
        """Heuristic to find the most relevant GF error line."""
        lines = text.strip().split("\n")
        for line in lines:
            if "does not exist" in line: return line.strip()
            if "constant not found" in line: return line.strip()
            if "syntax error" in line: return line.strip()
        return lines[0].strip() if lines else "Unknown Error"

def save_reports(results: List[AuditResult], old_cache: Dict):
    """Saves structured data and updates the cache."""
    
    # 1. Update Cache
    new_cache = old_cache.copy()
    valid_count = 0
    broken_count = 0
    regressions = []

    for r in results:
        # Check for Regression (Was Valid -> Now Broken)
        if r.status == "BROKEN":
            prev = old_cache.get(r.filename)
            if prev and prev.get("status") == "VALID":
                regressions.append(r.lang)
            broken_count += 1
        elif r.status in ["VALID", "SKIPPED"]:
            valid_count += 1

        # Update cache record
        new_cache[r.filename] = {
            "status": "VALID" if r.status in ["VALID", "SKIPPED"] else "BROKEN",
            "hash": r.file_hash,
            "last_check": time.time()
        }

    # Ensure directories exist
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    os.makedirs(os.path.dirname(REPORT_FILE), exist_ok=True)

    with open(CACHE_FILE, 'w') as f:
        json.dump(new_cache, f, indent=2)

    # 2. Console Summary
    print("\n" + "="*60)
    print("AUDIT SUMMARY")
    print("="*60)
    print(f"✅ VALID: {valid_count}")
    print(f"❌ BROKEN: {broken_count}")
    if regressions:
        print(f"⚠️  REGRESSIONS DETECTED: {', '.join(regressions)}")
        print("   (These languages worked previously but are now broken!)")

    # 3. Generate Disable Script
    broken_files = [r for r in results if r.status == "BROKEN"]
    if broken_files:
        print(f"\nGenerating fix script for {len(broken_files)} files...")
        with open("disable_broken.sh", "w") as f:
            f.write("#!/bin/bash\n# Generated by Audit Matrix\n")
            for r in broken_files:
                f.write(f"echo 'Disabling {r.filename} ({r.error})'\n")
                f.write(f"mv gf/{r.filename} gf/{r.filename}.SKIP\n")
        print("👉 Run 'bash disable_broken.sh' to disable broken languages.")

def run():
    parser = argparse.ArgumentParser(description="Senior Audit Tool")
    parser.add_argument("--fast", action="store_true", help="Skip unchanged files (use cache)")
    parser.add_argument("--parallel", type=int, default=os.cpu_count() or 4, help="Threads to use")
    args = parser.parse_args()

    print(f"🚀 Starting Audit (Threads: {args.parallel}, FastMode: {args.fast})...")
    
    auditor = LanguageAuditor(use_cache=args.fast)
    
    # Get Files
    files = sorted(glob.glob(os.path.join(GF_DIR, "Wiki*.gf")))
    files = [f for f in files if "Wiki.gf" not in f and not f.endswith(".SKIP")]

    results = []
    
    # Parallel Execution
    with ThreadPoolExecutor(max_workers=args.parallel) as executor:
        future_to_file = {executor.submit(auditor.check_language, f): f for f in files}
        
        total = len(files)
        completed = 0
        
        for future in as_completed(future_to_file):
            completed += 1
            res = future.result()
            results.append(res)
            
            # Dynamic Progress Bar
            status_icon = "✅" if res.status == "VALID" else "⏩" if res.status == "SKIPPED" else "❌"
            sys.stdout.write(f"\r   [{completed}/{total}] {status_icon} {res.lang:<10}")
            sys.stdout.flush()

    save_reports(results, auditor.cache)

if __name__ == "__main__":
    run()