#!/usr/bin/env python3
"""
Municipal Document Registry CLI Tool
Version: 1.0
Date: May 23, 2025

Consolidated command-line interface for document registry operations.
Combines alignment analysis and content validation in a single tool.

Usage:
    python document_registry_cli.py analyze [options]
    python document_registry_cli.py validate [options]
    python document_registry_cli.py report [options]
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts'))

from scripts.common.hierarchical_document_registry import create_registry_for_location
from scripts.common.config import get_default_location, get_reports_directory, ensure_directories_exist
from scripts.common.utils import save_json_file


def cmd_analyze(args):
    """Analyze document alignment"""
    print(f"Analyzing document alignment for: {args.content_dir}")
    
    # Create registry
    registry = create_registry_for_location(args.content_dir)
    
    # Generate report
    report = registry.generate_alignment_report()
    
    # Add metadata
    report['analysis_metadata'] = {
        'content_directory': args.content_dir,
        'analysis_type': 'hierarchical_alignment',
        'validation_performed': False
    }
    
    # Print summary
    metrics = report['metrics']
    print(f"\n{'='*60}")
    print("DOCUMENT ALIGNMENT ANALYSIS RESULTS")
    print(f"{'='*60}")
    print(f"Total Documents:           {metrics['total_documents']}")
    print(f"Documents with Files:      {metrics['documents_with_files']}")
    print(f"Documents without Files:   {metrics['documents_without_files']}")
    print(f"Total Subsections:         {metrics['total_subsections']}")
    print(f"Orphaned Files:            {metrics['orphaned_files']}")
    print(f"Alignment Percentage:      {metrics['alignment_percentage']:.1f}%")
    
    # Save report if requested
    if args.output:
        ensure_directories_exist(*Path(args.content_dir).parts[-2:])
        save_json_file(report, args.output)
        print(f"\nReport saved to: {args.output}")
    
    return report


def cmd_validate(args):
    """Validate document content"""
    print(f"Validating document content for: {args.content_dir}")
    
    # Create registry
    registry = create_registry_for_location(args.content_dir)
    
    if args.document_number:
        # Validate single document
        if args.document_number not in registry.document_hierarchy:
            print(f"Error: Document {args.document_number} not found in TOC")
            return None
        
        result = registry.validate_subsection_content(args.document_number)
        results = {'validation_results': [result]}
    else:
        # Validate all documents
        validation_results = []
        for doc_num, hierarchy in registry.document_hierarchy.items():
            if hierarchy.has_file:
                validation = registry.validate_subsection_content(doc_num)
                validation_results.append(validation)
        
        # Calculate summary
        successful = [r for r in validation_results if 'error' not in r]
        results = {
            'total_documents_with_files': len(validation_results),
            'successful_validations': len(successful),
            'failed_validations': len(validation_results) - len(successful),
            'validation_results': validation_results
        }
        
        if successful:
            results['average_validation_percentage'] = sum(
                r.get('validation_percentage', 0) for r in successful
            ) / len(successful)
            
            results['total_expected_subsections'] = sum(
                r.get('expected_subsections', 0) for r in successful
            )
            
            results['total_found_subsections'] = sum(
                r.get('found_subsections', 0) for r in successful
            )
    
    # Print summary
    print(f"\n{'='*60}")
    print("CONTENT VALIDATION RESULTS")
    print(f"{'='*60}")
    
    if 'total_documents_with_files' in results:
        print(f"Total Documents with Files:     {results['total_documents_with_files']}")
        print(f"Successful Validations:         {results['successful_validations']}")
        print(f"Failed Validations:             {results['failed_validations']}")
        if 'average_validation_percentage' in results:
            print(f"Average Validation Percentage:  {results['average_validation_percentage']:.1f}%")
    
    # Show individual results
    for result in results['validation_results']:
        if 'error' in result:
            print(f"  ERROR: {result['error']}")
            continue
        
        doc_num = result.get('document_number', 'Unknown')
        validation_pct = result.get('validation_percentage', 0)
        expected = result.get('expected_subsections', 0)
        found = result.get('found_subsections', 0)
        
        status = "✓" if validation_pct > 80 else "⚠" if validation_pct > 50 else "✗"
        print(f"  {status} {doc_num}: {validation_pct:.1f}% ({found}/{expected} subsections)")
    
    # Save results if requested
    if args.output:
        ensure_directories_exist(*Path(args.content_dir).parts[-2:])
        save_json_file(results, args.output)
        print(f"\nResults saved to: {args.output}")
    
    return results


def cmd_report(args):
    """Generate comprehensive report combining analysis and validation"""
    print(f"Generating comprehensive report for: {args.content_dir}")
    
    # Create registry
    registry = create_registry_for_location(args.content_dir)
    
    # Generate alignment report
    alignment_report = registry.generate_alignment_report()
    
    # Add content validation
    validation_results = []
    for doc_num, hierarchy in registry.document_hierarchy.items():
        if hierarchy.has_file:
            validation = registry.validate_subsection_content(doc_num)
            validation_results.append(validation)
    
    # Calculate validation summary
    successful = [r for r in validation_results if 'error' not in r]
    validation_summary = {
        'total_validations': len(validation_results),
        'successful_validations': len(successful),
        'average_validation_percentage': 0
    }
    
    if successful:
        validation_summary['average_validation_percentage'] = sum(
            r.get('validation_percentage', 0) for r in successful
        ) / len(successful)
    
    # Combine reports
    comprehensive_report = {
        **alignment_report,
        'content_validation': validation_results,
        'validation_summary': validation_summary,
        'analysis_metadata': {
            'content_directory': args.content_dir,
            'analysis_type': 'comprehensive',
            'validation_performed': True
        }
    }
    
    # Print summary
    metrics = comprehensive_report['metrics']
    validation = comprehensive_report['validation_summary']
    
    print(f"\n{'='*60}")
    print("COMPREHENSIVE DOCUMENT REGISTRY REPORT")
    print(f"{'='*60}")
    print("ALIGNMENT METRICS:")
    print(f"  Total Documents:           {metrics['total_documents']}")
    print(f"  Documents with Files:      {metrics['documents_with_files']}")
    print(f"  Alignment Percentage:      {metrics['alignment_percentage']:.1f}%")
    print()
    print("VALIDATION METRICS:")
    print(f"  Successful Validations:    {validation['successful_validations']}")
    print(f"  Average Validation %:      {validation['average_validation_percentage']:.1f}%")
    
    # Save report
    if args.output:
        ensure_directories_exist(*Path(args.content_dir).parts[-2:])
        save_json_file(comprehensive_report, args.output)
        print(f"\nComprehensive report saved to: {args.output}")
    
    return comprehensive_report


def main():
    # Get default configuration
    default_config = get_default_location()
    
    parser = argparse.ArgumentParser(description='Municipal Document Registry CLI Tool')
    parser.add_argument('command', choices=['analyze', 'validate', 'report'],
                       help='Command to execute')
    parser.add_argument('--content-dir', 
                       default=str(default_config['content_dir']),
                       help='Directory containing document files')
    parser.add_argument('--document-number', '-d',
                       help='Validate specific document number (validate command only)')
    parser.add_argument('--output', '-o',
                       help='Output file for results')
    
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
            
            if args.command == 'analyze':
                args.output = str(output_dir / 'alignment_analysis.json')
            elif args.command == 'validate':
                args.output = str(output_dir / 'content_validation.json')
            elif args.command == 'report':
                args.output = str(output_dir / 'comprehensive_report.json')
    
    try:
        # Execute command
        if args.command == 'analyze':
            result = cmd_analyze(args)
        elif args.command == 'validate':
            result = cmd_validate(args)
        elif args.command == 'report':
            result = cmd_report(args)
        
        if result is None:
            sys.exit(1)
            
    except Exception as e:
        print(f"Error during {args.command}: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
