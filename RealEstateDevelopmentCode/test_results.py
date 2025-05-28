#!/usr/bin/env python3
"""
Quick test script to show examples of processed municipal document results
"""

import json
from pathlib import Path

def show_sample_results():
    """Display sample extracted tables and text chunks"""
    
    # Load the extracted tables
    tables_file = Path("/workspace/RealEstateDevelopmentCode/rag_data_accurate/Oregon/gresham/extracted_tables.json")
    chunks_file = Path("/workspace/RealEstateDevelopmentCode/rag_data_accurate/Oregon/gresham/accurate_chunks.jsonl")

    print("🔍 SAMPLE EXTRACTED TABLES:")
    print("=" * 50)

    if tables_file.exists():
        with open(tables_file) as f:
            tables = json.load(f)
        
        # Show first 3 tables
        for i, table in enumerate(tables[:3]):
            print(f"\n📊 Table {i+1} ({table.get('method', 'unknown')} method):")
            print(f"Source: {table.get('metadata', {}).get('source', 'unknown')}")
            print(f"Content preview:")
            content = table.get('content', '')
            print(content[:300] + "..." if len(content) > 300 else content)
            print("-" * 30)
    else:
        print(f"❌ Tables file not found: {tables_file}")

    print("\n🔍 SAMPLE TEXT CHUNKS:")
    print("=" * 50)

    if chunks_file.exists():
        with open(chunks_file) as f:
            for i, line in enumerate(f):
                if i >= 3:  # Show first 3 chunks
                    break
                chunk = json.loads(line)
                if chunk.get('type') == 'text':
                    print(f"\n📝 Text Chunk {i+1}:")
                    print(f"Source: {chunk.get('metadata', {}).get('source', 'unknown')}")
                    print(f"Content preview:")
                    content = chunk.get('content', '')
                    print(content[:200] + "..." if len(content) > 200 else content)
                    print("-" * 30)
    else:
        print(f"❌ Chunks file not found: {chunks_file}")

    # Show processing stats
    print("\n📊 PROCESSING SUMMARY:")
    print("=" * 50)
    
    stats_file = Path('/workspace/RealEstateDevelopmentCode/rag_data_accurate/Oregon/gresham/accuracy_stats.json')
    if stats_file.exists():
        with open(stats_file) as f:
            stats = json.load(f)
        
        for key, value in stats.items():
            print(f'{key.capitalize()}: {value}')
    else:
        print("❌ Stats file not found")

    # Look for Section 4 tables specifically
    print("\n🎯 SECTION 4 DEVELOPMENT STANDARDS TABLES:")
    print("=" * 50)
    
    if tables_file.exists():
        section_4_tables = [
            table for table in tables
            if "4.0" in table.get("metadata", {}).get("source", "") or
               "4.0" in table.get("metadata", {}).get("document_id", "")
        ]
        
        print(f"Found {len(section_4_tables)} Section 4 tables")
        
        for i, table in enumerate(section_4_tables[:2]):  # Show first 2
            print(f"\n📋 Section 4 Table {i+1}:")
            print(f"Source: {table.get('metadata', {}).get('source', 'unknown')}")
            print(f"Method: {table.get('method', 'unknown')}")
            
            content = table.get('content', '')
            # Show more for Section 4 tables since they're the focus
            if len(content) > 500:
                lines = content.split('\n')
                preview_lines = lines[:10]  # First 10 lines
                print("Content preview (first 10 lines):")
                for line in preview_lines:
                    print(f"  {line}")
                if len(lines) > 10:
                    print(f"  ... ({len(lines) - 10} more lines)")
            else:
                print("Full content:")
                print(content)
            print("-" * 30)

if __name__ == "__main__":
    show_sample_results()
