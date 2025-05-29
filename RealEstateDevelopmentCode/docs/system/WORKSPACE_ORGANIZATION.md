# Workspace Organization

## Directory Structure

This document describes the organized directory structure of the Real Estate Development Code analysis system.

### Production Directories

- **`production_pdfs/`** - Production PDF documents (formerly `raw_pdfs/`)
  - `Oregon/gresham/` - Gresham municipal PDFs for processing

- **`production_rag_data/`** - Production RAG system data (consolidated from `rag_data*` folders)
  - `Oregon/gresham/` - Processed chunks, tables, and embeddings for Gresham

### Development & Testing

- **`test_scripts/`** - All test and demonstration scripts
  - `test_enhanced_extraction.py` - Tests enhanced three-phase table extraction
  - `test_toc_parsing.py` - Tests TOC structure loading (131 document entries)
  - `test_enhanced_single_pdf.py` - Tests single PDF enhanced extraction
    - `test_toc_parsing.py` - Tests TOC structure loading (131 document entries)
  - `test_toc_workflow.py` - Tests complete TOC validation workflow
  - `test_full_integration.py` - Tests full TOC+extraction integration
  - `test_results.py` - Quick results viewer for processed documents
  - `demo_enhanced_phases.py` - Demo of three-phase extraction
  - `test_phases_demo.py` - Tests using existing Section 4.0100 data
  - `test_simple_phases.py` - Simple verification test for phases

- **`test_data/`** - Organized test data structure
  - `results/` - Test execution results
  - `samples/` - Sample data for testing
  - `temp/` - Temporary test files

- **`test_pdfs/`** - PDF files for testing purposes

### Archive

- **`archive/`** - Archived components and historical data
  - `test_results_archive/` - Archived test results from previous system iterations
  - `rag_data_backup/` - Backup of previous RAG data folders
  - Other archived scripts and analyses

### Documentation

- **`docs/`** - Organized documentation
  - `system/` - System documentation and README files
  - `reports/` - Analysis reports and validation summaries
  - `municipality_reports/` - Municipality-specific analysis reports
    - `Oregon/gresham/` - Gresham municipal code analysis reports

### Logs

- **`logs/`** - System log files
  - `crawler_output.log` - PDF crawler execution logs

### Core Components

- **`chunking/`** - RAG system implementation and table extraction
- **`rag_assessment/`** - Quality assessment tools for RAG accuracy
- **`mcp_server/`** - Model Context Protocol server implementation
- **`GUI/`** - Graphical user interface components
- **`scripts/`** - Utility scripts and configuration
  - `crawl_gresham_pdfs.py` - PDF crawler script
  - `document_registry_cli.py` - Document registry CLI tool
  - `archive_and_test.py` - Archive and testing utilities
- **`pdf_content/`** - Extracted content from PDFs

## Path Updates

All code has been updated to use the new directory structure:

### Production Data Paths
- `raw_pdfs/` → `production_pdfs/`
- `rag_data*/` → `production_rag_data/`

### Test Data Paths
- `test_output/` → `test_data/results/`

### Code Files Updated
- Configuration files (`scripts/common/config.py`)
- Crawler scripts (`scripts/crawl_gresham_pdfs.py`)
- CLI tools (`scripts/document_registry_cli.py`)
- Utility scripts (`scripts/archive_and_test.py`)
- All test scripts in `test_scripts/`
- RAG assessment tools in `rag_assessment/`
- Chunking components in `chunking/`

## Benefits

1. **Clear Separation**: Production vs test data clearly separated
2. **Consolidated Storage**: RAG data consolidated from multiple scattered folders
3. **Organized Testing**: All test scripts centralized with descriptive comments
4. **Archived History**: Previous work preserved in archive for reference
5. **Maintainability**: Easier to understand and maintain the codebase structure
6. **Organized Documentation**: Documentation centralized in docs/ directory
7. **Centralized Utilities**: Scripts and tools organized in scripts/ directory

## Usage

To run the system:
1. Production data is in `production_pdfs/` and `production_rag_data/`
2. Test scripts are in `test_scripts/` with clear descriptions
3. Test results are written to `test_data/results/`
4. Utility scripts are in `scripts/` directory
5. Documentation is organized in `docs/` directory
6. Historical data is preserved in `archive/`
