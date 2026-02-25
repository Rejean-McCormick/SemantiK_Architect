# app/adapters/api/routers/__init__.py
"""
API Route Definitions.

This package contains the specific route handlers (controllers) organized by domain area.
- `generation`: Endpoints for text generation (Core Value).
- `languages`: Public endpoints for reading available languages.
- `management`: Admin endpoints for language lifecycle (Onboarding, Building).
- `tools`: Developer dashboard tools and utilities.
- `health`: System health checks.
"""

from . import generation
from . import languages
from . import management
from . import tools
from . import health

__all__ = [
    "generation",
    "languages",
    "management",
    "tools",
    "health",
]