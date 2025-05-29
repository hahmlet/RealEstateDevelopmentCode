#!/usr/bin/env python3
# TEST SCRIPT: Tests complete TOC validation workflow including quality scoring and section grouping
"""
Test the complete TOC validation workflow
"""

import sys
import os
from pathlib import Path
import json

# Add the chunking directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'chunking'))

def test_toc_validation_workflow():
    """Test the complete TOC validation workflow"""
    import os  # Import os explicitly within the function
    from accurate_municipal_rag import AccurateMunicipalRAG
    
    print("=== TESTING TOC VALIDATION WORKFLOW ===\n")
    
    # Create test directories
    test_source = "/tmp/test_source"
    test_output = "/tmp/test_output"
    os.makedirs(test_source, exist_ok=True)
    os.makedirs(test_output, exist_ok=True)
    
    # Create a test RAG instance
    rag = AccurateMunicipalRAG(
        source_dir=test_source, 
        output_dir=test_output, 
        enable_toc_validation=True
    )
    
    print("1. Testing TOC structure loading...")
    toc_structure = rag._load_toc_structure()
    if toc_structure:
        print(f"   ✅ TOC structure loaded successfully")
        print(f"   📊 Document-level entries: {len(toc_structure.get('document_level_entries', {}))}")
        print(f"   📊 Subsection mappings: {len(toc_structure.get('subsection_map', {}))}")
        print(f"   📊 Orphaned files: {len(toc_structure.get('orphaned_files', []))}")
    else:
        print("   ❌ Failed to load TOC structure")
        return
    
    print("\n2. Testing enhanced quality score calculation...")
    # Create mock table data for testing
    mock_tables = [
        {
            "table_id": "test_table_1",
            "content": "Test table content about zoning regulations 10.04",
            "confidence": 0.95,
            "source_page": 1,
            "extraction_method": "camelot"
        },
        {
            "table_id": "test_table_2", 
            "content": "Another table about development standards",
            "confidence": 0.85,
            "source_page": 2,
            "extraction_method": "tabula"
        }
    ]
    
    # Test enhanced quality scoring (test with single table)
    try:
        # Group tables first to get section groups
        section_groups = rag._group_content_by_section(mock_tables)
        enhanced_score = rag._calculate_enhanced_quality_score_with_toc(mock_tables[0], section_groups)
        print(f"   ✅ Enhanced quality score calculated: {enhanced_score['overall_score']:.3f}")
    except Exception as e:
        print(f"   ❌ Error calculating enhanced quality score: {e}")
    
    print("\n3. Testing content validation against TOC...")
    # Create a test table to validate
    test_table = {
        "content": "This document covers zoning regulations for section 10.04 and housing standards.",
        "table_id": "test_validation_table"
    }
    try:
        validation_result = rag._validate_content_against_toc(test_table)
        print(f"   ✅ Content validation completed")
        print(f"   📊 Validation confidence: {validation_result.get('confidence_score', 0):.3f}")
        print(f"   📊 Matched sections: {len(validation_result.get('matched_sections', []))}")
    except Exception as e:
        print(f"   ❌ Error validating content: {e}")
    
    print("\n4. Testing content grouping by section...")
    test_tables_with_content = [
        {"content": "Zoning regulations for residential areas in section 4.01", "table_id": "t1"},
        {"content": "Housing development standards under section 10.04", "table_id": "t2"},
        {"content": "General administrative procedures in section 3.01", "table_id": "t3"}
    ]
    try:
        grouped_content = rag._group_content_by_section(test_tables_with_content)
        print(f"   ✅ Content grouped by section")
        print(f"   📊 Sections with content: {len(grouped_content)}")
        for section, content in grouped_content.items():
            print(f"     - {section}: {len(content)} items")
    except Exception as e:
        print(f"   ❌ Error grouping content: {e}")
    
    print("\n5. Testing validation report generation...")
    # Create mock results structure to test report generation
    mock_results = {
        "extraction_id": "test_extraction_123",
        "timestamp": 1234567890,
        "source_pdf": "/tmp/test.pdf",
        "total_tables": len(mock_tables),
        "toc_validation_enabled": True,
        "tables": [
            {
                "table_id": "table_1",
                "quality_score": 0.85,
                "section_assignment": "Section 10.04",
                "toc_validation": {"is_valid": True},
                "validation_flags": ["toc_aligned"]
            }
        ],
        "quality_metrics": {"overall_quality": 0.87, "toc_validation_enabled": True}
    }
    try:
        rag._generate_toc_validation_report(mock_results, "/tmp", "test_extraction_123")
        print(f"   ✅ Validation report generated")
        # Check if report file was created
        import os
        report_file = "/tmp/test_extraction_123_toc_validation_report.md"
        if os.path.exists(report_file):
            with open(report_file, "r") as f:
                report_content = f.read()
            print(f"   📄 Report length: {len(report_content)} characters")
            print(f"   💾 Report saved to {report_file}")
        else:
            print("   ⚠ Report file not found")
    except Exception as e:
        print(f"   ❌ Error generating validation report: {e}")
    
    print("\n6. Testing complete enhanced save method...")
    try:
        save_result = rag._save_accurate_results_with_toc_validation(
            mock_tables,
            "/tmp/test.pdf",
            test_output,
            "test_municipal"
        )
        print(f"   ✅ Enhanced save method completed")
        print(f"   📊 Tables processed: {save_result.get('total_tables', 0)}")
        print(f"   📊 Overall quality: {save_result.get('quality_metrics', {}).get('overall_quality', 0):.3f}")
        print(f"   📊 TOC validation enabled: {save_result.get('quality_metrics', {}).get('toc_validation_enabled', False)}")
    except Exception as e:
        print(f"   ❌ Error in enhanced save method: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n🎉 TOC validation workflow testing completed!")

if __name__ == "__main__":
    test_toc_validation_workflow()
