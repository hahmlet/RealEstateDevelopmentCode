#!/usr/bin/env python3
"""
Hierarchical Document Alignment Analysis

This script performs comprehensive alignment analysis using the corrected
hierarchical understanding of municipal development codes.

Usage:
    python analyze_hierarchical_alignment.py [content_dir] [--validate] [--output report.json]
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts'))

from scripts.common.hierarchical_document_registry import (
    HierarchicalDocumentRegistry,
    create_registry_for_location
)
from scripts.common.config import get_default_location, get_reports_directory


def analyze_location(content_dir: str, validate_content: bool = False, output_file: str = None) -> dict:
    """Analyze document alignment for a specific location"""
    
    print(f"Analyzing location: {content_dir}")
    
    # Create registry
    registry = create_registry_for_location(content_dir)
    
    # Generate comprehensive report
    report = registry.generate_alignment_report()
    
    # Add location metadata
    report['analysis_metadata'] = {
        'content_directory': content_dir,
        'analysis_type': 'hierarchical_alignment',
        'validation_performed': validate_content
    }
    
    # Perform content validation if requested
    if validate_content:
        print("Performing content validation...")
        validation_results = []
        
        for doc_num, hierarchy in registry.document_hierarchy.items():
            if hierarchy.has_file:
                validation = registry.validate_subsection_content(doc_num)
                validation_results.append(validation)
        
        report['content_validation'] = validation_results
        
        # Calculate validation summary
        total_validations = len(validation_results)
        successful_validations = sum(1 for v in validation_results if 'error' not in v)
        
        if successful_validations > 0:
            avg_validation = sum(v.get('validation_percentage', 0) 
                               for v in validation_results if 'error' not in v) / successful_validations
        else:
            avg_validation = 0
        
        report['validation_summary'] = {
            'total_validations': total_validations,
            'successful_validations': successful_validations,
            'average_validation_percentage': round(avg_validation, 2)
        }
    
    # Save report if output file specified
    if output_file:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"Report saved to: {output_file}")
    
    return report


def print_summary(report: dict) -> None:
    """Print a summary of the analysis results"""
    metrics = report['metrics']
    
    print("\n" + "="*60)
    print("HIERARCHICAL DOCUMENT ALIGNMENT ANALYSIS")
    print("="*60)
    
    print(f"Content Directory: {report['analysis_metadata']['content_directory']}")
    print()
    
    print("ALIGNMENT METRICS:")
    print(f"  Total Documents:           {metrics['total_documents']}")
    print(f"  Documents with Files:      {metrics['documents_with_files']}")
    print(f"  Documents without Files:   {metrics['documents_without_files']}")
    print(f"  Total Subsections:         {metrics['total_subsections']}")
    print(f"  Orphaned Files:            {metrics['orphaned_files']}")
    print(f"  Alignment Percentage:      {metrics['alignment_percentage']:.1f}%")
    
    if 'validation_summary' in report:
        validation = report['validation_summary']
        print()
        print("CONTENT VALIDATION:")
        print(f"  Successful Validations:    {validation['successful_validations']}")
        print(f"  Average Validation %:      {validation['average_validation_percentage']:.1f}%")
    
    print()
    print("MISSING DOCUMENTS:")
    missing = report['missing_documents']
    if missing:
        for doc in missing[:10]:  # Show first 10
            print(f"  {doc['number']}: {doc['title']} ({doc['subsection_count']} subsections)")
        if len(missing) > 10:
            print(f"  ... and {len(missing) - 10} more")
    else:
        print("  None - all documents have corresponding files!")
    
    print()
    print("ORPHANED FILES:")
    orphaned = report['orphaned_files']
    if orphaned:
        for file_info in orphaned[:10]:  # Show first 10
            print(f"  {file_info['filename']} (extracted: {file_info['extracted_number']})")
        if len(orphaned) > 10:
            print(f"  ... and {len(orphaned) - 10} more")
    else:
        print("  None - all files have corresponding TOC entries!")
    
    print()
    print("DOCUMENT HIERARCHY SAMPLE:")
    hierarchy = report['document_hierarchy']
    for doc in hierarchy[:5]:  # Show first 5 documents
        status = "✓" if doc['has_file'] else "✗"
        print(f"  {status} {doc['number']}: {doc['title']}")
        print(f"    File: {doc['filename'] or 'MISSING'}")
        print(f"    Subsections: {doc['subsection_count']}")
        if doc['subsections']:
            for sub in doc['subsections']:
                if 'note' in sub:
                    print(f"      {sub['note']}")
                else:
                    print(f"      {sub['number']}: {sub['title']}")
        print()


def main():
    parser = argparse.ArgumentParser(description='Analyze hierarchical document alignment')
    
    # Get default location for fallback
    default_config = get_default_location()
    
    parser.add_argument('content_dir', nargs='?', 
                       default=str(default_config['content_dir']),
                       help='Directory containing document files')
    parser.add_argument('--validate', action='store_true',
                       help='Perform content validation to check if files contain expected subsections')
    parser.add_argument('--output', '-o', 
                       help='Output file for detailed JSON report')
    
    args = parser.parse_args()
    
    # Validate content directory
    if not os.path.exists(args.content_dir):
        print(f"Error: Content directory does not exist: {args.content_dir}")
        sys.exit(1)
    
    # Set default output file if not specified
    if args.output is None:
        location_parts = Path(args.content_dir).parts
        if len(location_parts) >= 2:
            state = location_parts[-2]
            city = location_parts[-1]
            output_dir = get_reports_directory(state, city)
            args.output = str(output_dir / 'hierarchical_alignment_report.json')
        else:
            args.output = str(get_reports_directory('default', 'location') / 'hierarchical_alignment_report.json')
    
    try:
        # Perform analysis
        report = analyze_location(args.content_dir, args.validate, args.output)
        
        # Print summary
        print_summary(report)
        
    except Exception as e:
        print(f"Error during analysis: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
