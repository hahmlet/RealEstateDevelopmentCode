#!/usr/bin/env python3
# TEST SCRIPT: Tests full integration of TOC validation with table extraction end-to-end
"""
Test the full integration of TOC validation with table extraction
"""

import sys
import os
from pathlib import Path

# Add the chunking directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'chunking'))

def test_full_integration():
    """Test the complete integration of TOC validation with table extraction"""
    from accurate_municipal_rag import AccurateMunicipalRAG
    
    print("=== FULL TOC INTEGRATION TEST ===\n")
    
    # Create test directories
    test_source = "/tmp/integration_source"
    test_output = "/tmp/integration_output"
    os.makedirs(test_source, exist_ok=True)
    os.makedirs(test_output, exist_ok=True)
    
    # Initialize the RAG system with TOC validation enabled
    rag = AccurateMunicipalRAG(
        source_dir=test_source, 
        output_dir=test_output, 
        enable_toc_validation=True
    )
    
    print("1. Checking TOC structure loading...")
    toc_structure = rag._load_toc_structure()
    if toc_structure:
        print(f"   ✅ TOC loaded: {len(toc_structure.get('document_level_entries', {}))} entries")
    else:
        print("   ❌ Failed to load TOC structure")
        return
    
    print("\n2. Testing with realistic table data...")
    # Create realistic table data for testing
    realistic_tables = [
        {
            "content": "Zoning District Regulations\nLow Density Residential (LDR): Minimum lot size 6,000 sq ft\nMedium Density Residential (MDR): Minimum lot size 4,000 sq ft",
            "extracted_text": "LDR 6,000 MDR 4,000",
            "page_number": 1,
            "extraction_method": "camelot",
            "confidence": 0.92
        },
        {
            "content": "Section 10.0400 Housing Development Standards\nMaximum height: 35 feet\nMinimum setbacks: Front 20 feet, Side 5 feet",
            "extracted_text": "10.0400 height 35 setback 20 5",
            "page_number": 2,
            "extraction_method": "tabula",
            "confidence": 0.87
        },
        {
            "content": "Administrative Procedures for Section 3.01\nApplication deadlines and review process",
            "extracted_text": "3.01 application deadlines review",
            "page_number": 3,
            "extraction_method": "camelot",
            "confidence": 0.78
        }
    ]
    
    print("\n3. Running enhanced save with TOC validation...")
    try:
        results = rag._save_accurate_results_with_toc_validation(
            realistic_tables,
            "/tmp/test_document.pdf",
            test_output,
            "integration_test"
        )
        
        print(f"   ✅ Integration test completed successfully!")
        print(f"   📊 Total tables processed: {results.get('total_tables', 0)}")
        print(f"   📊 Tables with TOC validation: {len([t for t in results.get('tables', []) if t.get('toc_validation', {}).get('is_valid', False)])}")
        print(f"   📊 Average quality score: {results.get('quality_metrics', {}).get('average_quality_score', 0):.3f}")
        print(f"   📊 Section coverage: {results.get('quality_metrics', {}).get('section_coverage', 0)} sections")
        
        # Show section assignments
        print("\n   📋 Section Assignments:")
        for i, table in enumerate(results.get('tables', [])):
            section = table.get('section_assignment', 'unassigned')
            quality = table.get('quality_score', 0)
            toc_valid = table.get('toc_validation', {}).get('is_valid', False)
            print(f"     Table {i+1}: {section} (Quality: {quality:.3f}, TOC Valid: {toc_valid})")
        
        # Check if files were created
        print(f"\n   📁 Output files created:")
        output_dir = Path(test_output)
        for file in output_dir.glob("integration_test_*"):
            print(f"     - {file.name}")
        
    except Exception as e:
        print(f"   ❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n🎉 Full integration test completed!")

if __name__ == "__main__":
    test_full_integration()
