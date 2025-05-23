#!/usr/bin/env python3
"""
Simple script to demonstrate the corrected hierarchical document structure.
"""

import os
import re
import json
from pathlib import Path
from collections import defaultdict

def analyze_hierarchical_structure():
    """
    Analyze document structure with the correct hierarchical understanding.
    """
    # Path to TOC and document files
    toc_path = Path("/workspace/data/pdf_content/Oregon/gresham/dc-table-of-contents.json")
    docs_dir = Path("/workspace/data/pdf_content/Oregon/gresham")
    
    # Load TOC
    if not toc_path.exists():
        print(f"ERROR: TOC file not found at {toc_path}")
        return
    
    with open(toc_path, 'r') as f:
        toc_data = json.load(f)
    
    toc_content = toc_data.get('content', '')
    print(f"Loaded TOC with {len(toc_content)} characters")
    
    # Scan available document files
    doc_files = [f.name for f in docs_dir.glob("*.json") if f.name != "dc-table-of-contents.json"]
    print(f"Found {len(doc_files)} document files")
    
    # Categorize files
    section_files = [f for f in doc_files if re.match(r'dc-section-', f)]
    article_files = [f for f in doc_files if re.match(r'dc-article-', f)]
    appendix_files = [f for f in doc_files if re.match(r'dc-appendix-', f) or "appendix" in f.lower()]
    other_files = [f for f in doc_files if f not in section_files + article_files + appendix_files]
    
    print(f"\nFile categories:")
    print(f"  Sections: {len(section_files)}")
    print(f"  Articles: {len(article_files)}")
    print(f"  Appendices: {len(appendix_files)}")
    print(f"  Other: {len(other_files)}")
    
    # Extract document IDs from filenames
    section_ids = []
    for fname in section_files:
        match = re.search(r'dc-section-(\d+\.\d{4})', fname)
        if match:
            section_ids.append(match.group(1))
    
    # Now extract TOC entries with hierarchical understanding
    # Section pattern: like "10.0400 Title for section"
    section_pattern = re.compile(r'(\d+\.\d{4})\s+(.*?)(?=\d+\.\d{4}|\Z)', re.DOTALL)
    
    # Extract document-level entries (XX.YY format)
    doc_level_entries = []
    for match in section_pattern.finditer(toc_content):
        section_id = match.group(1).strip()
        title = match.group(2).strip()
        
        # Convert to document-level ID (like 10.04 from 10.0400)
        if len(section_id) >= 5:  # At least 10.04 format
            doc_id = section_id[:section_id.find('.') + 3]
            doc_level_entries.append({
                "id": doc_id,
                "title": title,
                "full_id": section_id
            })
    
    # Count unique document-level entries
    unique_doc_ids = set(entry["id"] for entry in doc_level_entries)
    print(f"\nTOC Document Structure Analysis:")
    print(f"  Total TOC entries: {len(doc_level_entries)}")
    print(f"  Unique document-level entries: {len(unique_doc_ids)}")
    
    # Group TOC entries by document ID
    doc_hierarchy = defaultdict(list)
    for entry in doc_level_entries:
        doc_hierarchy[entry["id"]].append(entry["full_id"])
    
    # Report on document structure
    print(f"\nDocument Hierarchy Examples:")
    count = 0
    for doc_id, subsections in sorted(doc_hierarchy.items())[:5]:  # Show first 5 examples
        print(f"  Document {doc_id}:")
        for i, subsection in enumerate(subsections[:3]):  # Show first 3 subsections
            print(f"    - Subsection: {subsection}")
        if len(subsections) > 3:
            print(f"    - ... and {len(subsections) - 3} more subsections")
        count += 1
    
    if len(doc_hierarchy) > 5:
        print(f"  ... and {len(doc_hierarchy) - 5} more documents")
    
    # Calculate correct alignment metrics
    available_docs = set()
    for fname in doc_files:
        # Extract document ID from filename
        section_match = re.search(r'dc-section-(\d+\.\d{2})', fname)
        if section_match:
            available_docs.add(section_match.group(1))
        article_match = re.search(r'dc-article-(\d+)', fname)
        if article_match:
            available_docs.add(f"Article {article_match.group(1)}")
        appendix_match = re.search(r'dc-appendix-(\d+)', fname)
        if appendix_match:
            available_docs.add(f"Appendix {appendix_match.group(1)}")
    
    # Compare document-level entries with available files
    matched_docs = available_docs.intersection(unique_doc_ids)
    missing_docs = unique_doc_ids - available_docs
    orphaned_files = available_docs - unique_doc_ids
    
    print(f"\nCORRECTED Alignment Analysis:")
    print(f"  Document-level entries in TOC: {len(unique_doc_ids)}")
    print(f"  Available document files: {len(available_docs)}")
    print(f"  Successfully matched documents: {len(matched_docs)}")
    print(f"  Missing documents: {len(missing_docs)}")
    print(f"  Orphaned files: {len(orphaned_files)}")
    
    if unique_doc_ids:
        alignment_score = (len(matched_docs) / len(unique_doc_ids)) * 100
        print(f"  Alignment score: {alignment_score:.1f}%")
    
    print("\nCONCLUSION:")
    print("  The corrected analysis properly recognizes the hierarchical nature of municipal codes,")
    print("  where document files correspond to XX.YY entries, not every TOC entry.")

if __name__ == "__main__":
    analyze_hierarchical_structure()
