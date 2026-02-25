"""
System Performance Profiler.

Runs a standard benchmark suite against the Grammar Engine to measure:
1. Latency (Time per linearization)
2. Throughput (Sentences per second)
3. Memory Footprint (Peak allocation during batch processing)

Usage:
    python tools/health/profiler.py --lang en --iterations 1000 --verbose
    python tools/health/profiler.py --update-baseline

Output:
    Console report and exit code 1 if performance degrades > 15% vs baseline.
"""

import argparse
import time
import json
import sys
import os
import tracemalloc
import traceback
from typing import List, Dict, Any, Optional
from pathlib import Path

# --- Setup Path to import from 'app' ---
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, "../../"))
if root_dir not in sys.path:
    sys.path.append(root_dir)

try:
    from app.shared.config import settings
except ImportError:
    try:
        from app.core.config import settings
    except ImportError:
        print("[FATAL] Could not find 'settings' in app.shared.config or app.core.config", file=sys.stderr)
        sys.exit(1)

try:
    from app.adapters.engines.gf_wrapper import GFGrammarEngine
except ImportError as e:
    print(f"[FATAL] Import failed: {e}", file=sys.stderr)
    traceback.print_exc()
    sys.exit(1)

# Unify ISO -> concrete mapping with orchestrator/runtime
try:
    from builder.orchestrator.iso_map import iso_to_wiki_suffix
except Exception:
    iso_to_wiki_suffix = None  # type: ignore[assignment]

BASELINE_FILE = os.path.join(current_dir, "performance_baseline.json")

# Standard "Stress Test" Intents (mix of simple and nested structures)
STRESS_PAYLOADS = [
    {"function": "mkBioProf", "args": ["Marie Curie", "physicist"]},
    {
        "function": "mkEvent",
        "args": [
            "E_WWII",
            "war",
            {"function": "mkDateRange", "args": ["1939", "1945"]},
        ],
    },
    {
        "function": "mkS",
        "args": [
            {
                "function": "mkCl",
                "args": [
                    {"function": "mkNP", "args": ["the_long_winding_road_N"]},
                    {"function": "mkVP", "args": ["lead_V2", "nowhere_Adv"]},
                ],
            }
        ],
    },
]


def _resolve_concrete(lang: str) -> str:
    """
    Resolve concrete module name for a language ISO code.
    Prefers shared ISO mapping; falls back to Wiki{Lang.capitalize()}.
    """
    if iso_to_wiki_suffix is not None:
        try:
            suffix = iso_to_wiki_suffix(lang)
            if suffix:
                return f"Wiki{suffix}"
        except Exception:
            pass
    return f"Wiki{lang.capitalize()}"


class Profiler:
    def __init__(self, lang: str, verbose: bool = False):
        self.lang = (lang or "").strip()
        self.verbose = verbose
        self.concrete = _resolve_concrete(self.lang)

        if self.verbose:
            print(f"[INFO] Initializing Profiler for language: {self.lang} ({self.concrete})")
            print(f"[INFO] Loading PGF from: {settings.PGF_PATH}")

        try:
            self.engine = GFGrammarEngine(lib_path=settings.PGF_PATH)
            if self.verbose:
                avail = list(self.engine.grammar.languages.keys()) if getattr(self.engine, "grammar", None) else []
                print(f"[INFO] Engine loaded successfully. Available languages: {avail if avail else 'None'}")
        except Exception as e:
            print(f"[ERROR] Engine load failed: {e}")
            raise

    def run_benchmark(self, iterations: int) -> Dict[str, float]:
        """
        Runs the stress payloads 'iterations' times.
        Returns stats dict.
        """
        if self.verbose:
            print(f"[INFO] Starting Benchmark: {iterations} iterations...")
            print(f"[INFO] Warmup phase (10 iterations)...")

        # Warmup
        for i in range(10):
            intent = STRESS_PAYLOADS[i % len(STRESS_PAYLOADS)]
            try:
                ast_str = self.engine._convert_to_gf_ast(intent, self.lang)
                self.engine.linearize(ast_str, language=self.concrete)
            except Exception:
                pass

        if self.verbose:
            print(f"[INFO] Warmup complete. Starting collection phase...")

        tracemalloc.start()
        start_time = time.perf_counter()

        success_count = 0
        error_count = 0

        log_interval = max(1, iterations // 10)

        for i in range(iterations):
            intent = STRESS_PAYLOADS[i % len(STRESS_PAYLOADS)]

            try:
                ast_str = self.engine._convert_to_gf_ast(intent, self.lang)
                self.engine.linearize(ast_str, language=self.concrete)
                success_count += 1
            except Exception:
                error_count += 1

            if self.verbose and (i + 1) % log_interval == 0:
                print(f"[PROGRESS] Completed {i + 1}/{iterations} iterations...")

        end_time = time.perf_counter()
        current_mem, peak_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        total_time = end_time - start_time
        avg_tps = iterations / total_time if total_time > 0 else 0
        avg_latency_ms = (total_time / iterations) * 1000 if iterations > 0 else 0
        peak_mb = peak_mem / (1024 * 1024)

        if self.verbose:
            print(f"[INFO] Benchmark complete. Total time: {total_time:.4f}s")
            print(f"[INFO] Successes: {success_count}, Errors: {error_count}")

        return {
            "total_time_sec": round(total_time, 4),
            "avg_latency_ms": round(avg_latency_ms, 2),
            "throughput_tps": round(avg_tps, 2),
            "peak_memory_mb": round(peak_mb, 4),
            "success_rate": round(success_count / iterations, 2) if iterations > 0 else 0.0,
        }


def compare_baseline(current: Dict[str, float], baseline: Dict[str, float], threshold: float = 0.15) -> List[str]:
    """
    Returns a list of regression warnings if current stats are worse than baseline by > threshold %
    """
    warnings = []

    base_lat = baseline.get("avg_latency_ms", 0)
    curr_lat = current["avg_latency_ms"]
    if base_lat > 0:
        delta = (curr_lat - base_lat) / base_lat
        if delta > threshold:
            warnings.append(f"latency_degraded: {curr_lat}ms vs {base_lat}ms (+{delta:.1%})")

    base_mem = baseline.get("peak_memory_mb", 0)
    curr_mem = current["peak_memory_mb"]
    if base_mem > 0:
        delta = (curr_mem - base_mem) / base_mem
        if delta > threshold:
            warnings.append(f"memory_spike: {curr_mem}MB vs {base_mem}MB (+{delta:.1%})")

    return warnings


def main():
    parser = argparse.ArgumentParser(description="Performance Profiler")
    parser.add_argument("--lang", default="en", help="Target language to profile")
    parser.add_argument("--iterations", type=int, default=1000, help="Number of linearizations to run")
    parser.add_argument("--update-baseline", action="store_true", help="Overwrite the baseline file with these results")
    parser.add_argument("--threshold", type=float, default=0.15, help="Regression threshold (0.15 = 15%)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")

    args = parser.parse_args()

    trace_id = os.environ.get("TOOL_TRACE_ID", "N/A")
    if args.verbose:
        print(f"=== PERFORMANCE PROFILER ===")
        print(f"Trace ID: {trace_id}")
        print(f"Args: {vars(args)}")
        print(f"CWD: {os.getcwd()}")
        print("-" * 40)

    try:
        profiler = Profiler(args.lang, verbose=args.verbose)
        stats = profiler.run_benchmark(args.iterations)
    except Exception as e:
        print(f"CRITICAL: Benchmark crashed. {e}")
        traceback.print_exc()
        sys.exit(1)

    print("\n--- 📊 Results ---")
    print(json.dumps(stats, indent=2))

    baseline_path = Path(BASELINE_FILE)

    if args.update_baseline:
        try:
            with open(baseline_path, "w", encoding="utf-8") as f:
                json.dump(stats, f, indent=2)
            print(f"\n✅ Baseline updated at: {baseline_path.absolute()}")
            sys.exit(0)
        except Exception as e:
            print(f"\n❌ Failed to write baseline: {e}")
            sys.exit(1)

    if baseline_path.exists():
        if args.verbose:
            print(f"\n[INFO] Loading baseline from: {baseline_path}")

        try:
            with open(baseline_path, "r", encoding="utf-8") as f:
                baseline = json.load(f)

            warnings = compare_baseline(stats, baseline, args.threshold)

            if warnings:
                print(f"\n❌ PERFORMANCE REGRESSION DETECTED (Threshold: {args.threshold:.0%})")
                for w in warnings:
                    print(f"   - {w}")
                sys.exit(1)
            else:
                print("\n✅ Performance is within acceptable limits.")
        except Exception as e:
            print(f"\n[WARN] Failed to read baseline: {e}")
    else:
        print(f"\nℹ️ No baseline found at {baseline_path}. Run with --update-baseline to save this state.")


if __name__ == "__main__":
    main()