# app/main.py
import logging
import uvicorn

# 1. Import the factory from the new canonical location
from app.adapters.api.main import create_app

# 2. Setup logging
logger = logging.getLogger(__name__)

# 3. Instantiate the application
# This allows 'uvicorn app.main:app' to work by exposing the 'app' object here.
# It acts as a bridge/shim for any tools expecting the old entrypoint.
app = create_app()

if __name__ == "__main__":
    # Local debugging convenience
    logger.info("Starting Canonical App via Shim...")
    uvicorn.run(app, host="0.0.0.0", port=8000)