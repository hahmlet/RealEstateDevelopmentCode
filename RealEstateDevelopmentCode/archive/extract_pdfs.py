#!/usr/bin/env python3
"""
Generic script to extract content from PDF files for any jurisdiction.
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add project root to path for imports
SCRIPT_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = Path("/workspace/data/RealEstateDevelopmentCode")
sys.path.insert(0, str(PROJECT_ROOT))

# Import common configuration
try:
    from scripts.common.config import (
        get_jurisdiction_dirs,
        ensure_jurisdiction_dirs,
        PDF_CONTENT_DIR,
        RAW_PDFS_DIR,
        RE_EXTRACTOR_DIR
    )
except ImportError:
    print("Failed to import common configuration. Make sure the common module is properly set up.")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("pdf_extractor")

def setup_extractor(state: str, city: str) -> Any:
    """Set up the PDF extractor for a specific jurisdiction."""
    try:
        # Add RE-extractor path to Python path
        sys.path.insert(0, str(RE_EXTRACTOR_DIR))
        
        # Import the enhanced PDF extractor
        from pdf_extractor import EnhancedPDFExtractor
        logger.info("Successfully imported EnhancedPDFExtractor")
        
        return EnhancedPDFExtractor()
    except ImportError as e:
        logger.error(f"Error importing EnhancedPDFExtractor: {e}")
        try:
            # Fall back to the compatibility wrapper
            sys.path.insert(0, str(PROJECT_ROOT / "scripts" / "re-crawler"))
            from utils.pdf_extractor_wrapper import PDFExtractor
            logger.info("Falling back to PDFExtractor compatibility wrapper")
            return PDFExtractor()
        except ImportError as e2:
            logger.error(f"Error importing PDFExtractor wrapper: {e2}")
            return None

def extract_pdfs(state: str, city: str) -> Dict[str, Any]:
    """Extract all PDFs for a specific jurisdiction."""
    try:
        # Ensure directories exist
        dirs = ensure_jurisdiction_dirs(state, city)
        pdf_dir = dirs["raw_pdfs"]
        output_dir = dirs["pdf_content"]
        
        # Find all PDF files
        pdf_files = list(pdf_dir.glob("*.pdf*"))
        logger.info(f"Found {len(pdf_files)} PDF files to process for {city}, {state}")
        
        if not pdf_files:
            return {
                "success": False,
                "message": f"No PDF files found for {city}, {state} in {pdf_dir}",
                "extracted_count": 0
            }
        
        # Setup extractor
        extractor = setup_extractor(state, city)
        if not extractor:
            return {
                "success": False,
                "message": "Failed to initialize PDF extractor",
                "extracted_count": 0
            }
        
        # Process each PDF
        successful_extractions = 0
        failed_extractions = []
        
        for pdf_file in pdf_files:
            try:
                logger.info(f"Processing: {pdf_file.name}")
                
                # Create output filename
                output_filename = pdf_file.stem.lower().replace(" ", "-") + ".json"
                output_path = output_dir / output_filename
                
                # Extract content
                result = extractor.extract_document(pdf_file)
                
                # Save result
                with open(output_path, "w") as f:
                    json.dump(result, f, indent=2)
                
                successful_extractions += 1
                logger.info(f"Successfully extracted: {pdf_file.name} -> {output_path}")
                
            except Exception as e:
                logger.error(f"Error processing {pdf_file.name}: {str(e)}")
                failed_extractions.append({
                    "file": str(pdf_file),
                    "error": str(e)
                })
        
        # Return summary
        return {
            "success": True,
            "message": f"Processed {len(pdf_files)} PDF files for {city}, {state}",
            "extracted_count": successful_extractions,
            "failed_count": len(failed_extractions),
            "failed_files": failed_extractions
        }
        
    except Exception as e:
        logger.error(f"Error extracting PDFs: {str(e)}")
        return {
            "success": False,
            "message": f"Error extracting PDFs: {str(e)}",
            "extracted_count": 0
        }

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Extract content from PDF files.")
    parser.add_argument("--state", required=True, help="State name for the jurisdiction")
    parser.add_argument("--city", required=True, help="City name for the jurisdiction")
    
    args = parser.parse_args()
    
    state = args.state
    city = args.city
    
    logger.info(f"Starting PDF extraction for {city}, {state}")
    result = extract_pdfs(state, city)
    
    if result["success"]:
        logger.info(f"Extraction completed successfully: {result['extracted_count']} files processed")
    else:
        logger.error(f"Extraction failed: {result['message']}")

if __name__ == "__main__":
    main()
