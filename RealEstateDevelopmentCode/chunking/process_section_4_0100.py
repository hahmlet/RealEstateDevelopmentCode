#!/usr/bin/env python3
"""
Process a specific document (dc-section-4.0100.json) to verify table extraction works
"""

import json
import os
import sys
from pathlib import Path

# Add parent directory to path so we can import AccurateMunicipalRAG
sys.path.append(str(Path(__file__).parent.parent))
print("Added parent directory to path")

try:
    from chunking.accurate_municipal_rag import AccurateMunicipalRAG
    print("Successfully imported AccurateMunicipalRAG")
except Exception as e:
    print(f"Error importing AccurateMunicipalRAG: {e}")
    sys.exit(1)

def process_specific_document():
    """Process a specific document to verify table extraction"""
    
    input_file = "/workspace/RealEstateDevelopmentCode/pdf_content/Oregon/gresham/dc-section-4.0100.json"
    output_dir = "/workspace/RealEstateDevelopmentCode/rag_data_test/Oregon/gresham"
    
    print(f"Input file: {input_file}")
    print(f"Output directory: {output_dir}")
    
    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    print("Created output directory if needed")
    
    try:
        # Create RAG processor
        print("Creating RAG processor...")
        rag = AccurateMunicipalRAG(
            source_dir="/workspace/RealEstateDevelopmentCode/pdf_content",
            output_dir="/workspace/RealEstateDevelopmentCode/rag_data_test"
        )
        print("RAG processor created successfully")
        
        # Load document
        print("Loading document...")
        with open(input_file, 'r') as f:
            document = json.load(f)
        print(f"Document loaded: {len(document.get('pages', []))} pages")
        
        document_id = Path(input_file).stem
        print(f"Document ID: {document_id}")
        
        # Process document into chunks
        print("Processing document into chunks...")
        chunks = rag.prepare_from_json_content(document, document_id)
        print(f"Generated {len(chunks)} chunks")
        
        # Count table chunks
        table_chunks = [chunk for chunk in chunks if chunk["type"] == "table"]
        print(f"Table chunks: {len(table_chunks)}")
        
        # Write to output file
        output_file = Path(output_dir) / "section_4_0100_test.jsonl"
        print(f"Writing to output file: {output_file}")
        
        with open(output_file, 'w') as f:
            for chunk in chunks:
                f.write(json.dumps(chunk) + "\n")
        
        print(f"Wrote {len(chunks)} chunks to {output_file}")
        
        # Print table chunks
        if table_chunks:
            print("\nTable chunks:")
            for i, chunk in enumerate(table_chunks):
                print(f"\nTable {i+1} (first 200 chars):")
                print(chunk["content"][:200] + "...")
        else:
            print("\nNo table chunks found!")
    except Exception as e:
        print(f"Error processing document: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    process_specific_document()

if __name__ == "__main__":
    process_specific_document()
