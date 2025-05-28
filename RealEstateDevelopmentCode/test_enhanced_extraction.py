#!/usr/bin/env python3
"""
Test script for the enhanced table extraction system (Phases 1-3)
Using Section 4.0100 as the working example.
"""

import json
import sys
from pathlib import Path

# Add the chunking directory to the path
sys.path.append(str(Path(__file__).parent / "chunking"))

from accurate_municipal_rag import AccurateMunicipalRAG

def test_enhanced_extraction():
    """Test the enhanced table extraction on Section 4.0100"""
    
    # Setup
    source_dir = "/workspace/RealEstateDevelopmentCode/pdf_content"
    output_dir = "/workspace/RealEstateDevelopmentCode/test_output"
    
    rag = AccurateMunicipalRAG(source_dir, output_dir)
    
    # Test file - Section 4.0100
    pdf_path = "/workspace/RealEstateDevelopmentCode/pdf_content/Oregon/gresham/dc-section-4.0100.pdf"
    
    if not Path(pdf_path).exists():
        print(f"❌ Test PDF not found: {pdf_path}")
        return False
    
    print(f"🧪 Testing enhanced table extraction on: {pdf_path}")
    print("=" * 60)
    
    try:
        # Process the document
        results = rag.process_document_with_tables(pdf_path)
        
        print(f"📊 Extraction Results:")
        print(f"   Total elements: {len(results)}")
        
        # Analyze table results
        table_results = [r for r in results if r.get("type") == "table"]
        text_results = [r for r in results if r.get("type") == "text"]
        
        print(f"   Tables found: {len(table_results)}")
        print(f"   Text chunks: {len(text_results)}")
        print()
        
        # Detailed table analysis
        if table_results:
            print("🔍 Table Analysis:")
            print("-" * 40)
            
            for i, table in enumerate(table_results):
                method = table.get("method", "unknown")
                quality = table.get("quality_metrics", {})
                score = quality.get("overall_score", 0)
                status = quality.get("validation_status", "unknown")
                
                print(f"Table {i+1}:")
                print(f"  Method: {method}")
                print(f"  Quality Score: {score:.3f}")
                print(f"  Status: {status}")
                
                # Show content preview
                content = table.get("content", "")
                lines = content.split('\n')[:3]  # First 3 lines
                print(f"  Preview: {' | '.join(line.strip() for line in lines if line.strip())[:100]}...")
                
                # Show quality metrics details
                if "content_validation" in quality:
                    content_score = quality["content_validation"].get("content_score", 0)
                    print(f"  Content Score: {content_score:.3f}")
                
                if "municipal_validation" in quality:
                    municipal_score = quality["municipal_validation"].get("municipal_score", 0)
                    patterns = quality["municipal_validation"].get("detected_patterns", [])
                    print(f"  Municipal Score: {municipal_score:.3f}")
                    if patterns:
                        print(f"  Detected Patterns: {', '.join(patterns[:3])}...")
                
                print()
        
        # Test specific phases
        print("🔬 Phase Testing:")
        print("-" * 40)
        
        # Test Phase 1: Enhanced Unstructured extraction
        print("Phase 1: Enhanced Unstructured.io extraction...")
        enhanced_tables = rag._extract_tables_with_unstructured_advanced(pdf_path)
        print(f"  ✓ Found {len(enhanced_tables)} tables with advanced extraction")
        
        # Show coordinate information
        coord_count = sum(1 for table in enhanced_tables 
                         if table.get("metadata", {}).get("coordinates"))
        print(f"  ✓ {coord_count} tables have coordinate information")
        
        # Test Phase 2 & 3 on first table if available
        if enhanced_tables:
            first_table = enhanced_tables[0]
            
            print("Phase 2: Coordinate extraction and spatial reconstruction...")
            coords = first_table.get("metadata", {}).get("coordinates")
            if coords:
                print(f"  ✓ Coordinates available: {type(coords).__name__}")
            else:
                print("  ⚠ No coordinates found")
            
            print("Phase 3: Quality validation...")
            validated = rag._validate_and_score_tables([first_table])
            if validated:
                quality = validated[0].get("quality_metrics", {})
                score = quality.get("overall_score", 0)
                print(f"  ✓ Quality score: {score:.3f}")
                print(f"  ✓ Validation status: {quality.get('validation_status', 'unknown')}")
        
        print()
        print("🎯 Test completed successfully!")
        
        # Save results for inspection
        output_file = Path(output_dir) / "enhanced_extraction_test.json"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"📁 Results saved to: {output_file}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_enhanced_extraction()
    sys.exit(0 if success else 1)
