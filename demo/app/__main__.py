"""Main entry point."""

import logging

import uvicorn

logging.basicConfig(level=logging.INFO)
uvicorn.run("app.api:app")
