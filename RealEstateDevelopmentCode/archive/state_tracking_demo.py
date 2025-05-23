#!/usr/bin/env python3
"""
Example script demonstrating how to use the unified state tracking system.
"""

import os
import sys
import logging
import argparse
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('state_tracking_demo')

# Add project root to path for imports
SCRIPT_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = Path("/workspace/data/RealEstateDevelopmentCode")
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.common.state_tracking import UnifiedStateTracker
from scripts.common.config import get_jurisdiction_dirs

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Demo unified state tracking system.")
    parser.add_argument("--state", required=True, help="State name")
    parser.add_argument("--city", required=True, help="City name")
    parser.add_argument("--action", choices=["stats", "duplicates"], 
                      default="stats", help="Action to perform")
    
    args = parser.parse_args()
    
    state = args.state
    city = args.city
    
    # Initialize the tracker
    tracker = UnifiedStateTracker(city, state)
    
    if args.action == "stats":
        # Print current stats
        stats = tracker.get_stats()
        logger.info(f"Stats for {city}, {state}:")
        logger.info(f"Total files processed: {stats['total_files_processed']}")
        logger.info(f"Total files extracted: {stats['total_files_extracted']}")
        logger.info(f"Total sections processed: {stats['total_sections_processed']}")
        logger.info(f"Extraction progress: {stats['extraction_progress']}%")
        logger.info(f"Duplicate files: {stats['duplicates']['total_duplicates']}")
        
    elif args.action == "duplicates":
        # Detect duplicates
        dirs = get_jurisdiction_dirs(state, city)
        pdf_dir = dirs["raw_pdfs"]
        
        if not pdf_dir.exists():
            logger.error(f"PDF directory not found: {pdf_dir}")
            return
        
        duplicates, content_hashes = tracker.detect_duplicates(pdf_dir)
        logger.info(f"Found {len(duplicates)} duplicates out of {len(content_hashes)} files")
        
        # Print duplicates
        if duplicates:
            logger.info("Duplicates:")
            for dup in duplicates:
                hash_val = tracker.compute_content_hash(dup)
                original = content_hashes[hash_val][0] if hash_val in content_hashes else "unknown"
                logger.info(f"  {dup.name} -> duplicate of {original}")

if __name__ == "__main__":
    main()
