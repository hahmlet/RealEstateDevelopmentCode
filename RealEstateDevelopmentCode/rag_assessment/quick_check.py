#!/usr/bin/env python3
"""
Quick RAG Quality Checker - Fast assessment of key quality metrics
"""

import json
import os
from pathlib import Path
from collections import Counter

def quick_quality_check(rag_data_dir: str):
    """Perform a quick quality assessment of RAG data"""
    
    print("🔍 Quick RAG Quality Assessment")
    print("=" * 50)
    
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
    
    print(f"📊 Total chunks loaded: {len(chunks)}")
    
    # Basic statistics
    tables = [c for c in chunks if c.get('type') == 'table']
    text_chunks = [c for c in chunks if c.get('type') == 'text']
    
    print(f"📋 Table chunks: {len(tables)}")
    print(f"📝 Text chunks: {len(text_chunks)}")
    
    # Content size analysis
    chunk_sizes = [len(c.get('content', '')) for c in chunks]
    if chunk_sizes:
        avg_size = sum(chunk_sizes) / len(chunk_sizes)
        print(f"📏 Average chunk size: {avg_size:.0f} characters")
        print(f"📏 Size range: {min(chunk_sizes)} - {max(chunk_sizes)} characters")
    
    # Table quality check
    if tables:
        markdown_tables = sum(1 for t in tables if '|' in t.get('content', '') and '---' in t.get('content', ''))
        print(f"✅ Markdown formatted tables: {markdown_tables}/{len(tables)} ({markdown_tables/len(tables)*100:.1f}%)")
        
        # Sample table preview
        print(f"\n📋 Sample table content:")
        sample_table = tables[0] if tables else None
        if sample_table:
            content = sample_table.get('content', '')[:300]
            print(f"   {content}...")
    
    # Municipal code coverage check
    municipal_keywords = ['parking', 'zoning', 'setback', 'height', 'landscaping', 'sign']
    coverage = {}
    
    for keyword in municipal_keywords:
        matching_chunks = [c for c in chunks if keyword in c.get('content', '').lower()]
        coverage[keyword] = len(matching_chunks)
    
    print(f"\n🏛️ Municipal Code Coverage:")
    for keyword, count in coverage.items():
        print(f"   {keyword.title()}: {count} chunks")
    
    # Quality issues check
    issues = []
    for i, chunk in enumerate(chunks):
        content = chunk.get('content', '')
        if len(content.strip()) < 50:
            issues.append(f"Chunk {i}: Too short ({len(content)} chars)")
        if not chunk.get('metadata', {}):
            issues.append(f"Chunk {i}: Missing metadata")
    
    print(f"\n⚠️ Quality Issues Found: {len(issues)}")
    if issues:
        print("   Sample issues:")
        for issue in issues[:5]:
            print(f"     - {issue}")
    
    # Sample content preview
    print(f"\n📖 Sample Content Preview:")
    if text_chunks:
        sample_chunk = text_chunks[0]
        content = sample_chunk.get('content', '')[:200]
        source = sample_chunk.get('metadata', {}).get('source', 'Unknown')
        print(f"   Source: {Path(source).name}")
        print(f"   Content: {content}...")
    
    print(f"\n✅ Quick assessment complete!")

if __name__ == "__main__":
    rag_data_dir = "/workspace/RealEstateDevelopmentCode/production_rag_data/Oregon/gresham"
    quick_quality_check(rag_data_dir)
