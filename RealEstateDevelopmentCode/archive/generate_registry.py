#!/usr/bin/env python3
"""
Registry Generation Tool

This script integrates the Document Registry system with existing TOC analysis
to generate authoritative document registries from alignment analysis results.
"""

import sys
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

# Add the scripts directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from RealEstateDevelopmentCode.scripts.common.document_registry import DocumentRegistry
    from RealEstateDevelopmentCode.scripts.common.config import get_jurisdiction_dirs, ensure_jurisdiction_dirs
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Please ensure you're running from the correct directory.")
    
    # Fallback configuration
    class DocumentRegistry:
        pass


class RegistryGenerator:
    """
    Enhanced registry generator that integrates with existing TOC analysis
    and creates comprehensive document registries.
    """
    
    def __init__(self, state: str, city: str):
        """
        Initialize the registry generator.
        
        Args:
            state: State name
            city: City name
        """
        self.state = state
        self.city = city.lower()
        self.logger = logging.getLogger(f"registry_generator.{state}.{city}")
        
        # Ensure directories exist
        try:
            self.dirs = ensure_jurisdiction_dirs(state, city)
        except:
            # Fallback directory setup
            self.data_root = Path("/workspace/data")
            self.dirs = {
                "registry": self.data_root / "registry" / state / city.lower(),
                "reports": self.data_root / "reports" / state / city.lower(),
                "pdf_content": self.data_root / "pdf_content" / state / city.lower()
            }
            for dir_path in self.dirs.values():
                dir_path.mkdir(parents=True, exist_ok=True)
        
        # File paths
        self.registry_dir = self.dirs["registry"]
        self.reports_dir = self.dirs["reports"]
        
        # Enhanced TOC analysis integration
        self.enhanced_toc_analysis_file = Path("/workspace/data/analyze_toc_enhanced.py")
        self.existing_reports_dir = Path("/workspace/data/reports") / state / city.lower()
        
        # Registry files
        self.master_registry_file = self.registry_dir / "master_document_registry.json"
        self.validation_report_file = self.registry_dir / "registry_validation_report.json"
        self.integration_log_file = self.registry_dir / "integration_log.json"
    
    def integrate_with_existing_analysis(self) -> bool:
        """
        Integrate with existing TOC analysis results.
        
        Returns:
            bool: True if integration successful
        """
        try:
            self.logger.info("Integrating with existing TOC analysis...")
            
            # Check for existing analysis results
            existing_results = self._load_existing_analysis_results()
            
            if existing_results:
                self.logger.info(f"Found existing analysis results with {len(existing_results)} entries")
                return True
            else:
                self.logger.info("No existing analysis results found, proceeding with fresh analysis")
                return True
                
        except Exception as e:
            self.logger.error(f"Error integrating with existing analysis: {e}")
            return False
    
    def _load_existing_analysis_results(self) -> Optional[List[Dict[str, Any]]]:
        """Load existing TOC analysis results if available."""
        try:
            # Look for existing reports in common locations
            potential_files = [
                self.existing_reports_dir / "toc_analysis_enhanced.json",
                self.existing_reports_dir / "toc_analysis.json",
                self.reports_dir / "toc_analysis_enhanced.json",
                self.reports_dir / "toc_analysis.json"
            ]
            
            for report_file in potential_files:
                if report_file.exists():
                    self.logger.info(f"Loading existing analysis from: {report_file}")
                    with open(report_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        
                    # Extract relevant entries
                    if "toc_entries" in data:
                        return data["toc_entries"]
                    elif "analysis_results" in data:
                        return data["analysis_results"]
                    elif isinstance(data, list):
                        return data
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error loading existing analysis results: {e}")
            return None
    
    def run_enhanced_toc_analysis(self) -> bool:
        """
        Run the enhanced TOC analysis script if available.
        
        Returns:
            bool: True if analysis ran successfully
        """
        try:
            if not self.enhanced_toc_analysis_file.exists():
                self.logger.warning("Enhanced TOC analysis script not found")
                return False
            
            self.logger.info("Running enhanced TOC analysis...")
            
            # Import and run the enhanced analysis
            import subprocess
            import os
            
            # Change to the data directory
            original_dir = os.getcwd()
            os.chdir(str(self.enhanced_toc_analysis_file.parent))
            
            try:
                result = subprocess.run([
                    sys.executable, 
                    str(self.enhanced_toc_analysis_file)
                ], capture_output=True, text=True, timeout=300)
                
                if result.returncode == 0:
                    self.logger.info("Enhanced TOC analysis completed successfully")
                    return True
                else:
                    self.logger.error(f"Enhanced TOC analysis failed: {result.stderr}")
                    return False
                    
            finally:
                os.chdir(original_dir)
                
        except Exception as e:
            self.logger.error(f"Error running enhanced TOC analysis: {e}")
            return False
    
    def generate_master_registry(self, registry: DocumentRegistry) -> bool:
        """
        Generate a comprehensive master document registry.
        
        Args:
            registry: DocumentRegistry instance with analysis results
            
        Returns:
            bool: True if registry generated successfully
        """
        try:
            self.logger.info("Generating master document registry...")
            
            timestamp = datetime.now().isoformat()
            
            # Build comprehensive registry data
            master_registry = {
                "metadata": {
                    "generated_at": timestamp,
                    "generator_version": "1.0.0",
                    "jurisdiction": {
                        "state": self.state,
                        "city": self.city
                    },
                    "data_sources": [
                        "document_registry_analysis",
                        "toc_analysis_enhanced",
                        "file_system_scan"
                    ]
                },
                "statistics": {
                    "total_toc_entries": len(registry.toc_entries),
                    "total_available_files": sum(len(files) for files in registry.available_files.values()),
                    "matched_documents": len(registry.matched_documents),
                    "missing_documents": len(registry.missing_documents),
                    "orphaned_files": len(registry.orphaned_files),
                    "alignment_score": registry._calculate_alignment_score()
                },
                "document_categories": self._categorize_documents(registry),
                "verified_documents": self._build_verified_documents_list(registry),
                "issues": {
                    "missing_documents": registry.missing_documents,
                    "orphaned_files": registry.orphaned_files,
                    "recommendations": self._generate_comprehensive_recommendations(registry)
                },
                "validation": {
                    "last_validated": timestamp,
                    "validation_status": "pending",
                    "validation_checks": []
                },
                "integration_status": {
                    "toc_integration": "completed",
                    "file_system_integration": "completed",
                    "cross_reference_validation": "pending"
                }
            }
            
            # Save master registry
            with open(self.master_registry_file, 'w', encoding='utf-8') as f:
                json.dump(master_registry, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Master registry saved to: {self.master_registry_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error generating master registry: {e}")
            return False
    
    def _categorize_documents(self, registry: DocumentRegistry) -> Dict[str, Any]:
        """Categorize documents by type and status."""
        categories = {
            "by_type": {},
            "by_status": {
                "verified": 0,
                "missing": 0,
                "orphaned": 0
            },
            "by_section": {}
        }
        
        # Categorize by document type
        for entry in registry.toc_entries:
            doc_type = entry["type"]
            if doc_type not in categories["by_type"]:
                categories["by_type"][doc_type] = {
                    "total": 0,
                    "verified": 0,
                    "missing": 0,
                    "numbers": []
                }
            
            categories["by_type"][doc_type]["total"] += 1
            categories["by_type"][doc_type]["numbers"].append(entry["number"])
        
        # Update verified counts
        for match in registry.matched_documents:
            doc_type = match["toc_entry"]["type"]
            categories["by_type"][doc_type]["verified"] += 1
            categories["by_status"]["verified"] += 1
        
        # Update missing counts
        for missing in registry.missing_documents:
            doc_type = missing["toc_entry"]["type"]
            categories["by_type"][doc_type]["missing"] += 1
            categories["by_status"]["missing"] += 1
        
        # Count orphaned files
        categories["by_status"]["orphaned"] = len(registry.orphaned_files)
        
        # Categorize by section numbers (for sections)
        for entry in registry.toc_entries:
            if entry["type"] == "section":
                number = entry["number"]
                section_base = number.split('.')[0] if '.' in number else number
                
                if section_base not in categories["by_section"]:
                    categories["by_section"][section_base] = {
                        "total": 0,
                        "verified": 0,
                        "subsections": []
                    }
                
                categories["by_section"][section_base]["total"] += 1
                categories["by_section"][section_base]["subsections"].append(number)
        
        return categories
    
    def _build_verified_documents_list(self, registry: DocumentRegistry) -> List[Dict[str, Any]]:
        """Build a comprehensive list of verified documents."""
        verified_docs = []
        
        for match in registry.matched_documents:
            toc_entry = match["toc_entry"]
            
            doc = {
                "document_id": f"{toc_entry['type']}-{toc_entry['number']}",
                "type": toc_entry["type"],
                "number": toc_entry["number"],
                "title": toc_entry["title"],
                "filename": match["matched_file"],
                "match_confidence": match["match_confidence"],
                "match_method": match["match_method"],
                "toc_reference": {
                    "page": toc_entry.get("page"),
                    "section_reference": toc_entry.get("section_reference")
                },
                "file_metadata": self._extract_file_metadata(registry, match["matched_file"]),
                "verification_status": "verified",
                "last_verified": datetime.now().isoformat()
            }
            
            verified_docs.append(doc)
        
        return verified_docs
    
    def _extract_file_metadata(self, registry: DocumentRegistry, filename: str) -> Dict[str, Any]:
        """Extract metadata from the document file."""
        try:
            file_path = registry.pdf_content_dir / filename
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    metadata = data.get("metadata", {})
                    
                    return {
                        "extracted_at": metadata.get("extracted_at"),
                        "num_pages": metadata.get("num_pages"),
                        "title": metadata.get("title"),
                        "author": metadata.get("author"),
                        "creation_date": metadata.get("creation_date"),
                        "modification_date": metadata.get("modification_date")
                    }
        except:
            pass
        
        return {}
    
    def _generate_comprehensive_recommendations(self, registry: DocumentRegistry) -> List[Dict[str, Any]]:
        """Generate comprehensive recommendations for resolving issues."""
        recommendations = []
        
        # Recommendations for missing documents
        if registry.missing_documents:
            missing_by_type = {}
            for doc in registry.missing_documents:
                doc_type = doc["toc_entry"]["type"]
                missing_by_type[doc_type] = missing_by_type.get(doc_type, 0) + 1
            
            for doc_type, count in missing_by_type.items():
                recommendations.append({
                    "type": "missing_documents",
                    "priority": "high",
                    "category": doc_type,
                    "count": count,
                    "description": f"Locate or create {count} missing {doc_type} documents",
                    "action_items": [
                        f"Review TOC entries for {doc_type} documents",
                        f"Check for misfiled or differently named {doc_type} files",
                        f"Verify if {doc_type} documents are pending creation",
                        f"Update TOC if {doc_type} entries are outdated"
                    ]
                })
        
        # Recommendations for orphaned files
        if registry.orphaned_files:
            orphaned_with_matches = [f for f in registry.orphaned_files if f.get("potential_toc_matches")]
            orphaned_without_matches = [f for f in registry.orphaned_files if not f.get("potential_toc_matches")]
            
            if orphaned_with_matches:
                recommendations.append({
                    "type": "orphaned_files_with_matches",
                    "priority": "medium",
                    "category": "file_organization",
                    "count": len(orphaned_with_matches),
                    "description": f"Review {len(orphaned_with_matches)} orphaned files with potential TOC matches",
                    "action_items": [
                        "Review potential matches and verify correct associations",
                        "Rename files if needed to match TOC naming conventions",
                        "Add missing TOC entries if documents are valid",
                        "Consolidate duplicate or outdated versions"
                    ]
                })
            
            if orphaned_without_matches:
                recommendations.append({
                    "type": "orphaned_files_no_matches",
                    "priority": "low",
                    "category": "file_cleanup",
                    "count": len(orphaned_without_matches),
                    "description": f"Investigate {len(orphaned_without_matches)} orphaned files with no TOC matches",
                    "action_items": [
                        "Determine if files are outdated versions",
                        "Check if files represent new documents needing TOC entries",
                        "Archive or remove obsolete files",
                        "Review file naming conventions"
                    ]
                })
        
        # Alignment score recommendations
        alignment_score = registry._calculate_alignment_score()
        if alignment_score < 95:
            recommendations.append({
                "type": "alignment_improvement",
                "priority": "high",
                "category": "data_quality",
                "count": 1,
                "description": f"Improve overall alignment score from {alignment_score:.1f}% to 95%+",
                "action_items": [
                    "Address all missing document issues",
                    "Resolve orphaned file associations",
                    "Standardize naming conventions",
                    "Implement regular validation checks"
                ]
            })
        
        return recommendations
    
    def validate_registry(self) -> bool:
        """
        Perform validation checks on the generated registry.
        
        Returns:
            bool: True if validation passed
        """
        try:
            self.logger.info("Validating generated registry...")
            
            if not self.master_registry_file.exists():
                self.logger.error("Master registry file not found")
                return False
            
            # Load the registry
            with open(self.master_registry_file, 'r', encoding='utf-8') as f:
                registry_data = json.load(f)
            
            validation_results = {
                "validation_timestamp": datetime.now().isoformat(),
                "checks": [],
                "overall_status": "passed",
                "warnings": [],
                "errors": []
            }
            
            # Check 1: Required sections present
            required_sections = ["metadata", "statistics", "verified_documents", "issues"]
            for section in required_sections:
                if section in registry_data:
                    validation_results["checks"].append({
                        "check": f"required_section_{section}",
                        "status": "passed",
                        "message": f"Required section '{section}' is present"
                    })
                else:
                    validation_results["checks"].append({
                        "check": f"required_section_{section}",
                        "status": "failed",
                        "message": f"Required section '{section}' is missing"
                    })
                    validation_results["errors"].append(f"Missing required section: {section}")
                    validation_results["overall_status"] = "failed"
            
            # Check 2: Data consistency
            stats = registry_data.get("statistics", {})
            verified_docs = registry_data.get("verified_documents", [])
            
            if len(verified_docs) == stats.get("matched_documents", 0):
                validation_results["checks"].append({
                    "check": "verified_documents_count",
                    "status": "passed",
                    "message": "Verified documents count matches statistics"
                })
            else:
                validation_results["checks"].append({
                    "check": "verified_documents_count",
                    "status": "failed",
                    "message": "Verified documents count doesn't match statistics"
                })
                validation_results["errors"].append("Data inconsistency in verified documents count")
                validation_results["overall_status"] = "failed"
            
            # Check 3: Alignment score validation
            alignment_score = stats.get("alignment_score", 0)
            if 0 <= alignment_score <= 100:
                validation_results["checks"].append({
                    "check": "alignment_score_range",
                    "status": "passed",
                    "message": f"Alignment score {alignment_score}% is within valid range"
                })
            else:
                validation_results["checks"].append({
                    "check": "alignment_score_range",
                    "status": "failed",
                    "message": f"Alignment score {alignment_score}% is outside valid range"
                })
                validation_results["errors"].append("Invalid alignment score")
                validation_results["overall_status"] = "failed"
            
            # Save validation report
            with open(self.validation_report_file, 'w', encoding='utf-8') as f:
                json.dump(validation_results, f, indent=2, ensure_ascii=False)
            
            # Log results
            if validation_results["overall_status"] == "passed":
                self.logger.info("Registry validation passed")
                return True
            else:
                self.logger.error(f"Registry validation failed with {len(validation_results['errors'])} errors")
                for error in validation_results["errors"]:
                    self.logger.error(f"  - {error}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error during registry validation: {e}")
            return False
    
    def run_full_generation(self) -> bool:
        """
        Run the complete registry generation workflow.
        
        Returns:
            bool: True if generation completed successfully
        """
        self.logger.info(f"Starting registry generation for {self.state}/{self.city}")
        
        # Step 1: Integration with existing analysis
        if not self.integrate_with_existing_analysis():
            self.logger.error("Failed to integrate with existing analysis")
            return False
        
        # Step 2: Run Document Registry analysis
        try:
            registry = DocumentRegistry(self.state, self.city)
            if not registry.run_full_analysis():
                self.logger.error("Failed to run document registry analysis")
                return False
        except Exception as e:
            self.logger.error(f"Error creating document registry: {e}")
            return False
        
        # Step 3: Generate master registry
        if not self.generate_master_registry(registry):
            self.logger.error("Failed to generate master registry")
            return False
        
        # Step 4: Validate registry
        if not self.validate_registry():
            self.logger.error("Registry validation failed")
            return False
        
        self.logger.info("Registry generation completed successfully")
        return True


def main():
    """Main function for command-line usage."""
    parser = argparse.ArgumentParser(
        description="Registry Generation Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                           # Generate registry for Oregon/Gresham
  %(prog)s --state Oregon --city Portland  # Generate for Oregon/Portland
  %(prog)s --verbose                 # Enable verbose logging
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
    
    args = parser.parse_args()
    
    # Configure logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    try:
        # Run registry generation
        generator = RegistryGenerator(args.state, args.city)
        success = generator.run_full_generation()
        
        if success:
            print(f"\n✓ Registry generation completed successfully!")
            print(f"Master registry saved to: {generator.master_registry_file}")
            print(f"Validation report saved to: {generator.validation_report_file}")
        else:
            print("Registry generation failed!")
            return 1
        
        return 0
        
    except KeyboardInterrupt:
        print("\nRegistry generation interrupted by user.")
        return 1
    
    except Exception as e:
        print(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
