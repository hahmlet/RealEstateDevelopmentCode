#!/usr/bin/env python3
"""
Archive and Test Script v1.0
Duplicates previous archive/test workflow with baseline comparison functionality
Version: 1.0
Date: May 23, 2025

This script provides comprehensive testing and archiving capabilities:
1. Runs full system tests
2. Compares results against baseline 1.0
3. Archives test results with timestamps
4. Generates comparison reports
"""

import json
import sys
import os
import shutil
from datetime import datetime
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, '/workspace/RealEstateDevelopmentCode/scripts')

from scripts.common.hierarchical_document_registry import create_registry_for_location
from scripts.common.config import get_default_location
from scripts.common.utils import save_json_file, load_json_file


class ArchiveAndTestRunner:
    """Comprehensive test runner with baseline comparison and archiving"""
    
    def __init__(self):
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.test_dir = Path(f"/workspace/RealEstateDevelopmentCode/archive/test_runs/{self.timestamp}")
        self.baseline_dir = Path("/workspace/RealEstateDevelopmentCode/reports/Oregon/gresham/baseline")
        self.baseline_data = None
        
        # Create test directory
        self.test_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"Archive and Test Runner v1.0")
        print(f"Test run: {self.timestamp}")
        print(f"Test directory: {self.test_dir}")
        
    def load_baseline(self):
        """Load baseline 1.0 data for comparison"""
        baseline_file = self.baseline_dir / "baseline_1.0_detailed.json"
        
        if not baseline_file.exists():
            print(f"ERROR: Baseline file not found: {baseline_file}")
            return False
            
        try:
            self.baseline_data = load_json_file(str(baseline_file))
            print(f"✓ Loaded baseline 1.0 data")
            print(f"  - Documents: {self.baseline_data['summary_metrics']['total_documents']}")
            print(f"  - Alignment: {self.baseline_data['summary_metrics']['alignment_percentage']}%")
            return True
        except Exception as e:
            print(f"ERROR loading baseline: {e}")
            return False
    
    def run_alignment_analysis(self):
        """Run alignment analysis and save results"""
        print("\n=== Running Alignment Analysis ===")
        
        try:
            # Get default location
            default_config = get_default_location()
            content_dir = str(default_config['content_dir'])
            
            # Create registry
            registry = create_registry_for_location(content_dir)
            
            # Generate alignment report
            report = registry.generate_alignment_report()
            
            # Save results
            results_file = self.test_dir / "alignment_analysis.json"
            save_json_file(report, str(results_file))
            
            print(f"✓ Alignment analysis complete")
            print(f"  - Total documents: {report['metrics']['total_documents']}")
            print(f"  - Documents with files: {report['metrics']['documents_with_files']}")
            print(f"  - Alignment percentage: {report['metrics']['alignment_percentage']}%")
            
            return report
            
        except Exception as e:
            print(f"ERROR in alignment analysis: {e}")
            return None
    
    def run_content_validation(self):
        """Run content validation and save results"""
        print("\n=== Running Content Validation ===")
        
        try:
            # Get default location  
            default_config = get_default_location()
            content_dir = str(default_config['content_dir'])
            
            # Create registry
            registry = create_registry_for_location(content_dir)
            
            # Run validation for all documents with files
            validation_results = []
            for doc_num, hierarchy in registry.document_hierarchy.items():
                if hierarchy.has_file:
                    validation = registry.validate_subsection_content(doc_num)
                    validation_results.append(validation)
            
            # Save results
            results_file = self.test_dir / "content_validation.json"
            save_json_file(validation_results, str(results_file))
            
            successful = sum(1 for result in validation_results if 'error' not in result)
            avg_percentage = sum(result.get('validation_percentage', 0) for result in validation_results if 'error' not in result) / max(successful, 1)
            
            print(f"✓ Content validation complete")
            print(f"  - Total validations: {len(validation_results)}")
            print(f"  - Successful validations: {successful}")
            print(f"  - Average validation percentage: {avg_percentage:.1f}%")
            
            return validation_results
            
        except Exception as e:
            print(f"ERROR in content validation: {e}")
            return None
    
    def compare_with_baseline(self, current_alignment, current_validation):
        """Compare current results with baseline 1.0"""
        print("\n=== Baseline Comparison ===")
        
        if not self.baseline_data or not current_alignment or not current_validation:
            print("ERROR: Missing data for comparison")
            return None
        
        # Calculate current metrics
        current_metrics = {
            'total_documents': current_alignment['metrics']['total_documents'],
            'documents_with_files': current_alignment['metrics']['documents_with_files'],
            'alignment_percentage': current_alignment['metrics']['alignment_percentage'],
            'total_validations': len(current_validation),
            'successful_validations': sum(1 for v in current_validation if 'error' not in v),
            'avg_validation_percentage': sum(v.get('validation_percentage', 0) for v in current_validation if 'error' not in v) / max(sum(1 for v in current_validation if 'error' not in v), 1)
        }
        
        # Get baseline metrics
        baseline_metrics = self.baseline_data['summary_metrics']
        
        # Calculate differences
        comparison = {
            'timestamp': self.timestamp,
            'baseline_version': '1.0',
            'current_metrics': current_metrics,
            'baseline_metrics': baseline_metrics,
            'differences': {
                'total_documents': current_metrics['total_documents'] - baseline_metrics['total_documents'],
                'documents_with_files': current_metrics['documents_with_files'] - baseline_metrics['documents_with_files'],
                'alignment_percentage': round(current_metrics['alignment_percentage'] - baseline_metrics['alignment_percentage'], 1),
                'avg_validation_percentage': round(current_metrics['avg_validation_percentage'] - 96.3, 1)  # Baseline was 96.3%
            },
            'status': 'PASS'  # Will be updated based on thresholds
        }
        
        # Determine pass/fail status
        if (comparison['differences']['alignment_percentage'] < -1.0 or 
            comparison['differences']['avg_validation_percentage'] < -5.0):
            comparison['status'] = 'FAIL'
        elif (comparison['differences']['alignment_percentage'] < 0 or 
              comparison['differences']['avg_validation_percentage'] < 0):
            comparison['status'] = 'WARN'
        
        # Save comparison
        comparison_file = self.test_dir / "baseline_comparison.json"
        save_json_file(comparison, str(comparison_file))
        
        # Print results
        print(f"Status: {comparison['status']}")
        print(f"Alignment: {current_metrics['alignment_percentage']}% (Δ{comparison['differences']['alignment_percentage']:+.1f}%)")
        print(f"Validation: {current_metrics['avg_validation_percentage']:.1f}% (Δ{comparison['differences']['avg_validation_percentage']:+.1f}%)")
        print(f"Documents: {current_metrics['total_documents']} (Δ{comparison['differences']['total_documents']:+d})")
        
        return comparison
    
    def generate_test_report(self, alignment_data, validation_data, comparison_data):
        """Generate comprehensive test report"""
        print("\n=== Generating Test Report ===")
        
        report = {
            'test_run': {
                'timestamp': self.timestamp,
                'version': '1.0',
                'status': comparison_data['status'] if comparison_data else 'UNKNOWN'
            },
            'alignment_summary': alignment_data['metrics'] if alignment_data else None,
            'validation_summary': {
                'total_validations': len(validation_data) if validation_data else 0,
                'successful_validations': sum(1 for v in validation_data if 'error' not in v) if validation_data else 0,
                'failed_validations': sum(1 for v in validation_data if 'error' in v) if validation_data else 0
            } if validation_data else None,
            'baseline_comparison': comparison_data,
            'test_files': {
                'alignment_analysis': 'alignment_analysis.json',
                'content_validation': 'content_validation.json', 
                'baseline_comparison': 'baseline_comparison.json'
            }
        }
        
        # Save comprehensive report
        report_file = self.test_dir / "test_report.json"
        save_json_file(report, str(report_file))
        
        # Generate markdown summary
        md_content = f"""# Test Run Report - {self.timestamp}

## Summary
- **Status**: {report['test_run']['status']}
- **Version**: {report['test_run']['version']}
- **Timestamp**: {self.timestamp}

## Results vs Baseline 1.0
"""
        
        if comparison_data:
            md_content += f"""
### Alignment Analysis
- **Current**: {comparison_data['current_metrics']['alignment_percentage']}%
- **Baseline**: {comparison_data['baseline_metrics']['alignment_percentage']}%
- **Difference**: {comparison_data['differences']['alignment_percentage']:+.1f}%

### Content Validation  
- **Current**: {comparison_data['current_metrics']['avg_validation_percentage']:.1f}%
- **Baseline**: 96.3%
- **Difference**: {comparison_data['differences']['avg_validation_percentage']:+.1f}%

### Documents
- **Current**: {comparison_data['current_metrics']['total_documents']}
- **Baseline**: {comparison_data['baseline_metrics']['total_documents']}
- **Difference**: {comparison_data['differences']['total_documents']:+d}
"""
        
        md_content += f"""
## Test Files Generated
- `alignment_analysis.json` - Full alignment analysis
- `content_validation.json` - Content validation results  
- `baseline_comparison.json` - Comparison with baseline 1.0
- `test_report.json` - This comprehensive report

## Test Directory
`{self.test_dir}`
"""
        
        md_file = self.test_dir / "README.md"
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        print(f"✓ Test report generated: {report_file}")
        print(f"✓ Test summary: {md_file}")
        
        return report
    
    def archive_previous_runs(self, keep_latest=5):
        """Archive and clean up old test runs"""
        print(f"\n=== Archiving Previous Runs (keep latest {keep_latest}) ===")
        
        test_runs_dir = Path("/workspace/RealEstateDevelopmentCode/archive/test_runs")
        
        if not test_runs_dir.exists():
            print("No previous test runs to archive")
            return
        
        # Get all test run directories
        test_dirs = [d for d in test_runs_dir.iterdir() if d.is_dir() and d.name != self.timestamp]
        test_dirs.sort(key=lambda x: x.name, reverse=True)
        
        # Keep only the latest N runs
        if len(test_dirs) > keep_latest:
            for old_dir in test_dirs[keep_latest:]:
                print(f"Archiving old test run: {old_dir.name}")
                shutil.rmtree(old_dir)
        
        print(f"✓ Archived old runs, kept {min(len(test_dirs), keep_latest)} recent runs")
    
    def run_full_test_suite(self):
        """Run the complete test suite with baseline comparison"""
        print("="*60)
        print("MUNICIPAL DOCUMENT REGISTRY - ARCHIVE AND TEST v1.0")
        print("="*60)
        
        # Load baseline
        if not self.load_baseline():
            return False
        
        # Run tests
        alignment_data = self.run_alignment_analysis()
        validation_data = self.run_content_validation()
        
        # Compare with baseline
        comparison_data = self.compare_with_baseline(alignment_data, validation_data)
        
        # Generate reports
        test_report = self.generate_test_report(alignment_data, validation_data, comparison_data)
        
        # Archive old runs
        self.archive_previous_runs()
        
        # Final summary
        print("\n" + "="*60)
        print(f"TEST COMPLETE - Status: {test_report['test_run']['status']}")
        print(f"Results saved to: {self.test_dir}")
        print("="*60)
        
        return test_report['test_run']['status'] in ['PASS', 'WARN']


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Archive and Test Script v1.0')
    parser.add_argument('--baseline-only', action='store_true', 
                       help='Only compare against baseline, skip running new tests')
    
    args = parser.parse_args()
    
    runner = ArchiveAndTestRunner()
    
    if args.baseline_only:
        # Load previous test results for comparison
        print("Baseline comparison mode - using most recent test results")
        # Implementation for baseline-only mode could be added here
        return
    
    # Run full test suite
    success = runner.run_full_test_suite()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
