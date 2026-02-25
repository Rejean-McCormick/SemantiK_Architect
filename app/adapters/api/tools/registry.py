from __future__ import annotations

from typing import Dict

from .models import ToolSpec
from .registry_build import build_registry
from .registry_maintenance import maintenance_registry
from .registry_qa import qa_registry

# Compose all tool buckets into one allowlist
TOOL_REGISTRY: Dict[str, ToolSpec] = {
    **maintenance_registry(),
    **build_registry(),
    **qa_registry(),
}
