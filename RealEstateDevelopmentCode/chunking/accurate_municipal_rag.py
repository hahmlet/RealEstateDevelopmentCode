#!/usr/bin/env python3
"""
Municipal Document RAG Preparation v1.0 - Optimized for Tables & Accuracy
Version: 1.0
Date: May 23, 2025

Combines Unstructured.io + LangChain + specialized table extraction
to ensure maximum accuracy for municipal development codes, especially tables.
Updates to work with the multi-jurisdiction MCP server structure.
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import sys
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AccurateMunicipalRAG")

class AccurateMunicipalRAG:
    """High-accuracy RAG preparation optimized for municipal codes with tables"""
    
    def __init__(self, source_dir: str, output_dir: str):
        self.source_dir = Path(source_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Check for required packages
        self._check_dependencies()
        
        # Import after dependency check
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        
        # Configure for legal document accuracy
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,            # Smaller for table accuracy
            chunk_overlap=150,         # More overlap for context
            length_function=len,
            separators=["\n\n", "\n", ".", " "]
        )
    
    def _check_dependencies(self):
        """Check for all required dependencies"""
        try:
            # Primary tools
            import unstructured
            from unstructured.partition.auto import partition
            
            # Secondary processing
            import langchain
            from langchain.text_splitter import RecursiveCharacterTextSplitter
            from langchain.schema import Document
            
            # Table extraction (camelot optional)
            self.has_camelot = False
            try:
                import camelot
                self.has_camelot = True
                logger.info("Camelot available for advanced table extraction")
            except ImportError:
                logger.warning("Camelot not available - using tabula and pandas only")
                
            import tabula
            import pandas as pd
            
            logger.info("Core dependencies successfully loaded!")
            
        except ImportError as e:
            logger.error(f"Required package missing: {e}")
            logger.error("Install all dependencies with:")
            logger.error("pip install -r requirements.txt")
            sys.exit(1)
    
    def process_document_with_tables(self, pdf_path: str) -> List[Dict]:
        """Process document with high table accuracy"""
        
        # Import here to avoid load issues
        from unstructured.partition.auto import partition
        from langchain.schema import Document
        import tabula
        import pandas as pd
        
        pdf_file = Path(pdf_path)
        if not pdf_file.exists():
            logger.warning(f"PDF not found at {pdf_path}")
            return []
        
        results = []
        
        # Step 1: Extract with Unstructured (best for structure)
        logger.info(f"Processing {pdf_file.name} with Unstructured...")
        try:
            elements = partition(
                filename=str(pdf_file),
                strategy="hi_res",              # High resolution
                infer_table_structure=True,     # Critical for tables
                extract_tables=True,
                include_page_breaks=True,
                chunking_strategy="by_title",   # Respect document structure
                max_characters=1000,
                combine_text_under_n_chars=100
            )
            
            # Step 2: Separate tables from text
            text_elements = []
            table_elements = []
            
            for element in elements:
                if hasattr(element, 'category'):
                    if element.category == "Table":
                        table_elements.append(element)
                    else:
                        text_elements.append(element)
            
            # Step 3: Process tables with specialized extraction
            if table_elements:
                logger.info(f"Found {len(table_elements)} tables, extracting with high accuracy...")
                table_results = self._extract_tables_accurately(pdf_path, table_elements)
                results.extend(table_results)
            
            # Step 4: Process text content
            if text_elements:
                text_results = self._process_text_elements(text_elements, pdf_file)
                results.extend(text_results)
                
        except Exception as e:
            logger.error(f"Error in Unstructured processing: {e}")
            # Fallback to simpler parsing options
            logger.info("Falling back to simpler extraction...")
            results.extend(self._extract_with_fallback(pdf_path))
        
        return results
    
    def _extract_tables_accurately(self, pdf_path: str, table_elements: List) -> List[Dict]:
        """Extract tables with multiple methods for accuracy"""
        
        import tabula
        
        table_results = []
        
        # Method 1: Camelot (if available - best for lattice tables)
        if self.has_camelot:
            try:
                import camelot
                camelot_tables = camelot.read_pdf(pdf_path, pages='all', flavor='lattice')
                logger.info(f"Camelot extracted {len(camelot_tables)} tables")
                
                for i, table in enumerate(camelot_tables):
                    if table.accuracy > 80:  # Only high-accuracy tables
                        table_results.append({
                            "type": "table",
                            "method": "camelot_lattice",
                            "accuracy": table.accuracy,
                            "content": table.df.to_markdown(index=False),
                            "raw_data": table.df.to_dict('records'),
                            "metadata": {
                                "table_id": f"camelot_{i}",
                                "page": table.page,
                                "shape": table.df.shape,
                                "whitespace": table.whitespace
                            }
                        })
            except Exception as e:
                logger.error(f"Camelot extraction failed: {e}")
        else:
            logger.info("Camelot not available, using tabula for table extraction")
        
        # Method 2: Tabula (backup for stream tables)
        try:
            tabula_tables = tabula.read_pdf(pdf_path, pages='all', multiple_tables=True)
            logger.info(f"Tabula extracted {len(tabula_tables)} tables")
            
            for i, df in enumerate(tabula_tables):
                if not df.empty and len(df.columns) > 1:  # Valid table check
                    table_results.append({
                        "type": "table",
                        "method": "tabula",
                        "content": df.to_markdown(index=False),
                        "raw_data": df.to_dict('records'),
                        "metadata": {
                            "table_id": f"tabula_{i}",
                            "shape": df.shape,
                            "columns": list(df.columns)
                        }
                    })
        except Exception as e:
            logger.error(f"Tabula extraction failed: {e}")
        
        # Method 3: Use Unstructured's table data as fallback
        for i, element in enumerate(table_elements):
            if hasattr(element, 'metadata') and element.metadata.get('text_as_html'):
                table_results.append({
                    "type": "table",
                    "method": "unstructured",
                    "content": str(element),
                    "html": element.metadata.get('text_as_html'),
                    "metadata": {
                        "table_id": f"unstructured_{i}",
                        "element_metadata": element.metadata
                    }
                })
        
        return table_results
    
    def _process_text_elements(self, text_elements: List, pdf_file: Path) -> List[Dict]:
        """Process non-table text with structure preservation"""
        
        from langchain.schema import Document
        
        # Convert elements to text
        full_text = "\n\n".join([str(element) for element in text_elements])
        
        # Create LangChain document
        doc = Document(
            page_content=full_text,
            metadata={
                "source": str(pdf_file),
                "document_id": pdf_file.stem.replace('dc-section-', ''),
                "jurisdiction": "Oregon/Gresham",
                "content_type": "text"
            }
        )
        
        # Chunk with structure preservation
        chunks = self.text_splitter.split_documents([doc])
        
        return [{
            "type": "text",
            "content": chunk.page_content,
            "metadata": chunk.metadata
        } for chunk in chunks]
    
    def _extract_with_fallback(self, pdf_path: str) -> List[Dict]:
        """Fallback extraction when primary methods fail"""
        
        from langchain.schema import Document
        import tabula
        
        results = []
        
        # Try simple tabula extraction for tables
        try:
            tables = tabula.read_pdf(pdf_path, pages='all', multiple_tables=True)
            for i, df in enumerate(tables):
                if not df.empty:
                    results.append({
                        "type": "table",
                        "method": "tabula_fallback",
                        "content": df.to_markdown(index=False),
                        "raw_data": df.to_dict('records'),
                        "metadata": {
                            "table_id": f"fallback_{i}",
                            "source": pdf_path,
                            "extraction": "fallback"
                        }
                    })
        except Exception as e:
            logger.error(f"Fallback table extraction failed: {e}")
        
        # Still need to extract text even if table extraction failed
        try:
            import pdfplumber
            
            with pdfplumber.open(pdf_path) as pdf:
                full_text = ""
                for page in pdf.pages:
                    full_text += page.extract_text() + "\n\n"
            
            # Create document
            doc = Document(
                page_content=full_text,
                metadata={
                    "source": pdf_path,
                    "document_id": Path(pdf_path).stem.replace('dc-section-', ''),
                    "jurisdiction": "Oregon/Gresham",
                    "content_type": "text_fallback"
                }
            )
            
            # Chunk
            chunks = self.text_splitter.split_documents([doc])
            
            results.extend([{
                "type": "text",
                "content": chunk.page_content,
                "metadata": chunk.metadata
            } for chunk in chunks])
                
        except Exception as e:
            logger.error(f"Fallback text extraction failed: {e}")
        
        return results
    
    def prepare_from_json_content(self, jurisdiction: str = None) -> Dict[str, Any]:
        """Process already-extracted JSON content, looking for corresponding PDFs
        
        Args:
            jurisdiction: Optional jurisdiction in format "State/locality", defaults to detecting from paths
        """
        
        all_results = []
        stats = {"processed": 0, "tables_found": 0, "text_chunks": 0, "errors": 0}
        
        # Determine jurisdiction from paths if not provided
        if jurisdiction is None:
            # Try to infer from output path, assuming standard structure
            path_parts = self.output_dir.parts
            if len(path_parts) >= 3:
                state_idx = len(path_parts) - 2
                locality_idx = len(path_parts) - 1
                jurisdiction = f"{path_parts[state_idx]}/{path_parts[locality_idx]}"
            else:
                jurisdiction = "Oregon/gresham"  # default
        
        # Get state and locality from jurisdiction
        state, locality = jurisdiction.split('/')
        
        # Look for PDFs corresponding to JSON files
        workspace_dir = Path("/workspace/RealEstateDevelopmentCode")
        pdf_dir = workspace_dir / "raw_pdfs" / state / locality
        
        if not pdf_dir.exists():
            logger.warning(f"PDF directory not found at {pdf_dir}")
        
        for json_file in self.source_dir.glob("*.json"):
            try:
                # Find corresponding PDF
                pdf_name = json_file.stem + ".pdf"
                pdf_path = pdf_dir / pdf_name
                
                if pdf_path.exists():
                    logger.info(f"Processing {json_file.name} with corresponding PDF...")
                    doc_results = self.process_document_with_tables(str(pdf_path))
                    
                    # Ensure jurisdiction is set correctly in metadata
                    for result in doc_results:
                        result["metadata"]["jurisdiction"] = jurisdiction
                    
                    all_results.extend(doc_results)
                    
                    # Count results
                    table_count = len([r for r in doc_results if r['type'] == 'table'])
                    text_count = len([r for r in doc_results if r['type'] == 'text'])
                    
                    stats["tables_found"] += table_count
                    stats["text_chunks"] += text_count
                    
                else:
                    # Fallback to JSON content only
                    logger.info(f"No PDF found for {json_file.name}, using JSON content...")
                    json_results = self._process_json_fallback(json_file, jurisdiction)
                    all_results.extend(json_results)
                    stats["text_chunks"] += len(json_results)
                
                stats["processed"] += 1
                
            except Exception as e:
                logger.error(f"Error processing {json_file}: {e}")
                stats["errors"] += 1
        
        # Save results
        self._save_accurate_results(all_results, stats)
        return stats
    
    def _process_json_fallback(self, json_file: Path, jurisdiction: str) -> List[Dict]:
        """Fallback processing for JSON-only content
        
        Args:
            json_file: Path to the JSON file
            jurisdiction: Jurisdiction in format "State/locality"
        """
        
        from langchain.schema import Document
        
        with open(json_file, 'r') as f:
            doc_data = json.load(f)
        
        # Extract text content
        full_text = ""
        for page in doc_data.get('pages', []):
            full_text += page.get('text', '') + "\n\n"
        
        # Create document
        doc = Document(
            page_content=full_text,
            metadata={
                "source": str(json_file),
                "document_id": json_file.stem.replace('dc-section-', ''),
                "jurisdiction": jurisdiction,
                "content_type": "text_only"
            }
        )
        
        # Chunk
        chunks = self.text_splitter.split_documents([doc])
        
        return [{
            "type": "text",
            "content": chunk.page_content,
            "metadata": chunk.metadata
        } for chunk in chunks]
    
    def _save_accurate_results(self, results: List[Dict], stats: Dict):
        """Save results optimized for table and text accuracy"""
        
        # Save all chunks
        chunks_file = self.output_dir / "accurate_chunks.jsonl"
        with open(chunks_file, 'w') as f:
            for result in results:
                f.write(json.dumps(result) + '\n')
        
        # Save tables separately for reference
        tables = [r for r in results if r['type'] == 'table']
        if tables:
            tables_file = self.output_dir / "extracted_tables.json"
            with open(tables_file, 'w') as f:
                json.dump(tables, f, indent=2)
        
        # Save stats
        stats_file = self.output_dir / "accuracy_stats.json"
        with open(stats_file, 'w') as f:
            json.dump(stats, f, indent=2)
        
        logger.info(f"\n📊 Processing Complete:")
        logger.info(f"   - Documents: {stats['processed']}")
        logger.info(f"   - Tables extracted: {stats['tables_found']}")
        logger.info(f"   - Text chunks: {stats['text_chunks']}")
        logger.info(f"   - Errors: {stats['errors']}")
        logger.info(f"   - Output: {self.output_dir}")

if __name__ == "__main__":
    # Process with high accuracy for tables
    processor = AccurateMunicipalRAG(
        source_dir="/workspace/RealEstateDevelopmentCode/pdf_content/Oregon/gresham",
        output_dir="/workspace/RealEstateDevelopmentCode/rag_data_accurate/Oregon/gresham"
    )
    
    stats = processor.prepare_from_json_content()