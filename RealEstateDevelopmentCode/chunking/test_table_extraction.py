#!/usr/bin/env python3
"""
Test script to verify table extraction, especially for abbreviated tables in Section 4.0100
"""

import json
import os
import sys
import re
from pathlib import Path

# Add parent directory to path so we can import AccurateMunicipalRAG
sys.path.append(str(Path(__file__).parent.parent))
from chunking.accurate_municipal_rag import AccurateMunicipalRAG

def test_table_extraction():
    """Test the table extraction functionality"""
    
    # Load the problematic document
    file_path = Path("/workspace/RealEstateDevelopmentCode/pdf_content/Oregon/gresham/dc-section-4.0100.json")
    
    if not file_path.exists():
        print(f"Test file not found: {file_path}")
        return
    
    # Create a RAG processor instance
    rag = AccurateMunicipalRAG(
        source_dir="/workspace/RealEstateDevelopmentCode/pdf_content",
        output_dir="/workspace/RealEstateDevelopmentCode/test_data/results"
    )
    
    # Load the JSON content
    with open(file_path, 'r') as f:
        content = json.load(f)
    
    # Find the page with the table (page 4)
    for page in content["pages"]:
        if page["page_number"] == 4:
            page_text = page["text"]
            
            print("Testing table pattern matching:")
            
            # Test the pattern directly
            pattern = r'(?:USES\s+|Uses\s+|Table\s+\d+\.\d+\s*:\s*Permitted\s+Uses)(?:[A-Z0-9-]+\s+){3,10}\n(?:[A-Za-z][A-Za-z\s\d\/\(\)]+\n?(?:[A-Za-z\s\d\/\(\)]+)?\s+(?:P|NP|SUR|L\d*)\s+(?:P|NP|SUR|L\d*)\s+(?:P|NP|SUR|L\d*)[^\n]*\n){3,}'
            matches = re.finditer(pattern, page_text, re.MULTILINE | re.IGNORECASE | re.DOTALL)
            
            match_found = False
            for match in matches:
                match_found = True
                table_text = match.group(0).strip()
                print("\nPattern matched successfully!")
                print(f"Matched text length: {len(table_text)} characters")
                print(f"First 200 characters: {table_text[:200]}...")
                
                # Debug the formatting process
                print("\nDebugging table formatting:")
                
                # Split into lines and identify header row
                lines = [line.strip() for line in table_text.split('\n') if line.strip()]
                print(f"Found {len(lines)} lines in the table")
                
                # Try to identify the header row with district/zone names
                header_row = None
                for i, line in enumerate(lines):
                    if re.search(r'(USES|Uses|Table\s+\d+\.\d+\s*:\s*Permitted\s+Uses)', line) and i < 5:
                        header_row = i
                        print(f"Found header row at index {i}: {line}")
                        break
                
                if header_row is None:
                    for i, line in enumerate(lines):
                        if re.search(r'[A-Z0-9-]{2,5}\s+[A-Z0-9-]{2,5}\s+[A-Z0-9-]{2,5}', line) and i < 5:
                            header_row = i
                            print(f"Found district abbreviation header row at index {i}: {line}")
                            break
                
                if header_row is None:
                    header_row = 0
                    print(f"Using default header row at index 0: {lines[0]}")
                
                # Extract column headers
                headers = re.findall(r'([A-Z0-9][A-Z0-9-]*(?:-\d+)?)', lines[header_row])
                print(f"Extracted headers: {headers}")
                
                # Handle MDR-12 MDR-24 issue
                for i, header in enumerate(headers):
                    if header == "MDR-12" and i+1 < len(headers) and headers[i+1] == "MDR-24":
                        headers[i] = "MDR-12"
                        headers[i+1] = "MDR-24"
                print(f"Headers after MDR fix: {headers}")
                
                # If no headers found or too few, try a different approach
                if len(headers) < 3:
                    words = lines[header_row].split()
                    headers = [w for w in words if len(w) >= 2 and w.isupper()]
                    print(f"Headers after word extraction: {headers}")
                
                # If still no headers, use a default set
                if len(headers) < 3:
                    if 'LDR' in table_text or 'MDR' in table_text:
                        headers = ['USES', 'LDR-5', 'LDR-7', 'TR', 'TLDR', 'MDR-12', 'MDR-24', 'OFR']
                    else:
                        headers = ['USES', 'DISTRICT1', 'DISTRICT2', 'DISTRICT3', 'DISTRICT4', 'DISTRICT5']
                    print(f"Using default headers: {headers}")
                
                # Check for P, NP, SUR, L values
                codes_found = False
                for i in range(header_row + 1, min(header_row + 10, len(lines))):
                    codes = re.findall(r'\b(P|NP|SUR|L\d*)\b', lines[i])
                    if codes:
                        codes_found = True
                        print(f"Found codes at row {i}: {codes}")
                        break
                
                if not codes_found:
                    print("No P/NP/SUR/L codes found in table rows!")
                
                # Now try to format it
                formatted_table = rag._format_abbreviated_use_table(table_text)
                if formatted_table and formatted_table != table_text:
                    print("\nSuccessfully formatted table!")
                    print(f"First 200 characters of formatted table: {formatted_table[:200]}...")
                else:
                    print("\nFailed to format table properly")
                    print("Original text returned unchanged")
            
            if not match_found:
                print("\nNo match found with the pattern!")
                print("Here's the text of page 4:")
                print(page_text[:500] + "...")  # Print first 500 chars
            
            # Try to extract tables using the extract_tables_from_text method
            print("\nTesting full table extraction:")
            tables = rag._extract_tables_from_text(page_text)
            
            if tables:
                print(f"Found {len(tables)} tables on page 4")
                for i, table in enumerate(tables):
                    print(f"\nTable {i+1} (first 200 chars):")
                    print(table[:200] + "...")
            else:
                print("No tables found on page 4 using extract_tables_from_text")
            
            break

if __name__ == "__main__":
    test_table_extraction()
