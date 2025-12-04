"""
nlg/cli_frontend.py

Command-line interface for the high-level NLG frontend API.

Typical usage:

    nlg-cli generate \
        --lang fr \
        --frame-type bio \
        --input path/to/frame.json \
        --max-sentences 2 \
        --register neutral \
        --debug

The CLI:

- Reads a JSON frame from a file (or stdin).
- Ensures a frame_type is set (CLI flag or JSON field).
- Forwards the frame to nlg.api.generate with optional GenerationOptions.
- Prints the realized text to stdout, and optional debug info to stderr.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from nlg.api import generate, GenerationOptions  # Assumed to exist


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nlg-cli",
        description="CLI frontend for the NLG API (frame → text).",
    )

    subparsers = parser.add_subparsers(
        title="commands",
        dest="command",
        required=True,
    )

    # `generate` command
    gen = subparsers.add_parser(
        "generate",
        help="Generate text for a given language and frame.",
    )

    gen.add_argument(
        "--lang",
        required=True,
        help="Target language code (e.g. 'en', 'fr', 'sw').",
    )

    gen.add_argument(
        "--frame-type",
        help=(
            "Frame type label (e.g. 'bio', 'event'). "
            "If omitted, the JSON must contain a 'frame_type' field."
        ),
    )

    gen.add_argument(
        "--input",
        "-i",
        metavar="PATH",
        help=(
            "Path to a JSON file containing the frame. "
            "If omitted or '-', read from stdin."
        ),
    )

    gen.add_argument(
        "--max-sentences",
        type=int,
        default=None,
        help="Optional upper bound on the number of sentences to generate.",
    )

    gen.add_argument(
        "--register",
        choices=["neutral", "formal", "informal"],
        default=None,
        help="Optional register/style hint.",
    )

    gen.add_argument(
        "--discourse-mode",
        default=None,
        help="Optional discourse mode hint (e.g. 'intro', 'summary').",
    )

    gen.add_argument(
        "--debug",
        action="store_true",
        help="Include debug information from the generator.",
    )

    return parser


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_json(path: Optional[str]) -> Dict[str, Any]:
    """
    Load a JSON object from a file or stdin.

    If path is None or '-', read from stdin.
    """
    if not path or path == "-":
        raw = sys.stdin.read()
    else:
        raw = Path(path).read_text(encoding="utf-8")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Error: invalid JSON input ({exc}).") from exc

    if not isinstance(data, dict):
        raise SystemExit("Error: expected a JSON object at top level.")

    return data


def _ensure_frame_type(payload: Dict[str, Any], frame_type_arg: Optional[str]) -> None:
    """
    Ensure that the payload has a 'frame_type' key.

    Precedence:
        1. --frame-type argument
        2. existing 'frame_type' field in JSON

    If neither is available, exit with an error.
    """
    if frame_type_arg:
        payload.setdefault("frame_type", frame_type_arg)

    if "frame_type" not in payload or not payload["frame_type"]:
        raise SystemExit(
            "Error: frame type not specified. "
            "Use --frame-type or include 'frame_type' in the JSON."
        )


def _build_generation_options(args: argparse.Namespace) -> GenerationOptions:
    """
    Construct a GenerationOptions instance from CLI arguments.
    """
    return GenerationOptions(
        register=args.register,
        max_sentences=args.max_sentences,
        discourse_mode=args.discourse_mode,
        seed=None,
    )


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------


def _cmd_generate(args: argparse.Namespace) -> int:
    """
    Handle `nlg-cli generate` command.
    """
    payload = _load_json(args.input)
    _ensure_frame_type(payload, args.frame_type)

    options = _build_generation_options(args)

    result = generate(
        lang=args.lang,
        frame=payload,
        options=options,
        debug=args.debug,
    )

    # Main output: realized text
    print(result.text)

    # Optional debug output to stderr
    if args.debug and getattr(result, "debug_info", None) is not None:
        debug_serialized = json.dumps(
            result.debug_info,
            indent=2,
            ensure_ascii=False,
        )
        print("\n[DEBUG]", file=sys.stderr)
        print(debug_serialized, file=sys.stderr)

    return 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv: Optional[list[str]] = None) -> None:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    if args.command == "generate":
        exit_code = _cmd_generate(args)
    else:
        parser.error(f"Unknown command: {args.command}")
        return

    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
