#!/usr/bin/env python3
"""
Test script to compare the new generic PDF extraction with the old Gresham-specific extraction.
"""

import os
import sys
import logging
import json
import tempfile
import shutil
from pathlib import Path
import subprocess

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('extraction_comparison')

# Add project root to path for imports
SCRIPT_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
DATA_ROOT = Path("/workspace/data")

def run_gresham_extractor():
    """Run the original Gresham-specific extractor."""
    logger.info("Running Gresham-specific extractor...")
    
    try:
        result = subprocess.run(
            ["python3", str(DATA_ROOT / "extract_all_gresham_pdfs.py")],
            capture_output=True,
            text=True,
            cwd=str(DATA_ROOT)
        )
        
        if result.returncode != 0:
            logger.error(f"Error running Gresham extractor: {result.stderr}")
            return False
        
        logger.info("Gresham extractor finished successfully")
        return True
    except Exception as e:
        logger.error(f"Exception running Gresham extractor: {str(e)}")
        return False

def run_generic_extractor():
    """Run the new generic PDF extractor for Gresham."""
    logger.info("Running generic extractor for Gresham...")
    
    try:
        result = subprocess.run(
            ["python3", str(DATA_ROOT / "extract_pdfs.py"), "--state", "Oregon", "--city", "gresham"],
            capture_output=True,
            text=True,
            cwd=str(DATA_ROOT)
        )
        
        if result.returncode != 0:
            logger.error(f"Error running generic extractor: {result.stderr}")
            return False
        
        logger.info("Generic extractor finished successfully")
        return True
    except Exception as e:
        logger.error(f"Exception running generic extractor: {str(e)}")
        return False

def compare_results():
    """Compare the extraction results from both extractors."""
    logger.info("Comparing extraction results...")
    
    # Create temp directory to store Gresham-specific results
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Path to content files
        content_dir = DATA_ROOT / "pdf_content" / "Oregon" / "gresham"
        
        # First backup existing results
        logger.info(f"Backing up existing content to {temp_path}")
        if content_dir.exists():
            for json_file in content_dir.glob("*.json"):
                shutil.copy(json_file, temp_path)
        
        # Run Gresham extractor
        success_gresham = run_gresham_extractor()
        
        if not success_gresham:
            logger.error("Gresham extractor failed, skipping comparison")
            return
        
        # Save Gresham results
        gresham_results = {}
        for json_file in content_dir.glob("*.json"):
            try:
                with open(json_file) as f:
                    data = json.load(f)
                gresham_results[json_file.name] = data
            except Exception as e:
                logger.error(f"Error reading {json_file}: {str(e)}")
        
        logger.info(f"Processed {len(gresham_results)} files with Gresham extractor")
        
        # Run generic extractor
        success_generic = run_generic_extractor()
        
        if not success_generic:
            logger.error("Generic extractor failed, skipping comparison")
            return
        
        # Compare results
        different_files = 0
        missing_files = 0
        extra_files = 0
        
        # Check generic results against Gresham results
        generic_results = {}
        for json_file in content_dir.glob("*.json"):
            try:
                with open(json_file) as f:
                    data = json.load(f)
                generic_results[json_file.name] = data
                
                # Compare with Gresham results
                if json_file.name in gresham_results:
                    if data != gresham_results[json_file.name]:
                        different_files += 1
                        logger.info(f"File content differs: {json_file.name}")
                else:
                    extra_files += 1
                    logger.info(f"Extra file in generic results: {json_file.name}")
                    
            except Exception as e:
                logger.error(f"Error reading {json_file}: {str(e)}")
        
        # Check for missing files in generic results
        for filename in gresham_results:
            if filename not in generic_results:
                missing_files += 1
                logger.info(f"Missing file in generic results: {filename}")
        
        # Print summary
        logger.info("=== Comparison Summary ===")
        logger.info(f"Gresham extractor: {len(gresham_results)} files")
        logger.info(f"Generic extractor: {len(generic_results)} files")
        logger.info(f"Different content: {different_files} files")
        logger.info(f"Missing in generic: {missing_files} files")
        logger.info(f"Extra in generic: {extra_files} files")
        
        # Restore original files
        logger.info("Restoring original files...")
        for json_file in temp_path.glob("*.json"):
            dest_file = content_dir / json_file.name
            shutil.copy(json_file, dest_file)

if __name__ == "__main__":
    compare_results()
