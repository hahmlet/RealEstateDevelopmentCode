"""
Hierarchical Document Registry System for Municipal Development Codes
Version: 1.0
Date: May 23, 2025

This module provides a corrected understanding of municipal code structure where:
- Document-level entries (XX.YY format) correspond to actual files
- Subsection entries (XX.YYYY format) are contained within parent documents
- Alignment is measured at the document level, not individual subsections

Key insight: Municipal codes have hierarchical structure where subsections 
exist within parent document files, not as separate files.
"""

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass, field
from collections import defaultdict

from .config import PATTERNS, DEFAULT_FILES
from .utils import (
    load_json_file, save_json_file, extract_number_from_filename,
    is_document_level, is_subsection, get_parent_document,
    parse_toc_text_content, extract_toc_entries_from_text,
    calculate_percentage
)


@dataclass
class TOCEntry:
    """Represents a Table of Contents entry"""
    number: str
    title: str
    page: Optional[str] = None
    level: int = 0
    
    @property
    def is_document_level(self) -> bool:
        """Check if this is a document-level entry (XX.YY format)"""
        return is_document_level(self.number)
    
    @property
    def is_subsection(self) -> bool:
        """Check if this is a subsection entry (XX.YYYY format)"""
        return is_subsection(self.number)
    
    @property
    def parent_document(self) -> Optional[str]:
        """Get parent document number for subsections"""
        return get_parent_document(self.number)


@dataclass
class DocumentFile:
    """Represents an actual document file"""
    filename: str
    filepath: str
    extracted_number: Optional[str] = None
    content_preview: Optional[str] = None
    
    @property
    def document_number(self) -> Optional[str]:
        """Extract document number from filename"""
        if self.extracted_number:
            return self.extracted_number
        return extract_number_from_filename(self.filename)


@dataclass
class DocumentHierarchy:
    """Represents the hierarchical structure of a document"""
    document_number: str
    document_title: str
    file_info: Optional[DocumentFile] = None
    subsections: List[TOCEntry] = field(default_factory=list)
    
    @property
    def has_file(self) -> bool:
        """Check if this document has a corresponding file"""
        return self.file_info is not None
    
    @property
    def subsection_count(self) -> int:
        """Number of subsections in this document"""
        return len(self.subsections)


@dataclass
class AlignmentMetrics:
    """Metrics for TOC-to-file alignment"""
    total_documents: int
    documents_with_files: int
    documents_without_files: int
    total_subsections: int
    orphaned_files: int
    
    @property
    def alignment_percentage(self) -> float:
        """Calculate alignment percentage"""
        return calculate_percentage(self.documents_with_files, self.total_documents)


class HierarchicalDocumentRegistry:
    """Registry for managing hierarchical document structures"""
    
    def __init__(self):
        self.toc_entries: List[TOCEntry] = []
        self.document_files: List[DocumentFile] = []
        self.document_hierarchy: Dict[str, DocumentHierarchy] = {}
    
    def load_toc_from_file(self, toc_file_path: str) -> None:
        """Load TOC entries from JSON file"""
        toc_data = load_json_file(toc_file_path)
        
        self.toc_entries = []
        
        # Handle different TOC data structures
        if isinstance(toc_data, dict) and 'toc' in toc_data:
            # Structured TOC format
            toc_items = toc_data['toc']
            for item in toc_items:
                entry = TOCEntry(
                    number=item.get('number', ''),
                    title=item.get('title', ''),
                    page=item.get('page'),
                    level=item.get('level', 0)
                )
                self.toc_entries.append(entry)
        elif isinstance(toc_data, list):
            # List of TOC items
            for item in toc_data:
                entry = TOCEntry(
                    number=item.get('number', ''),
                    title=item.get('title', ''),
                    page=item.get('page'),
                    level=item.get('level', 0)
                )
                self.toc_entries.append(entry)
        elif isinstance(toc_data, dict):
            # Check if this is extracted PDF format with pages
            has_pages_with_text = False
            
            # Check for pages list structure
            if 'pages' in toc_data and isinstance(toc_data['pages'], list):
                for page in toc_data['pages']:
                    if isinstance(page, dict) and 'text' in page:
                        has_pages_with_text = True
                        break
            else:
                # Check other structures
                for key, value in toc_data.items():
                    if isinstance(value, dict) and 'text' in value:
                        has_pages_with_text = True
                        break
                    elif isinstance(value, list):
                        for item in value:
                            if isinstance(item, dict) and 'text' in item:
                                has_pages_with_text = True
                                break
                        if has_pages_with_text:
                            break
            
            if has_pages_with_text:
                # Extracted PDF format - parse from page text
                self._parse_toc_from_page_text(toc_data)
            else:
                raise ValueError("Unsupported TOC data structure")
        else:
            raise ValueError("Unsupported TOC data structure")
    
    def _parse_toc_from_page_text(self, pdf_data: dict) -> None:
        """Parse TOC entries from extracted PDF page text"""
        # Extract all text from the PDF data
        all_text = parse_toc_text_content(pdf_data)
        
        # Extract TOC entries using centralized utility
        entries = extract_toc_entries_from_text(all_text)
        
        # Convert to TOCEntry objects
        for entry_data in entries:
            if entry_data['type'] == 'section_header':
                # Document-level entry
                number = entry_data['number']
                # Normalize to XX.YY format
                if '.' in number:
                    parts = number.split('.')
                    if len(parts) == 2 and len(parts[1]) > 2:
                        number = f"{parts[0]}.{parts[1][:2]}"
                
                entry = TOCEntry(
                    number=number,
                    title=entry_data['title'],
                    level=0
                )
                self.toc_entries.append(entry)
            
            elif entry_data['type'] == 'subsection':
                # Subsection entry
                entry = TOCEntry(
                    number=entry_data['number'],
                    title=entry_data['title'],
                    level=1
                )
                self.toc_entries.append(entry)
    
    def scan_document_files(self, content_dir: str) -> None:
        """Scan directory for document files"""
        self.document_files = []
        content_path = Path(content_dir)
        
        if not content_path.exists():
            return
        
        for file_path in content_path.glob('*.json'):
            if file_path.name == 'dc-table-of-contents.json':
                continue  # Skip TOC file
            
            doc_file = DocumentFile(
                filename=file_path.name,
                filepath=str(file_path)
            )
            self.document_files.append(doc_file)
    
    def build_hierarchy(self) -> None:
        """Build hierarchical document structure"""
        self.document_hierarchy = {}
        
        # First, identify all document-level entries
        document_entries = [entry for entry in self.toc_entries if entry.is_document_level]
        subsection_entries = [entry for entry in self.toc_entries if entry.is_subsection]
        
        # Create hierarchy objects for each document
        for doc_entry in document_entries:
            hierarchy = DocumentHierarchy(
                document_number=doc_entry.number,
                document_title=doc_entry.title
            )
            self.document_hierarchy[doc_entry.number] = hierarchy
        
        # Assign subsections to their parent documents
        for subsection in subsection_entries:
            parent_num = subsection.parent_document
            if parent_num and parent_num in self.document_hierarchy:
                self.document_hierarchy[parent_num].subsections.append(subsection)
        
        # Match files to documents
        for doc_file in self.document_files:
            doc_num = doc_file.document_number
            if doc_num and doc_num in self.document_hierarchy:
                self.document_hierarchy[doc_num].file_info = doc_file
    
    def calculate_alignment_metrics(self) -> AlignmentMetrics:
        """Calculate alignment metrics"""
        total_documents = len(self.document_hierarchy)
        documents_with_files = sum(1 for h in self.document_hierarchy.values() if h.has_file)
        documents_without_files = total_documents - documents_with_files
        total_subsections = sum(h.subsection_count for h in self.document_hierarchy.values())
        
        # Count orphaned files (files without matching documents)
        matched_files = set()
        for hierarchy in self.document_hierarchy.values():
            if hierarchy.file_info:
                matched_files.add(hierarchy.file_info.filename)
        
        orphaned_files = len(self.document_files) - len(matched_files)
        
        return AlignmentMetrics(
            total_documents=total_documents,
            documents_with_files=documents_with_files,
            documents_without_files=documents_without_files,
            total_subsections=total_subsections,
            orphaned_files=orphaned_files
        )
    
    def get_missing_documents(self) -> List[DocumentHierarchy]:
        """Get list of documents without corresponding files"""
        return [h for h in self.document_hierarchy.values() if not h.has_file]
    
    def get_orphaned_files(self) -> List[DocumentFile]:
        """Get list of files without corresponding TOC entries"""
        matched_files = set()
        for hierarchy in self.document_hierarchy.values():
            if hierarchy.file_info:
                matched_files.add(hierarchy.file_info.filename)
        
        return [f for f in self.document_files if f.filename not in matched_files]
    
    def generate_alignment_report(self) -> Dict:
        """Generate comprehensive alignment report"""
        metrics = self.calculate_alignment_metrics()
        missing_docs = self.get_missing_documents()
        orphaned_files = self.get_orphaned_files()
        
        report = {
            'metrics': {
                'total_documents': metrics.total_documents,
                'documents_with_files': metrics.documents_with_files,
                'documents_without_files': metrics.documents_without_files,
                'total_subsections': metrics.total_subsections,
                'orphaned_files': metrics.orphaned_files,
                'alignment_percentage': round(metrics.alignment_percentage, 2)
            },
            'missing_documents': [
                {
                    'number': doc.document_number,
                    'title': doc.document_title,
                    'subsection_count': doc.subsection_count,
                    'subsections': [
                        {'number': sub.number, 'title': sub.title}
                        for sub in doc.subsections
                    ]
                }
                for doc in missing_docs
            ],
            'orphaned_files': [
                {
                    'filename': f.filename,
                    'extracted_number': f.document_number
                }
                for f in orphaned_files
            ],
            'document_hierarchy': [
                {
                    'number': doc.document_number,
                    'title': doc.document_title,
                    'has_file': doc.has_file,
                    'filename': doc.file_info.filename if doc.file_info else None,
                    'subsection_count': doc.subsection_count,
                    'subsections': [
                        {'number': sub.number, 'title': sub.title}
                        for sub in doc.subsections[:5]  # Limit for readability
                    ] + ([{'note': f'... and {doc.subsection_count - 5} more'}] 
                         if doc.subsection_count > 5 else [])
                }
                for doc in self.document_hierarchy.values()
            ]
        }
        
        return report
    
    def validate_subsection_content(self, document_number: str) -> Dict:
        """Validate that a document file contains its expected subsections"""
        if document_number not in self.document_hierarchy:
            return {'error': f'Document {document_number} not found in hierarchy'}
        
        hierarchy = self.document_hierarchy[document_number]
        if not hierarchy.has_file:
            return {'error': f'No file found for document {document_number}'}
        
        try:
            with open(hierarchy.file_info.filepath, 'r', encoding='utf-8') as f:
                content = json.load(f)
            
            # Extract text content for searching
            if isinstance(content, dict):
                text_content = str(content)
            else:
                text_content = str(content)
            
            # Check for subsection numbers in content
            found_subsections = []
            missing_subsections = []
            
            for subsection in hierarchy.subsections:
                if subsection.number in text_content:
                    found_subsections.append(subsection.number)
                else:
                    missing_subsections.append(subsection.number)
            
            return {
                'document_number': document_number,
                'file_path': hierarchy.file_info.filepath,
                'expected_subsections': len(hierarchy.subsections),
                'found_subsections': len(found_subsections),
                'missing_subsections': len(missing_subsections),
                'found_list': found_subsections,
                'missing_list': missing_subsections,
                'validation_percentage': (len(found_subsections) / len(hierarchy.subsections) * 100) 
                                       if hierarchy.subsections else 100
            }
            
        except Exception as e:
            return {'error': f'Failed to validate content: {str(e)}'}


def create_registry_for_location(content_dir: str, toc_file: str = None) -> HierarchicalDocumentRegistry:
    """Factory function to create a registry for a specific location"""
    registry = HierarchicalDocumentRegistry()
    
    # Default TOC file location
    if toc_file is None:
        toc_file = os.path.join(content_dir, DEFAULT_FILES['toc'])
    
    # Load data
    if os.path.exists(toc_file):
        registry.load_toc_from_file(toc_file)
    
    registry.scan_document_files(content_dir)
    registry.build_hierarchy()
    
    return registry


if __name__ == "__main__":
    # Demo usage with configurable location
    from .config import get_default_location
    
    default_config = get_default_location()
    content_dir = str(default_config['content_dir'])
    
    print(f"Creating Hierarchical Document Registry for {default_config['city']}...")
    registry = create_registry_for_location(content_dir)
    
    print(f"Loaded {len(registry.toc_entries)} TOC entries")
    print(f"Found {len(registry.document_files)} document files")
    print(f"Built hierarchy with {len(registry.document_hierarchy)} documents")
    
    # Generate and display metrics
    metrics = registry.calculate_alignment_metrics()
    print(f"\nAlignment Metrics:")
    print(f"  Total documents: {metrics.total_documents}")
    print(f"  Documents with files: {metrics.documents_with_files}")
    print(f"  Documents without files: {metrics.documents_without_files}")
    print(f"  Total subsections: {metrics.total_subsections}")
    print(f"  Orphaned files: {metrics.orphaned_files}")
    print(f"  Alignment percentage: {metrics.alignment_percentage:.1f}%")
