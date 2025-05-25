#!/usr/bin/env python3
"""
RAG Accuracy Assessment Suite for Municipal Development Codes
Tests the quality, completeness, and accuracy of processed RAG data.
"""

import json
import os
import re
import random
from pathlib import Path
from typing import List, Dict, Tuple, Any
from collections import defaultdict, Counter
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("RAGAccuracyTester")

class RAGAccuracyTester:
    """Comprehensive accuracy testing for municipal code RAG system"""
    
    def __init__(self, rag_data_dir: str, source_json_dir: str = None):
        self.rag_data_dir = Path(rag_data_dir)
        self.source_json_dir = Path(source_json_dir) if source_json_dir else None
        
        # Load processed RAG data
        self.chunks = self._load_rag_chunks()
        self.tables = [c for c in self.chunks if c.get('type') == 'table']
        self.text_chunks = [c for c in self.chunks if c.get('type') == 'text']
        
        logger.info(f"Loaded {len(self.chunks)} total chunks ({len(self.tables)} tables, {len(self.text_chunks)} text)")
    
    def _load_rag_chunks(self) -> List[Dict]:
        """Load all processed RAG chunks from JSONL files"""
        chunks = []
        
        # Look for JSONL files
        jsonl_files = list(self.rag_data_dir.rglob("*.jsonl"))
        if not jsonl_files:
            # Look for JSON files as fallback
            json_files = list(self.rag_data_dir.rglob("*.json"))
            if json_files:
                for json_file in json_files:
                    if 'stats' not in json_file.name.lower():
                        try:
                            with open(json_file, 'r') as f:
                                data = json.load(f)
                                if isinstance(data, list):
                                    chunks.extend(data)
                                else:
                                    chunks.append(data)
                        except Exception as e:
                            logger.warning(f"Failed to load {json_file}: {e}")
        else:
            # Load JSONL files
            for jsonl_file in jsonl_files:
                try:
                    with open(jsonl_file, 'r') as f:
                        for line in f:
                            if line.strip():
                                chunks.append(json.loads(line))
                except Exception as e:
                    logger.warning(f"Failed to load {jsonl_file}: {e}")
        
        return chunks
    
    def test_overall_statistics(self) -> Dict[str, Any]:
        """Generate overall statistics about the RAG data"""
        
        stats = {
            'total_chunks': len(self.chunks),
            'table_chunks': len(self.tables),
            'text_chunks': len(self.text_chunks),
            'average_chunk_size': 0,
            'chunk_size_distribution': {},
            'sources_covered': set(),
            'jurisdictions_covered': set(),
            'content_types': Counter()
        }
        
        # Calculate size statistics
        if self.chunks:
            chunk_sizes = [len(c.get('content', '')) for c in self.chunks]
            stats['average_chunk_size'] = sum(chunk_sizes) / len(chunk_sizes)
            
            # Size distribution
            size_ranges = [(0, 200), (200, 500), (500, 1000), (1000, 2000), (2000, float('inf'))]
            for min_size, max_size in size_ranges:
                count = sum(1 for size in chunk_sizes if min_size <= size < max_size)
                range_label = f"{min_size}-{max_size if max_size != float('inf') else '∞'}"
                stats['chunk_size_distribution'][range_label] = count
        
        # Source and metadata analysis
        for chunk in self.chunks:
            metadata = chunk.get('metadata', {})
            
            if 'source' in metadata:
                stats['sources_covered'].add(str(metadata['source']))
            
            if 'jurisdiction' in metadata:
                stats['jurisdictions_covered'].add(metadata['jurisdiction'])
            
            content_type = metadata.get('content_type', chunk.get('type', 'unknown'))
            stats['content_types'][content_type] += 1
        
        # Convert sets to lists for JSON serialization
        stats['sources_covered'] = list(stats['sources_covered'])
        stats['jurisdictions_covered'] = list(stats['jurisdictions_covered'])
        stats['content_types'] = dict(stats['content_types'])
        
        return stats
    
    def test_table_extraction_quality(self) -> Dict[str, Any]:
        """Assess the quality of extracted tables"""
        
        results = {
            'total_tables': len(self.tables),
            'table_methods': Counter(),
            'table_sizes': [],
            'markdown_formatted': 0,
            'well_structured': 0,
            'municipal_table_types': defaultdict(int),
            'sample_tables': []
        }
        
        # Analyze each table
        for i, table in enumerate(self.tables):
            content = table.get('content', '')
            metadata = table.get('metadata', {})
            method = table.get('method', metadata.get('extraction_method', 'unknown'))
            
            results['table_methods'][method] += 1
            results['table_sizes'].append(len(content))
            
            # Check if markdown formatted
            if '|' in content and '---' in content:
                results['markdown_formatted'] += 1
            
            # Check if well-structured (has multiple rows/columns)
            lines = content.split('\n')
            if len(lines) >= 3 and any('|' in line for line in lines):
                results['well_structured'] += 1
            
            # Identify municipal table types
            content_lower = content.lower()
            municipal_keywords = {
                'parking': ['parking', 'spaces', 'stall'],
                'setback': ['setback', 'yard', 'distance'],
                'height': ['height', 'stories', 'feet'],
                'density': ['density', 'units', 'dwelling'],
                'use': ['permitted', 'conditional', 'prohibited'],
                'fees': ['fee', 'cost', 'charge', 'rate'],
                'landscaping': ['landscape', 'tree', 'plant'],
                'signs': ['sign', 'display', 'advertising']
            }
            
            for table_type, keywords in municipal_keywords.items():
                if any(keyword in content_lower for keyword in keywords):
                    results['municipal_table_types'][table_type] += 1
            
            # Sample tables for manual review
            if i < 5:  # First 5 tables
                results['sample_tables'].append({
                    'method': method,
                    'source': metadata.get('source', 'unknown'),
                    'size': len(content),
                    'preview': content[:300] + '...' if len(content) > 300 else content
                })
        
        # Calculate statistics
        if results['table_sizes']:
            results['average_table_size'] = sum(results['table_sizes']) / len(results['table_sizes'])
        
        results['table_methods'] = dict(results['table_methods'])
        results['municipal_table_types'] = dict(results['municipal_table_types'])
        
        return results
    
    def test_municipal_code_coverage(self) -> Dict[str, Any]:
        """Test coverage of important municipal development code topics"""
        
        # Key municipal code topics we expect to find
        municipal_topics = {
            'zoning': ['zoning', 'zone', 'district', 'residential', 'commercial', 'industrial'],
            'parking': ['parking', 'vehicle', 'space', 'stall', 'garage'],
            'setbacks': ['setback', 'yard', 'front yard', 'side yard', 'rear yard'],
            'building_height': ['height', 'stories', 'feet', 'maximum height'],
            'landscaping': ['landscape', 'tree', 'plant', 'vegetation', 'buffer'],
            'signs': ['sign', 'signage', 'advertising', 'display'],
            'subdivisions': ['subdivision', 'plat', 'lot', 'parcel'],
            'conditional_use': ['conditional use', 'cup', 'special use'],
            'variances': ['variance', 'exception', 'deviation'],
            'appeals': ['appeal', 'hearing', 'review'],
            'enforcement': ['violation', 'penalty', 'enforcement', 'compliance'],
            'fees': ['fee', 'cost', 'charge', 'application fee']
        }
        
        coverage_results = {}
        
        for topic, keywords in municipal_topics.items():
            matching_chunks = []
            
            for chunk in self.chunks:
                content = chunk.get('content', '').lower()
                if any(keyword in content for keyword in keywords):
                    matching_chunks.append({
                        'type': chunk.get('type'),
                        'source': chunk.get('metadata', {}).get('source', 'unknown'),
                        'content_preview': chunk.get('content', '')[:200] + '...'
                    })
            
            coverage_results[topic] = {
                'chunk_count': len(matching_chunks),
                'sample_chunks': matching_chunks[:3]  # First 3 matches
            }
        
        return coverage_results
    
    def test_chunk_quality(self) -> Dict[str, Any]:
        """Assess the quality of individual chunks"""
        
        quality_issues = []
        chunk_quality_stats = {
            'total_chunks': len(self.chunks),
            'empty_chunks': 0,
            'too_short': 0,
            'too_long': 0,
            'missing_metadata': 0,
            'malformed_content': 0,
            'quality_score_distribution': defaultdict(int)
        }
        
        for i, chunk in enumerate(self.chunks):
            content = chunk.get('content', '')
            metadata = chunk.get('metadata', {})
            issues_for_chunk = []
            quality_score = 100  # Start with perfect score
            
            # Check for empty content
            if not content or len(content.strip()) == 0:
                chunk_quality_stats['empty_chunks'] += 1
                issues_for_chunk.append("Empty content")
                quality_score -= 50
            
            # Check content length
            elif len(content.strip()) < 50:
                chunk_quality_stats['too_short'] += 1
                issues_for_chunk.append(f"Too short ({len(content)} chars)")
                quality_score -= 20
            elif len(content) > 5000:
                chunk_quality_stats['too_long'] += 1
                issues_for_chunk.append(f"Too long ({len(content)} chars)")
                quality_score -= 10
            
            # Check metadata completeness
            required_metadata = ['source', 'content_type']
            missing_metadata = [field for field in required_metadata if field not in metadata]
            if missing_metadata:
                chunk_quality_stats['missing_metadata'] += 1
                issues_for_chunk.append(f"Missing metadata: {missing_metadata}")
                quality_score -= len(missing_metadata) * 10
            
            # Check for malformed content (encoding issues, etc.)
            if any(char in content for char in ['\ufffd', '\x00']):
                chunk_quality_stats['malformed_content'] += 1
                issues_for_chunk.append("Malformed characters detected")
                quality_score -= 15
            
            # Score distribution
            score_range = (quality_score // 10) * 10
            chunk_quality_stats['quality_score_distribution'][f"{score_range}-{score_range+9}"] += 1
            
            # Track significant issues
            if issues_for_chunk and len(quality_issues) < 20:  # Limit to first 20 issues
                quality_issues.append({
                    'chunk_index': i,
                    'type': chunk.get('type'),
                    'issues': issues_for_chunk,
                    'quality_score': quality_score,
                    'source': metadata.get('source', 'unknown')
                })
        
        chunk_quality_stats['quality_issues'] = quality_issues
        chunk_quality_stats['quality_score_distribution'] = dict(chunk_quality_stats['quality_score_distribution'])
        
        return chunk_quality_stats
    
    def test_source_file_accuracy(self) -> Dict[str, Any]:
        """Compare processed chunks against original source files if available"""
        
        if not self.source_json_dir or not self.source_json_dir.exists():
            return {"error": "Source JSON directory not available for comparison"}
        
        source_comparison = {
            'source_files_found': 0,
            'processed_files': 0,
            'missing_from_processing': [],
            'content_discrepancies': []
        }
        
        # Get list of source files
        source_files = list(self.source_json_dir.glob("*.json"))
        source_comparison['source_files_found'] = len(source_files)
        
        # Check which files were processed
        processed_sources = set()
        for chunk in self.chunks:
            source = chunk.get('metadata', {}).get('source', '')
            if source:
                processed_sources.add(Path(source).name)
        
        source_comparison['processed_files'] = len(processed_sources)
        
        # Find missing files
        for source_file in source_files:
            if source_file.name not in processed_sources:
                source_comparison['missing_from_processing'].append(source_file.name)
        
        return source_comparison
    
    def generate_sample_queries(self) -> List[Dict[str, Any]]:
        """Generate sample queries to test retrieval quality"""
        
        # Municipal code query patterns
        query_templates = [
            "What are the parking requirements for {use_type}?",
            "What are the setback requirements in {zone}?",
            "What is the maximum building height for {zone}?",
            "What landscaping is required for {development_type}?",
            "What are the sign regulations for {zone}?",
            "What fees are required for {permit_type}?",
            "What are the conditional use requirements for {use}?",
            "What are the subdivision requirements for {lot_type}?"
        ]
        
        # Extract common terms from content
        all_content = " ".join([chunk.get('content', '') for chunk in self.chunks[:100]])  # Sample
        
        # Simple term extraction (could be improved with NLP)
        zones = re.findall(r'\b(?:R-\d+|C-\d+|I-\d+|residential|commercial|industrial)\b', all_content, re.IGNORECASE)
        uses = re.findall(r'\b(?:restaurant|retail|office|warehouse|dwelling|apartment)\b', all_content, re.IGNORECASE)
        
        sample_queries = []
        for template in query_templates[:5]:  # Limit to 5 templates
            # Fill template with extracted terms or defaults
            if '{zone}' in template:
                zone = zones[0] if zones else "residential"
                query = template.format(zone=zone)
            elif '{use_type}' in template or '{use}' in template:
                use = uses[0] if uses else "restaurant"
                query = template.format(use_type=use, use=use)
            else:
                # Use defaults for other placeholders
                query = template.format(
                    development_type="commercial",
                    permit_type="building permit",
                    lot_type="residential"
                )
            
            sample_queries.append({
                'query': query,
                'template': template,
                'expected_content_types': ['text', 'table']
            })
        
        return sample_queries
    
    def run_full_assessment(self) -> Dict[str, Any]:
        """Run the complete RAG accuracy assessment"""
        
        logger.info("Starting comprehensive RAG accuracy assessment...")
        
        assessment_results = {
            'timestamp': str(pd.Timestamp.now()),
            'overall_stats': self.test_overall_statistics(),
            'table_quality': self.test_table_extraction_quality(),
            'municipal_coverage': self.test_municipal_code_coverage(),
            'chunk_quality': self.test_chunk_quality(),
            'source_accuracy': self.test_source_file_accuracy(),
            'sample_queries': self.generate_sample_queries()
        }
        
        logger.info("RAG accuracy assessment completed!")
        return assessment_results

def main():
    """Main function to run RAG accuracy assessment"""
    
    # Configuration
    rag_data_dir = "/workspace/RealEstateDevelopmentCode/rag_data_accurate/Oregon/gresham"
    source_json_dir = "/workspace/RealEstateDevelopmentCode/pdf_content/Oregon/gresham"
    output_dir = Path("/workspace/RealEstateDevelopmentCode/rag_assessment")
    
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Run assessment
    tester = RAGAccuracyTester(rag_data_dir, source_json_dir)
    results = tester.run_full_assessment()
    
    # Save results
    results_file = output_dir / "accuracy_assessment_results.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    # Generate summary report
    generate_summary_report(results, output_dir / "accuracy_assessment_summary.md")
    
    print(f"\n🎯 RAG Accuracy Assessment Complete!")
    print(f"📊 Full results: {results_file}")
    print(f"📋 Summary report: {output_dir / 'accuracy_assessment_summary.md'}")
    
    return results

def generate_summary_report(results: Dict[str, Any], output_file: Path):
    """Generate a human-readable summary report"""
    
    report = f"""# RAG Accuracy Assessment Summary
Generated: {results.get('timestamp', 'Unknown')}

## 📊 Overall Statistics
- **Total Chunks**: {results['overall_stats']['total_chunks']:,}
- **Table Chunks**: {results['overall_stats']['table_chunks']:,}
- **Text Chunks**: {results['overall_stats']['text_chunks']:,}
- **Average Chunk Size**: {results['overall_stats']['average_chunk_size']:.0f} characters
- **Jurisdictions Covered**: {len(results['overall_stats']['jurisdictions_covered'])}
- **Source Files Processed**: {len(results['overall_stats']['sources_covered'])}

### Chunk Size Distribution
"""
    
    for size_range, count in results['overall_stats']['chunk_size_distribution'].items():
        percentage = (count / results['overall_stats']['total_chunks']) * 100
        report += f"- {size_range} chars: {count:,} chunks ({percentage:.1f}%)\n"
    
    report += f"""
## 📋 Table Extraction Quality
- **Total Tables Extracted**: {results['table_quality']['total_tables']:,}
- **Markdown Formatted**: {results['table_quality']['markdown_formatted']:,} ({(results['table_quality']['markdown_formatted']/max(results['table_quality']['total_tables'],1)*100):.1f}%)
- **Well Structured**: {results['table_quality']['well_structured']:,} ({(results['table_quality']['well_structured']/max(results['table_quality']['total_tables'],1)*100):.1f}%)
- **Average Table Size**: {results['table_quality'].get('average_table_size', 0):.0f} characters

### Table Extraction Methods
"""
    
    for method, count in results['table_quality']['table_methods'].items():
        report += f"- {method}: {count:,} tables\n"
    
    report += f"""
### Municipal Table Types Found
"""
    
    for table_type, count in results['table_quality']['municipal_table_types'].items():
        report += f"- {table_type.title()}: {count:,} tables\n"
    
    report += f"""
## 🏛️ Municipal Code Coverage
"""
    
    for topic, data in results['municipal_coverage'].items():
        chunk_count = data['chunk_count']
        report += f"- **{topic.replace('_', ' ').title()}**: {chunk_count:,} chunks\n"
    
    report += f"""
## ✅ Chunk Quality Assessment
- **Total Chunks Analyzed**: {results['chunk_quality']['total_chunks']:,}
- **Empty Chunks**: {results['chunk_quality']['empty_chunks']:,}
- **Too Short (<50 chars)**: {results['chunk_quality']['too_short']:,}
- **Too Long (>5000 chars)**: {results['chunk_quality']['too_long']:,}
- **Missing Metadata**: {results['chunk_quality']['missing_metadata']:,}
- **Malformed Content**: {results['chunk_quality']['malformed_content']:,}

### Quality Issues (Sample)
"""
    
    for issue in results['chunk_quality']['quality_issues'][:5]:
        report += f"- Chunk {issue['chunk_index']} ({issue['type']}): {', '.join(issue['issues'])}\n"
    
    report += f"""
## 🔍 Sample Test Queries
These queries can be used to test retrieval accuracy:

"""
    
    for i, query in enumerate(results['sample_queries'], 1):
        report += f"{i}. {query['query']}\n"
    
    report += f"""
## 📈 Recommendations

### Strengths
"""
    
    # Generate recommendations based on results
    total_chunks = results['overall_stats']['total_chunks']
    table_count = results['table_quality']['total_tables']
    quality_issues = len(results['chunk_quality']['quality_issues'])
    
    if total_chunks > 1000:
        report += "- ✅ Good volume of processed content\n"
    if table_count > 50:
        report += "- ✅ Strong table extraction coverage\n"
    if results['table_quality']['markdown_formatted'] / max(table_count, 1) > 0.7:
        report += "- ✅ Good table formatting consistency\n"
    
    report += f"""
### Areas for Improvement
"""
    
    if quality_issues > total_chunks * 0.1:
        report += "- ⚠️ High number of chunk quality issues - review processing pipeline\n"
    if results['chunk_quality']['empty_chunks'] > 0:
        report += "- ⚠️ Empty chunks detected - filter out during processing\n"
    if results['chunk_quality']['too_short'] > total_chunks * 0.2:
        report += "- ⚠️ Many chunks are too short - consider adjusting chunk size\n"
    
    # Save the report
    with open(output_file, 'w') as f:
        f.write(report)

if __name__ == "__main__":
    # Add pandas import for timestamp
    try:
        import pandas as pd
    except ImportError:
        # Fallback to datetime if pandas not available
        from datetime import datetime
        class pd:
            @staticmethod
            def Timestamp():
                return datetime.now()
            
            @staticmethod
            def now():
                return datetime.now()
    
    main()
