#!/usr/bin/env python3
"""Simple script to test execution"""

import sys
import json
from pathlib import Path

def main():
    # Print some basic information
    print("Python version:", sys.version)
    print("Current directory:", Path.cwd())
    
    # Try to load a TOC file
    toc_file = Path("/workspace/data/pdf_content/Oregon/gresham/dc-table-of-contents.json")
    print(f"TOC file exists: {toc_file.exists()}")
    
    if toc_file.exists():
        try:
            with open(toc_file, 'r') as f:
                toc_data = json.load(f)
            print(f"Successfully loaded TOC with {len(toc_data.get('content', ''))} characters")
        except Exception as e:
            print(f"Error loading TOC: {e}")
    
    # Print document files
    content_dir = Path("/workspace/data/pdf_content/Oregon/gresham")
    doc_files = list(content_dir.glob("*.json"))
    print(f"Found {len(doc_files)} document files")
    
    # Categorize some files
    section_files = [f.name for f in doc_files if f.name.startswith("dc-section-")]
    article_files = [f.name for f in doc_files if f.name.startswith("dc-article-")]
    appendix_files = [f.name for f in doc_files if f.name.startswith("dc-appendix-")]
    
    print(f"Section files: {len(section_files)}")
    print(f"Article files: {len(article_files)}")
    print(f"Appendix files: {len(appendix_files)}")
    
    print("\nSuccess! Script completed.")

if __name__ == "__main__":
    main()
