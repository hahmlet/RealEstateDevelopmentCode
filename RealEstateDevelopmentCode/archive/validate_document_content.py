#!/usr/bin/env python3
"""
Document Content Validation Utility
Version: 1.0
Date: May 23, 2025

This script validates that document files contain their expected subsections
according to the Table of Contents structure.

Usage:
    python validate_document_content.py [content_dir] [--document-number XX.YY] [--detailed]
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts'))

from scripts.common.hierarchical_document_registry import create_registry_for_location
from scripts.common.config import get_default_location


def validate_single_document(registry, document_number: str, detailed: bool = False) -> dict:
    """Validate a single document's content"""
    result = registry.validate_subsection_content(document_number)
    
    if detailed and 'error' not in result:
        # Get the hierarchy for more details
        hierarchy = registry.document_hierarchy.get(document_number)
        if hierarchy:
            result['document_details'] = {
                'title': hierarchy.document_title,
                'file_path': hierarchy.file_info.filepath if hierarchy.file_info else None,
                'subsections_detail': [
                    {
                        'number': sub.number,
                        'title': sub.title,
                        'found_in_content': sub.number in result.get('found_list', [])
                    }
                    for sub in hierarchy.subsections
                ]
            }
    
    return result


def validate_all_documents(registry, detailed: bool = False) -> dict:
    """Validate all documents with files"""
    results = []
    
    for doc_num, hierarchy in registry.document_hierarchy.items():
        if hierarchy.has_file:
            validation = validate_single_document(registry, doc_num, detailed)
            results.append(validation)
    
    # Calculate summary statistics
    successful = [r for r in results if 'error' not in r]
    
    summary = {
        'total_documents_with_files': len(results),
        'successful_validations': len(successful),
        'failed_validations': len(results) - len(successful),
        'average_validation_percentage': 0,
        'total_expected_subsections': 0,
        'total_found_subsections': 0,
        'validation_results': results
    }
    
    if successful:
        summary['average_validation_percentage'] = sum(
            r.get('validation_percentage', 0) for r in successful
        ) / len(successful)
        
        summary['total_expected_subsections'] = sum(
            r.get('expected_subsections', 0) for r in successful
        )
        
        summary['total_found_subsections'] = sum(
            r.get('found_subsections', 0) for r in successful
        )
    
    return summary


def print_validation_results(results: dict, detailed: bool = False) -> None:
    """Print validation results"""
    
    print("\n" + "="*60)
    print("DOCUMENT CONTENT VALIDATION RESULTS")
    print("="*60)
    
    summary_stats = {
        'total_documents_with_files': results.get('total_documents_with_files', 0),
        'successful_validations': results.get('successful_validations', 0),
        'failed_validations': results.get('failed_validations', 0),
        'average_validation_percentage': results.get('average_validation_percentage', 0),
        'total_expected_subsections': results.get('total_expected_subsections', 0),
        'total_found_subsections': results.get('total_found_subsections', 0)
    }
    
    print("SUMMARY STATISTICS:")
    print(f"  Total Documents with Files:     {summary_stats['total_documents_with_files']}")
    print(f"  Successful Validations:         {summary_stats['successful_validations']}")
    print(f"  Failed Validations:             {summary_stats['failed_validations']}")
    print(f"  Average Validation Percentage:  {summary_stats['average_validation_percentage']:.1f}%")
    print(f"  Total Expected Subsections:     {summary_stats['total_expected_subsections']}")
    print(f"  Total Found Subsections:        {summary_stats['total_found_subsections']}")
    
    if summary_stats['total_expected_subsections'] > 0:
        overall_percentage = (summary_stats['total_found_subsections'] / 
                            summary_stats['total_expected_subsections']) * 100
        print(f"  Overall Subsection Coverage:    {overall_percentage:.1f}%")
    
    print()
    
    # Show individual results
    validation_results = results.get('validation_results', [])
    if isinstance(results, dict) and 'document_number' in results:
        # Single document result
        validation_results = [results]
    
    if detailed:
        print("DETAILED VALIDATION RESULTS:")
        for result in validation_results:
            if 'error' in result:
                print(f"  ERROR: {result['error']}")
                continue
            
            doc_num = result.get('document_number', 'Unknown')
            print(f"  Document {doc_num}:")
            print(f"    File: {result.get('file_path', 'Unknown')}")
            print(f"    Expected Subsections: {result.get('expected_subsections', 0)}")
            print(f"    Found Subsections: {result.get('found_subsections', 0)}")
            print(f"    Validation Percentage: {result.get('validation_percentage', 0):.1f}%")
            
            if 'document_details' in result:
                details = result['document_details']
                print(f"    Title: {details.get('title', 'Unknown')}")
                
                if 'subsections_detail' in details:
                    print("    Subsections:")
                    for sub in details['subsections_detail'][:10]:  # Limit output
                        status = "✓" if sub['found_in_content'] else "✗"
                        print(f"      {status} {sub['number']}: {sub['title']}")
                    
                    if len(details['subsections_detail']) > 10:
                        remaining = len(details['subsections_detail']) - 10
                        print(f"      ... and {remaining} more subsections")
            
            print()
    else:
        print("VALIDATION RESULTS SUMMARY:")
        for result in validation_results:
            if 'error' in result:
                print(f"  ERROR: {result['error']}")
                continue
            
            doc_num = result.get('document_number', 'Unknown')
            validation_pct = result.get('validation_percentage', 0)
            expected = result.get('expected_subsections', 0)
            found = result.get('found_subsections', 0)
            
            status = "✓" if validation_pct > 80 else "⚠" if validation_pct > 50 else "✗"
            print(f"  {status} {doc_num}: {validation_pct:.1f}% ({found}/{expected} subsections)")


def main():
    parser = argparse.ArgumentParser(description='Validate document content against TOC structure')
    
    # Get default location for fallback
    default_config = get_default_location()
    
    parser.add_argument('content_dir', nargs='?',
                       default=str(default_config['content_dir']),
                       help='Directory containing document files')
    parser.add_argument('--document-number', '-d',
                       help='Validate specific document number (e.g., 10.04)')
    parser.add_argument('--detailed', action='store_true',
                       help='Show detailed subsection validation results')
    parser.add_argument('--output', '-o',
                       help='Output file for detailed JSON results')
    
    args = parser.parse_args()
    
    # Validate content directory
    if not os.path.exists(args.content_dir):
        print(f"Error: Content directory does not exist: {args.content_dir}")
        sys.exit(1)
    
    try:
        # Create registry
        print(f"Loading document registry from: {args.content_dir}")
        registry = create_registry_for_location(args.content_dir)
        
        # Perform validation
        if args.document_number:
            # Validate single document
            if args.document_number not in registry.document_hierarchy:
                print(f"Error: Document {args.document_number} not found in TOC")
                sys.exit(1)
            
            result = validate_single_document(registry, args.document_number, args.detailed)
            print_validation_results(result, args.detailed)
            
            if args.output:
                os.makedirs(os.path.dirname(args.output), exist_ok=True)
                with open(args.output, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
                print(f"Results saved to: {args.output}")
        
        else:
            # Validate all documents
            results = validate_all_documents(registry, args.detailed)
            print_validation_results(results, args.detailed)
            
            if args.output:
                os.makedirs(os.path.dirname(args.output), exist_ok=True)
                with open(args.output, 'w', encoding='utf-8') as f:
                    json.dump(results, f, indent=2, ensure_ascii=False)
                print(f"Results saved to: {args.output}")
    
    except Exception as e:
        print(f"Error during validation: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
