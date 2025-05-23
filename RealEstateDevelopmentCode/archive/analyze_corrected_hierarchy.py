#!/usr/bin/env python3
"""
Implementation of a Hierarchical Document Registry that correctly understands
the structure of municipal code documents.

Key insights:
- Document files (e.g., dc-section-10.0400.json) correspond to XX.YY entries
- Subsections (10.0410, 10.0411, etc.) are contained within these document files
- Not every TOC entry needs its own separate file
"""

import json
import os
import re
import logging
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set, Tuple, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

class HierarchicalDocumentRegistry:
    """
    Document registry that properly understands the hierarchical nature of municipal codes.
    """
    
    def __init__(self, state: str, city: str):
        self.state = state
        self.city = city
        self.jurisdiction = f"{state}/{city}"
        self.logger = logging.getLogger(f"hier_doc_registry.{state}.{city}")
        
        # Configure paths
        self.base_dir = Path("/workspace/data")
        self.content_dir = self.base_dir / "pdf_content" / state / city
        self.toc_file = self.content_dir / "dc-table-of-contents.json"
        self.output_dir = self.base_dir / "registry" / state / city
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def analyze(self):
        """Run the hierarchical document analysis."""
        self.logger.info(f"Starting hierarchical document analysis for {self.jurisdiction}")
        
        # 1. Load TOC
        toc_data = self._load_toc()
        if not toc_data:
            return None
            
        # 2. Scan available document files
        available_files = self._scan_document_files()
        
        # 3. Extract document hierarchy from TOC
        doc_hierarchy = self._extract_document_hierarchy(toc_data)
        
        # 4. Match document files to TOC entries
        matching_results = self._match_documents_to_files(doc_hierarchy, available_files)
        
        # 5. Generate analysis report
        analysis = self._generate_analysis_report(doc_hierarchy, available_files, matching_results)
        
        # 6. Save reports
        self._save_reports(analysis)
        
        return analysis
    
    def _load_toc(self) -> Optional[Dict]:
        """Load TOC data from JSON file."""
        if not self.toc_file.exists():
            self.logger.error(f"TOC file not found: {self.toc_file}")
            return None
            
        try:
            with open(self.toc_file, 'r') as f:
                toc_data = json.load(f)
                
            self.logger.info(f"Loaded TOC with {len(toc_data.get('content', ''))} characters")
            return toc_data
        except Exception as e:
            self.logger.error(f"Error loading TOC: {e}")
            return None
    
    def _scan_document_files(self) -> Dict[str, List[str]]:
        """Scan for available document files by category."""
        files = {
            "sections": [],
            "articles": [],
            "appendices": [],
            "other": []
        }
        
        if not self.content_dir.exists():
            self.logger.error(f"Content directory not found: {self.content_dir}")
            return files
        
        # Scan all JSON files except TOC
        for file_path in self.content_dir.glob("*.json"):
            if file_path.name == "dc-table-of-contents.json":
                continue
                
            file_name = file_path.name
            
            # Categorize files by type
            if re.match(r'dc-section-\d+\.\d{4}', file_name):
                files["sections"].append(file_name)
            elif re.match(r'dc-article-\d+', file_name):
                files["articles"].append(file_name)
            elif re.match(r'dc-appendix-\d+', file_name) or "appendix" in file_name.lower():
                files["appendices"].append(file_name)
            else:
                files["other"].append(file_name)
        
        # Log file counts
        for category, category_files in files.items():
            self.logger.info(f"  {category.capitalize()}: {len(category_files)} files found")
            
        return files
    
    def _extract_document_hierarchy(self, toc_data: Dict) -> Dict[str, Any]:
        """
        Extract hierarchical document structure from TOC.
        
        Returns a structure that groups subsections under their parent documents.
        """
        toc_content = toc_data.get('content', '')
        hierarchy = {
            "document_entries": [],  # Document-level entries (XX.YY format)
            "subsection_groups": defaultdict(list),  # Group subsections by parent document
            "article_entries": [],   # Article entries
            "appendix_entries": [],  # Appendix entries
            "stats": {
                "total_entries": 0,
                "document_level": 0,
                "subsections": 0,
                "articles": 0,
                "appendices": 0,
                "other": 0
            }
        }
        
        # Pattern for section numbers (10.0400, 10.0401, etc.)
        section_pattern = re.compile(r'(\d+\.\d{4,6})\s+(.*?)(?=\d+\.\d{4}|\Z)', re.DOTALL)
        
        # Pattern for document-level section numbers (10.0400, etc.)
        doc_section_pattern = re.compile(r'SECTION\s+(\d+\.\d{4})', re.DOTALL | re.IGNORECASE)
        
        # Pattern for articles
        article_pattern = re.compile(r'ARTICLE\s+(\d+)\s+(.*?)(?=ARTICLE|\Z)', re.DOTALL | re.IGNORECASE)
        
        # Pattern for appendices
        appendix_pattern = re.compile(r'APPENDIX\s+(\d+(?:\.\d+)?)\s+(.*?)(?=APPENDIX|\Z)', re.DOTALL | re.IGNORECASE)
        
        # Extract document-level section headers
        doc_sections = set()
        for match in doc_section_pattern.finditer(toc_content):
            doc_id = match.group(1)
            doc_sections.add(doc_id)
            hierarchy["document_entries"].append({
                "id": doc_id,
                "type": "section",
                "title": f"SECTION {doc_id}"
            })
            hierarchy["stats"]["document_level"] += 1
        
        # Extract all section entries including subsections
        for match in section_pattern.finditer(toc_content):
            section_id = match.group(1).strip()
            title = match.group(2).strip()
            hierarchy["stats"]["total_entries"] += 1
            
            # Determine if this is a document-level entry or subsection
            if section_id in doc_sections or section_id.endswith("00"):  # Document level
                # Document ID is already added above, just grouping subsections
                pass
            else:
                # This is a subsection - group under parent document
                parent_doc_id = section_id[:section_id.find('.') + 3] + "00"  # Convert 10.0401 to 10.0400
                hierarchy["subsection_groups"][parent_doc_id].append({
                    "id": section_id,
                    "title": title,
                    "type": "subsection"
                })
                hierarchy["stats"]["subsections"] += 1
        
        # Extract article entries
        for match in article_pattern.finditer(toc_content):
            article_num = match.group(1).strip()
            title = match.group(2).strip()
            article_id = f"Article {article_num}"
            
            hierarchy["article_entries"].append({
                "id": article_id,
                "title": title,
                "type": "article"
            })
            hierarchy["stats"]["articles"] += 1
            hierarchy["stats"]["document_level"] += 1
            hierarchy["stats"]["total_entries"] += 1
        
        # Extract appendix entries
        for match in appendix_pattern.finditer(toc_content):
            appendix_num = match.group(1).strip()
            title = match.group(2).strip()
            appendix_id = f"Appendix {appendix_num}"
            
            hierarchy["appendix_entries"].append({
                "id": appendix_id,
                "title": title,
                "type": "appendix"
            })
            hierarchy["stats"]["appendices"] += 1
            hierarchy["stats"]["document_level"] += 1
            hierarchy["stats"]["total_entries"] += 1
        
        self.logger.info(f"Extracted TOC hierarchy:")
        self.logger.info(f"  Total entries: {hierarchy['stats']['total_entries']}")
        self.logger.info(f"  Document-level entries: {hierarchy['stats']['document_level']}")
        self.logger.info(f"  Subsections: {hierarchy['stats']['subsections']}")
        self.logger.info(f"  Articles: {hierarchy['stats']['articles']}")
        self.logger.info(f"  Appendices: {hierarchy['stats']['appendices']}")
        
        return hierarchy
    
    def _match_documents_to_files(self, hierarchy: Dict, available_files: Dict) -> Dict:
        """Match document-level entries to available files."""
        results = {
            "matched_documents": [],
            "missing_documents": [],
            "orphaned_files": []
        }
        
        # Create a flattened list of document-level entries to match
        doc_entries = []
        doc_entries.extend(hierarchy["document_entries"])
        doc_entries.extend(hierarchy["article_entries"])
        doc_entries.extend(hierarchy["appendix_entries"])
        
        # Flatten available files
        all_files = []
        for category, files in available_files.items():
            all_files.extend(files)
        
        # Set of matched files to track orphans
        matched_files = set()
        
        # Match each document entry to available files
        for doc in doc_entries:
            doc_id = doc["id"]
            doc_type = doc["type"]
            
            # Generate possible filename patterns for this document
            patterns = self._generate_filename_patterns(doc_id, doc_type)
            
            # Try to find a matching file
            matched_file = None
            for pattern in patterns:
                for file_name in all_files:
                    if pattern.lower() in file_name.lower():
                        matched_file = file_name
                        matched_files.add(file_name)
                        break
                
                if matched_file:
                    break
            
            # Record the match result
            if matched_file:
                # Count subsections contained in this document
                subsection_count = len(hierarchy["subsection_groups"].get(doc_id, []))
                
                results["matched_documents"].append({
                    "document": doc,
                    "file_name": matched_file,
                    "subsection_count": subsection_count,
                    "subsections": hierarchy["subsection_groups"].get(doc_id, [])
                })
            else:
                results["missing_documents"].append({
                    "document": doc,
                    "expected_patterns": patterns,
                    "subsection_count": len(hierarchy["subsection_groups"].get(doc_id, []))
                })
        
        # Find orphaned files
        for file_name in all_files:
            if file_name not in matched_files:
                results["orphaned_files"].append({
                    "file_name": file_name,
                    "potential_matches": self._suggest_document_matches(file_name, doc_entries)
                })
        
        self.logger.info(f"Document matching results:")
        self.logger.info(f"  Matched documents: {len(results['matched_documents'])}")
        self.logger.info(f"  Missing documents: {len(results['missing_documents'])}")
        self.logger.info(f"  Orphaned files: {len(results['orphaned_files'])}")
        
        return results
    
    def _generate_filename_patterns(self, doc_id: str, doc_type: str) -> List[str]:
        """Generate possible filename patterns for a document."""
        patterns = []
        
        if doc_type == "section":
            # For section documents (10.0400)
            patterns.extend([
                f"dc-section-{doc_id}",
                f"section-{doc_id}",
                doc_id.replace(".", "")
            ])
        
        elif doc_type == "article":
            # For articles (Article 3)
            article_num = re.search(r'\d+', doc_id)
            if article_num:
                num = article_num.group()
                patterns.extend([
                    f"dc-article-{num}",
                    f"article-{num}"
                ])
        
        elif doc_type == "appendix":
            # For appendices (Appendix 5.000)
            appendix_num = re.search(r'\d+(?:\.\d+)?', doc_id)
            if appendix_num:
                num = appendix_num.group()
                patterns.extend([
                    f"dc-appendix-{num}",
                    f"appendix-{num}"
                ])
        
        return patterns
    
    def _suggest_document_matches(self, file_name: str, doc_entries: List[Dict]) -> List[Dict]:
        """Suggest potential document matches for an orphaned file."""
        suggestions = []
        
        # Extract identifiers from filename
        section_match = re.search(r'section-(\d+\.\d{4})', file_name.lower())
        article_match = re.search(r'article-(\d+)', file_name.lower())
        appendix_match = re.search(r'appendix-(\d+)', file_name.lower())
        
        # Try to match based on extracted identifiers
        if section_match:
            section_id = section_match.group(1)
            for doc in doc_entries:
                if doc["id"] == section_id:
                    suggestions.append({
                        "id": doc["id"],
                        "type": doc["type"],
                        "confidence": "high"
                    })
        
        elif article_match:
            article_num = article_match.group(1)
            for doc in doc_entries:
                if doc["type"] == "article" and article_num in doc["id"]:
                    suggestions.append({
                        "id": doc["id"],
                        "type": doc["type"],
                        "confidence": "high"
                    })
        
        elif appendix_match:
            appendix_num = appendix_match.group(1)
            for doc in doc_entries:
                if doc["type"] == "appendix" and appendix_num in doc["id"]:
                    suggestions.append({
                        "id": doc["id"],
                        "type": doc["type"],
                        "confidence": "high"
                    })
        
        return suggestions
    
    def _generate_analysis_report(self, hierarchy: Dict, available_files: Dict, matching_results: Dict) -> Dict:
        """Generate a comprehensive analysis report."""
        # Calculate document-level alignment metrics
        total_document_entries = hierarchy["stats"]["document_level"]
        total_files = sum(len(files) for files in available_files.values())
        matched_documents = len(matching_results["matched_documents"])
        
        alignment_score = 0
        if total_document_entries > 0:
            alignment_score = (matched_documents / total_document_entries) * 100
        
        # Calculate subsection coverage
        total_subsections = hierarchy["stats"]["subsections"]
        covered_subsections = sum(match["subsection_count"] for match in matching_results["matched_documents"])
        
        subsection_coverage = 0
        if total_subsections > 0:
            subsection_coverage = (covered_subsections / total_subsections) * 100
        
        # Generate analysis report
        analysis = {
            "jurisdiction": {
                "state": self.state,
                "city": self.city
            },
            "summary": {
                "total_toc_entries": hierarchy["stats"]["total_entries"],
                "document_level_entries": total_document_entries,
                "subsection_entries": total_subsections,
                "total_available_files": total_files,
                "matched_documents": matched_documents,
                "missing_documents": len(matching_results["missing_documents"]),
                "orphaned_files": len(matching_results["orphaned_files"]),
                "document_alignment_score": round(alignment_score, 1),
                "subsection_coverage": round(subsection_coverage, 1)
            },
            "available_files": available_files,
            "document_hierarchy": hierarchy,
            "matching_results": matching_results,
            "recommendations": self._generate_recommendations(matching_results, total_document_entries)
        }
        
        return analysis
    
    def _generate_recommendations(self, matching_results: Dict, total_docs: int) -> List[str]:
        """Generate recommendations based on analysis results."""
        recommendations = []
        
        # Missing documents recommendations
        missing_count = len(matching_results["missing_documents"])
        if missing_count > 0:
            missing_percentage = (missing_count / total_docs) * 100
            if missing_percentage > 50:
                recommendations.append(f"Critical: {missing_count} documents ({missing_percentage:.1f}% of document-level entries) are missing")
            elif missing_percentage > 20:
                recommendations.append(f"Important: Locate {missing_count} missing documents ({missing_percentage:.1f}% of document-level entries)")
            else:
                recommendations.append(f"Consider adding the {missing_count} missing documents ({missing_percentage:.1f}% of document-level entries)")
        
        # Orphaned files recommendations
        orphaned_count = len(matching_results["orphaned_files"])
        if orphaned_count > 0:
            recommendations.append(f"Review {orphaned_count} orphaned files to determine if they should be added to the TOC")
        
        # Subsection validation recommendation
        recommendations.append("Validate that subsections in the TOC exist within their parent document files")
        
        # Naming convention recommendation
        if missing_count > 0 or orphaned_count > 0:
            recommendations.append("Establish consistent file naming conventions that map clearly to document IDs")
        
        return recommendations
    
    def _save_reports(self, analysis: Dict) -> None:
        """Save analysis reports to files."""
        # Save main analysis report
        analysis_file = self.output_dir / "hierarchical_document_analysis.json"
        with open(analysis_file, 'w') as f:
            json.dump(analysis, f, indent=2)
        
        # Save missing documents report
        missing_file = self.output_dir / "missing_documents.json"
        with open(missing_file, 'w') as f:
            missing_data = {
                "jurisdiction": analysis["jurisdiction"],
                "missing_documents": analysis["matching_results"]["missing_documents"],
                "total_missing": len(analysis["matching_results"]["missing_documents"]),
                "recommendations": [rec for rec in analysis["recommendations"] if "missing" in rec.lower()]
            }
            json.dump(missing_data, f, indent=2)
        
        # Save orphaned files report
        orphaned_file = self.output_dir / "orphaned_files.json"
        with open(orphaned_file, 'w') as f:
            orphaned_data = {
                "jurisdiction": analysis["jurisdiction"],
                "orphaned_files": analysis["matching_results"]["orphaned_files"],
                "total_orphaned": len(analysis["matching_results"]["orphaned_files"]),
                "recommendations": [rec for rec in analysis["recommendations"] if "orphaned" in rec.lower()]
            }
            json.dump(orphaned_data, f, indent=2)
        
        # Save summary report in markdown format
        summary_file = self.output_dir / "hierarchical_analysis_summary.md"
        with open(summary_file, 'w') as f:
            f.write(f"""# Hierarchical Document Analysis - {self.jurisdiction}

## Summary

The analysis correctly understands the hierarchical structure of municipal codes:
- Top-level sections (like "10") are logical groupings, not documents themselves
- Document-level entries (like "10.0400") should have corresponding files
- Subsections (like "10.0410") are contained within parent document files

### Key Metrics

- **Total TOC entries**: {analysis["summary"]["total_toc_entries"]}
- **Document-level entries**: {analysis["summary"]["document_level_entries"]}
- **Subsection entries**: {analysis["summary"]["subsection_entries"]}
- **Available document files**: {analysis["summary"]["total_available_files"]}
- **Successfully matched documents**: {analysis["summary"]["matched_documents"]}
- **Missing documents**: {analysis["summary"]["missing_documents"]}
- **Orphaned files**: {analysis["summary"]["orphaned_files"]}
- **Document alignment score**: {analysis["summary"]["document_alignment_score"]}%
- **Subsection coverage**: {analysis["summary"]["subsection_coverage"]}%

## Document Breakdown

""")
            
            # Add file breakdown
            for category, files in analysis["available_files"].items():
                if files:
                    f.write(f"### {category.capitalize()}\n")
                    f.write(f"- Found {len(files)} files\n")
                    for i, file in enumerate(sorted(files)[:5]):
                        f.write(f"  - {file}\n")
                    if len(files) > 5:
                        f.write(f"  - ... and {len(files) - 5} more\n")
                    f.write("\n")
            
            # Add recommendations
            if analysis["recommendations"]:
                f.write("## Recommendations\n\n")
                for rec in analysis["recommendations"]:
                    f.write(f"- {rec}\n")
        
        self.logger.info(f"Reports saved:")
        self.logger.info(f"  Analysis: {analysis_file}")
        self.logger.info(f"  Missing documents: {missing_file}")
        self.logger.info(f"  Orphaned files: {orphaned_file}")
        self.logger.info(f"  Summary: {summary_file}")

# Command-line interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze document alignment with hierarchical understanding")
    parser.add_argument("--state", required=True, help="State name")
    parser.add_argument("--city", required=True, help="City name")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Adjust logging level if verbose
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Run analysis
    registry = HierarchicalDocumentRegistry(args.state, args.city)
    analysis = registry.analyze()
    
    if analysis:
        print(f"\n✅ Analysis completed successfully!")
        print(f"Reports saved to: {registry.output_dir}\n")
        
        # Print summary
        print(f"Document Alignment Summary for {args.state}/{args.city}:")
        print(f"  Document-level entries: {analysis['summary']['document_level_entries']}")
        print(f"  Available files: {analysis['summary']['total_available_files']}")
        print(f"  Matched documents: {analysis['summary']['matched_documents']}")
        print(f"  Alignment score: {analysis['summary']['document_alignment_score']}%\n")
    else:
        print("❌ Analysis failed. Check logs for details.")
