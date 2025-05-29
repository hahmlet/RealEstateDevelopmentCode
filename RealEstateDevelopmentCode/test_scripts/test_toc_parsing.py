#!/usr/bin/env python3
# TEST SCRIPT: Tests TOC structure loading and parsing functionality - validates 131 document-level entries
"""
Test the fixed TOC parsing functionality
"""

import sys
import os
from pathlib import Path

# Add the chunking directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'chunking'))

def test_toc_parsing():
    """Test the TOC parsing functionality"""
    from accurate_municipal_rag import AccurateMunicipalRAG
    
    # Create a temporary instance to test the parsing
    rag = AccurateMunicipalRAG(
        source_dir="/tmp", 
        output_dir="/tmp", 
        enable_toc_validation=True
    )
    
    # Test the TOC parsing
    print("Testing TOC structure loading...")
    toc_structure = rag._load_toc_structure()
    
    if toc_structure:
        print(f"\n✅ Successfully loaded TOC structure!")
        print(f"Document-level entries: {len(toc_structure.get('document_level_entries', {}))}")
        print(f"Subsection mappings: {len(toc_structure.get('subsection_map', {}))}")
        print(f"Orphaned files: {len(toc_structure.get('orphaned_files', []))}")
        
        # Show a few examples
        doc_entries = toc_structure.get('document_level_entries', {})
        print(f"\nFirst few document-level entries:")
        for i, (key, value) in enumerate(list(doc_entries.items())[:5]):
            print(f"  {key}: {value}")
        
        subsec_map = toc_structure.get('subsection_map', {})
        print(f"\nFirst few subsection mappings:")
        for i, (parent, children) in enumerate(list(subsec_map.items())[:3]):
            print(f"  {parent} -> {len(children)} subsections")
            if children:
                for j, child in enumerate(children[:3]):
                    if isinstance(child, dict):
                        print(f"    - {child.get('id', 'N/A')}: {child.get('title', 'N/A')}")
                    else:
                        print(f"    - {child}")
        
        stats = toc_structure.get('statistics', {})
        print(f"\nStatistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        orphaned = toc_structure.get('orphaned_files', [])
        print(f"\nOrphaned files:")
        for file in orphaned:
            print(f"  - {file}")
            
    else:
        print("❌ Failed to load TOC structure")

if __name__ == "__main__":
    test_toc_parsing()
