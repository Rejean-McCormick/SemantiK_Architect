# app/adapters/api/__init__.py
"""
REST API Adapter.

This package acts as the HTTP entry point for the Semantik Architect.
It is built on FastAPI and follows the Hexagonal Architecture principles:
- It depends on `app.core` (Use Cases & Models).
- It wires the `app.shared.container` to inject dependencies.
- It does NOT contain business logic.
"""

# NOTE: We do NOT import create_app here to avoid circular imports 
# when the DI container scans this package.