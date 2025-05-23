#!/usr/bin/env python3
"""
Script to extract content from all Gresham PDFs and verify against the TOC.
"""

import os
import json
import sys
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("gresham_extractor")

# Print current working directory for debugging
print(f"Current working directory: {os.getcwd()}")

# Constants
PDF_DIR = Path("/workspace/data/raw_pdfs/Oregon/gresham")
OUTPUT_DIR = Path("/workspace/data/pdf_content/Oregon/gresham")
RE_EXTRACTOR_PATH = Path("/workspace/data/RealEstateDevelopmentCode/scripts/re-extractor")

# Add RE-extractor path to Python path
sys.path.insert(0, str(RE_EXTRACTOR_PATH))

try:
    from pdf_extractor import EnhancedPDFExtractor
    logger.info("Successfully imported EnhancedPDFExtractor")
except ImportError as e:
    logger.error(f"Error importing EnhancedPDFExtractor: {e}")
    sys.exit(1)

def extract_pdfs():
    """Extract all PDFs in the Gresham directory."""
    pdf_files = list(PDF_DIR.glob("*.pdf*"))
    logger.info(f"Found {len(pdf_files)} PDF files to process")

    # Create extractor
    extractor = EnhancedPDFExtractor()
    
    # Create output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Process each PDF
    success_count = 0
    for pdf_file in pdf_files:
        try:
            # Define output path
            base_name = pdf_file.stem
            output_path = OUTPUT_DIR / f"{base_name}.json"
            
            # Extract content
            logger.info(f"Processing {pdf_file.name}")
            result = extractor.extract_document(pdf_file)
            
            # Save result to JSON
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2)
            
            logger.info(f"Saved extraction to {output_path}")
            success_count += 1
                
        except Exception as e:
            logger.error(f"Error processing {pdf_file.name}: {e}")
    
    logger.info(f"Extraction complete. Successfully processed {success_count} of {len(pdf_files)} files.")

if __name__ == "__main__":
    extract_pdfs()
