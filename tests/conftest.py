"""Pytest configuration and fixtures."""

import os
import tempfile

# Set test database path BEFORE any imports that load config
os.environ["DATABASE_PATH"] = tempfile.mktemp(suffix=".db")
