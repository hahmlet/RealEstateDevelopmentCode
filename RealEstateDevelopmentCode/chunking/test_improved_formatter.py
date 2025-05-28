#!/usr/bin/env python3
"""
Minimal test for the improved table formatter
"""

import json
import os
import sys
from pathlib import Path

# Add parent directory to path so we can import AccurateMunicipalRAG
sys.path.append(str(Path(__file__).parent.parent))
print("Added parent directory to path")

from chunking.accurate_municipal_rag import AccurateMunicipalRAG
print("Successfully imported AccurateMunicipalRAG")

def test_business_retail_fix():
    """Test the fix for Business and Retail Service and Trade issue"""
    
    # Create a processor instance
    processor = AccurateMunicipalRAG(
        source_dir="/workspace/RealEstateDevelopmentCode/pdf_content/Oregon/gresham",
        output_dir="/workspace/RealEstateDevelopmentCode/rag_data_test/Oregon/gresham"
    )
    
    # Create a test table with the problematic entry
    test_table = """Table 4.0120: Permitted Uses
USES
LDR-5
LDR-7
TR
TLDR
MDR-12 MDR-24
OFR
COMMERCIAL
Auto-Dependent Use
NP
NP
NP
NP
NP
NP
NP
Business and Retail Service and
Trade
NP
NP
NP
NP
NP
NP
L7
Clinics
NP
NP
NP
NP
NP
NP
P"""
    
    # Format the table using our improved method
    formatted_table = processor._format_abbreviated_use_table(test_table)
    
    # Print the result
    print("\nFormatted table with Business and Retail Service fix:")
    print(formatted_table)
    
    # Check if "Business and Retail Service and Trade" appears correctly in the output
    if "Business and Retail Service and Trade" in formatted_table:
        print("\nSUCCESS: Business and Retail Service and Trade is correctly formatted")
    else:
        print("\nFAILURE: Business and Retail Service and Trade is not correctly formatted")

def test_empty_cells_fix():
    """Test the fix for empty cells being replaced with dashes"""
    
    # Create a processor instance
    processor = AccurateMunicipalRAG(
        source_dir="/workspace/RealEstateDevelopmentCode/pdf_content/Oregon/gresham",
        output_dir="/workspace/RealEstateDevelopmentCode/rag_data_test/Oregon/gresham"
    )
    
    # Create a test table with incomplete cells
    test_table = """Table 4.0120: Permitted Uses
USES
LDR-5
LDR-7
TR
TLDR
MDR-12 MDR-24
OFR
RESIDENTIAL
Single Detached Dwelling
P
P
P
P
L1
NP
L1
Multifamily
NP
NP
NP
NP
P2
P2
P2, 3"""
    
    # Format the table using our improved method
    formatted_table = processor._format_abbreviated_use_table(test_table)
    
    # Print the result
    print("\nFormatted table with dash placeholders:")
    print(formatted_table)
    
    # Check if empty cells are replaced with "-"
    if " - " in formatted_table:
        print("\nSUCCESS: Empty cells are correctly replaced with dashes")
    else:
        print("\nFAILURE: Empty cells are not replaced with dashes")

if __name__ == "__main__":
    print("Testing improved table formatter...")
    test_business_retail_fix()
    test_empty_cells_fix()
    print("\nTesting completed")
