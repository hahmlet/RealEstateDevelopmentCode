#!/usr/bin/env python3
"""
Integration bridge between the new Document Registry system and existing TOC analysis.
This script enhances the existing analyze_toc_enhanced.py functionality while maintaining
compatibility with current workflows.
"""

import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

# Add script paths for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from RealEstateDevelopmentCode.scripts.common.document_registry import DocumentRegistry
    from RealEstateDevelopmentCode.scripts.common.config import get_jurisdiction_dirs
except ImportError:
    # Fallback for direct execution
    print("Note: Running with fallback imports")


class TOCRegistryIntegrator:
    """
    Integration bridge that connects the new Document Registry system
    with existing TOC analysis functionality.
    """
    
    def __init__(self, state: str = "Oregon", city: str = "Gresham"):
        """Initialize the integrator."""
        self.state = state
        self.city = city.lower()
        self.logger = logging.getLogger(f"toc_registry_integrator.{state}.{city}")
        
        # Data directories
        self.data_root = Path("/workspace/data")
        self.pdf_content_dir = self.data_root / "pdf_content" / state / city.lower()
        self.reports_dir = self.data_root / "reports" / state / city.lower()
        self.registry_dir = self.data_root / "registry" / state / city.lower()
        
        # Ensure directories exist
        for dir_path in [self.reports_dir, self.registry_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # File paths
        self.toc_file = self.pdf_content_dir / "dc-table-of-contents.json"
        self.enhanced_analysis_file = self.data_root / "analyze_toc_enhanced.py"
        
        # Output files
        self.integrated_report_file = self.reports_dir / "integrated_toc_analysis.json"
        self.comparison_report_file = self.reports_dir / "analysis_comparison.json"
        
    def run_existing_analysis(self) -> Optional[Dict[str, Any]]:
        """
        Run the existing analyze_toc_enhanced.py script and capture results.
        
        Returns:
            Dictionary containing the analysis results, or None if failed
        """
        try:
            self.logger.info("Running existing TOC analysis...")
            
            # Check if the enhanced analysis script exists
            if not self.enhanced_analysis_file.exists():
                self.logger.warning(f"Enhanced analysis script not found: {self.enhanced_analysis_file}")
                return None
            
            # Import and run the existing analysis
            import subprocess
            import os
            
            original_dir = os.getcwd()
            os.chdir(str(self.data_root))
            
            try:
                # Run the existing script
                result = subprocess.run([
                    sys.executable, 
                    str(self.enhanced_analysis_file)
                ], capture_output=True, text=True, timeout=300)
                
                if result.returncode == 0:
                    self.logger.info("Existing analysis completed successfully")
                    
                    # Try to load the generated reports
                    return self._load_existing_analysis_results()
                else:
                    self.logger.error(f"Existing analysis failed: {result.stderr}")
                    return None
                    
            finally:
                os.chdir(original_dir)
                
        except Exception as e:
            self.logger.error(f"Error running existing analysis: {e}")
            return None
    
    def _load_existing_analysis_results(self) -> Optional[Dict[str, Any]]:
        """Load results from the existing analysis."""
        try:
            # Look for generated reports
            potential_files = [
                self.reports_dir / "toc_analysis_enhanced.json",
                self.reports_dir / "toc_analysis.json",
                self.data_root / "reports" / self.state / self.city / "toc_analysis_enhanced.json"
            ]
            
            for report_file in potential_files:
                if report_file.exists():
                    self.logger.info(f"Loading existing results from: {report_file}")
                    with open(report_file, 'r', encoding='utf-8') as f:
                        return json.load(f)
            
            # If no JSON reports found, try to parse stdout from the script
            self.logger.warning("No existing analysis JSON reports found")
            return None
            
        except Exception as e:
            self.logger.error(f"Error loading existing analysis results: {e}")
            return None
    
    def run_registry_analysis(self) -> Optional[DocumentRegistry]:
        """
        Run the new Document Registry analysis.
        
        Returns:
            DocumentRegistry instance with results, or None if failed
        """
        try:
            self.logger.info("Running Document Registry analysis...")
            
            registry = DocumentRegistry(self.state, self.city)
            success = registry.run_full_analysis()
            
            if success:
                self.logger.info("Document Registry analysis completed successfully")
                return registry
            else:
                self.logger.error("Document Registry analysis failed")
                return None
                
        except Exception as e:
            self.logger.error(f"Error running Document Registry analysis: {e}")
            return None
    
    def compare_analyses(self, existing_results: Dict[str, Any], registry: DocumentRegistry) -> Dict[str, Any]:
        """
        Compare results from existing analysis and new registry system.
        
        Args:
            existing_results: Results from existing TOC analysis
            registry: DocumentRegistry with new analysis results
            
        Returns:
            Comparison report
        """
        try:
            self.logger.info("Comparing analysis results...")
            
            comparison = {
                "comparison_timestamp": datetime.now().isoformat(),
                "jurisdiction": {"state": self.state, "city": self.city},
                "analysis_methods": {
                    "existing_analysis": {
                        "description": "Enhanced TOC analysis from analyze_toc_enhanced.py",
                        "results_available": existing_results is not None
                    },
                    "registry_analysis": {
                        "description": "Document Registry system analysis",
                        "results_available": registry is not None
                    }
                },
                "comparison_results": {}
            }
            
            if existing_results and registry:
                # Compare TOC entries count
                existing_toc_count = len(existing_results.get("toc_entries", []))
                registry_toc_count = len(registry.toc_entries)
                
                comparison["comparison_results"]["toc_entries"] = {
                    "existing_count": existing_toc_count,
                    "registry_count": registry_toc_count,
                    "difference": registry_toc_count - existing_toc_count,
                    "match": existing_toc_count == registry_toc_count
                }
                
                # Compare file counts
                existing_files = existing_results.get("available_files", {})
                registry_files = registry.available_files
                
                comparison["comparison_results"]["available_files"] = {
                    "existing": existing_files,
                    "registry": registry_files,
                    "differences": self._compare_file_lists(existing_files, registry_files)
                }
                
                # Compare matching results
                existing_matches = existing_results.get("matches", [])
                registry_matches = registry.matched_documents
                
                comparison["comparison_results"]["matches"] = {
                    "existing_count": len(existing_matches),
                    "registry_count": len(registry_matches),
                    "difference": len(registry_matches) - len(existing_matches)
                }
                
                # Compare missing documents
                existing_missing = existing_results.get("missing_documents", [])
                registry_missing = registry.missing_documents
                
                comparison["comparison_results"]["missing_documents"] = {
                    "existing_count": len(existing_missing),
                    "registry_count": len(registry_missing),
                    "difference": len(registry_missing) - len(existing_missing)
                }
                
                # Overall assessment
                comparison["assessment"] = self._assess_comparison_results(comparison["comparison_results"])
            
            return comparison
            
        except Exception as e:
            self.logger.error(f"Error comparing analyses: {e}")
            return {"error": str(e)}
    
    def _compare_file_lists(self, existing_files: Dict, registry_files: Dict) -> Dict[str, Any]:
        """Compare file lists from both analyses."""
        differences = {}
        
        # Get all categories from both analyses
        all_categories = set(existing_files.keys()) | set(registry_files.keys())
        
        for category in all_categories:
            existing_list = set(existing_files.get(category, []))
            registry_list = set(registry_files.get(category, []))
            
            differences[category] = {
                "existing_count": len(existing_list),
                "registry_count": len(registry_list),
                "only_in_existing": list(existing_list - registry_list),
                "only_in_registry": list(registry_list - existing_list),
                "common": list(existing_list & registry_list)
            }
        
        return differences
    
    def _assess_comparison_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Assess the comparison results and provide recommendations."""
        assessment = {
            "overall_consistency": "good",
            "significant_differences": [],
            "recommendations": [],
            "confidence_level": "high"
        }
        
        # Check TOC entries consistency
        toc_diff = results.get("toc_entries", {}).get("difference", 0)
        if abs(toc_diff) > 2:
            assessment["significant_differences"].append(f"TOC entries count differs by {toc_diff}")
            assessment["overall_consistency"] = "fair"
            assessment["recommendations"].append("Review TOC parsing differences between methods")
        
        # Check file detection consistency
        file_diffs = results.get("available_files", {}).get("differences", {})
        for category, diff_info in file_diffs.items():
            only_existing = len(diff_info.get("only_in_existing", []))
            only_registry = len(diff_info.get("only_in_registry", []))
            
            if only_existing > 0 or only_registry > 0:
                assessment["significant_differences"].append(
                    f"{category}: {only_existing} files only in existing, {only_registry} only in registry"
                )
        
        # Check matching consistency
        match_diff = results.get("matches", {}).get("difference", 0)
        if abs(match_diff) > 1:
            assessment["significant_differences"].append(f"Matched documents count differs by {match_diff}")
            assessment["recommendations"].append("Review matching algorithm differences")
        
        # Adjust overall assessment based on differences
        if len(assessment["significant_differences"]) > 3:
            assessment["overall_consistency"] = "poor"
            assessment["confidence_level"] = "low"
            assessment["recommendations"].append("Investigate fundamental differences between analysis methods")
        elif len(assessment["significant_differences"]) > 1:
            assessment["overall_consistency"] = "fair"
            assessment["confidence_level"] = "medium"
        
        return assessment
    
    def generate_integrated_report(self, existing_results: Optional[Dict[str, Any]], 
                                 registry: Optional[DocumentRegistry],
                                 comparison: Dict[str, Any]) -> bool:
        """
        Generate an integrated report combining both analyses.
        
        Args:
            existing_results: Results from existing analysis
            registry: DocumentRegistry results
            comparison: Comparison results
            
        Returns:
            True if report generated successfully
        """
        try:
            self.logger.info("Generating integrated report...")
            
            integrated_report = {
                "report_metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "report_type": "integrated_toc_analysis",
                    "jurisdiction": {"state": self.state, "city": self.city},
                    "integration_version": "1.0.0"
                },
                "data_sources": {
                    "existing_analysis": {
                        "available": existing_results is not None,
                        "source": "analyze_toc_enhanced.py",
                        "results": existing_results if existing_results else None
                    },
                    "registry_analysis": {
                        "available": registry is not None,
                        "source": "Document Registry system",
                        "results": self._extract_registry_summary(registry) if registry else None
                    }
                },
                "comparison_analysis": comparison,
                "recommendations": self._generate_integrated_recommendations(existing_results, registry, comparison),
                "next_steps": self._generate_next_steps(comparison)
            }
            
            # Save integrated report
            with open(self.integrated_report_file, 'w', encoding='utf-8') as f:
                json.dump(integrated_report, f, indent=2, ensure_ascii=False)
            
            # Save comparison report separately
            with open(self.comparison_report_file, 'w', encoding='utf-8') as f:
                json.dump(comparison, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Integrated report saved to: {self.integrated_report_file}")
            self.logger.info(f"Comparison report saved to: {self.comparison_report_file}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error generating integrated report: {e}")
            return False
    
    def _extract_registry_summary(self, registry: DocumentRegistry) -> Dict[str, Any]:
        """Extract summary information from registry analysis."""
        return {
            "toc_entries": len(registry.toc_entries),
            "available_files": registry.available_files,
            "matched_documents": len(registry.matched_documents),
            "missing_documents": len(registry.missing_documents),
            "orphaned_files": len(registry.orphaned_files),
            "alignment_score": registry._calculate_alignment_score()
        }
    
    def _generate_integrated_recommendations(self, existing_results: Optional[Dict], 
                                           registry: Optional[DocumentRegistry],
                                           comparison: Dict) -> List[Dict[str, Any]]:
        """Generate recommendations based on integrated analysis."""
        recommendations = []
        
        # Assessment-based recommendations
        assessment = comparison.get("assessment", {})
        consistency = assessment.get("overall_consistency", "unknown")
        
        if consistency == "poor":
            recommendations.append({
                "priority": "high",
                "category": "methodology_review",
                "title": "Review Analysis Methodology Differences",
                "description": "Significant differences found between analysis methods",
                "actions": [
                    "Compare TOC parsing algorithms",
                    "Review file detection patterns",
                    "Verify document matching criteria",
                    "Standardize analysis approaches"
                ]
            })
        
        # Registry-specific recommendations
        if registry:
            if registry.missing_documents:
                recommendations.append({
                    "priority": "high",
                    "category": "missing_documents",
                    "title": f"Address {len(registry.missing_documents)} Missing Documents",
                    "description": "Documents referenced in TOC but not found in file system",
                    "actions": [
                        "Verify document naming conventions",
                        "Check for misfiled documents",
                        "Confirm if documents are pending creation",
                        "Update TOC if entries are outdated"
                    ]
                })
            
            if registry.orphaned_files:
                recommendations.append({
                    "priority": "medium",
                    "category": "orphaned_files",
                    "title": f"Review {len(registry.orphaned_files)} Orphaned Files",
                    "description": "Files found without corresponding TOC entries",
                    "actions": [
                        "Determine if files should be added to TOC",
                        "Check for outdated or duplicate versions",
                        "Verify file naming accuracy",
                        "Archive or remove obsolete files"
                    ]
                })
        
        # Integration recommendations
        recommendations.append({
            "priority": "medium",
            "category": "system_integration",
            "title": "Implement Integrated Analysis Workflow",
            "description": "Combine strengths of both analysis methods",
            "actions": [
                "Use Document Registry for systematic alignment analysis",
                "Leverage existing analysis for detailed parsing",
                "Implement regular cross-validation",
                "Create unified reporting format"
            ]
        })
        
        return recommendations
    
    def _generate_next_steps(self, comparison: Dict) -> List[str]:
        """Generate next steps based on comparison results."""
        next_steps = []
        
        assessment = comparison.get("assessment", {})
        confidence = assessment.get("confidence_level", "unknown")
        
        if confidence == "high":
            next_steps.extend([
                "Proceed with Document Registry system for ongoing analysis",
                "Implement automated alignment monitoring",
                "Create regular validation schedules"
            ])
        elif confidence == "medium":
            next_steps.extend([
                "Investigate specific differences identified",
                "Run additional validation tests",
                "Consider hybrid approach using both methods"
            ])
        else:
            next_steps.extend([
                "Conduct detailed review of analysis methodologies",
                "Verify data source integrity",
                "Consider re-implementing analysis with unified approach"
            ])
        
        # Always include these steps
        next_steps.extend([
            "Review and act on specific recommendations",
            "Update documentation with findings",
            "Plan implementation of identified improvements"
        ])
        
        return next_steps
    
    def run_full_integration(self) -> bool:
        """
        Run the complete integration workflow.
        
        Returns:
            True if integration completed successfully
        """
        self.logger.info(f"Starting TOC/Registry integration for {self.state}/{self.city}")
        
        # Step 1: Run existing analysis
        existing_results = self.run_existing_analysis()
        
        # Step 2: Run registry analysis
        registry = self.run_registry_analysis()
        
        # Step 3: Compare analyses
        comparison = self.compare_analyses(existing_results, registry)
        
        # Step 4: Generate integrated report
        success = self.generate_integrated_report(existing_results, registry, comparison)
        
        if success:
            self.logger.info("Integration completed successfully")
            self._print_integration_summary(existing_results, registry, comparison)
        else:
            self.logger.error("Integration failed")
        
        return success
    
    def _print_integration_summary(self, existing_results: Optional[Dict], 
                                 registry: Optional[DocumentRegistry], 
                                 comparison: Dict) -> None:
        """Print a summary of the integration results."""
        print("\n" + "="*60)
        print("TOC/REGISTRY INTEGRATION SUMMARY")
        print("="*60)
        
        print(f"\nJurisdiction: {self.state} / {self.city.title()}")
        
        print(f"\nAnalysis Results:")
        if existing_results:
            print(f"  ✓ Existing analysis completed")
            print(f"    TOC entries: {len(existing_results.get('toc_entries', []))}")
        else:
            print(f"  ✗ Existing analysis failed or unavailable")
        
        if registry:
            print(f"  ✓ Registry analysis completed")
            print(f"    TOC entries: {len(registry.toc_entries)}")
            print(f"    Matched documents: {len(registry.matched_documents)}")
            print(f"    Missing documents: {len(registry.missing_documents)}")
            print(f"    Orphaned files: {len(registry.orphaned_files)}")
            print(f"    Alignment score: {registry._calculate_alignment_score():.1f}%")
        else:
            print(f"  ✗ Registry analysis failed")
        
        assessment = comparison.get("assessment", {})
        if assessment:
            print(f"\nComparison Assessment:")
            print(f"  Overall consistency: {assessment.get('overall_consistency', 'unknown')}")
            print(f"  Confidence level: {assessment.get('confidence_level', 'unknown')}")
            
            differences = assessment.get("significant_differences", [])
            if differences:
                print(f"  Significant differences: {len(differences)}")
                for diff in differences[:3]:  # Show first 3
                    print(f"    - {diff}")
                if len(differences) > 3:
                    print(f"    ... and {len(differences) - 3} more")
        
        print(f"\nReports generated:")
        print(f"  Integrated report: {self.integrated_report_file}")
        print(f"  Comparison report: {self.comparison_report_file}")


def main():
    """Main function for command-line usage."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="TOC/Registry Integration Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                           # Integrate for Oregon/Gresham
  %(prog)s --state Oregon --city Portland  # Integrate for Oregon/Portland
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
        # Run integration
        integrator = TOCRegistryIntegrator(args.state, args.city)
        success = integrator.run_full_integration()
        
        if success:
            print(f"\n✓ Integration completed successfully!")
        else:
            print("Integration failed!")
            return 1
        
        return 0
        
    except KeyboardInterrupt:
        print("\nIntegration interrupted by user.")
        return 1
    
    except Exception as e:
        print(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
