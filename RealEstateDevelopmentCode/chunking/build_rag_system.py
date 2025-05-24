#!/usr/bin/env python3
"""
Complete RAG System Builder v1.0
Version: 1.0
Date: May 23, 2025

Builds the complete RAG system from extracted documents
with special focus on table accuracy and document structure.
Outputs to the shared rag_data directory for use with the MCP server.
"""

import os
import sys
import logging
import asyncio
from pathlib import Path
import subprocess
import json
import time
import argparse

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("RAGSystemBuilder")

def check_dependencies():
    """Check if all required dependencies are installed"""
    
    # Required packages with correct import names
    required_packages = {
        "unstructured": "unstructured",
        "langchain": "langchain", 
        "camelot": "camelot",
        "tabula": "tabula",
        "pandas": "pandas",
        "pdfplumber": "pdfplumber"
    }
    
    missing_packages = []
    
    for package_name, import_name in required_packages.items():
        try:
            __import__(import_name)
        except ImportError:
            missing_packages.append(package_name)
    
    if missing_packages:
        logger.error("Missing required packages:")
        logger.error(f"  {', '.join(missing_packages)}")
        logger.error("Install all dependencies with:")
        logger.error("  pip install -r requirements.txt")
        return False
        
    return True

def install_dependencies():
    """Attempt to install dependencies if missing"""
    
    logger.info("Installing dependencies...")
    
    requirements_path = Path(__file__).parent / "requirements.txt"
    if not requirements_path.exists():
        logger.error(f"Requirements file not found at {requirements_path}")
        return False
    
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(requirements_path)],
            check=True
        )
        logger.info("Dependencies installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install dependencies: {e}")
        return False

def build_complete_rag_system(source_dir=None, jurisdiction=None):
    """Build the complete RAG system"""
    
    # Skip dependency check for now since we have confirmed packages are available
    logger.info("⚠️  Skipping dependency check (packages confirmed available)")
    
    # Add current directory to path to import local modules
    current_dir = Path(__file__).parent
    sys.path.insert(0, str(current_dir))
    
    # Import after dependency check
    try:
        from accurate_municipal_rag import AccurateMunicipalRAG
    except ImportError as e:
        logger.error(f"Failed to import local modules: {e}")
        return False
    
    # Set default source and jurisdiction if not provided
    if source_dir is None:
        source_dir = "/workspace/RealEstateDevelopmentCode/pdf_content/Oregon/gresham"
    if jurisdiction is None:
        jurisdiction = "Oregon/gresham"
    
    # Parse jurisdiction into parts for path construction
    jurisdiction_parts = jurisdiction.split('/')
    if len(jurisdiction_parts) != 2:
        logger.error(f"Invalid jurisdiction format: {jurisdiction}. Expected format: state/locality")
        return False
    
    state, locality = jurisdiction_parts
    
    # Set up paths
    source_path = Path(source_dir)
    rag_data_dir = Path("/workspace/RealEstateDevelopmentCode/rag_data") / state / locality
    
    logger.info("🏗️  Building Municipal RAG System...")
    logger.info(f"     Source: {source_path}")
    logger.info(f"     Jurisdiction: {jurisdiction}")
    logger.info(f"     Output: {rag_data_dir}")
    
    # Step 1: Prepare documents for RAG
    logger.info("\n📄 Step 1: Preparing documents for RAG...")
    
    preparator = AccurateMunicipalRAG(
        source_dir=str(source_path),
        output_dir=str(rag_data_dir)
    )
    
    stats = preparator.prepare_from_json_content(jurisdiction=jurisdiction)
    
    if stats['errors'] > 0:
        logger.warning(f"⚠️  Warning: {stats['errors']} errors occurred during preparation")
    
    
    # Create a README for the RAG data
    readme_content = f"""# {jurisdiction} Municipal Code RAG Data

## System Overview
- Built: {time.strftime('%Y-%m-%d %H:%M:%S')}
- Documents processed: {stats['processed']}
- Tables extracted: {stats['tables_found']}
- Text chunks: {stats['text_chunks']}

## Files
- `accurate_chunks.jsonl`: All chunks (text + tables)
- `extracted_tables.json`: Tables only
- `accuracy_stats.json`: Processing statistics

## Integration with MCP Server
This data is automatically accessible via the MCP server at:
```
http://localhost:8000/mcp
```

Example request:
```json
{{
  "method": "get_context",
  "params": {{
    "query": "parking requirements",
    "jurisdiction": "{jurisdiction}",
    "max_length": 4000
  }}
}}
```

See the MCP server documentation for more details.
"""
    
    with open(rag_data_dir / "README.md", 'w') as f:
        f.write(readme_content)
    
    logger.info("\n🎉 RAG Data Preparation Complete!")
    logger.info(f"📊 Stats:")
    logger.info(f"   - Documents processed: {stats['processed']}")
    logger.info(f"   - Tables extracted: {stats['tables_found']}")
    logger.info(f"   - Text chunks: {stats['text_chunks']}")
    logger.info(f"   - Output directory: {rag_data_dir}")
    logger.info(f"\n🚀 Ready for MCP server integration!")
    logger.info(f"\n📖 Next Steps:")
    logger.info(f"   # Start the MCP server:")
    logger.info(f"   cd /workspace/RealEstateDevelopmentCode/mcp_server")
    logger.info(f"   python server.py")
    
    return True


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Build RAG data for municipal code')
    parser.add_argument('--source', help='Source directory with JSON documents')
    parser.add_argument('--jurisdiction', help='Jurisdiction code (state/locality)')
    
    args = parser.parse_args()
    
    success = build_complete_rag_system(
        source_dir=args.source,
        jurisdiction=args.jurisdiction
    )
    
    sys.exit(0 if success else 1)