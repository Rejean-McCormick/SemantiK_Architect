# tools/everything_matrix/io_utils.py
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterable, Optional


def read_json(path: Path) -> Optional[Any]:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except Exception:
        return None


def read_json_dict(path: Path) -> Optional[dict[str, Any]]:
    obj = read_json(path)
    return obj if isinstance(obj, dict) else None


def atomic_write_json(path: Path, obj: Any, *, indent: int = 2) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=indent, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def _iter_files(paths: Iterable[Path]) -> Iterable[Path]:
    for p in paths:
        p = Path(p)
        if not p.exists():
            continue
        if p.is_file():
            yield p
            continue
        for root, _, files in os.walk(p):
            for name in files:
                yield Path(root) / name


def directory_fingerprint(*, content_roots: Iterable[Path], config_files: Iterable[Path]) -> str:
    """
    Fingerprint inputs that should trigger a rebuild.

    Includes:
      - absolute path
      - file size
      - mtime_ns (hi-res)
    """
    hasher = hashlib.sha256()
    all_items = list(content_roots) + list(config_files)

    for fp in sorted(_iter_files(all_items), key=lambda p: str(p).lower()):
        try:
            st = fp.stat()
            abspath = str(fp.resolve()).replace("\\", "/")
            mtime_ns = getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9))
            raw = f"{abspath}|{st.st_size}|{mtime_ns}"
            hasher.update(raw.encode("utf-8"))
        except OSError:
            continue

    return hasher.hexdigest()
