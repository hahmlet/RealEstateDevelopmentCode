#!/usr/bin/env python3
"""
Utilities for document processing and analysis
Version: 1.0
Date: May 23, 2025

Consolidates common utility functions to avoid duplication.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from .config import PATTERNS


def load_json_file(file_path: str | Path) -> Dict[str, Any]:
    """Load JSON file with error handling"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        raise FileNotFoundError(f"Could not load JSON file {file_path}: {str(e)}")


def save_json_file(data: Dict[str, Any], file_path: str | Path) -> None:
    """Save data to JSON file with directory creation"""
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def extract_number_from_filename(filename: str) -> Optional[str]:
    """Extract document number from filename using centralized regex"""
    match = re.search(PATTERNS['filename_number'], filename)
    if match:
        number = match.group(1)
        # Normalize to XX.YY format if it's XX.YYYY
        if '.' in number:
            parts = number.split('.')
            if len(parts) == 2 and len(parts[1]) > 2:
                return f"{parts[0]}.{parts[1][:2]}"
        return number
    return None


def is_document_level(number: str) -> bool:
    """Check if number is document level (XX.YY format)"""
    return bool(re.match(PATTERNS['document_level'], number))


def is_subsection(number: str) -> bool:
    """Check if number is subsection level (XX.YYYY format)"""
    return bool(re.match(PATTERNS['subsection'], number))


def get_parent_document(subsection_number: str) -> Optional[str]:
    """Get parent document number for a subsection"""
    if is_subsection(subsection_number):
        parts = subsection_number.split('.')
        if len(parts) == 2 and len(parts[1]) == 4:
            return f"{parts[0]}.{parts[1][:2]}"
    return None


def parse_toc_text_content(toc_data: Dict[str, Any]) -> str:
    """Extract text content from TOC data structure"""
    all_text = ""
    
    for key, value in toc_data.items():
        if isinstance(value, dict) and 'text' in value:
            all_text += value['text'] + "\n"
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict) and 'text' in item:
                    all_text += item['text'] + "\n"
    
    return all_text


def extract_toc_entries_from_text(text: str) -> List[Dict[str, str]]:
    """Extract TOC entries from text using centralized patterns"""
    entries = []
    
    # Extract section headers
    section_matches = re.finditer(PATTERNS['section_header'], text, re.MULTILINE)
    for match in section_matches:
        entries.append({
            'number': match.group(1),
            'title': match.group(2).strip(),
            'type': 'section_header'
        })
    
    # Extract subsection entries
    subsection_matches = re.finditer(PATTERNS['toc_subsection'], text, re.MULTILINE)
    for match in subsection_matches:
        entries.append({
            'number': match.group(1),
            'title': match.group(2).strip(),
            'type': 'subsection'
        })
    
    return entries


def calculate_percentage(numerator: int, denominator: int) -> float:
    """Calculate percentage with zero division protection"""
    if denominator == 0:
        return 0.0
    return (numerator / denominator) * 100


def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"
