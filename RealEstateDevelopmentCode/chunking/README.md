# Municipal Document RAG System

## Overview
This system prepares municipal development code documents for AI agent consumption via the Model Context Protocol (MCP). The system is specially optimized for:

1. **Table accuracy** - Using multiple extraction methods to ensure tables are accurately captured
2. **Structure preservation** - Maintaining the hierarchical structure of development codes
3. **Efficient RAG retrieval** - Optimized chunking and metadata for municipal code context

## Components

### 1. Document Preparation (`accurate_municipal_rag.py`)
- Multi-method table extraction using Unstructured.io, Camelot, and Tabula
- Structure-preserving text chunking with LangChain
- Comprehensive metadata retention for context
- Multi-jurisdiction support with flexible directory structure

### 2. Complete System Builder (`build_rag_system.py`)
- End-to-end pipeline for processing documents
- Dependency management and installation
- Multi-jurisdiction support
- Integration with the standalone MCP server

## Installation

### Quick Installation (Recommended)
```bash
cd /workspace/RealEstateDevelopmentCode/chunking
sudo ./install_dependencies.sh
```

### Manual Installation
1. Install system dependencies:
```bash
sudo apt-get update && sudo apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    default-jre \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-eng
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

### Dependencies Explained
- **libgl1-mesa-glx**: OpenGL support for OpenCV
- **default-jre**: Java runtime for Tabula table extraction
- **poppler-utils**: PDF utilities (pdfinfo, pdftoppm, etc.)
- **tesseract-ocr**: OCR engine for scanned PDFs
- **JPype1**: Java-Python bridge for Tabula
- **camelot-py**: Advanced table extraction from PDFs
- **unstructured[all-docs]**: AI-powered document parsing

## Usage

### 1. Build the RAG System for a Jurisdiction

```bash
cd /workspace/RealEstateDevelopmentCode/chunking
python build_rag_system.py --jurisdiction="State/locality" --source="/path/to/documents"
```

Example:
```bash
python build_rag_system.py --jurisdiction="Oregon/multnomah_county" --source="/workspace/RealEstateDevelopmentCode/pdf_content/Oregon/multnomah_county"
```

This will:
- Process all documents in the specified source directory
- Extract tables and text with high accuracy
- Create optimized chunks and metadata
- Store results in `/workspace/RealEstateDevelopmentCode/rag_data/State/locality`
- Create necessary output files and stats

### 2. Integration with the MCP Server

After processing documents for a jurisdiction, the data is automatically available through the standalone MCP server:

```bash
cd /workspace/RealEstateDevelopmentCode/mcp_server
python server.py
```

The MCP server will automatically discover and load all processed jurisdictions from the `/workspace/RealEstateDevelopmentCode/rag_data/` directory.

## Adding a New Jurisdiction

1. Prepare the source documents in the appropriate directory:
   ```
   /workspace/RealEstateDevelopmentCode/pdf_content/State/locality/
   ```

2. Run the build system for the new jurisdiction:
   ```bash
   python build_rag_system.py --jurisdiction="State/locality" --source="/workspace/RealEstateDevelopmentCode/pdf_content/State/locality"
   ```

3. Restart the MCP server to load the new jurisdiction.

## MCP Server Endpoints

The MCP server provides these endpoints:

#### `search`
Find relevant chunks by keyword.

```python
response = await mcp_client.request('search', {
    'query': 'zoning requirements', 
    'limit': 5,
    'include_tables': True
})
```

#### `get_context`
Generate context for AI queries with proper formatting.

```python
response = await mcp_client.request('get_context', {
    'query': 'parking requirements for commercial buildings',
    'max_length': 2000
})
```

#### `get_document`
Retrieve all chunks for a specific document.

```python
response = await mcp_client.request('get_document', {
    'document_id': '4.01',
    'jurisdiction': 'Oregon/gresham'
})
```

#### `compare`
Compare multiple jurisdictions for the same query.

```python
response = await mcp_client.request('compare', {
    'query': 'parking requirements',
    'jurisdictions': ['Oregon/gresham', 'Oregon/multnomah_county']
})
```

#### `get_jurisdictions`
Get information about available jurisdictions.

```python
response = await mcp_client.request('get_jurisdictions', {})
```

## Dependencies

The chunking system requires several specialized packages for accurate document extraction:

- **unstructured[all-docs]**: Core document parsing
- **langchain & langchain-text-splitters**: Smart document chunking
- **camelot-py[cv]**: Precision table extraction
- **tabula-py**: Alternative table extraction
- **pandas**: Table data manipulation
- **sentence-transformers & faiss-cpu**: For vector embeddings (future enhancement)

Install all dependencies with:
```bash
pip install -r requirements.txt
```

## Output Format

The system produces several files in the jurisdiction-specific output directory:

1. `accurate_chunks.jsonl`: All text and table chunks in JSONL format for fast loading
2. `extracted_tables.json`: Table-only chunks for reference and verification
3. `accuracy_stats.json`: Processing statistics and metadata
4. `README.md`: Jurisdiction-specific documentation

## Technical Details

### Table Extraction Methods
1. **Camelot** - Used for lattice tables with grid lines
2. **Tabula** - Used for stream tables without clear boundaries
3. **Unstructured.io** - Used for general document structure and tables

### Chunk Storage
- All chunks stored in `accurate_chunks.jsonl`
- Tables stored separately in `extracted_tables.json`
- SQLite database in the MCP server for efficient querying

### System Requirements
- Python 3.8+
- RAM: 4GB+ recommended
- Storage: ~500MB for processed data

## Troubleshooting

If you encounter issues:

1. Check dependencies with `pip list | grep <package_name>`
2. Ensure source PDFs exist in `raw_pdfs/State/locality/`
3. Check logs in the terminal output

For table extraction issues, you can process specific documents:

```python
from accurate_municipal_rag import AccurateMunicipalRAG
processor = AccurateMunicipalRAG(source_dir="...", output_dir="...")
processor.process_document_with_tables("/path/to/specific_document.pdf")
```
