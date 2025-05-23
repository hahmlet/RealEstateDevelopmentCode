#!/usr/bin/env python3
"""
Debug TOC parsing to understand the structure
"""

import json
import re
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts'))

def debug_toc_parsing():
    toc_file = "/workspace/data/pdf_content/Oregon/gresham/dc-table-of-contents.json"
    
    with open(toc_file, 'r', encoding='utf-8') as f:
        toc_data = json.load(f)
    
    # Collect all text from pages
    all_text = ""
    page_count = 0
    
    print("Analyzing TOC structure...")
    
    for key, value in toc_data.items():
        if isinstance(value, dict) and 'text' in value:
            all_text += value['text'] + "\n"
            page_count += 1
            print(f"Found page with text: {key}")
        elif isinstance(value, list):
            for i, page in enumerate(value):
                if isinstance(page, dict) and 'text' in page:
                    all_text += page['text'] + "\n"
                    page_count += 1
                    print(f"Found page in list {key}[{i}] with text")
    
    print(f"Total pages with text: {page_count}")
    print(f"Total text length: {len(all_text)}")
    
    # Show sample text
    print("\nSample text (first 1000 chars):")
    print(all_text[:1000])
    
    # Test different patterns
    patterns = [
        # Pattern for SECTION headers
        (r'SECTION\s+(\d+\.\d+)\s+([A-Z\s]+)', "SECTION headers"),
        # Pattern for subsection entries with dots
        (r'(\d+\.\d{4})\s+([^.]+?)\s+\.+\s*\[([^\]]+)\]', "Subsection entries with page refs"),
        # Pattern for subsection entries without dots
        (r'(\d+\.\d{4})\s+([^.\n]+?)(?=\s*\n|\s+\d+\.\d{4})', "Subsection entries without page refs"),
        # Pattern for document level (XX.XX format)
        (r'(\d+\.\d{2})\s+([^.\n]+?)(?=\s*\n|\s+\d+\.\d)', "Document level entries"),
        # General number pattern
        (r'(\d+\.\d+)', "All numbers"),
    ]
    
    for pattern, description in patterns:
        matches = re.findall(pattern, all_text, re.MULTILINE)
        print(f"\n{description}: Found {len(matches)} matches")
        if matches:
            print("Sample matches:")
            for i, match in enumerate(matches[:5]):
                print(f"  {i+1}: {match}")
    
    # Look for SECTION patterns specifically
    print("\nSearching for SECTION patterns...")
    section_matches = re.finditer(r'SECTION\s+(\d+\.\d+)\s+([A-Z\s]+)', all_text, re.MULTILINE)
    for i, match in enumerate(section_matches):
        if i >= 10:  # Limit output
            break
        print(f"  SECTION {match.group(1)}: {match.group(2).strip()}")

if __name__ == "__main__":
    debug_toc_parsing()
