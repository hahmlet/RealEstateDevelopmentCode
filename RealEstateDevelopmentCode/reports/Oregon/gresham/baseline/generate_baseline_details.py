#!/usr/bin/env python3
"""
Baseline Detail Generator v1.0
Extracts comprehensive document and subsection data for baseline comparison
"""

import json
import sys
import os
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, '/workspace/RealEstateDevelopmentCode/scripts')

from scripts.common.hierarchical_document_registry import create_registry_for_location
from scripts.common.config import get_default_location


def generate_detailed_baseline():
    """Generate detailed baseline data for comparison purposes"""
    
    # Get default location
    default_config = get_default_location()
    content_dir = str(default_config['content_dir'])
    
    # Create registry
    registry = create_registry_for_location(content_dir)
    
    # Generate comprehensive report
    report = registry.generate_alignment_report()
    
    # Extract detailed document listings
    all_documents = []
    for doc_num, hierarchy in sorted(registry.document_hierarchy.items()):
        doc_info = {
            'number': doc_num,
            'title': hierarchy.document_title.strip(),
            'has_file': hierarchy.has_file,
            'filename': hierarchy.file_info.filename if hierarchy.file_info else None,
            'filepath': hierarchy.file_info.filepath if hierarchy.file_info else None,
            'subsection_count': len(hierarchy.subsections),
            'subsections': [
                {
                    'number': sub.number,
                    'title': sub.title.strip()
                }
                for sub in hierarchy.subsections
            ]
        }
        all_documents.append(doc_info)
    
    # Extract orphaned files with more detail
    orphaned_files = []
    for doc_file in registry.document_files:
        # Check if file is matched to any document
        is_matched = False
        for hierarchy in registry.document_hierarchy.values():
            if hierarchy.file_info and hierarchy.file_info.filename == doc_file.filename:
                is_matched = True
                break
        
        if not is_matched:
            orphaned_files.append({
                'filename': doc_file.filename,
                'filepath': doc_file.filepath,
                'extracted_number': doc_file.document_number
            })
    
    # Extract all subsections across all documents
    all_subsections = []
    for doc_num, hierarchy in sorted(registry.document_hierarchy.items()):
        for subsection in hierarchy.subsections:
            all_subsections.append({
                'number': subsection.number,
                'title': subsection.title.strip(),
                'parent_document': doc_num,
                'parent_title': hierarchy.document_title.strip(),
                'parent_has_file': hierarchy.has_file
            })
    
    # Create detailed baseline data
    baseline_detail = {
        'baseline_version': '1.0',
        'generation_date': '2025-05-23',
        'summary_metrics': {
            'total_documents': len(all_documents),
            'documents_with_files': sum(1 for doc in all_documents if doc['has_file']),
            'documents_without_files': sum(1 for doc in all_documents if not doc['has_file']),
            'total_subsections': len(all_subsections),
            'total_files': len(registry.document_files),
            'orphaned_files': len(orphaned_files),
            'alignment_percentage': round((sum(1 for doc in all_documents if doc['has_file']) / len(all_documents)) * 100, 1)
        },
        'all_documents': all_documents,
        'orphaned_files': orphaned_files,
        'all_subsections': all_subsections
    }
    
    return baseline_detail


def format_baseline_markdown(baseline_data):
    """Format baseline data as markdown for appending to baseline document"""
    
    md_content = []
    
    # Document listings
    md_content.append("\n## Detailed Document Inventory - Baseline 1.0\n")
    md_content.append("### All Documents in TOC with File Matches\n")
    
    for doc in baseline_data['all_documents']:
        status = "✓" if doc['has_file'] else "✗"
        filename = doc['filename'] if doc['filename'] else "**MISSING**"
        subsection_info = f"({doc['subsection_count']} subsection{'s' if doc['subsection_count'] != 1 else ''})"
        
        md_content.append(f"- {status} **{doc['number']}**: {doc['title']} → `{filename}` {subsection_info}\n")
    
    # Orphaned files
    md_content.append("\n### Orphaned Files (No TOC Match)\n")
    if baseline_data['orphaned_files']:
        for orphan in baseline_data['orphaned_files']:
            extracted = f"(extracted: {orphan['extracted_number']})" if orphan['extracted_number'] else "(no number extracted)"
            md_content.append(f"- `{orphan['filename']}` {extracted}\n")
    else:
        md_content.append("- None\n")
    
    # All subsections
    md_content.append("\n### Complete Subsection Inventory\n")
    md_content.append("| Subsection | Title | Parent Document | Parent Has File |\n")
    md_content.append("|------------|-------|-----------------|----------------|\n")
    
    for sub in baseline_data['all_subsections']:
        parent_status = "✓" if sub['parent_has_file'] else "✗"
        title = sub['title'][:50] + "..." if len(sub['title']) > 50 else sub['title']
        md_content.append(f"| {sub['number']} | {title} | {sub['parent_document']} | {parent_status} |\n")
    
    # Statistics summary
    metrics = baseline_data['summary_metrics']
    md_content.append(f"\n### Baseline 1.0 Statistics Summary\n")
    md_content.append(f"- **Total Documents**: {metrics['total_documents']}\n")
    md_content.append(f"- **Documents with Files**: {metrics['documents_with_files']}\n")
    md_content.append(f"- **Documents without Files**: {metrics['documents_without_files']}\n")
    md_content.append(f"- **Total Subsections**: {metrics['total_subsections']}\n")
    md_content.append(f"- **Total Files**: {metrics['total_files']}\n")
    md_content.append(f"- **Orphaned Files**: {metrics['orphaned_files']}\n")
    md_content.append(f"- **Alignment Percentage**: {metrics['alignment_percentage']}%\n")
    
    return ''.join(md_content)


if __name__ == "__main__":
    print("Generating detailed baseline data...")
    
    # Generate baseline data
    baseline_data = generate_detailed_baseline()
    
    # Save detailed JSON
    with open('/workspace/RealEstateDevelopmentCode/reports/Oregon/gresham/baseline/baseline_1.0_detailed.json', 'w', encoding='utf-8') as f:
        json.dump(baseline_data, f, indent=2, ensure_ascii=False)
    
    print(f"Saved detailed baseline to: baseline_1.0_detailed.json")
    print(f"Total documents: {baseline_data['summary_metrics']['total_documents']}")
    print(f"Total subsections: {baseline_data['summary_metrics']['total_subsections']}")
    print(f"Orphaned files: {baseline_data['summary_metrics']['orphaned_files']}")
    
    # Generate markdown content
    markdown_content = format_baseline_markdown(baseline_data)
    
    # Append to baseline markdown file
    with open('/workspace/RealEstateDevelopmentCode/reports/Oregon/gresham/baseline/BASELINE_1.0.md', 'a', encoding='utf-8') as f:
        f.write(markdown_content)
    
    print("Appended detailed listings to BASELINE_1.0.md")
    print("Baseline 1.0 detailed documentation complete!")
