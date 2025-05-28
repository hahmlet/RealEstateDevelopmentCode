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
import re
import time
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
        """Enhanced table extraction using Unstructured.io's latest features and multiple methods"""
        
        import tabula
        
        table_results = []
        
        # Phase 1: Enhanced Unstructured.io extraction with advanced parameters
        enhanced_tables = self._extract_tables_with_unstructured_advanced(pdf_path)
        if enhanced_tables:
            logger.info(f"Enhanced Unstructured extraction found {len(enhanced_tables)} tables")
            table_results.extend(enhanced_tables)
        
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
                                "whitespace": table.whitespace,
                                "coordinates": None  # Camelot doesn't provide coordinates
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
                            "columns": list(df.columns),
                            "coordinates": None  # Tabula doesn't provide coordinates
                        }
                    })
        except Exception as e:
            logger.error(f"Tabula extraction failed: {e}")
        
        # Method 3: Process original Unstructured table elements with coordinate awareness
        for i, element in enumerate(table_elements):
            if hasattr(element, 'metadata'):
                # Phase 2: Extract coordinates for spatial table reconstruction
                coordinates = self._extract_element_coordinates(element)
                
                table_result = {
                    "type": "table",
                    "method": "unstructured_original",
                    "content": str(element),
                    "metadata": {
                        "table_id": f"unstructured_{i}",
                        "element_metadata": element.metadata,
                        "coordinates": coordinates
                    }
                }
                
                # Add HTML if available
                if element.metadata.get('text_as_html'):
                    table_result["html"] = element.metadata.get('text_as_html')
                
                # Phase 2: Attempt spatial reconstruction if coordinates available
                if coordinates:
                    try:
                        reconstructed_table = self._reconstruct_spatial_table(element, coordinates)
                        if reconstructed_table:
                            table_result["content"] = reconstructed_table
                            table_result["method"] = "unstructured_spatial"
                    except Exception as e:
                        logger.warning(f"Spatial reconstruction failed for table {i}: {e}")
                
                table_results.append(table_result)
        
        # Phase 3: Enhanced validation and quality scoring
        validated_tables = self._validate_and_score_tables(table_results)
        
        # Sort by quality score (highest first)
        validated_tables.sort(key=lambda x: x.get("quality_metrics", {}).get("overall_score", 0), reverse=True)
        
        logger.info(f"Table extraction completed: {len(validated_tables)} tables extracted and validated")
        for i, table in enumerate(validated_tables[:3]):  # Log top 3 tables
            score = table.get("quality_metrics", {}).get("overall_score", 0)
            method = table.get("method", "unknown")
            logger.info(f"  Table {i+1}: {method} (score: {score:.2f})")
        
        return validated_tables
    
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
                # Prioritize JSON content (much more accurate than PDF parsing)
                logger.info(f"Processing {json_file.name} using structured JSON content...")
                json_results = self._process_json_primary(json_file, jurisdiction)
                all_results.extend(json_results)
                
                # Count results
                table_count = len([r for r in json_results if r['type'] == 'table'])
                text_count = len([r for r in json_results if r['type'] == 'text'])
                
                stats["tables_found"] += table_count
                stats["text_chunks"] += text_count
                
                # Optional: If PDF exists and we want additional table extraction
                pdf_name = json_file.stem + ".pdf"
                pdf_path = pdf_dir / pdf_name
                
                if pdf_path.exists() and table_count == 0:
                    # Only use PDF for table extraction if JSON had no tables
                    logger.info(f"Supplementing with PDF table extraction for {json_file.name}...")
                    try:
                        pdf_results = self.process_document_with_tables(str(pdf_path))
                        pdf_tables = [r for r in pdf_results if r['type'] == 'table']
                        
                        if pdf_tables:
                            # Update metadata for PDF tables
                            for table in pdf_tables:
                                table["metadata"]["jurisdiction"] = jurisdiction
                                table["metadata"]["source_supplement"] = "pdf_tables"
                            
                            all_results.extend(pdf_tables)
                            stats["tables_found"] += len(pdf_tables)
                            logger.info(f"Added {len(pdf_tables)} tables from PDF")
                        else:
                            logger.info(f"No additional tables found in PDF for {json_file.name}")
                    except Exception as e:
                        logger.warning(f"PDF table extraction failed for {json_file.name}: {e}")
                        logger.info("Continuing with JSON-only processing...")
                elif pdf_path.exists():
                    logger.debug(f"Skipping PDF supplement for {json_file.name} (JSON already has {table_count} tables)")
                
                stats["processed"] += 1
                
            except Exception as e:
                logger.error(f"Error processing {json_file}: {e}")
                stats["errors"] += 1
        
        # Save results
        self._save_accurate_results(all_results, stats)
        return stats
    
    def _process_json_primary(self, json_file: Path, jurisdiction: str) -> List[Dict]:
        """Process JSON content as primary source with timeout protection"""
        
        from langchain.schema import Document
        import time
        
        start_time = time.time()
        max_document_time = 600  # 10 minute timeout per document (adjustable)
        
        with open(json_file, 'r') as f:
            doc_data = json.load(f)
        
        results = []
        
        # Extract structured content from JSON (much richer than PDF)
        document_title = doc_data.get('metadata', {}).get('title', json_file.stem)
        document_id = json_file.stem.replace('dc-section-', '')
        
        # Track progress statistics for this document
        page_count = len(doc_data.get('pages', []))
        logger.info(f"Processing document {document_title} ({page_count} pages)")
        
        # Process each page with its structured content
        for page_num, page in enumerate(doc_data.get('pages', [])):
            # Check for document timeout
            if time.time() - start_time > max_document_time:
                logger.warning(f"Document timeout reached for {json_file.name} after {page_num+1}/{page_count} pages")
                break
                
            # Log progress for large documents
            if page_count > 10 and page_num % 5 == 0:
                logger.info(f"  Processing page {page_num+1}/{page_count} of {json_file.name}")
                
            page_text = page.get('text', '')
            
            # Extract tables from JSON structured tables array
            if 'tables' in page and page['tables']:
                for table_idx, table in enumerate(page['tables']):
                    results.append({
                        "type": "table",
                        "method": "json_structured",
                        "content": self._format_json_table(table),
                        "raw_data": table,
                        "metadata": {
                            "source": str(json_file),
                            "document_id": document_id,
                            "document_title": document_title,
                            "jurisdiction": jurisdiction,
                            "page": page_num + 1,
                            "table_id": f"json_p{page_num}_t{table_idx}",
                            "content_type": "structured_table"
                        }
                    })
            
            # Only extract tables from text if text is not excessively large
            if len(page_text) < 100000:  # Skip massive pages to prevent hanging
                try:
                    # Set timeout just for table extraction
                    page_start_time = time.time()
                    max_page_table_time = 60  # 1 minute per page for table extraction
                    
                    # Skip the most complex pattern (pattern 5) for pages over 20KB
                    if len(page_text) > 20000:
                        logger.info(f"Using simplified pattern set for large page ({len(page_text)/1000:.1f}KB)")
                        embedded_tables = self._extract_tables_from_text_simple(page_text)
                    else:
                        embedded_tables = self._extract_tables_from_text(page_text)
                    
                    # Check if table extraction took too long
                    if time.time() - page_start_time > max_page_table_time:
                        logger.warning(f"Table extraction timeout on page {page_num+1} of {json_file.name}")
                    
                    for table_idx, table_content in enumerate(embedded_tables):
                        results.append({
                            "type": "table",
                            "method": "text_embedded",
                            "content": table_content,
                            "raw_data": {"text_table": table_content},
                            "metadata": {
                                "source": str(json_file),
                                "document_id": document_id,
                                "document_title": document_title,
                                "jurisdiction": jurisdiction,
                                "page": page_num + 1,
                                "table_id": f"text_p{page_num}_t{table_idx}",
                                "content_type": "text_embedded_table"
                            }
                        })
                except Exception as e:
                    logger.warning(f"Table extraction error on page {page_num+1} of {json_file.name}: {e}")
            else:
                logger.warning(f"Skipping table extraction for oversized page {page_num+1} ({len(page_text)/1000:.1f}KB)")
            
            # Process text content if substantial
            if page_text.strip() and len(page_text.strip()) > 50:
                # Create document for this page
                doc = Document(
                    page_content=page_text,
                    metadata={
                        "source": str(json_file),
                        "document_id": document_id,
                        "document_title": document_title,
                        "jurisdiction": jurisdiction,
                        "page": page_num + 1,
                        "content_type": "structured_text"
                    }
                )
                
                # Chunk the page content
                chunks = self.text_splitter.split_documents([doc])
                
                for chunk in chunks:
                    results.append({
                        "type": "text",
                        "content": chunk.page_content,
                        "metadata": chunk.metadata
                    })
        
        processing_time = time.time() - start_time
        logger.info(f"Completed {json_file.name} in {processing_time:.1f}s ({len(results)} results)")
        return results
    
    def _extract_tables_from_text(self, text: str) -> List[str]:
        """Extract table-like structures from text content with improved formatting and performance"""
        import re
        import time
        
        tables = []
        start_time = time.time()
        
        # Optimized patterns with bounded repetition and non-greedy quantifiers to prevent catastrophic backtracking
        table_patterns = [
            # Pattern for fee/permit tables - bounded repetition and non-greedy
            r'((?:Type\s+[IVX]+[^$\n]*?\$[0-9,]+[^\n]*?\n){2,8})',
            # Pattern for dimensional tables - bounded and non-greedy
            r'((?:[A-Za-z\s]+:\s*[0-9]+\s*(?:feet|ft|inches|in|%)[^\n]*?\n){2,8})',
            # Pattern for zoning/use tables - bounded and non-greedy  
            r'((?:[A-Z][A-Za-z\s]+\s+(?:Permitted|Conditional|Prohibited)[^\n]*?\n){2,8})',
            # Pattern for parking/space requirements - bounded and non-greedy
            r'((?:[A-Za-z\s]+\s+[0-9]+\s+space[s]?[^\n]*?\n){2,8})',
            # Pattern for street classification tables - more specific end conditions and non-greedy
            r'STREET CLASS\s+PARKING\s+PAVEMENT WIDTH[^\n]*?\n(?:[^\n]+?\n){1,15}?(?=\n\n|\n[0-9]+\.|\nE\.|\Z)',
            # Pattern for municipal code table with P, NP, SUR, L abbreviations (like uses tables)
            r'(?:USES\s+|Uses\s+|Table\s+\d+\.\d+\s*:\s*Permitted\s+Uses)(?:[A-Z0-9-]+\s+){3,10}\n(?:[A-Za-z][A-Za-z\s\d\/\(\)]+\n?(?:[A-Za-z\s\d\/\(\)]+)?\s+(?:P|NP|SUR|L\d*)\s+(?:P|NP|SUR|L\d*)\s+(?:P|NP|SUR|L\d*)[^\n]*\n){3,}',
            # Simplified generic structured data pattern - more constrained to avoid timeouts
            r'([A-Z][A-Za-z]{2,20}\s+[A-Za-z0-9]{2,20}\s+[A-Za-z0-9]{2,20}[^\n]*\n)(?:[A-Z][A-Za-z]{2,20}\s+[A-Za-z0-9]{2,20}\s+[A-Za-z0-9]{2,20}[^\n]*\n){2,5}'
        ]
        
        # Process text in manageable chunks if very large
        text_length = len(text)
        
        if text_length > 30000:  # Only chunk very large text
            chunk_size = 15000
            overlap = 1000  # Overlap to catch tables at chunk boundaries
            
            for start in range(0, text_length, chunk_size - overlap):
                end = min(start + chunk_size, text_length)
                chunk = text[start:end]
                
                # Process each pattern with timeout protection
                for pattern_idx, pattern in enumerate(table_patterns):
                    try:
                        # Set a timeout per pattern to prevent excessive processing
                        pattern_start = time.time()
                        pattern_timeout = 15  # 15 seconds max per pattern
                        
                        # Use re.finditer with timeout check
                        matches = re.finditer(pattern, chunk, re.MULTILINE | re.IGNORECASE | re.DOTALL)
                        
                        for match in matches:
                            # Check for timeout on each iteration
                            if time.time() - pattern_start > pattern_timeout:
                                logger.warning(f"Pattern {pattern_idx} timeout, moving to next pattern")
                                break
                                
                            table_text = match.group(0).strip()
                            if 150 < len(table_text) < 5000:  # Only substantial tables with reasonable size
                                # Enhanced table formatting
                                formatted_table = self._format_extracted_table(table_text)
                                if formatted_table and formatted_table not in tables:
                                    tables.append(formatted_table)
                                    
                                # Limit matches per pattern to avoid excessive extraction
                                if len(tables) > 20:  # Cap total tables to prevent memory issues
                                    break
                    except Exception as e:
                        logger.warning(f"Error processing pattern {pattern_idx}: {e}")
                        continue
        else:
            # For normal sized text, process normally but with timeout protection
            for pattern_idx, pattern in enumerate(table_patterns):
                try:
                    # Set a reasonable timeout
                    pattern_start = time.time()
                    pattern_timeout = 5  # Reduced to 5 seconds max per pattern
                    
                    matches = re.finditer(pattern, text, re.MULTILINE | re.IGNORECASE | re.DOTALL)
                    
                    for match in matches:
                        # Check for timeout more frequently
                        if time.time() - pattern_start > pattern_timeout:
                            logger.warning(f"Pattern {pattern_idx} timeout, moving to next pattern")
                            break
                            
                        table_text = match.group(0).strip()
                        if 150 < len(table_text) < 5000:  # Only substantial tables
                            # Enhanced table formatting
                            formatted_table = self._format_extracted_table(table_text)
                            if formatted_table and formatted_table not in tables:
                                tables.append(formatted_table)
                except Exception as e:
                    logger.warning(f"Error processing pattern {pattern_idx}: {e}")
                    continue
        
        logger.debug(f"Table extraction took {time.time() - start_time:.2f}s, found {len(tables)} tables")
        return tables[:15]  # Limit total tables per document to prevent memory issues

    def _extract_tables_from_text_simple(self, text: str) -> List[str]:
        """Extract table-like structures from text content with simpler patterns for large pages"""
        import re
        import time
        
        tables = []
        start_time = time.time()
        
        # Simpler patterns for large pages - skipping the complex generic pattern
        simple_patterns = [
            # Pattern for fee/permit tables - bounded repetition and non-greedy
            r'((?:Type\s+[IVX]+[^$\n]*?\$[0-9,]+[^\n]*?\n){2,8})',
            # Pattern for dimensional tables - bounded and non-greedy
            r'((?:[A-Za-z\s]+:\s*[0-9]+\s*(?:feet|ft|inches|in|%)[^\n]*?\n){2,8})',
            # Pattern for zoning/use tables - bounded and non-greedy  
            r'((?:[A-Z][A-Za-z\s]+\s+(?:Permitted|Conditional|Prohibited)[^\n]*?\n){2,8})',
            # Pattern for parking/space requirements - bounded and non-greedy
            r'((?:[A-Za-z\s]+\s+[0-9]+\s+space[s]?[^\n]*?\n){2,8})',
            # Pattern for street classification tables - more specific end conditions and non-greedy
            r'STREET CLASS\s+PARKING\s+PAVEMENT WIDTH[^\n]*?\n(?:[^\n]+?\n){1,15}?(?=\n\n|\n[0-9]+\.|\nE\.|\Z)',
            # Pattern for municipal code table with P, NP, SUR, L abbreviations (like uses tables)
            r'(?:USES\s+|Uses\s+|Table\s+\d+\.\d+\s*:\s*Permitted\s+Uses)(?:[A-Z0-9-]+\s+){3,10}\n(?:[A-Za-z][A-Za-z\s\d\/\(\)]+\n?(?:[A-Za-z\s\d\/\(\)]+)?\s+(?:P|NP|SUR|L\d*)\s+(?:P|NP|SUR|L\d*)\s+(?:P|NP|SUR|L\d*)[^\n]*\n){3,}'
            # Generic pattern intentionally omitted for large pages
        ]
        
        # Process text with very strict timeouts for large pages
        for pattern_idx, pattern in enumerate(simple_patterns):
            try:
                # Even shorter timeout for large pages
                pattern_start = time.time()
                pattern_timeout = 3  # 3 seconds max per pattern for large pages
                
                matches = re.finditer(pattern, text, re.MULTILINE | re.IGNORECASE | re.DOTALL)
                
                for match in matches:
                    # Check for timeout more aggressively
                    if time.time() - pattern_start > pattern_timeout:
                        logger.warning(f"Pattern {pattern_idx} timeout on large page, skipping")
                        break
                        
                    table_text = match.group(0).strip()
                    if 150 < len(table_text) < 3000:  # Stricter size bounds for large pages
                        # Enhanced table formatting
                        formatted_table = self._format_extracted_table(table_text)
                        if formatted_table and formatted_table not in tables:
                            tables.append(formatted_table)
                            
                        # Limit matches per pattern more aggressively
                        if len(tables) > 5:  # Take just the first few tables per pattern
                            break
            except Exception as e:
                logger.warning(f"Error processing pattern {pattern_idx} on large page: {e}")
                continue
        
        logger.debug(f"Simple table extraction took {time.time() - start_time:.2f}s, found {len(tables)} tables")
        return tables[:10]  # Stricter limit for large pages

    def _format_extracted_table(self, table_text: str) -> str:
        """Format extracted table text into proper markdown with improved structure"""
        
        lines = [line.strip() for line in table_text.split('\n') if line.strip()]
        if len(lines) < 3:
            return None
            
        # Detect table type and apply appropriate formatting
        
        # Fee table detection (Type I, Type II, etc.)
        if any('Type ' in line and '$' in line for line in lines):
            return self._format_fee_table(lines)
            
        # Street class table detection
        if 'STREET CLASS' in table_text.upper() and 'PARKING' in table_text.upper():
            return self._format_street_class_table(table_text)
            
        # Municipal code table with P, NP, SUR, L abbreviations
        if (re.search(r'(?:USES|Uses|Table\s+\d+\.\d+\s*:\s*Permitted\s+Uses)', table_text) and 
            re.search(r'\b(P|NP|SUR|L\d*)\b', table_text)):
            return self._format_abbreviated_use_table(table_text)
            
        # Use/zoning table detection
        if any(word in line for line in lines for word in ['Permitted', 'Conditional', 'Prohibited']):
            return self._format_use_table(lines)
            
        # Dimensional table detection (feet, inches, etc.)
        if any(unit in line for line in lines for unit in ['feet', 'ft', 'inches', 'in', '%']):
            return self._format_dimensional_table(lines)
            
        # Generic three-column table format
        return self._format_generic_table(lines)

    def _format_fee_table(self, lines: List[str]) -> str:
        """Format fee tables with Type/Description/Fee structure"""
        md_table = "| Application Type | Description | Fee |\n"
        md_table += "| --- | --- | --- |\n"
        
        for line in lines:
            if 'Type ' in line and '$' in line:
                # Extract type, description, and fee
                parts = line.split('$')
                if len(parts) >= 2:
                    pre_fee = parts[0].strip()
                    fee = '$' + parts[1].strip()
                    
                    # Extract type
                    type_match = re.search(r'Type [IVX]+', pre_fee)
                    if type_match:
                        app_type = type_match.group()
                        description = pre_fee.replace(app_type, '').strip()
                        md_table += f"| {app_type} | {description} | {fee} |\n"
        
        return md_table if md_table.count('|') > 6 else None

    def _format_use_table(self, lines: List[str]) -> str:
        """Format use/zoning tables"""
        md_table = "| Use | Zone | Status |\n"
        md_table += "| --- | --- | --- |\n"
        
        for line in lines:
            for status in ['Permitted', 'Conditional', 'Prohibited']:
                if status in line:
                    parts = line.split(status)
                    if len(parts) >= 2:
                        use_zone = parts[0].strip()
                        # Try to split use from zone
                        use_parts = use_zone.split()
                        if len(use_parts) > 1:
                            use = ' '.join(use_parts[:-1])
                            zone = use_parts[-1]
                        else:
                            use = use_zone
                            zone = ""
                        md_table += f"| {use} | {zone} | {status} |\n"
                    break
        
        return md_table if md_table.count('|') > 6 else None

    def _format_dimensional_table(self, lines: List[str]) -> str:
        """Format dimensional tables (setbacks, heights, etc.)"""
        md_table = "| Dimension | Requirement | Zone/Type |\n"
        md_table += "| --- | --- | --- |\n"
        
        has_rows = False
        for line in lines:
            # Look for dimension patterns
            for unit in ['feet', 'ft', 'inches', 'in', '%']:
                if unit in line.lower():
                    # Extract the dimensional requirement
                    dim_match = re.search(r'([0-9]+(?:\.[0-9]+)?)\s*' + unit, line.lower())
                    if dim_match:
                        has_rows = True
                        requirement = line[dim_match.start():dim_match.end()]
                        before_req = line[:dim_match.start()].strip()
                        after_req = line[dim_match.end():].strip()
                        
                        # Determine what the dimension is
                        if ':' in before_req:
                            parts = before_req.split(':', 1)
                            dimension = parts[0].strip()
                            before_req = parts[1].strip() if len(parts) > 1 else ""
                        else:
                            dimension = before_req if before_req else "Requirement"
                        
                        # Combine any remaining parts with the zone/type
                        remaining = (before_req + " " + after_req).strip()
                        zone_type = remaining if remaining else ""
                        
                        md_table += f"| {dimension} | {requirement} | {zone_type} |\n"
                    break
        
        # Only return if we have actual rows
        return md_table if has_rows else None
        
    def _parse_section_4_0100_table(self, table_text: str) -> str:
        """Special parser for Section 4.0100 table with vertical layout
        
        This specialized parser handles the unique vertical layout of tables in Section 4.0100,
        where use codes (P, NP, SUR, L) are arranged in columns by district.
        
        The table has several sections (RESIDENTIAL, COMMERCIAL, etc.) and uses that may span
        multiple lines. This parser identifies sections, uses, and their corresponding codes,
        and formats them into a properly structured markdown table.
        
        Key features:
        1. Multi-line use name handling:
           - Identifies when use names span multiple lines (e.g., "Business and Retail Service and" + "Trade")
           - Combines these multi-line names into a single entry
           - Uses a dictionary of known multi-line uses to improve accuracy
           
        2. Section identification:
           - Recognizes section headers like "RESIDENTIAL", "COMMERCIAL", etc.
           - Preserves section structure in the output table
           
        3. Empty cell handling:
           - Replaces empty cells with dashes ("-") for better readability
           - Makes it clear when a cell is intentionally empty vs. missing data
           
        4. Known use name dictionary:
           - Uses a predefined list of known use names to improve identification accuracy
           - Helps distinguish between use names and other text
        
        Args:
            table_text: The raw text of the table extracted from the document
            
        Returns:
            A formatted markdown table with proper headers, sections, and codes
        """
        import re
        
        # Define the headers for this specific table
        headers = ['Use', 'LDR-5', 'LDR-7', 'TR', 'TLDR', 'MDR-12', 'MDR-24', 'OFR']
        
        # Create markdown table header
        md_table = "| " + " | ".join(headers) + " |\n"
        md_table += "| " + " | ".join(["---"] * len(headers)) + " |\n"
        
        # Extract the content between "Table 4.0120" and "Table Notes" if available
        match = re.search(r'Table\s+4\.0120.*?(?=Table\s+Notes|$)', table_text, re.DOTALL)
        if match:
            table_text = match.group(0)
        
        # Clean up the text and split into lines
        lines = [line.strip() for line in table_text.split('\n') if line.strip()]
        
        # Known sections in the table
        sections = ["RESIDENTIAL", "COMMERCIAL", "INDUSTRIAL", "INSTITUTIONAL USES", "RENEWABLE ENERGY", "OTHER"]
        
        # Known use names from the table to help with proper identification
        known_uses = [
            "Single Detached Dwelling", "Duplex", "Triplex", "Quadplex", "Townhouse", 
            "Cottage Cluster", "Multifamily", "Elderly Housing", "Manufactured Dwelling Park", 
            "Residential Facility", "Residential Home", "Affordable Housing", 
            "Auto-Dependent Use", "Business and Retail Service and Trade", "Clinics", 
            "Commercial Parking", "Daycare Facilities", "Live-Work", "Major Event Entertainment", 
            "Mini-Storage Facilities", "Outdoor Commercial", "Construction", 
            "Exclusive Heavy Industrial Uses", "Industrial Office", "Information Services", 
            "Manufacturing", "Miscellaneous Industrial", "Trade Schools", 
            "Transportation/Distribution", "Warehousing/Storage", "Waste Management", 
            "Wholesale Trade", "Civic Uses", "Community Services", "Medical", 
            "Parks, Open Spaces, and Trails", "Religious Institutions", "Schools", 
            "Solar Energy Systems", "Wind Energy Systems", "Biomass Energy Systems", 
            "Geothermal Energy Systems", "Micro-Hydro Energy Systems", "Basic Utilities", 
            "Heliports", "Wireless Communications Facilities", 
            "Temporary, Intermittent & Interim Uses", "Marijuana Businesses"
        ]
        
        # Special multi-line use names that need to be preserved
        multi_line_uses = {
            "Business and Retail Service and": "Business and Retail Service and Trade",
            "Trade": "Business and Retail Service and Trade"  # Map "Trade" back to full name when found in context
        }
        
        # Build a list of rows to process (use name + 7 codes)
        table_rows = []
        current_section = ""
        current_multi_line = ""
        
        i = 0        # View a few extracted tables
        head -50 /workspace/RealEstateDevelopmentCode/rag_data_accurate/Oregon/gresham/extracted_tables.json
        
        # View some text chunks
        head -20 /workspace/RealEstateDevelopmentCode/rag_data_accurate/Oregon/gresham/accurate_chunks.jsonl
        
        # Check processing stats
        cat /workspace/RealEstateDevelopmentCode/rag_data_accurate/Oregon/gresham/accuracy_stats.json
        while i < len(lines):
            # Check for section headers
            if lines[i] in sections:
                current_section = lines[i]
                table_rows.append(("SECTION", current_section))
                i += 1
                continue
            
            # Skip header/metadata lines
            if any(x in lines[i] for x in ["Table 4.0120", "USES", "City of Gresham", "Article", "Section", "Page"]):
                i += 1
                continue
            
            # Check if this is a known use name or could be a use name
            is_use_name = False
            use_name = ""
            
            # Handle multi-line use names (part 1 of 2)
            if current_multi_line and lines[i] in multi_line_uses.keys():
                # This is a continuation of a multi-line use
                # Get the full name from our mapping
                use_name = multi_line_uses.get(current_multi_line + " " + lines[i], multi_line_uses.get(lines[i]))
                current_multi_line = ""
                is_use_name = True
            # Check if this could start a multi-line use name
            elif lines[i] in multi_line_uses or any(lines[i].startswith(part) for part in multi_line_uses if isinstance(part, str)):
                # This might be part of a multi-line use name
                # Store it and continue to next line to see if it's a complete use
                current_multi_line = lines[i]
                i += 1
                continue
            # Check if it matches a known use name
            elif any(use == lines[i] for use in known_uses):
                use_name = lines[i]
                is_use_name = True
            
            # Check if it's not a code
            elif not re.match(r'^(P|NP|SUR|L\d*)$', lines[i]) and not any(x in lines[i] for x in ["LDR-", "MDR-", "TR", "TLDR", "OFR"]):
                # Make sure it's not another kind of header
                if not lines[i].isupper() or lines[i] in known_uses:
                    use_name = lines[i]
                    is_use_name = True
            
            if is_use_name:
                codes = []
                
                # Look ahead for codes (up to 7)
                j = i + 1
                while j < len(lines) and len(codes) < 7:
                    if re.match(r'^(P|NP|SUR|L\d*)$', lines[j]):
                        codes.append(lines[j])
                        j += 1
                    else:
                        break                    # If we found some codes, add as a row
                    if codes:
                        # Pad to 7 codes with dashes (not empty strings)
                        while len(codes) < 7:
                            codes.append("-")  # Use dash instead of empty for better readability
                        
                        # Add to our table rows
                        table_rows.append(("USE", use_name, codes))
                    
                        # Skip past the codes
                        i = j
                    else:
                        # No codes found, move to next line
                        i += 1
            else:
                # Not a use name, move to next line
                i += 1
        
        # Now build the markdown table from our processed rows
        for row_type, *row_data in table_rows:
            if row_type == "SECTION":
                section_name = row_data[0]
                md_table += f"| **{section_name}** | " + " | ".join([""] * (len(headers)-1)) + " |\n"
            elif row_type == "USE":
                use_name, codes = row_data
                md_table += f"| {use_name} | " + " | ".join(codes) + " |\n"
        
        return md_table
    
    def _format_abbreviated_use_table(self, table_text: str) -> str:
        """Format tables that use P, NP, SUR, L abbreviations for Permitted, Not Permitted, Special Use Review, Limited
        
        This method handles formatting tables that use specific abbreviations common in municipal codes:
        - P = Permitted use
        - NP = Not permitted
        - SUR = Special Use Review required
        - L = Limited use (often with a numeric suffix like L1, L2)
        
        The method has two approaches:
        1. For Section 4.0100 tables: Use specialized parser with vertical layout handling
        2. For other abbreviated tables: Use general formatter with district columns
        
        Special handling for multi-line use names:
        - Some use names span multiple lines (e.g., "Business and Retail Service and" + "Trade")
        - These are identified using a dictionary of known multi-line uses
        - When a line is identified as part of a multi-line use, it's combined with the next line
          before processing
        
        Empty cell handling:
        - Empty cells are replaced with dashes ("-") for better readability
        - This makes it clear when a cell is intentionally empty vs. missing data
        
        Args:
            table_text: The raw text of the table extracted from the document
            
        Returns:
            A formatted markdown table with proper headers and district columns
        """
        import re
        
        # Special handling for Section 4.0100 table which has a specific format
        if "Table 4.0120" in table_text or ("USES" in table_text and "LDR-5" in table_text and "LDR-7" in table_text):
            # Use specialized parser for section 4.0100
            try:
                formatted_table = self._parse_section_4_0100_table(table_text)
                # If the formatted table has at least a few rows, return it
                if formatted_table.count('\n') > 3:
                    return formatted_table
                # Otherwise fall back to the general formatter
            except Exception as e:
                logger.warning(f"Error in specialized parser for Section 4.0100: {e}. Falling back to general formatter.")
        
        # General formatting for other tables with P, NP, SUR, L abbreviations
        lines = [line.strip() for line in table_text.split('\n') if line.strip()]
        if len(lines) < 4:  # Need at least header and some rows
            return table_text
            
        # Try to identify the header row with district/zone names
        header_row = None
        for i, line in enumerate(lines):
            if re.search(r'(USES|Uses|Table\s+\d+\.\d+\s*:\s*Permitted\s+Uses)', line) and i < 5:
                header_row = i
                break
        
        if header_row is None:
            # Try to find a row with multiple district abbreviations
            for i, line in enumerate(lines):
                if re.search(r'[A-Z0-9-]{2,5}\s+[A-Z0-9-]{2,5}\s+[A-Z0-9-]{2,5}', line) and i < 5:
                    header_row = i
                    break
        
        if header_row is None:
            # If still can't find header, use first row
            header_row = 0
        
        # Extract column headers
        district_pattern = r'([A-Z][A-Z0-9-]*(?:-\d+)?)'
        headers = re.findall(district_pattern, lines[header_row])
        
        # If no headers found or too few, try looking at multiple lines
        if len(headers) < 3:
            # Try to extract from lines after header
            district_headers = []
            for i in range(header_row + 1, min(header_row + 5, len(lines))):
                if not re.search(r'\b(P|NP|SUR|L\d*)\b', lines[i]):  # Skip rows with codes
                    district_headers.extend(re.findall(district_pattern, lines[i]))
            
            if district_headers:
                headers = ['USES'] + district_headers
        
        # If still no headers, use a default set
        if len(headers) < 3:
            if 'LDR' in table_text or 'MDR' in table_text:
                headers = ['USES', 'LDR-5', 'LDR-7', 'TR', 'TLDR', 'MDR-12', 'MDR-24', 'OFR']
            else:
                headers = ['USES', 'DISTRICT1', 'DISTRICT2', 'DISTRICT3', 'DISTRICT4', 'DISTRICT5']
        
        # Create markdown table
        md_table = "| Use | " + " | ".join(headers[1:]) + " |\n"
        md_table += "| --- | " + " | ".join(["---"] * (len(headers)-1)) + " |\n"
        
        # Process rows
        current_use = ""
        use_category = ""
        skip_rows = header_row + 1
        
        # Special handling for multi-line use names
        multi_line_uses = {
            "Business and Retail Service and": "Business and Retail Service and Trade",
            "Trade": "Business and Retail Service and Trade"
        }
        
        current_multi_line = ""
        
        for i in range(skip_rows, len(lines)):
            line = lines[i]
            
            # Check for category headers
            if line.isupper() and not re.search(r'\b(P|NP|SUR|L\d*)\b', line):
                use_category = line
                md_table += f"| **{use_category}** | " + " | ".join([""] * (len(headers)-1)) + " |\n"
                continue
            
            # Handle multi-line use names
            if current_multi_line and line in multi_line_uses:
                # Complete the multi-line use name
                use = multi_line_uses.get(current_multi_line + " " + line, multi_line_uses.get(line))
                current_multi_line = ""
                
                # Try to extract codes from the next line
                if i + 1 < len(lines) and re.search(r'\b(P|NP|SUR|L\d*)\b', lines[i + 1]):
                    codes = re.findall(r'\b(P|NP|SUR|L\d*)\b', lines[i + 1])
                    i += 1  # Skip the codes line
                else:
                    codes = []
                    
                # Ensure we have enough codes
                while len(codes) < len(headers) - 1:
                    codes.append("-")  # Use dash for empty cells
                
                # Trim codes to match header count
                codes = codes[:len(headers) - 1]
                
                md_table += f"| {use} | " + " | ".join(codes) + " |\n"
                current_use = use
                continue
                
            # Check if this could be a start of multi-line use
            if line in multi_line_uses or any(line.startswith(part) for part in multi_line_uses if isinstance(part, str)):
                current_multi_line = line
                continue
                
            # Check if this line contains P, NP, SUR or L codes
            if re.search(r'\b(P|NP|SUR|L\d*)\b', line):
                # Try to extract the use name and codes
                codes = re.findall(r'\b(P|NP|SUR|L\d*)\b', line)
                
                # If we have enough codes, extract the use
                if len(codes) >= 3:
                    # Extract the use name by removing the codes
                    use_part = re.sub(r'\b(P|NP|SUR|L\d*)\b', '', line)
                    use = use_part.strip()
                    
                    # If use is empty, continue the previous use
                    if not use and current_use:
                        use = current_use + " (continued)"
                    elif use:
                        current_use = use
                    elif use_category:
                        use = use_category
                        
                    # Add the row with the extracted codes
                    if use:
                        # Make sure we have the right number of columns
                        while len(codes) < len(headers) - 1:
                            codes.append("-")  # Use dash instead of empty for better readability
                        
                        # Trim codes to match header count
                        codes = codes[:len(headers) - 1]
                        
                        md_table += f"| {use} | " + " | ".join(codes) + " |\n"
        
        # Return the formatted table if we have at least a few rows, otherwise return the original text
        if md_table.count('\n') > 3:
            return md_table;
        else:
            return table_text;

    def _format_generic_table(self, lines: List[str]) -> str:
        """Format generic three-column tables"""
        if len(lines) < 3:
            return None
            
        # Try to detect patterns in the first few lines
        md_table = "| Column 1 | Column 2 | Column 3 |\n"
        md_table += "| --- | --- | --- |\n"
        
        for line in lines:
            # Split on multiple spaces or tabs
            parts = re.split(r'\s{2,}|\t+', line)
            if len(parts) >= 2:
                # Pad to 3 columns
                while len(parts) < 3:
                    parts.append("")
                # Take first 3 columns
                parts = parts[:3]
                md_table += f"| {' | '.join(parts)} |\n"
        
        return md_table if md_table.count('|') > 6 else None

    def _format_street_class_table(self, table_text: str) -> str:
        """Format the specific STREET CLASS table into proper markdown"""
        import re
        
        lines = [line.strip() for line in table_text.split('\n') if line.strip()]
        
        if len(lines) < 3:
            return table_text
        
        # Create markdown table
        md_table = "| Street Class | Parking | Pavement Width |\n"
        md_table += "| --- | --- | --- |\n"
        
        # Enhanced parsing for street class tables
        current_class = None
        parking_type = None
        
        for line in lines:
            line_lower = line.lower()
            
            # Detect class definitions
            if 'class 1' in line_lower:
                if 'fewer than 50' in line_lower or '50 spaces' in line_lower:
                    current_class = "Class 1 (Fewer than 50 spaces)"
                else:
                    current_class = "Class 1"
                    
            elif 'class 2' in line_lower:
                if '50 or more' in line_lower:
                    current_class = "Class 2 (50 or more spaces)"
                else:
                    current_class = "Class 2"
                    
            # Detect parking options
            elif line in ['None', 'One side', 'Both sides'] or any(p in line_lower for p in ['no parking', 'one side', 'both sides']):
                parking_type = line
                
            # Detect width specifications
            elif any(unit in line_lower for unit in ['feet', 'ft', 'inch', 'in']):
                width = line
                # If we have all components, add row
                if current_class and parking_type:
                    md_table += f"| {current_class} | {parking_type} | {width} |\n"
                    # Reset for next entry
                    parking_type = None
                    
            # Handle combined entries (Class, parking, width in one line)
            elif current_class and any(unit in line_lower for unit in ['feet', 'ft']) and any(p in line_lower for p in ['none', 'one', 'both']):
                # Parse combined line
                if 'none' in line_lower:
                    parking_type = "None"
                elif 'one side' in line_lower:
                    parking_type = "One side"
                elif 'both' in line_lower:
                    parking_type = "Both sides"
                    
                # Extract width
                width_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:feet|ft)', line_lower)
                if width_match:
                    width = f"{width_match.group(1)} feet"
                    md_table += f"| {current_class} | {parking_type} | {width} |\n"
        
        return md_table if md_table.count('|') > 6 else table_text

    def _format_json_table(self, table: Dict) -> str:
        """Format a JSON table into markdown format
        
        Args:
            table: Dictionary containing table data from the JSON
            
        Returns:
            Markdown formatted table
        """
        # Extract table data
        rows = table.get('data', [])
        if not rows or len(rows) < 2:  # Need at least header + one row
            return str(table)  # Fallback
        
        # Create markdown table
        md_table = ""
        
        # Try to extract headers
        headers = []
        if 'header' in table:
            headers = table['header']
        elif rows and len(rows) > 0:
            # Use first row as header
            headers = rows[0]
            rows = rows[1:]  # Skip header row
        
        # Create header row
        if headers:
            md_table += "| " + " | ".join(str(h) for h in headers) + " |\n"
            md_table += "| " + " | ".join(["---"] * len(headers)) + " |\n"
        
        # Add data rows
        for row in rows:
            if not row:  # Skip empty rows
                continue
            # Pad row if shorter than headers
            while len(row) < len(headers):
                row.append("")
            md_table += "| " + " | ".join(str(cell) for cell in row) + " |\n"
        
        return md_table

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
    
    def _validate_and_score_tables(self, table_results: List[Dict]) -> List[Dict]:
        """Phase 3: Enhanced validation and quality scoring system for extracted tables"""
        
        logger.info("Running Phase 3: Table validation and quality scoring")
        
        validated_tables = []
        
        for table in table_results:
            try:
                # Calculate quality score
                quality_score = self._calculate_table_quality_score(table)
                
                # Add quality metrics
                table["quality_metrics"] = {
                    "overall_score": quality_score,
                    "extraction_method": table.get("method", "unknown"),
                    "has_coordinates": bool(table.get("metadata", {}).get("coordinates")),
                    "has_html": bool(table.get("html")),
                    "has_raw_data": bool(table.get("raw_data")),
                    "validation_status": "passed" if quality_score >= 0.6 else "needs_review"
                }
                
                # Enhanced content validation
                validation_results = self._validate_table_content(table)
                table["quality_metrics"]["content_validation"] = validation_results
                
                # Structural validation
                structure_validation = self._validate_table_structure(table)
                table["quality_metrics"]["structure_validation"] = structure_validation
                
                # Municipal document specific validation
                municipal_validation = self._validate_municipal_table(table)
                table["quality_metrics"]["municipal_validation"] = municipal_validation
                
                # Only include tables that meet minimum quality threshold
                if quality_score >= 0.3:  # Lower threshold to avoid losing data
                    validated_tables.append(table)
                else:
                    logger.warning(f"Table {table.get('metadata', {}).get('table_id', 'unknown')} "
                                   f"failed quality validation (score: {quality_score:.2f})")
                    
            except Exception as e:
                logger.error(f"Table validation failed: {e}")
                # Include the table but mark it as failed validation
                table["quality_metrics"] = {
                    "overall_score": 0.0,
                    "validation_status": "failed",
                    "error": str(e)
                }
                validated_tables.append(table)
        
        logger.info(f"Phase 3 completed: {len(validated_tables)}/{len(table_results)} tables passed validation")
        return validated_tables

    def _calculate_table_quality_score(self, table: Dict) -> float:
        """Calculate comprehensive quality score for a table (0.0 to 1.0)"""
        
        score_components = {}
        
        # Content quality (30%)
        content = table.get("content", "")
        if content:
            score_components["content_length"] = min(len(content) / 500, 1.0) * 0.1
            score_components["has_structure"] = 0.2 if any(char in content for char in ['|', '\t', '  ']) else 0.0
        else:
            score_components["content_length"] = 0.0
            score_components["has_structure"] = 0.0
        
        # Method reliability (25%)
        method = table.get("method", "")
        method_scores = {
            "camelot_lattice": 0.25,
            "unstructured_advanced": 0.23,
            "unstructured_spatial": 0.22,
            "tabula": 0.20,
            "unstructured_original": 0.18,
            "tabula_fallback": 0.15
        }
        score_components["method_reliability"] = method_scores.get(method, 0.10)
        
        # Coordinate information (20%)
        coordinates = table.get("metadata", {}).get("coordinates")
        if coordinates:
            score_components["coordinates"] = 0.20
        else:
            score_components["coordinates"] = 0.0
        
        # Structured data availability (15%)
        if table.get("raw_data"):
            score_components["structured_data"] = 0.15
        elif table.get("html"):
            score_components["structured_data"] = 0.10
        else:
            score_components["structured_data"] = 0.0
        
        # Accuracy indicators (10%)
        accuracy = table.get("accuracy", 0)
        if accuracy > 0:
            score_components["accuracy"] = (accuracy / 100) * 0.10
        else:
            score_components["accuracy"] = 0.05  # Default score for methods without accuracy
        
        total_score = sum(score_components.values())
        
        # Log score breakdown for debugging
        logger.debug(f"Quality score breakdown: {score_components} = {total_score:.2f}")
        
        return total_score

    def _validate_table_content(self, table: Dict) -> Dict:
        """Validate table content for common issues"""
        
        validation = {
            "has_content": True,
            "content_issues": [],
            "content_score": 1.0
        }
        
        content = table.get("content", "")
        
        if not content or not content.strip():
            validation["has_content"] = False
            validation["content_issues"].append("empty_content")
            validation["content_score"] = 0.0
            return validation
        
        # Check for common content issues
        lines = content.split('\n')
        non_empty_lines = [line.strip() for line in lines if line.strip()]
        
        if len(non_empty_lines) < 2:
            validation["content_issues"].append("insufficient_rows")
            validation["content_score"] *= 0.5
        
        # Check for table structure indicators
        has_pipes = any('|' in line for line in non_empty_lines)
        has_tabs = any('\t' in line for line in non_empty_lines)
        has_consistent_spacing = len(set(len(line.split()) for line in non_empty_lines[:3])) <= 2
        
        if not (has_pipes or has_tabs or has_consistent_spacing):
            validation["content_issues"].append("poor_structure")
            validation["content_score"] *= 0.7
        
        # Check for excessive repetition (OCR artifacts)
        if len(non_empty_lines) > 1:
            unique_lines = set(non_empty_lines)
            if len(unique_lines) / len(non_empty_lines) < 0.5:
                validation["content_issues"].append("excessive_repetition")
                validation["content_score"] *= 0.6
        
        return validation

    def _validate_table_structure(self, table: Dict) -> Dict:
        """Validate table structure and formatting"""
        
        validation = {
            "is_valid_table": True,
            "structure_issues": [],
            "structure_score": 1.0,
            "estimated_columns": 0,
            "estimated_rows": 0
        }
        
        # Analyze raw data if available
        raw_data = table.get("raw_data")
        if raw_data and isinstance(raw_data, list):
            validation["estimated_rows"] = len(raw_data)
            if raw_data:
                validation["estimated_columns"] = len(raw_data[0]) if isinstance(raw_data[0], dict) else 0
                
                # Check for consistent column structure
                if len(raw_data) > 1:
                    column_counts = [len(row) if isinstance(row, dict) else 0 for row in raw_data]
                    if len(set(column_counts)) > 1:
                        validation["structure_issues"].append("inconsistent_columns")
                        validation["structure_score"] *= 0.8
            
            return validation
        
        # Analyze content structure
        content = table.get("content", "")
        if not content:
            validation["is_valid_table"] = False
            validation["structure_score"] = 0.0
            return validation
        
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        validation["estimated_rows"] = len(lines)
        
        if len(lines) < 2:
            validation["structure_issues"].append("insufficient_rows")
            validation["structure_score"] *= 0.5
        
        # Estimate columns from pipe-delimited content
        if any('|' in line for line in lines):
            column_counts = [len(line.split('|')) - 2 for line in lines if '|' in line]  # -2 for start/end pipes
            if column_counts:
                validation["estimated_columns"] = max(column_counts)
                if len(set(column_counts)) > 1:
                    validation["structure_issues"].append("inconsistent_pipe_columns")
                    validation["structure_score"] *= 0.9
        else:
            # Estimate from whitespace
            column_counts = [len(line.split()) for line in lines]
            if column_counts:
                validation["estimated_columns"] = max(column_counts)
                if len(set(column_counts)) > 2:  # Allow some variation
                    validation["structure_issues"].append("inconsistent_whitespace_columns")
                    validation["structure_score"] *= 0.8
        
        return validation

    def _validate_municipal_table(self, table: Dict) -> Dict:
        """Validate table against municipal document patterns"""
        
        validation = {
            "municipal_relevance": True,
            "municipal_issues": [],
            "municipal_score": 1.0,
            "detected_patterns": []
        }
        
        content = table.get("content", "").lower()
        
        # Common municipal table indicators
        municipal_keywords = [
            "zone", "district", "setback", "height", "density", "parking", 
            "requirement", "minimum", "maximum", "feet", "square feet",
            "unit", "dwelling", "commercial", "residential", "industrial",
            "permitted", "conditional", "prohibited", "ldr", "hdr", "tr"
        ]
        
        found_keywords = [kw for kw in municipal_keywords if kw in content]
        validation["detected_patterns"] = found_keywords
        
        if not found_keywords:
            validation["municipal_issues"].append("no_municipal_keywords")
            validation["municipal_score"] *= 0.7
        elif len(found_keywords) >= 3:
            validation["municipal_score"] = 1.0  # High confidence
        
        # Check for table patterns specific to Section 4.0100
        section_4100_patterns = [
            "table 4.0120", "development standards", "tldr", "ldr-5", "ldr-7"
        ]
        
        found_4100_patterns = [pattern for pattern in section_4100_patterns if pattern in content]
        if found_4100_patterns:
            validation["detected_patterns"].extend(found_4100_patterns)
            validation["municipal_score"] = min(validation["municipal_score"] + 0.2, 1.0)
        
        # Check for measurement patterns (feet, percentages, etc.)
        import re
        if re.search(r'\d+\s*(?:feet|ft|%|\s+sf)', content):
            validation["detected_patterns"].append("measurement_values")
            validation["municipal_score"] = min(validation["municipal_score"] + 0.1, 1.0)
        
        return validation

    def _extract_tables_with_unstructured_advanced(self, pdf_path: str) -> List[Dict]:
        """Phase 1: Enhanced Unstructured.io extraction with advanced parameters for coordinate awareness"""
        
        try:
            from unstructured.partition.auto import partition
            from unstructured.partition.pdf import partition_pdf
            
            logger.info("Running Phase 1: Enhanced Unstructured.io table extraction")
            
            # Advanced partitioning with coordinate extraction enabled
            elements = partition_pdf(
                filename=pdf_path,
                strategy="hi_res",
                infer_table_structure=True,
                extract_tables=True,
                include_page_breaks=True,
                coordinates=True,  # Enable coordinate extraction
                include_metadata=True,
                extract_image_block_types=["Table"],
                extract_image_block_to_payload=False,
                chunking_strategy=None,  # No chunking for precise table extraction
                languages=["eng"],
                ocr_languages=["eng"],
                pdf_infer_table_structure=True,
                pdf_extract_images=False,  # Focus on tables, not images
                unique_element_ids=True  # For tracking
            )
            
            enhanced_tables = []
            
            for element in elements:
                if hasattr(element, 'category') and element.category == "Table":
                    
                    # Extract coordinates if available
                    coordinates = None
                    if hasattr(element, 'metadata') and element.metadata:
                        if hasattr(element.metadata, 'coordinates'):
                            coordinates = element.metadata.coordinates
                        elif 'coordinates' in element.metadata:
                            coordinates = element.metadata['coordinates']
                    
                    # Extract HTML table structure if available
                    html_content = None
                    if hasattr(element, 'metadata') and element.metadata:
                        html_content = getattr(element.metadata, 'text_as_html', None)
                        if not html_content and 'text_as_html' in element.metadata:
                            html_content = element.metadata['text_as_html']
                    
                    # Get page information
                    page_number = None
                    if hasattr(element, 'metadata') and element.metadata:
                        page_number = getattr(element.metadata, 'page_number', None)
                        if not page_number and 'page_number' in element.metadata:
                            page_number = element.metadata['page_number']
                    
                    table_result = {
                        "type": "table",
                        "method": "unstructured_advanced",
                        "content": str(element),
                        "html": html_content,
                        "metadata": {
                            "table_id": getattr(element, 'id', f"advanced_{len(enhanced_tables)}"),
                            "page_number": page_number,
                            "coordinates": coordinates,
                            "element_metadata": element.metadata if hasattr(element, 'metadata') else None,
                            "extraction_confidence": "high" if coordinates else "medium"
                        }
                    }
                    
                    # Attempt to convert HTML to structured data if available
                    if html_content:
                        try:
                            import pandas as pd
                            from io import StringIO
                            
                            # Parse HTML table
                            html_tables = pd.read_html(StringIO(html_content))
                            if html_tables:
                                df = html_tables[0]
                                table_result["raw_data"] = df.to_dict('records')
                                table_result["content"] = df.to_markdown(index=False)
                                table_result["metadata"]["shape"] = df.shape
                                table_result["metadata"]["columns"] = list(df.columns)
                        except Exception as e:
                            logger.warning(f"Failed to parse HTML table: {e}")
                    
                    enhanced_tables.append(table_result)
            
            logger.info(f"Phase 1 completed: Extracted {len(enhanced_tables)} enhanced tables")
            return enhanced_tables
            
        except Exception as e:
            logger.error(f"Phase 1 enhanced extraction failed: {e}")
            return []

    def _extract_element_coordinates(self, element) -> Optional[Dict]:
        """Phase 2: Extract coordinate information from Unstructured element"""
        
        try:
            coordinates = None
            
            # Check different ways coordinates might be stored
            if hasattr(element, 'metadata') and element.metadata:
                # Direct coordinates attribute
                if hasattr(element.metadata, 'coordinates'):
                    coordinates = element.metadata.coordinates
                # Coordinates in metadata dict
                elif isinstance(element.metadata, dict) and 'coordinates' in element.metadata:
                    coordinates = element.metadata['coordinates']
                # Check for coordinate points
                elif hasattr(element.metadata, 'coordinate_system'):
                    coordinates = {
                        'coordinate_system': element.metadata.coordinate_system,
                        'points': getattr(element.metadata, 'points', None)
                    }
            
            # If coordinates found, format them consistently
            if coordinates:
                # Handle different coordinate formats
                if isinstance(coordinates, dict):
                    return coordinates
                elif hasattr(coordinates, '__dict__'):
                    # Convert coordinate object to dict
                    coord_dict = {}
                    for attr in ['points', 'coordinate_system', 'layout_width', 'layout_height']:
                        if hasattr(coordinates, attr):
                            coord_dict[attr] = getattr(coordinates, attr)
                    return coord_dict if coord_dict else None
                elif isinstance(coordinates, (list, tuple)) and len(coordinates) >= 4:
                    # Assume it's [x1, y1, x2, y2] format
                    return {
                        'points': coordinates,
                        'coordinate_system': 'pixel',
                        'bbox': {
                            'x1': coordinates[0],
                            'y1': coordinates[1], 
                            'x2': coordinates[2],
                            'y2': coordinates[3]
                        }
                    }
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to extract coordinates: {e}")
            return None

    def _reconstruct_spatial_table(self, element, coordinates: Dict) -> Optional[str]:
        """Phase 2: Reconstruct table using spatial coordinate information"""
        
        try:
            logger.debug("Attempting spatial table reconstruction")
            
            # Get the original text content
            original_text = str(element)
            
            # If we have HTML content, prefer that for reconstruction
            html_content = None
            if hasattr(element, 'metadata') and element.metadata:
                html_content = getattr(element.metadata, 'text_as_html', None)
                if not html_content and isinstance(element.metadata, dict):
                    html_content = element.metadata.get('text_as_html')
            
            if html_content:
                try:
                    import pandas as pd
                    from io import StringIO
                    
                    # Parse HTML and reconstruct as markdown
                    html_tables = pd.read_html(StringIO(html_content))
                    if html_tables:
                        df = html_tables[0]
                        
                        # Clean up the dataframe
                        df = df.fillna('')  # Replace NaN with empty strings
                        
                        # Remove completely empty rows and columns
                        df = df.dropna(how='all').dropna(how='all', axis=1)
                        
                        # Convert to markdown with better formatting
                        markdown_table = df.to_markdown(index=False, tablefmt='grid')
                        
                        logger.debug("Successfully reconstructed table from HTML")
                        return markdown_table
                        
                except Exception as e:
                    logger.warning(f"HTML table reconstruction failed: {e}")
            
            # Fallback: Try to improve text-based table format using coordinate info
            if coordinates and 'points' in coordinates:
                try:
                    # Split original text into lines
                    lines = original_text.strip().split('\n')
                    
                    # Clean up lines and remove empty ones
                    cleaned_lines = [line.strip() for line in lines if line.strip()]
                    
                    if len(cleaned_lines) > 1:
                        # Attempt to detect table structure
                        # Look for common table patterns
                        if any('|' in line for line in cleaned_lines):
                            # Already pipe-delimited, just clean up
                            return '\n'.join(cleaned_lines)
                        
                        # Try to detect columns by common separators
                        potential_separators = ['\t', '  ', '   ', '    ']
                        for sep in potential_separators:
                            if all(sep in line for line in cleaned_lines[:3] if line):  # Check first few lines
                                # Convert to pipe-delimited table
                                table_rows = []
                                for line in cleaned_lines:
                                    cols = [col.strip() for col in line.split(sep) if col.strip()]
                                    if cols:
                                        table_rows.append('| ' + ' | '.join(cols) + ' |')
                                
                                if table_rows:
                                    # Add header separator if it looks like a table
                                    if len(table_rows) > 1:
                                        header_sep = '|' + '|'.join([' --- ' for _ in table_rows[0].split('|')[1:-1]]) + '|'
                                        reconstructed = [table_rows[0], header_sep] + table_rows[1:]
                                        return '\n'.join(reconstructed)
                
                except Exception as e:
                    logger.warning(f"Text-based reconstruction failed: {e}")
            
            # If all else fails, return the original text with basic cleanup
            lines = original_text.strip().split('\n')
            cleaned_lines = [line.strip() for line in lines if line.strip()]
            return '\n'.join(cleaned_lines)
            
        except Exception as e:
            logger.error(f"Spatial table reconstruction failed: {e}")
            return None