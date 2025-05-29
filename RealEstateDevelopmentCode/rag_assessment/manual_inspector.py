#!/usr/bin/env python3
"""
Manual Content Inspector - Interactive tool to manually review content quality
"""

import json
import random
from pathlib import Path

def inspect_content_interactively(rag_data_dir: str):
    """Interactive content inspection tool"""
    
    print("🔍 Manual Content Inspector")
    print("=" * 40)
    
    # Load chunks
    chunks_file = Path(rag_data_dir) / "accurate_chunks.jsonl"
    if not chunks_file.exists():
        print(f"❌ No chunks file found at {chunks_file}")
        return
    
    chunks = []
    with open(chunks_file, 'r') as f:
        for line in f:
            if line.strip():
                chunks.append(json.loads(line))
    
    print(f"📊 Loaded {len(chunks)} chunks")
    
    while True:
        print(f"\n🔍 Content Inspection Options:")
        print("1. Random chunk")
        print("2. Random table") 
        print("3. Search by keyword")
        print("4. Chunks by source file")
        print("5. Quality issue examples")
        print("6. Exit")
        
        choice = input("\nSelect option (1-6): ").strip()
        
        if choice == "1":
            # Show random chunk
            chunk = random.choice(chunks)
            show_chunk_details(chunk)
            
        elif choice == "2":
            # Show random table
            tables = [c for c in chunks if c.get('type') == 'table']
            if tables:
                table = random.choice(tables)
                show_chunk_details(table)
            else:
                print("❌ No tables found")
                
        elif choice == "3":
            # Search by keyword
            keyword = input("Enter keyword to search: ").strip().lower()
            matching = [c for c in chunks if keyword in c.get('content', '').lower()]
            
            if matching:
                print(f"Found {len(matching)} matching chunks")
                chunk = random.choice(matching)
                show_chunk_details(chunk)
            else:
                print(f"❌ No chunks found containing '{keyword}'")
                
        elif choice == "4":
            # Show chunks by source
            sources = list(set(c.get('metadata', {}).get('source', 'Unknown') for c in chunks))
            print(f"Available sources:")
            for i, source in enumerate(sources[:10]):  # Show first 10
                print(f"  {i+1}. {Path(source).name}")
            
            try:
                source_idx = int(input("Select source number: ")) - 1
                selected_source = sources[source_idx]
                source_chunks = [c for c in chunks if c.get('metadata', {}).get('source') == selected_source]
                
                if source_chunks:
                    chunk = random.choice(source_chunks)
                    show_chunk_details(chunk)
                    print(f"📊 This source has {len(source_chunks)} total chunks")
            except (ValueError, IndexError):
                print("❌ Invalid selection")
                
        elif choice == "5":
            # Show quality issues
            issues = []
            for chunk in chunks:
                content = chunk.get('content', '')
                if len(content.strip()) < 50:
                    issues.append(('Too short', chunk))
                elif len(content) > 5000:
                    issues.append(('Too long', chunk))
                elif not chunk.get('metadata', {}):
                    issues.append(('Missing metadata', chunk))
            
            if issues:
                issue_type, chunk = random.choice(issues)
                print(f"🚨 Quality Issue: {issue_type}")
                show_chunk_details(chunk)
            else:
                print("✅ No obvious quality issues found")
                
        elif choice == "6":
            print("👋 Goodbye!")
            break
            
        else:
            print("❌ Invalid option")

def show_chunk_details(chunk):
    """Display detailed information about a chunk"""
    
    print(f"\n" + "="*60)
    print(f"📄 Chunk Details")
    print(f"="*60)
    
    # Basic info
    chunk_type = chunk.get('type', 'unknown')
    print(f"Type: {chunk_type}")
    
    # Metadata
    metadata = chunk.get('metadata', {})
    print(f"Source: {Path(str(metadata.get('source', 'Unknown'))).name}")
    print(f"Document ID: {metadata.get('document_id', 'Unknown')}")
    print(f"Document Title: {metadata.get('document_title', 'Unknown')}")
    print(f"Page: {metadata.get('page', 'Unknown')}")
    print(f"Content Type: {metadata.get('content_type', 'Unknown')}")
    
    if chunk_type == 'table':
        print(f"Table Method: {chunk.get('method', 'Unknown')}")
        print(f"Table ID: {metadata.get('table_id', 'Unknown')}")
    
    # Content
    content = chunk.get('content', '')
    print(f"Content Length: {len(content)} characters")
    print(f"\n📝 Content Preview:")
    print("-" * 40)
    
    # Show first part of content
    preview_length = 500
    if len(content) <= preview_length:
        print(content)
    else:
        print(content[:preview_length])
        print(f"\n... [Content truncated - showing first {preview_length} of {len(content)} characters]")
    
    print("-" * 40)
    
    # Quality assessment
    print(f"\n🔍 Quality Assessment:")
    
    if chunk_type == 'table':
        if '|' in content and '---' in content:
            print("✅ Properly formatted markdown table")
        else:
            print("⚠️ Not markdown formatted")
            
        lines = content.split('\n')
        if len(lines) >= 3:
            print("✅ Multi-row table")
        else:
            print("⚠️ Very short table")
    else:
        if len(content.strip()) < 50:
            print("⚠️ Very short content")
        elif len(content) > 2000:
            print("⚠️ Very long content")
        else:
            print("✅ Reasonable content length")
    
    if metadata:
        print("✅ Has metadata")
    else:
        print("⚠️ Missing metadata")
    
    input(f"\nPress Enter to continue...")

if __name__ == "__main__":
    rag_data_dir = "/workspace/RealEstateDevelopmentCode/production_rag_data/Oregon/gresham"
    inspect_content_interactively(rag_data_dir)
