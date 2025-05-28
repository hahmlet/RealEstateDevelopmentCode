#!/usr/bin/env python3
"""
Test script to verify table extraction and formatting specifically for Section 4.0100
"""

import json
import os
import sys
import re
from pathlib import Path

# Add parent directory to path so we can import AccurateMunicipalRAG
print("Adding parent directory to path")
sys.path.append(str(Path(__file__).parent.parent))
print("Successfully imported path")

from chunking.accurate_municipal_rag import AccurateMunicipalRAG
print("Successfully imported AccurateMunicipalRAG")

def format_section_4_0100_tables():
    """Format tables directly from the original text of Section 4.0100"""
    
    # Create a processor instance to use its formatting method
    processor = AccurateMunicipalRAG(
        source_dir="/workspace/RealEstateDevelopmentCode/pdf_content/Oregon/gresham",
        output_dir="/workspace/RealEstateDevelopmentCode/rag_data_test/Oregon/gresham"
    )
    
    # Load the document
    file_path = "/workspace/RealEstateDevelopmentCode/pdf_content/Oregon/gresham/dc-section-4.0100.json"
    with open(file_path, 'r') as f:
        content = json.load(f)
    
    # Find the table text across pages 4 and 5
    table_text = ""
    for page in content["pages"]:
        if page["page_number"] == 4:
            # Page 4 contains the first part of the table
            print("Processing page 4")
            if "Table 4.0120" in page["text"]:
                table_text += page["text"]
        elif page["page_number"] == 5 and table_text:
            # Page 5 contains the continuation
            print("Processing page 5")
            table_text += page["text"]
    
    if table_text:
        print("Found table text across pages")
        # Extract the table content
        # Find "Table 4.0120" and then extract until we reach the Table Notes section
        table_start = table_text.find("Table 4.0120")
        if table_start > -1:
            table_end = table_text.find("Table Notes", table_start)
            if table_end > -1:
                extracted_table = table_text[table_start:table_end]
                print(f"Extracted table content (first 200 chars): {extracted_table[:200]}...")
                
                # Print the raw table content for debugging
                print("\nRaw table content (first 20 lines):")
                lines = extracted_table.split('\n')
                for i, line in enumerate(lines[:20]):
                    print(f"Line {i}: {line}")
                
                # Format the table using our improved method
                formatted_table = processor._format_abbreviated_use_table(extracted_table)
                print(f"\nFormatted table (first 500 chars):\n{formatted_table[:500]}...")
                
                # Save the formatted table to a file
                output_path = "/workspace/RealEstateDevelopmentCode/chunking/formatted_section_4_0100_table.md"
                with open(output_path, 'w') as f:
                    f.write(formatted_table)
                print(f"\nSaved formatted table to {output_path}")
            else:
                print("Could not find end of table")
        else:
            print("Could not find start of table")
    else:
        print("No table text found")

if __name__ == "__main__":
    print("Starting table formatting...")
    format_section_4_0100_tables()
    print("Formatting completed")
