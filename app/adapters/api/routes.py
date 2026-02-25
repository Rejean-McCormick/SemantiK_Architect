# app/adapters/api/routes.py
"""
⛔ DEPRECATED: This module is obsolete.

As part of the API Unification Update, the monolithic router has been 
split into domain-specific modules. This file must not be imported.

Moved Logic:
- Text Generation   -> app.adapters.api.routers.generation
- Language Mgmt     -> app.adapters.api.routers.management
- Health Checks     -> app.adapters.api.routers.health

Please update your imports and delete this file once verified.
"""

import sys

# Define the error message
ERROR_MSG = (
    "CRITICAL ARCHITECTURE ERROR: You are importing 'app.adapters.api.routes'. "
    "This module is deprecated. Use 'app.adapters.api.routers' instead."
)

# Raise an immediate error to prevent 'split-brain' deployments
raise RuntimeError(ERROR_MSG)