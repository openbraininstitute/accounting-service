"""Main entry point."""

import logging

import uvicorn

logging.basicConfig(level=logging.INFO)
uvicorn.run("app.api:app", port=5000, log_level="info")
