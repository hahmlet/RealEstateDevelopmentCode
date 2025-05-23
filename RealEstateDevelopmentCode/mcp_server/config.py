#!/usr/bin/env python3
"""
MCP Server Configuration
Version: 1.0
Date: May 23, 2025

Configuration settings for the multi-jurisdiction MCP server.
"""

import os
from pathlib import Path

# Base directory settings
BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
WORKSPACE_DIR = Path("/workspace/RealEstateDevelopmentCode")
RAG_DATA_DIR = WORKSPACE_DIR / "rag_data"

# Server settings
HOST = "0.0.0.0"  # Listen on all interfaces
PORT = 8000
DEBUG = True

# Database settings
DATABASE_PATH = BASE_DIR / "database" / "mcp_chunks.db"

# Logging settings
LOG_LEVEL = "INFO"
LOG_FILE = BASE_DIR / "logs" / "mcp_server.log"

# Default values
DEFAULT_CHUNK_LIMIT = 20
DEFAULT_CONTEXT_LENGTH = 4000

# Jurisdiction settings
AVAILABLE_JURISDICTIONS = {
    "Oregon/gresham": {
        "name": "City of Gresham",
        "state": "Oregon",
        "data_path": RAG_DATA_DIR / "Oregon" / "gresham",
        "chunks_file": "accurate_chunks.jsonl",
    },
    "Oregon/multnomah_county": {
        "name": "Multnomah County",
        "state": "Oregon",
        "data_path": RAG_DATA_DIR / "Oregon" / "multnomah_county", 
        "chunks_file": "accurate_chunks.jsonl",
    }
}

# Make sure the database directory exists
os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)

# Make sure the log directory exists
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
