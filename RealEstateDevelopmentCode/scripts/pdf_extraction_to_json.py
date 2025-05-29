#!/usr/bin/env python3
"""
PDF Extraction to JSON - Generalized Production Script
Extracts all PDFs from production_pdfs/Oregon/gresham to JSON content files
using the enhanced three-phase extraction system (AccurateMunicipalRAG).

This script generalizes the working test_enhanced_single_pdf.py to process
all PDFs in the production directory and save them as JSON content files.
"""

import json
import logging
import sys
import time
from pathlib import Path
from datetime import datetime

# Setup logging first
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("pdf_extraction_to_json")

# Add the chunking directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "chunking"))

try:
    from accurate_municipal_rag import AccurateMunicipalRAG
    logger.info("Successfully imported AccurateMunicipalRAG")
except ImportError as e:
    logger.error(f"Failed to import AccurateMunicipalRAG: {e}")
    sys.exit(1)

def extract_all_pdfs_to_json():
    """Extract all PDFs from production directory to JSON content files"""
    
    # Define paths
    pdf_dir = Path("/workspace/RealEstateDevelopmentCode/production_pdfs/Oregon/gresham")
    json_output_dir = Path("/workspace/RealEstateDevelopmentCode/pdf_content/Oregon/gresham")
    debug_log_dir = Path("/workspace/RealEstateDevelopmentCode/debug_rebuild/logs")
    
    # Create output directories
    json_output_dir.mkdir(parents=True, exist_ok=True)
    debug_log_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Starting PDF extraction from: {pdf_dir}")
    logger.info(f"Output JSON directory: {json_output_dir}")
    
    # Find all PDFs
    pdf_files = list(pdf_dir.glob("*.pdf"))
    logger.info(f"Found {len(pdf_files)} PDF files to process")
    
    if not pdf_files:
        logger.error(f"No PDF files found in {pdf_dir}")
        return False
    
    # Initialize the enhanced RAG system for PDF processing
    # We'll use the pdf_dir as source and json_output_dir as output
    rag = AccurateMunicipalRAG(str(pdf_dir), str(json_output_dir))
    
    # Track processing results
    success_count = 0
    failed_files = []
    start_time = time.time()
    
    # Process each PDF file
    for i, pdf_file in enumerate(pdf_files):
        try:
            logger.info(f"Processing {i+1}/{len(pdf_files)}: {pdf_file.name}")
            
            # Process this single PDF using the working method
            results = rag.process_pdfs([pdf_file], max_files=1)
            
            if results:
                # Create output JSON filename
                json_filename = pdf_file.stem + ".json"
                json_output_path = json_output_dir / json_filename
                
                # Convert results to the standard JSON format expected by prepare_from_json_content
                pdf_content = convert_rag_results_to_json_format(results, pdf_file.name)
                
                # Save to JSON file
                with open(json_output_path, 'w', encoding='utf-8') as f:
                    json.dump(pdf_content, f, indent=2, ensure_ascii=False)
                
                # Count elements
                table_count = len([r for r in results if r.get("type") == "table"])
                text_count = len([r for r in results if r.get("type") == "text"])
                
                logger.info(f"  ✓ Saved {json_filename}: {table_count} tables, {text_count} text chunks")
                success_count += 1
                
            else:
                logger.warning(f"  ⚠ No results extracted from {pdf_file.name}")
                failed_files.append({"file": pdf_file.name, "error": "No results extracted"})
                
        except Exception as e:
            logger.error(f"  ✗ Failed to process {pdf_file.name}: {e}")
            failed_files.append({"file": pdf_file.name, "error": str(e)})
    
    # Calculate timing
    end_time = time.time()
    duration = end_time - start_time
    
    # Print summary
    logger.info(f"\n{'='*60}")
    logger.info(f"PDF EXTRACTION TO JSON SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"Total PDFs processed: {len(pdf_files)}")
    logger.info(f"Successful extractions: {success_count}")
    logger.info(f"Failed extractions: {len(failed_files)}")
    logger.info(f"Processing time: {duration:.2f} seconds")
    logger.info(f"Average time per PDF: {duration/len(pdf_files):.2f} seconds")
    
    if failed_files:
        logger.info(f"\nFailed files:")
        for failure in failed_files:
            logger.info(f"  - {failure['file']}: {failure['error']}")
    
    # Save detailed log to debug directory
    log_file = debug_log_dir / "pdf_extraction_to_json.log"
    with open(log_file, 'w') as f:
        f.write(f"PDF Extraction to JSON Log - {datetime.now().isoformat()}\n")
        f.write(f"Source Directory: {pdf_dir}\n")
        f.write(f"Output Directory: {json_output_dir}\n")
        f.write(f"Total PDFs: {len(pdf_files)}\n")
        f.write(f"Successful: {success_count}\n")
        f.write(f"Failed: {len(failed_files)}\n")
        f.write(f"Duration: {duration:.2f} seconds\n\n")
        
        if failed_files:
            f.write("Failed extractions:\n")
            for failure in failed_files:
                f.write(f"  {failure['file']}: {failure['error']}\n")
        
        f.write(f"\nSuccessful extractions:\n")
        successful_files = [pdf.name for pdf in pdf_files if pdf.name not in [f['file'] for f in failed_files]]
        for filename in successful_files:
            f.write(f"  {filename}\n")
    
    logger.info(f"\nDetailed log saved to: {log_file}")
    
    # Verify output
    json_files = list(json_output_dir.glob("*.json"))
    logger.info(f"Verification: {len(json_files)} JSON files created in output directory")
    
    return success_count == len(pdf_files)

def convert_rag_results_to_json_format(results, filename):
    """Convert RAG processing results to the standard JSON format expected by prepare_from_json_content"""
    
    # Group results by page number
    pages_data = {}
    
    for result in results:
        page_num = result.get("page_number", 1)
        result_type = result.get("type", "unknown")
        
        if page_num not in pages_data:
            pages_data[page_num] = {
                "page_number": page_num,
                "text": "",
                "tables": []
            }
        
        if result_type == "text":
            # Append text content
            content = result.get("content", "")
            if content:
                if pages_data[page_num]["text"]:
                    pages_data[page_num]["text"] += "\n" + content
                else:
                    pages_data[page_num]["text"] = content
                    
        elif result_type == "table":
            # Add table data
            content = result.get("content", "")
            if content:
                table_data = {
                    "text": content,
                    "html": f"<table>{content}</table>",  # Basic HTML wrapper
                }
                pages_data[page_num]["tables"].append(table_data)
    
    # Convert to standard format
    json_content = {
        "metadata": {
            "filename": filename,
            "extracted_at": datetime.now().isoformat(),
            "extractor": "AccurateMunicipalRAG",
            "strategy": "enhanced_three_phase"
        },
        "pages": [pages_data[page_num] for page_num in sorted(pages_data.keys())]
    }
    
    return json_content

def main():
    """Main entry point"""
    logger.info("Starting PDF extraction to JSON for all Gresham PDFs...")
    
    try:
        success = extract_all_pdfs_to_json()
        if success:
            logger.info("✅ PDF extraction to JSON completed successfully!")
            return 0
        else:
            logger.error("❌ PDF extraction to JSON completed with errors")
            return 1
    except Exception as e:
        logger.error(f"❌ PDF extraction to JSON failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
