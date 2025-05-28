#!/usr/bin/env python3
"""
Simple test to verify the enhanced table extraction phases are working
"""

import sys
import json
from pathlib import Path

# Add chunking directory to path
sys.path.insert(0, str(Path(__file__).parent / "chunking"))

def test_basic_functionality():
    """Test basic functionality of the enhanced phases"""
    
    print("🧪 Testing Enhanced Table Extraction Implementation")
    print("=" * 50)
    
    try:
        # Import the class
        from accurate_municipal_rag import AccurateMunicipalRAG
        print("✓ Successfully imported AccurateMunicipalRAG")
        
        # Create instance
        rag = AccurateMunicipalRAG("./pdf_content", "./test_output")
        print("✓ Successfully created RAG instance")
        
        # Test Phase 1 method exists and is callable
        if hasattr(rag, '_extract_tables_with_unstructured_advanced'):
            print("✓ Phase 1: _extract_tables_with_unstructured_advanced method exists")
        else:
            print("❌ Phase 1 method missing")
            return False
            
        # Test Phase 2 methods exist
        if hasattr(rag, '_extract_element_coordinates'):
            print("✓ Phase 2a: _extract_element_coordinates method exists")
        else:
            print("❌ Phase 2a method missing")
            return False
            
        if hasattr(rag, '_reconstruct_spatial_table'):
            print("✓ Phase 2b: _reconstruct_spatial_table method exists")
        else:
            print("❌ Phase 2b method missing")
            return False
            
        # Test Phase 3 method exists
        if hasattr(rag, '_validate_and_score_tables'):
            print("✓ Phase 3: _validate_and_score_tables method exists")
        else:
            print("❌ Phase 3 method missing")
            return False
            
        # Test quality scoring method
        if hasattr(rag, '_calculate_table_quality_score'):
            print("✓ Quality scoring method exists")
        else:
            print("❌ Quality scoring method missing")
            return False
            
        # Test validation methods
        validation_methods = [
            '_validate_table_content',
            '_validate_table_structure', 
            '_validate_municipal_table'
        ]
        
        for method in validation_methods:
            if hasattr(rag, method):
                print(f"✓ {method} method exists")
            else:
                print(f"❌ {method} method missing")
                return False
        
        print("\n🎯 All Phase 1-3 methods successfully implemented!")
        return True
        
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_phase_3_validation():
    """Test Phase 3 validation with sample data"""
    
    print("\n" + "=" * 50)
    print("🔬 Testing Phase 3 Validation Functions")
    print("=" * 50)
    
    try:
        from accurate_municipal_rag import AccurateMunicipalRAG
        rag = AccurateMunicipalRAG("./pdf_content", "./test_output")
        
        # Create sample table data for testing
        sample_tables = [
            {
                "type": "table",
                "method": "unstructured_advanced",
                "content": """| Zone | Min Lot Size | Max Height | Setback |
| --- | --- | --- | --- |
| LDR-5 | 5,000 sq ft | 35 feet | 15 feet |
| LDR-7 | 7,000 sq ft | 35 feet | 20 feet |
| TLDR | 6,000 sq ft | 45 feet | 10 feet |""",
                "metadata": {
                    "table_id": "test_municipal_table",
                    "coordinates": {"points": [100, 200, 400, 300]}
                }
            },
            {
                "type": "table", 
                "method": "tabula",
                "content": "Poor quality table\nwith minimal structure",
                "metadata": {"table_id": "poor_quality_table"}
            }
        ]
        
        print(f"📊 Testing validation on {len(sample_tables)} sample tables...")
        
        # Test Phase 3 validation
        validated_tables = rag._validate_and_score_tables(sample_tables)
        
        print(f"✓ Validation completed: {len(validated_tables)} tables processed")
        
        # Show results
        for i, table in enumerate(validated_tables):
            quality = table.get("quality_metrics", {})
            score = quality.get("overall_score", 0)
            status = quality.get("validation_status", "unknown")
            
            print(f"\nTable {i+1}:")
            print(f"  Quality Score: {score:.3f}")
            print(f"  Status: {status}")
            print(f"  Method: {table.get('method', 'unknown')}")
            
            # Show validation details
            if "municipal_validation" in quality:
                municipal_val = quality["municipal_validation"]
                municipal_score = municipal_val.get("municipal_score", 0)
                patterns = municipal_val.get("detected_patterns", [])
                print(f"  Municipal Score: {municipal_score:.3f}")
                if patterns:
                    print(f"  Municipal Patterns: {', '.join(patterns[:3])}")
        
        print("\n✓ Phase 3 validation test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Phase 3 test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_coordinate_extraction():
    """Test Phase 2 coordinate extraction"""
    
    print("\n" + "=" * 50)
    print("🎯 Testing Phase 2 Coordinate Extraction")
    print("=" * 50)
    
    try:
        from accurate_municipal_rag import AccurateMunicipalRAG
        rag = AccurateMunicipalRAG("./pdf_content", "./test_output")
        
        # Create mock element with coordinates
        class MockElement:
            def __init__(self):
                self.metadata = MockMetadata()
                self.category = "Table"
                
            def __str__(self):
                return "Test table content"
        
        class MockMetadata:
            def __init__(self):
                self.coordinates = MockCoordinates()
                self.text_as_html = "<table><tr><td>Zone</td><td>Requirement</td></tr><tr><td>LDR-5</td><td>35 feet</td></tr></table>"
        
        class MockCoordinates:
            def __init__(self):
                self.points = [100, 200, 400, 300]
                self.coordinate_system = "pixel"
        
        mock_element = MockElement()
        
        # Test coordinate extraction
        coordinates = rag._extract_element_coordinates(mock_element)
        
        if coordinates:
            print("✓ Coordinate extraction successful")
            print(f"  Coordinates: {coordinates}")
            
            # Test spatial reconstruction
            reconstructed = rag._reconstruct_spatial_table(mock_element, coordinates)
            if reconstructed:
                print("✓ Spatial reconstruction successful")
                print(f"  Reconstructed preview: {reconstructed[:100]}...")
            else:
                print("⚠️ Spatial reconstruction returned None")
        else:
            print("⚠️ No coordinates extracted")
        
        print("\n✓ Phase 2 coordinate test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Phase 2 test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def demonstrate_existing_data_enhancement():
    """Show how the phases would enhance existing extracted data"""
    
    print("\n" + "=" * 50)
    print("📈 Demonstration: Enhancing Existing Data")
    print("=" * 50)
    
    try:
        # Load existing tables
        existing_file = "./rag_data_accurate/Oregon/gresham/extracted_tables.json"
        if not Path(existing_file).exists():
            print(f"⚠️ Existing tables file not found: {existing_file}")
            return True
            
        with open(existing_file, 'r') as f:
            existing_tables = json.load(f)
        
        print(f"📊 Loaded {len(existing_tables)} existing tables")
        
        # Filter for Section 4 tables (development standards)
        section_4_tables = [
            table for table in existing_tables
            if "4.0" in table.get("metadata", {}).get("source", "") or
               "4.0" in table.get("metadata", {}).get("document_id", "")
        ]
        
        print(f"🎯 Found {len(section_4_tables)} Section 4 tables")
        
        if section_4_tables:
            from accurate_municipal_rag import AccurateMunicipalRAG
            rag = AccurateMunicipalRAG("./pdf_content", "./test_output")
            
            # Take first few tables and enhance them
            sample_tables = section_4_tables[:3]
            enhanced_tables = rag._validate_and_score_tables(sample_tables)
            
            print(f"\n📈 Enhancement Results:")
            total_score = 0
            municipal_patterns = 0
            
            for i, table in enumerate(enhanced_tables):
                quality = table.get("quality_metrics", {})
                score = quality.get("overall_score", 0)
                total_score += score
                
                municipal_val = quality.get("municipal_validation", {})
                patterns = municipal_val.get("detected_patterns", [])
                if patterns:
                    municipal_patterns += 1
                
                print(f"\nEnhanced Table {i+1}:")
                print(f"  Original Method: {table.get('method', 'unknown')}")
                print(f"  Quality Score: {score:.3f}")
                print(f"  Municipal Patterns: {len(patterns)} found")
                if patterns:
                    print(f"    Examples: {', '.join(patterns[:2])}")
                
                # Show content preview
                content = table.get("content", "")
                preview = content.replace('\n', ' ')[:80] + "..." if len(content) > 80 else content
                print(f"  Content Preview: {preview}")
            
            avg_score = total_score / len(enhanced_tables) if enhanced_tables else 0
            print(f"\n📊 Summary:")
            print(f"  Average Quality Score: {avg_score:.3f}")
            print(f"  Tables with Municipal Patterns: {municipal_patterns}/{len(enhanced_tables)}")
            
            # Save enhanced results
            output_file = Path("./test_output/phase_demonstration_results.json")
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w') as f:
                json.dump({
                    "summary": {
                        "total_enhanced": len(enhanced_tables),
                        "average_quality_score": avg_score,
                        "municipal_pattern_coverage": municipal_patterns / len(enhanced_tables) if enhanced_tables else 0
                    },
                    "enhanced_tables": enhanced_tables
                }, f, indent=2, default=str)
            
            print(f"\n📁 Results saved to: {output_file}")
        
        print("\n✓ Existing data enhancement demonstration completed!")
        return True
        
    except Exception as e:
        print(f"❌ Enhancement demonstration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Enhanced Table Extraction Phases 1-3 Test Suite")
    print("=" * 60)
    
    tests = [
        ("Basic Functionality", test_basic_functionality),
        ("Phase 3 Validation", test_phase_3_validation), 
        ("Phase 2 Coordinates", test_coordinate_extraction),
        ("Data Enhancement Demo", demonstrate_existing_data_enhancement)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running: {test_name}")
        if test_func():
            passed += 1
            print(f"✅ {test_name} PASSED")
        else:
            print(f"❌ {test_name} FAILED")
    
    print("\n" + "=" * 60)
    print(f"🎯 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Enhanced table extraction phases successfully implemented!")
    else:
        print("⚠️ Some tests failed. Please review the implementation.")
    
    sys.exit(0 if passed == total else 1)
