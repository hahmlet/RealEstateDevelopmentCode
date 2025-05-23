#!/usr/bin/env python3
"""
Configuration management for document registry system
Version: 1.0
Date: May 23, 2025

Centralizes all hard-coded paths and configuration values.
"""

import os
from pathlib import Path
from typing import Dict, Any

# Base paths
WORKSPACE_ROOT = Path("/workspace")
DATA_ROOT = WORKSPACE_ROOT / "RealEstateDevelopmentCode"

# Directory structure
DIRECTORIES = {
    'pdf_content': DATA_ROOT / "pdf_content",
    'raw_pdfs': DATA_ROOT / "raw_pdfs", 
    'reports': DATA_ROOT / "reports",
    'scripts': DATA_ROOT / "scripts",
    'archive': DATA_ROOT / "archive"
}

# Default file names
DEFAULT_FILES = {
    'toc': 'dc-table-of-contents.json',
    'alignment_report': 'hierarchical_alignment_report.json',
    'validation_report': 'content_validation_report.json'
}

# Regex patterns for document parsing
PATTERNS = {
    'document_level': r'^\d+\.\d{2}$',  # XX.YY format
    'subsection': r'^\d+\.\d{4}$',      # XX.YYYY format
    'section_header': r'SECTION\s+(\d+\.\d+)\s+([A-Z\s]+)',
    'toc_subsection': r'(\d+\.\d{4})\s+([^.\n]+?)(?=\s*\n|\s+\d+\.\d{4})',
    'filename_number': r'(\d+\.\d+)'
}

# Default locations for testing/demo
DEFAULT_LOCATIONS = {
    'gresham': {
        'state': 'Oregon',
        'city': 'gresham',
        'content_dir': DIRECTORIES['pdf_content'] / "Oregon" / "gresham",
        'reports_dir': DIRECTORIES['reports'] / "Oregon" / "gresham"
    }
}


def get_content_directory(state: str, city: str) -> Path:
    """Get content directory for a specific location"""
    return DIRECTORIES['pdf_content'] / state / city


def get_reports_directory(state: str, city: str) -> Path:
    """Get reports directory for a specific location"""
    return DIRECTORIES['reports'] / state / city


def get_toc_file_path(state: str, city: str) -> Path:
    """Get TOC file path for a specific location"""
    return get_content_directory(state, city) / DEFAULT_FILES['toc']


def get_default_location() -> Dict[str, Any]:
    """Get default location configuration"""
    return DEFAULT_LOCATIONS['gresham'].copy()


def ensure_directories_exist(state: str, city: str) -> None:
    """Ensure all necessary directories exist for a location"""
    dirs_to_create = [
        get_content_directory(state, city),
        get_reports_directory(state, city)
    ]
    
    for directory in dirs_to_create:
        directory.mkdir(parents=True, exist_ok=True)
