#!/usr/bin/env python3
"""
Single PDF Enhanced Extraction Test
Tests the enhanced three-phase extraction system on a single PDF containing Section 4.0100
to validate improvements in table extraction accuracy, especially for P/NP/SUR municipal use codes.
"""

import json
import logging
import sys
from pathlib import Path

# Add the chunking directory to the path
sys.path.insert(0, str(Path(__file__).parent / "chunking"))

from accurate_municipal_rag import AccurateMunicipalRAG

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Test enhanced extraction on the Section 4.0100 PDF"""
    
    # Find the Section 4.0100 PDF
    pdf_dir = Path("raw_pdfs/Oregon/gresham")
    section_pdf = None
    
    for pdf_file in pdf_dir.glob("*.pdf"):
        if "section-4.0100" in pdf_file.name.lower() or "4.0100" in pdf_file.name:
            section_pdf = pdf_file
            break
    
    if not section_pdf:
        logger.error("Could not find Section 4.0100 PDF")
        return
    
    logger.info(f"Testing enhanced extraction on: {section_pdf}")
    
    # Create output directory
    output_dir = Path("test_enhanced_single_output")
    output_dir.mkdir(exist_ok=True)
    
    # Initialize the enhanced RAG system
    rag = AccurateMunicipalRAG(str(pdf_dir), str(output_dir))
    
    try:
        # Process just this single PDF
        logger.info("Starting enhanced extraction...")
        
        # Get the file list with just our target PDF
        pdf_files = [section_pdf]
        
        # Process the PDF
        results = rag.process_pdfs(pdf_files, max_files=1)
        
        logger.info(f"Enhanced extraction completed with {len(results)} results")
        
        # Find and analyze table extractions
        table_count = 0
        section_4120_tables = []
        
        for result in results:
            if result.get("type") == "table":
                table_count += 1
                content = result.get("content", "")
                if "4.0120" in content or "Permitted Uses" in content:
                    section_4120_tables.append(result)
                    logger.info(f"Found Section 4.0120 table: {len(content)} chars")
        
        logger.info(f"Total tables extracted: {table_count}")
        logger.info(f"Section 4.0120 tables found: {len(section_4120_tables)}")
        
        # Save detailed results
        results_file = output_dir / "enhanced_single_results.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        # Save specific 4.0120 analysis
        if section_4120_tables:
            analysis_file = output_dir / "section_4120_analysis.json"
            with open(analysis_file, 'w') as f:
                json.dump({
                    "total_4120_tables": len(section_4120_tables),
                    "tables": section_4120_tables
                }, f, indent=2)
            
            logger.info(f"Enhanced extraction analysis saved to {analysis_file}")
            
            # Check for P/NP/SUR preservation
            for i, table in enumerate(section_4120_tables):
                content = table.get("content", "")
                p_count = content.count(" P ")
                np_count = content.count(" NP ")
                sur_count = content.count(" SUR ")
                l_count = content.count(" L")
                
                logger.info(f"Table {i+1} code preservation: P={p_count}, NP={np_count}, SUR={sur_count}, L={l_count}")
        
        logger.info(f"Enhanced single PDF test completed successfully")
        logger.info(f"Results saved to: {results_file}")
        
    except Exception as e:
        logger.error(f"Enhanced extraction failed: {e}")
        raise

if __name__ == "__main__":
    main()
