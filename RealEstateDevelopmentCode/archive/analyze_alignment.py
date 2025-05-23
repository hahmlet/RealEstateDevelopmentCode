#!/usr/bin/env python3
"""
Automated TOC/Document Alignment Analysis Tool

This script provides a command-line interface for analyzing TOC/document alignment
using the Document Registry system. It detects orphaned PDFs, missing documents,
and generates comprehensive reports.
"""

import sys
import logging
import argparse
from pathlib import Path

# Add the scripts directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from scripts.common.document_registry import DocumentRegistry
    from scripts.common.config import get_jurisdiction_dirs
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Please ensure you're running from the correct directory.")
    sys.exit(1)


def setup_logging(verbose: bool = False) -> logging.Logger:
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logging.getLogger("alignment_analyzer")


def print_summary(registry: DocumentRegistry) -> None:
    """Print a summary of the analysis results."""
    print("\n" + "="*60)
    print(f"DOCUMENT ALIGNMENT ANALYSIS SUMMARY")
    print(f"Jurisdiction: {registry.state} / {registry.city.title()}")
    print("="*60)
    
    print(f"\nTOC Analysis:")
    print(f"  Total TOC entries found: {len(registry.toc_entries)}")
    
    # Break down by document type
    toc_types = {}
    for entry in registry.toc_entries:
        doc_type = entry["type"]
        toc_types[doc_type] = toc_types.get(doc_type, 0) + 1
    
    for doc_type, count in sorted(toc_types.items()):
        print(f"    {doc_type.title()}s: {count}")
    
    print(f"\nFile Analysis:")
    total_files = sum(len(files) for files in registry.available_files.values())
    print(f"  Total document files found: {total_files}")
    
    for category, files in registry.available_files.items():
        if files:
            print(f"    {category.title()}: {len(files)}")
    
    print(f"\nAlignment Results:")
    print(f"  Matched documents: {len(registry.matched_documents)}")
    print(f"  Missing documents: {len(registry.missing_documents)}")
    print(f"  Orphaned files: {len(registry.orphaned_files)}")
    
    # Calculate alignment percentage
    if registry.toc_entries:
        alignment_pct = (len(registry.matched_documents) / len(registry.toc_entries)) * 100
        print(f"  Alignment score: {alignment_pct:.1f}%")
    
    # Show specific issues if any
    if registry.missing_documents:
        print(f"\nMissing Documents:")
        for i, doc in enumerate(registry.missing_documents[:5]):  # Show first 5
            toc_entry = doc["toc_entry"]
            print(f"  {i+1}. {toc_entry['type'].title()} {toc_entry['number']}: {toc_entry['title']}")
        
        if len(registry.missing_documents) > 5:
            print(f"  ... and {len(registry.missing_documents) - 5} more")
    
    if registry.orphaned_files:
        print(f"\nOrphaned Files:")
        for i, file_info in enumerate(registry.orphaned_files[:5]):  # Show first 5
            filename = file_info["filename"]
            print(f"  {i+1}. {filename}")
        
        if len(registry.orphaned_files) > 5:
            print(f"  ... and {len(registry.orphaned_files) - 5} more")
    
    print(f"\nReports generated in:")
    print(f"  {registry.registry_dir}")


def print_detailed_orphaned_files(registry: DocumentRegistry) -> None:
    """Print detailed information about orphaned files."""
    if not registry.orphaned_files:
        print("No orphaned files found.")
        return
    
    print("\n" + "="*60)
    print("DETAILED ORPHANED FILES ANALYSIS")
    print("="*60)
    
    for i, file_info in enumerate(registry.orphaned_files, 1):
        filename = file_info["filename"]
        potential_matches = file_info.get("potential_toc_matches", [])
        
        print(f"\n{i}. {filename}")
        
        if potential_matches:
            print("   Potential TOC matches:")
            for match in potential_matches[:3]:  # Show top 3 matches
                toc_entry = match["toc_entry"]
                confidence = match["confidence"]
                print(f"     - {toc_entry['type'].title()} {toc_entry['number']}: {toc_entry['title']} (confidence: {confidence:.2f})")
        else:
            print("   No potential TOC matches found")


def print_detailed_missing_docs(registry: DocumentRegistry) -> None:
    """Print detailed information about missing documents."""
    if not registry.missing_documents:
        print("No missing documents found.")
        return
    
    print("\n" + "="*60)
    print("DETAILED MISSING DOCUMENTS ANALYSIS")
    print("="*60)
    
    for i, doc_info in enumerate(registry.missing_documents, 1):
        toc_entry = doc_info["toc_entry"]
        expected_patterns = doc_info.get("expected_patterns", [])
        
        print(f"\n{i}. {toc_entry['type'].title()} {toc_entry['number']}: {toc_entry['title']}")
        
        if toc_entry.get("page"):
            print(f"   Referenced on TOC page: {toc_entry['page']}")
        
        if expected_patterns:
            print("   Expected filename patterns:")
            for pattern in expected_patterns:
                print(f"     - {pattern}")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Automated TOC/Document Alignment Analysis Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                           # Analyze Oregon/Gresham (default)
  %(prog)s --state Oregon --city Portland  # Analyze Oregon/Portland
  %(prog)s --verbose                 # Enable verbose logging
  %(prog)s --detailed-orphaned       # Show detailed orphaned files analysis
  %(prog)s --detailed-missing        # Show detailed missing documents analysis
  %(prog)s --all-details             # Show all detailed analyses
        """
    )
    
    parser.add_argument(
        "--state", 
        default="Oregon", 
        help="State name (default: Oregon)"
    )
    
    parser.add_argument(
        "--city", 
        default="Gresham", 
        help="City name (default: Gresham)"
    )
    
    parser.add_argument(
        "--verbose", "-v", 
        action="store_true", 
        help="Enable verbose logging"
    )
    
    parser.add_argument(
        "--detailed-orphaned", 
        action="store_true", 
        help="Show detailed analysis of orphaned files"
    )
    
    parser.add_argument(
        "--detailed-missing", 
        action="store_true", 
        help="Show detailed analysis of missing documents"
    )
    
    parser.add_argument(
        "--all-details", 
        action="store_true", 
        help="Show all detailed analyses"
    )
    
    parser.add_argument(
        "--report-only", 
        action="store_true", 
        help="Generate reports only, skip console output"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    logger = setup_logging(args.verbose)
    
    try:
        # Initialize Document Registry
        logger.info(f"Initializing Document Registry for {args.state}/{args.city}")
        registry = DocumentRegistry(args.state, args.city)
        
        # Run full analysis
        logger.info("Starting document alignment analysis...")
        success = registry.run_full_analysis()
        
        if not success:
            logger.error("Document alignment analysis failed!")
            return 1
        
        # Print results unless report-only mode
        if not args.report_only:
            print_summary(registry)
            
            # Show detailed analyses if requested
            if args.detailed_orphaned or args.all_details:
                print_detailed_orphaned_files(registry)
            
            if args.detailed_missing or args.all_details:
                print_detailed_missing_docs(registry)
        
        print(f"\n✓ Analysis completed successfully!")
        print(f"Reports saved to: {registry.registry_dir}")
        
        return 0
        
    except KeyboardInterrupt:
        print("\nAnalysis interrupted by user.")
        return 1
    
    except Exception as e:
        logger.error(f"Unexpected error during analysis: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
