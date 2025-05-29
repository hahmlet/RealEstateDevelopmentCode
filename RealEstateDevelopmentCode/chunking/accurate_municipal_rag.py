#!/usr/bin/env python3
"""
Municipal Document RAG Preparation v1.0 - Optimized for Tables & Accuracy
Version: 1.0
Date: May 23, 2025

Combines Unstructured.io + LangChain + specialized table extraction
to ensure maximum accuracy for municipal development codes, especially tables.
Updates to work with the multi-jurisdiction MCP server structure.

Enhanced with TOC structure validation for comprehensive document mapping.
"""

import json
import os
import re
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
import sys
import logging
from collections import defaultdict

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
        """Enhanced table extraction using multi-pass approach with layout awareness"""
        
        logger.info(f"Starting enhanced table extraction for {Path(pdf_path).name}")
        
        # Use the new enhanced multi-pass extraction
        enhanced_tables = self._extract_tables_with_enhanced_multi_pass(pdf_path)
        
        # Legacy fallback: Process original Unstructured table elements if no enhanced results
        if not enhanced_tables and table_elements:
            logger.info("Falling back to original Unstructured elements processing...")
            fallback_tables = []
            
            for i, element in enumerate(table_elements):
                if hasattr(element, 'metadata'):
                    # Extract coordinates for spatial table reconstruction
                    coordinates = self._extract_element_coordinates(element)
                    
                    table_result = {
                        "type": "table",
                        "method": "unstructured_fallback",
                        "content": str(element),
                        "metadata": {
                            "table_id": f"fallback_{i}",
                            "element_metadata": element.metadata,
                            "coordinates": coordinates
                        }
                    }
                    
                    # Add HTML if available
                    if element.metadata.get('text_as_html'):
                        table_result["html"] = element.metadata.get('text_as_html')
                    
                    # Attempt spatial reconstruction if coordinates available
                    if coordinates:
                        try:
                            reconstructed_table = self._reconstruct_spatial_table(element, coordinates)
                            if reconstructed_table:
                                table_result["content"] = reconstructed_table
                                table_result["method"] = "unstructured_spatial_fallback"
                        except Exception as e:
                            logger.warning(f"Spatial reconstruction failed for fallback table {i}: {e}")
                    
                    fallback_tables.append(table_result)
            
            enhanced_tables = fallback_tables
        
        # Final validation and scoring
        if enhanced_tables:
            validated_tables = self._validate_and_score_tables(enhanced_tables)
            
            logger.info(f"Table extraction completed: {len(validated_tables)} tables extracted and validated")
            for i, table in enumerate(validated_tables[:3]):  # Log top 3 tables
                score = table.get("quality_score", 0)
                method = table.get("method", "unknown")
                table_type = table.get("metadata", {}).get("table_type", "unknown")
                logger.info(f"  Table {i+1}: {method} (score: {score:.2f}, type: {table_type})")
            
            return validated_tables
        else:
            logger.warning("No tables extracted by any method")
            return []
    
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

    def _intelligent_result_ranking_and_deduplication(self, all_tables: List[Dict]) -> List[Dict]:
        """
        Intelligent ranking and deduplication of extracted tables
        
        This method scores tables based on quality metrics and removes duplicates,
        keeping the best version of each unique table.
        """
        if not all_tables:
            return []
        
        # Step 1: Score all tables
        scored_tables = []
        for table in all_tables:
            score = self._calculate_table_quality_score(table)
            table["quality_score"] = score
            scored_tables.append(table)
        
        # Step 2: Group similar tables for deduplication
        table_groups = self._group_similar_tables(scored_tables)
        
        # Step 3: Select best table from each group
        deduplicated_tables = []
        for group in table_groups:
            best_table = max(group, key=lambda t: t["quality_score"])
            deduplicated_tables.append(best_table)
        
        # Step 4: Final ranking by quality score
        deduplicated_tables.sort(key=lambda t: t["quality_score"], reverse=True)
        
        logger.info(f"Deduplication: {len(all_tables)} -> {len(deduplicated_tables)} tables")
        
        return deduplicated_tables
    
    def _calculate_table_quality_score(self, table: Dict) -> float:
        """Calculate quality score for a table based on multiple factors"""
        score = 0.0
        content = table.get("content", "")
        method = table.get("method", "")
        metadata = table.get("metadata", {})
        
        # Base score by extraction method (higher = better quality)
        method_scores = {
            "pdfplumber_spatial": 0.9,
            "coordinate_grouping": 0.8, 
            "camelot_lattice": 0.85,
            "unstructured_spatial": 0.75,
            "tabula": 0.6,
            "unstructured_original": 0.7,
            "ocr_extraction": 0.4,
            "text_embedded": 0.3
        }
        score += method_scores.get(method, 0.5)
        
        # Content quality factors
        if content:
            # Length factor (substantial content is better)
            content_length = len(content)
            if content_length > 100:
                score += min(0.3, content_length / 1000)
            
            # Structure quality (proper markdown table format)
            # Municipal content relevance
            content_upper = content.upper()
            
            # High value municipal patterns
            if any(pattern in content_upper for pattern in [
                '4.0100', 'PERMITTED USES', 'SECTION 4'
            ]):
                score += 0.4
            
            # Medium value municipal patterns  
            if any(pattern in content_upper for pattern in [
                'P|', 'NP|', 'SUR|', 'ZONE', 'DISTRICT'
            ]):
                score += 0.2
            
            # General municipal patterns
            if any(pattern in content_upper for pattern in [
                'SETBACK', 'HEIGHT', 'FEET', 'MINIMUM', 'MAXIMUM'
            ]):
                score += 0.1
        
        # Metadata quality factors
        if metadata.get("is_section_4_table"):
            score += 0.3
        if metadata.get("is_municipal_uses"):
            score += 0.2
        if metadata.get("bbox"):  # Has spatial coordinates
            score += 0.1
        if metadata.get("specialized_formatting"):
            score += 0.1
        
        # Method-specific bonuses
        if method == "camelot_lattice" and metadata.get("accuracy", 0) > 90:
            score += 0.2
        if method == "ocr_extraction" and metadata.get("confidence", 0) > 0.8:
            score += 0.1
        
        return min(1.0, score)  # Cap at 1.0
    
    def _validate_table_content(self, table: Dict) -> Dict:
        """Content-specific validation for extracted tables"""
        content = table.get("content", "")
        validation_result = {
            "content_score": 0.0,
            "has_valid_structure": False,
            "content_length": len(content),
            "detected_patterns": []
        }
        
        if not content:
            return validation_result
        
        # Base content score
        content_length = len(content)
        if content_length >= 50:
            validation_result["content_score"] += 0.3
        if content_length >= 200:
            validation_result["content_score"] += 0.2
        if content_length >= 500:
            validation_result["content_score"] += 0.2
        
        # Check for table structure indicators
        if '|' in content and '---' in content:
            validation_result["has_valid_structure"] = True
            validation_result["content_score"] += 0.3
        
        # Check for municipal content patterns
        content_upper = content.upper()
        municipal_patterns = [
            'PERMITTED', 'CONDITIONAL', 'PROHIBITED', 'SETBACK', 'HEIGHT',
            'FEET', 'FT', 'MINIMUM', 'MAXIMUM', 'ZONE', 'DISTRICT', 'P|', 'NP|', 'SUR|'
        ]
        
        for pattern in municipal_patterns:
            if pattern in content_upper:
                validation_result["detected_patterns"].append(pattern.lower())
        
        # Bonus for municipal patterns
        if validation_result["detected_patterns"]:
            validation_result["content_score"] += min(0.2, len(validation_result["detected_patterns"]) * 0.05)
        
        validation_result["content_score"] = min(1.0, validation_result["content_score"])
        return validation_result
    
    def _validate_table_structure(self, table: Dict) -> Dict:
        """Structural validation for extracted tables"""
        content = table.get("content", "")
        metadata = table.get("metadata", {})
        
        validation_result = {
            "structure_score": 0.0,
            "has_headers": False,
            "row_count": 0,
            "column_count": 0,
            "is_well_formed": False
        }
        
        if not content:
            return validation_result
        
        lines = content.split('\n')
        table_lines = [line for line in lines if '|' in line]
        
        if not table_lines:
            return validation_result
        
        validation_result["row_count"] = len(table_lines)
        
        # Check for header separator (markdown table indicator)
        has_separator = any('---' in line for line in table_lines)
        if has_separator:
            validation_result["has_headers"] = True
            validation_result["structure_score"] += 0.3
        
        # Estimate column count from first table row
        if table_lines:
            first_row = table_lines[0]
            column_count = first_row.count('|') - 1  # Subtract border pipes
            validation_result["column_count"] = max(0, column_count)
            
            if column_count >= 2:
                validation_result["structure_score"] += 0.2
            if column_count >= 3:
                validation_result["structure_score"] += 0.2
        
        # Check for consistent structure across rows
        if len(table_lines) >= 3:  # Header + separator + at least one data row
            pipe_counts = [line.count('|') for line in table_lines if line.strip()]
            if pipe_counts and max(pipe_counts) - min(pipe_counts) <= 1:  # Allow some variation
                validation_result["is_well_formed"] = True
                validation_result["structure_score"] += 0.3
        
        validation_result["structure_score"] = min(1.0, validation_result["structure_score"])
        return validation_result
    
    def _validate_municipal_table(self, table: Dict) -> Dict:
        """Municipal document pattern validation"""
        content = table.get("content", "")
        metadata = table.get("metadata", {})
        
        validation_result = {
            "municipal_score": 0.0,
            "detected_patterns": [],
            "table_type": "unknown",
            "is_section_4": False,
            "has_zoning_codes": False
        }
        
        if not content:
            return validation_result
        
        content_upper = content.upper()
        
        # Check for Section 4.0100 patterns
        section_4_patterns = ['4.0100', 'SECTION 4', 'PERMITTED USES', 'USE CATEGORIES']
        for pattern in section_4_patterns:
            if pattern in content_upper:
                validation_result["is_section_4"] = True
                validation_result["detected_patterns"].append(f"section_4_{pattern.lower().replace('.', '_')}")
                validation_result["municipal_score"] += 0.3
                break
        
        # Check for zoning codes (P/NP/SUR/L patterns)
        import re
        if re.search(r'\b(P|NP|SUR|L\d*)\b', content_upper):
            validation_result["has_zoning_codes"] = True
            validation_result["detected_patterns"].append("zoning_codes")
            validation_result["municipal_score"] += 0.4
        
        # Check for municipal table types
        municipal_keywords = {
            'dimensional_standards': ['SETBACK', 'HEIGHT', 'COVERAGE', 'DENSITY'],
            'parking_requirements': ['PARKING', 'SPACE', 'STALL', 'VEHICLE'],
            'fee_schedule': ['FEE', 'COST', 'CHARGE', 'TYPE I', 'TYPE II'],
            'permitted_uses': ['PERMITTED', 'CONDITIONAL', 'PROHIBITED'],
            'zoning_districts': ['ZONE', 'DISTRICT', 'LDR', 'MDR', 'HDR']
        }
        
        for table_type, keywords in municipal_keywords.items():
            if any(keyword in content_upper for keyword in keywords):
                validation_result["table_type"] = table_type
                validation_result["detected_patterns"].append(table_type)
                validation_result["municipal_score"] += 0.2
                break
        
        # Check for measurement patterns
        measurement_patterns = [
            r'\d+\s*(?:feet|ft|inches|in)',
            r'\d+\s*%',
            r'\d+\s*square\s*feet',
            r'\d+\s*stories'
        ]
        
        for pattern in measurement_patterns:
            if re.search(pattern, content_upper):
                validation_result["detected_patterns"].append("measurements")
                validation_result["municipal_score"] += 0.1
                break
        
        # Bonus for metadata indicators
        if metadata.get("is_section_4_table"):
            validation_result["municipal_score"] += 0.2
        if metadata.get("is_municipal_uses"):
            validation_result["municipal_score"] += 0.2
        
        validation_result["municipal_score"] = min(1.0, validation_result["municipal_score"])
        return validation_result

    def _group_similar_tables(self, tables: List[Dict]) -> List[List[Dict]]:
        """Group similar tables for deduplication"""
        if not tables:
            return []
        
        groups = []
        
        for table in tables:
            # Find if this table belongs to an existing group
            assigned = False
            
            for group in groups:
                if self._are_tables_similar(table, group[0]):
                    group.append(table)
                    assigned = True
                    break
            
            if not assigned:
                groups.append([table])
        
        return groups
    
    def _are_tables_similar(self, table1: Dict, table2: Dict) -> bool:
        """Determine if two tables are similar (likely the same table extracted differently)"""
        content1 = table1.get("content", "")
        content2 = table2.get("content", "")
        metadata1 = table1.get("metadata", {})
        metadata2 = table2.get("metadata", {})
        
        # Same page check
        if (metadata1.get("page") and metadata2.get("page") and 
            metadata1["page"] != metadata2["page"]):
            return False
        
        # Content similarity check
        if content1 and content2:
            # Simple text similarity
            words1 = set(content1.lower().split())
            words2 = set(content2.lower().split())
            
            if words1 and words2:
                intersection = len(words1.intersection(words2))
                union = len(words1.union(words2))
                similarity = intersection / union if union > 0 else 0
                
                if similarity > 0.7:  # 70% word overlap
                    return True
        
        # Spatial overlap check (if coordinates available)
        bbox1 = metadata1.get("bbox")
        bbox2 = metadata2.get("bbox")
        coords1 = metadata1.get("coordinates")
        coords2 = metadata2.get("coordinates")
        
        if bbox1 and bbox2:
            overlap = self._calculate_bbox_overlap(bbox1, bbox2)
            if overlap > 0.5:  # 50% spatial overlap
                return True
        
        if coords1 and coords2:
            # Check coordinate overlap
            x1_overlap = max(0, min(coords1.get("x1", 0), coords2.get("x1", 0)) - 
                           max(coords1.get("x0", 0), coords2.get("x0", 0)))
            y1_overlap = max(0, min(coords1.get("y1", 0), coords2.get("y1", 0)) - 
                           max(coords1.get("y0", 0), coords2.get("y0", 0)))
            
            if x1_overlap > 100 and y1_overlap > 50:  # Significant spatial overlap
                return True
        
        return False
    
    def _calculate_bbox_overlap(self, bbox1: tuple, bbox2: tuple) -> float:
        """Calculate overlap ratio between two bounding boxes"""
        if not bbox1 or not bbox2 or len(bbox1) < 4 or len(bbox2) < 4:
            return 0.0
        
        x1_max = max(bbox1[0], bbox2[0])
        y1_max = max(bbox1[1], bbox2[1])
        x2_min = min(bbox1[2], bbox2[2])
        y2_min = min(bbox1[3], bbox2[3])
        
        if x2_min <= x1_max or y2_min <= y1_max:
            return 0.0  # No overlap
        
        overlap_area = (x2_min - x1_max) * (y2_min - y1_max)
        area1 = (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1])
        area2 = (bbox2[2] - bbox2[0]) * (bbox2[3] - bbox2[1])
        
        if area1 <= 0 or area2 <= 0:
            return 0.0
        
        return overlap_area / min(area1, area2)
    
    def _extract_tables_with_enhanced_multi_pass(self, pdf_path: str) -> List[Dict]:
        """
        Enhanced multi-pass table extraction using all available methods
        
        This is the main orchestrator that combines all extraction approaches:
        1. Layout-aware spatial extraction (pdfplumber)
        2. Advanced Unstructured.io processing  
        3. Traditional tabula/camelot extraction
        4. OCR fallback for complex layouts
        5. Municipal template application
        6. Intelligent ranking and deduplication
        """
        logger.info(f"Starting enhanced multi-pass table extraction for {Path(pdf_path).name}")
        
        all_extracted_tables = []
        
        # Pass 1: Spatial awareness extraction (highest priority for municipal tables)
        logger.info("Pass 1: Spatial awareness extraction...")
        try:
            spatial_tables = self._extract_tables_with_spatial_awareness(pdf_path)
            all_extracted_tables.extend(spatial_tables)
            logger.info(f"Spatial extraction found {len(spatial_tables)} tables")
        except Exception as e:
            logger.warning(f"Spatial extraction failed: {e}")
        
        # Pass 2: Enhanced Unstructured.io (structure-aware)
        logger.info("Pass 2: Enhanced Unstructured.io extraction...")
        try:
            unstructured_tables = self._extract_tables_with_unstructured_advanced(pdf_path)
            all_extracted_tables.extend(unstructured_tables)
            logger.info(f"Unstructured extraction found {len(unstructured_tables)} tables")
        except Exception as e:
            logger.warning(f"Unstructured extraction failed: {e}")
        
        # Pass 3: Traditional extraction methods (camelot/tabula)
        logger.info("Pass 3: Traditional extraction methods...")
        try:
            traditional_tables = self._extract_tables_traditional_methods(pdf_path)
            all_extracted_tables.extend(traditional_tables)
            logger.info(f"Traditional extraction found {len(traditional_tables)} tables")
        except Exception as e:
            logger.warning(f"Traditional extraction failed: {e}")
        
        # Pass 4: OCR fallback for complex layouts
        logger.info("Pass 4: OCR fallback extraction...")
        try:
            ocr_tables = self._extract_tables_with_ocr_enhancement(pdf_path)
            all_extracted_tables.extend(ocr_tables)
            logger.info(f"OCR extraction found {len(ocr_tables)} tables")
        except Exception as e:
            logger.warning(f"OCR extraction failed: {e}")
        
        # Pass 5: Apply municipal-specific templates
        logger.info("Pass 5: Applying municipal templates...")
        try:
            templated_tables = self._apply_municipal_specific_templates(all_extracted_tables)
            logger.info(f"Applied templates to {len(templated_tables)} tables")
        except Exception as e:
            logger.warning(f"Template application failed: {e}")
            templated_tables = all_extracted_tables
        
        # Pass 6: Intelligent ranking and deduplication
        logger.info("Pass 6: Intelligent ranking and deduplication...")
        try:
            final_tables = self._intelligent_result_ranking_and_deduplication(templated_tables)
            logger.info(f"Final result: {len(final_tables)} unique, ranked tables")
        except Exception as e:
            logger.warning(f"Ranking and deduplication failed: {e}")
            final_tables = templated_tables
        
        # Log summary of results
        if final_tables:
            logger.info("Table extraction summary:")
            for i, table in enumerate(final_tables[:5]):  # Top 5 tables
                method = table.get("method", "unknown")
                score = table.get("quality_score", 0)
                table_type = table.get("metadata", {}).get("table_type", "unknown")
                logger.info(f"  #{i+1}: {method} (score: {score:.2f}, type: {table_type})")
        
        return final_tables
    
    def _extract_tables_traditional_methods(self, pdf_path: str) -> List[Dict]:
        """Extract tables using traditional camelot/tabula methods"""
        traditional_tables = []
        
        # Camelot lattice extraction
        if self.has_camelot:
            try:
                import camelot
                camelot_tables = camelot.read_pdf(pdf_path, pages='all', flavor='lattice')
                
                for i, table in enumerate(camelot_tables):
                    if table.accuracy > 70:  # Reasonable accuracy threshold
                        traditional_tables.append({
                            "type": "table",
                            "method": "camelot_lattice",
                            "content": table.df.to_markdown(index=False),
                            "raw_data": {"dataframe": table.df.to_dict('records')},
                            "metadata": {
                                "table_id": f"camelot_{i}",
                                "page": table.page,
                                "accuracy": table.accuracy,
                                "shape": table.df.shape
                            }
                        })
            except Exception as e:
                logger.warning(f"Camelot extraction failed: {e}")
        
        # Tabula extraction
        try:
            import tabula
            tabula_tables = tabula.read_pdf(pdf_path, pages='all', multiple_tables=True)
            
            for i, df in enumerate(tabula_tables):
                if not df.empty and len(df.columns) > 1:
                    traditional_tables.append({
                        "type": "table",
                        "method": "tabula",
                        "content": df.to_markdown(index=False),
                        "raw_data": {"dataframe": df.to_dict('records')},
                        "metadata": {
                            "table_id": f"tabula_{i}",
                            "shape": df.shape,
                            "columns": list(df.columns)
                        }
                    })
        except Exception as e:
            logger.warning(f"Tabula extraction failed: {e}")
        
        return traditional_tables

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

    def _extract_tables_with_spatial_awareness(self, pdf_path: str) -> List[Dict]:
        """
        Phase 2 Enhancement: Layout-aware table extraction using pdfplumber for spatial relationships
        
        This method preserves 2D spatial relationships that are lost in text linearization,
        specifically targeting municipal code tables like Section 4.0100 with P/NP/SUR codes.
        """
        try:
            import pdfplumber
        except ImportError:
            logger.warning("pdfplumber not available for spatial table extraction")
            return []
        
        spatial_tables = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    # Method 1: Direct table detection with pdfplumber
                    tables = page.find_tables()
                    
                    for table_idx, table in enumerate(tables):
                        try:
                            # Extract table data with spatial coordinates
                            extracted_table = table.extract()
                            if not extracted_table or len(extracted_table) < 2:
                                continue
                            
                            # Get table bounding box
                            bbox = table.bbox
                            
                            # Convert to markdown with preserved structure
                            md_table = self._convert_extracted_table_to_markdown(extracted_table)
                            
                            # Check if this looks like a municipal uses table (P/NP/SUR pattern)
                            is_municipal_uses = self._detect_municipal_uses_table(extracted_table)
                            
                            spatial_tables.append({
                                "type": "table",
                                "method": "pdfplumber_spatial",
                                "content": md_table,
                                "raw_data": {"table_data": extracted_table},
                                "metadata": {
                                    "source": pdf_path,
                                    "page": page_num + 1,
                                    "table_id": f"spatial_p{page_num}_t{table_idx}",
                                    "bbox": bbox,
                                    "coordinates": {
                                        "x0": bbox[0], "y0": bbox[1], 
                                        "x1": bbox[2], "y1": bbox[3]
                                    },
                                    "is_municipal_uses": is_municipal_uses,
                                    "extraction_method": "direct_table_detection"
                                }
                            })
                            
                        except Exception as e:
                            logger.warning(f"Failed to extract spatial table {table_idx} on page {page_num + 1}: {e}")
                    
                    # Method 2: Coordinate-based text grouping for complex layouts
                    text_based_tables = self._extract_tables_from_coordinates(page, page_num)
                    spatial_tables.extend(text_based_tables)
                    
        except Exception as e:
            logger.error(f"Spatial table extraction failed: {e}")
        
        return spatial_tables
    
    def _convert_extracted_table_to_markdown(self, table_data: List[List]) -> str:
        """Convert pdfplumber extracted table to clean markdown format"""
        if not table_data or len(table_data) < 2:
            return ""
        
        # Filter out empty rows
        clean_data = []
        for row in table_data:
            if row and any(cell and str(cell).strip() for cell in row):
                # Clean and standardize cells
                clean_row = []
                for cell in row:
                    if cell is None:
                        clean_row.append("")
                    else:
                        # Clean cell content
                        clean_cell = str(cell).strip().replace('\n', ' ').replace('|', '\\|')
                        clean_row.append(clean_cell)
                clean_data.append(clean_row)
        
        if len(clean_data) < 2:
            return ""
        
        # Determine number of columns from the most complete row
        max_cols = max(len(row) for row in clean_data)
        
        # Pad rows to consistent length
        for row in clean_data:
            while len(row) < max_cols:
                row.append("")
        
        # Build markdown table
        md_table = ""
        
        # Header row
        header = clean_data[0]
        md_table += "| " + " | ".join(header) + " |\n"
        
        # Separator row
        md_table += "| " + " | ".join(["---"] * len(header)) + " |\n"
        
        # Data rows
        for row in clean_data[1:]:
            md_table += "| " + " | ".join(row) + " |\n"
        
        return md_table
    
    def _detect_municipal_uses_table(self, table_data: List[List]) -> bool:
        """Detect if this is a municipal uses table with P/NP/SUR codes"""
        if not table_data or len(table_data) < 3:
            return False
        
        # Look for characteristic patterns
        table_text = str(table_data).upper()
        
        # Check for P/NP/SUR pattern
        has_codes = bool(re.search(r'\b(P|NP|SUR|L\d*)\b', table_text))
        
        # Check for uses-related headers
        header_text = str(table_data[0]).upper() if table_data else ""
        has_uses_header = any(term in header_text for term in [
            'USE', 'USES', 'PERMITTED', 'ZONE', 'DISTRICT'
        ])
        
        # Check for zone abbreviations in headers
        has_zone_codes = bool(re.search(r'\b(LDR|MDR|HDR|NC|GC|CC|TC|DMU|CM|CI|LI|HI)\b', header_text))
        
        return has_codes and (has_uses_header or has_zone_codes)
    
    def _extract_tables_from_coordinates(self, page, page_num: int) -> List[Dict]:
        """
        Extract tables using coordinate-based text grouping
        
        This method groups text elements by their spatial positions to reconstruct
        tabular data that may not be detected by standard table extraction.
        """
        coordinate_tables = []
        
        try:
            # Get all text elements with coordinates
            chars = page.chars
            
            if not chars:
                return []
            
            # Group characters into words with coordinates
            words = self._group_chars_into_words(chars)
            
            # Group words into potential table rows based on vertical alignment
            potential_rows = self._group_words_into_rows(words)
            
            # Identify table-like structures
            tables = self._identify_table_structures(potential_rows)
            
            for table_idx, table_data in enumerate(tables):
                if len(table_data) >= 2:  # At least header + one data row
                    md_table = self._convert_coordinate_table_to_markdown(table_data)
                    
                    # Check if this looks like Section 4.0100 table
                    is_section_4_table = self._detect_section_4_pattern(table_data)
                    
                    coordinate_tables.append({
                        "type": "table",
                        "method": "coordinate_grouping",
                        "content": md_table,
                        "raw_data": {"coordinate_table": table_data},
                        "metadata": {
                            "page": page_num + 1,
                            "table_id": f"coord_p{page_num}_t{table_idx}",
                            "is_section_4_table": is_section_4_table,
                            "extraction_method": "coordinate_based_grouping",
                            "row_count": len(table_data),
                            "col_count": max(len(row) for row in table_data) if table_data else 0
                        }
                    })
                    
        except Exception as e:
            logger.warning(f"Coordinate-based table extraction failed on page {page_num + 1}: {e}")
        
        return coordinate_tables
    
    def _group_chars_into_words(self, chars: List[Dict]) -> List[Dict]:
        """Group character objects into word objects with bounding boxes"""
        if not chars:
            return []
        
        words = []
        current_word = {"text": "", "x0": None, "y0": None, "x1": None, "y1": None}
        
        for char in sorted(chars, key=lambda c: (c.get('y0', 0), c.get('x0', 0))):
            char_text = char.get('text', '')
            
            if char_text.isspace():
                # End current word
                if current_word["text"]:
                    words.append(current_word)
                    current_word = {"text": "", "x0": None, "y0": None, "x1": None, "y1": None}
            else:
                # Add to current word
                if not current_word["text"]:
                    # Start new word
                    current_word = {
                        "text": char_text,
                        "x0": char.get('x0'),
                        "y0": char.get('y0'),
                        "x1": char.get('x1'),
                        "y1": char.get('y1')
                    }
                else:
                    # Continue word
                    current_word["text"] += char_text
                    current_word["x1"] = char.get('x1')
                    current_word["y1"] = max(current_word["y1"] or 0, char.get('y1', 0))
        
        # Add final word
        if current_word["text"]:
            words.append(current_word)
        
        return words
    
    def _group_words_into_rows(self, words: List[Dict], y_tolerance: float = 3) -> List[List[Dict]]:
        """Group words into rows based on vertical alignment"""
        if not words:
            return []
        
        # Sort words by vertical position
        sorted_words = sorted(words, key=lambda w: w.get('y0', 0))
        
        rows = []
        current_row = []
        current_y = None
        
        for word in sorted_words:
            word_y = word.get('y0')
            
            if current_y is None:
                current_y = word_y
                current_row = [word]
            elif abs(word_y - current_y) <= y_tolerance:
                # Same row
                current_row.append(word)
            else:
                # New row
                if current_row:
                    # Sort current row by x position
                    current_row.sort(key=lambda w: w.get('x0', 0))
                    rows.append(current_row)
                current_row = [word]
                current_y = word_y
        
        # Add final row
        if current_row:
            current_row.sort(key=lambda w: w.get('x0', 0))
            rows.append(current_row)
        
        return rows
    
    def _identify_table_structures(self, rows: List[List[Dict]]) -> List[List[List[str]]]:
        """Identify table-like structures from grouped rows"""
        if len(rows) < 2:
            return []
        
        tables = []
        current_table = []
        
        for row_idx, row in enumerate(rows):
            # Convert words to text cells
            row_texts = [word["text"] for word in row]
            
            # Check if this looks like a table row
            is_table_row = self._is_potential_table_row(row_texts, row)
            
            if is_table_row:
                current_table.append(row_texts)
            else:
                # End current table if it has enough rows
                if len(current_table) >= 2:
                    tables.append(current_table)
                current_table = []
        
        # Add final table
        if len(current_table) >= 2:
            tables.append(current_table)
        
        return tables
    
    def _is_potential_table_row(self, row_texts: List[str], word_objects: List[Dict]) -> bool:
        """Determine if a row of text looks like part of a table"""
        if len(row_texts) < 2:
            return False
        
        # Check for table-like characteristics
        
        # 1. Multiple columns with reasonable spacing
        if len(row_texts) >= 3:
            return True
        
        # 2. Contains typical table content
        text = " ".join(row_texts).upper()
        
        # Municipal table indicators
        if any(indicator in text for indicator in [
            'PERMITTED', 'CONDITIONAL', 'PROHIBITED', 'P', 'NP', 'SUR', 'L1', 'L2'
        ]):
            return True
        
        # 3. Numeric patterns common in tables
        if re.search(r'\d+\s*(feet|ft|inches|in|%)', text):
            return True
        
        # 4. Check spacing between words (columns should be well-spaced)
        if len(word_objects) >= 2:
            spacings = []
            for i in range(1, len(word_objects)):
                prev_x1 = word_objects[i-1].get('x1', 0)
                curr_x0 = word_objects[i].get('x0', 0)
                spacing = curr_x0 - prev_x1
                spacings.append(spacing)
            
            # If there are significant gaps, likely table columns
            avg_spacing = sum(spacings) / len(spacings)
            if avg_spacing > 20:  # Significant spacing suggests columns
                return True
        
        return False
    
    def _convert_coordinate_table_to_markdown(self, table_data: List[List[str]]) -> str:
        """Convert coordinate-based table data to markdown"""
        if not table_data or len(table_data) < 2:
            return ""
        
        # Determine maximum columns
        max_cols = max(len(row) for row in table_data)
        
        # Pad rows
        padded_data = []
        for row in table_data:
            padded_row = row + [""] * (max_cols - len(row))
            padded_data.append(padded_row)
        
        # Build markdown
        md_table = ""
        header = padded_data[0]
        md_table += "| " + " | ".join(header) + " |\n"
        md_table += "| " + " | ".join(["---"] * len(header)) + " |\n"
        
        for row in padded_data[1:]:
            md_table += "| " + " | ".join(row) + " |\n"
        
        return md_table
    
    def _detect_section_4_pattern(self, table_data: List[List[str]]) -> bool:
        """Detect Section 4.0100 permitted uses table pattern"""
        if not table_data or len(table_data) < 2:
            return False
        
        # Convert to string for pattern matching
        table_text = str(table_data).upper()
        
        # Look for Section 4 indicators
        section_4_indicators = [
            '4.0100', 'SECTION 4', 'PERMITTED USES', 'USE CATEGORIES'
        ]
        
        has_section_4 = any(indicator in table_text for indicator in section_4_indicators)
        
        # Look for P/NP/SUR pattern
        has_pnp_pattern = bool(re.search(r'\b(P|NP|SUR|L\d*)\b', table_text))
        
        # Look for multi-line use names pattern
        has_multiline_uses = any(len(" ".join(row)) > 50 for row in table_data[1:] if row)
        
        return has_section_4 or (has_pnp_pattern and has_multiline_uses)
    
    def _extract_tables_with_ocr_enhancement(self, pdf_path: str) -> List[Dict]:
        """
        Phase 3 Enhancement: OCR-based table extraction for complex layouts
        
        This method uses computer vision and OCR as a fallback for tables that
        standard extraction methods cannot handle properly.
        """
        ocr_tables = []
        
        try:
            # Try to import OCR dependencies
            try:
                import pytesseract
                from PIL import Image
                import pdf2image
            except ImportError:
                logger.warning("OCR dependencies not available (pytesseract, PIL, pdf2image)")
                return []
            
            # Convert PDF pages to images
            images = pdf2image.convert_from_path(pdf_path, dpi=300)
            
            for page_num, image in enumerate(images):
                try:
                    # Extract text with position information
                    ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
                    
                    # Group OCR text into potential table structures
                    table_candidates = self._group_ocr_text_into_tables(ocr_data, page_num)
                    
                    for table_idx, table_data in enumerate(table_candidates):
                        md_table = self._convert_ocr_table_to_markdown(table_data)
                        
                        ocr_tables.append({
                            "type": "table",
                            "method": "ocr_extraction",
                            "content": md_table,
                            "raw_data": {"ocr_table": table_data},
                            "metadata": {
                                "page": page_num + 1,
                                "table_id": f"ocr_p{page_num}_t{table_idx}",
                                "extraction_method": "ocr_computer_vision",
                                "confidence": self._calculate_ocr_confidence(table_data)
                            }
                        })
                        
                except Exception as e:
                    logger.warning(f"OCR extraction failed on page {page_num + 1}: {e}")
                    
        except Exception as e:
            logger.error(f"OCR table extraction failed: {e}")
        
        return ocr_tables
    
    def _group_ocr_text_into_tables(self, ocr_data: Dict, page_num: int) -> List[List[List[str]]]:
        """Group OCR text data into table structures based on spatial positioning"""
        if not ocr_data or 'text' not in ocr_data:
            return []
        
        # Extract words with coordinates and confidence
        words = []
        for i, text in enumerate(ocr_data['text']):
            if text.strip() and int(ocr_data['conf'][i]) > 30:  # Confidence threshold
                words.append({
                    'text': text.strip(),
                    'x': int(ocr_data['left'][i]),
                    'y': int(ocr_data['top'][i]),
                    'width': int(ocr_data['width'][i]),
                    'height': int(ocr_data['height'][i]),
                    'conf': int(ocr_data['conf'][i])
                })
        
        if not words:
            return []
        
        # Group words into rows based on Y coordinates
        rows = self._group_ocr_words_into_rows(words)
        
        # Identify table-like structures
        tables = self._identify_ocr_table_structures(rows)
        
        return tables
    
    def _group_ocr_words_into_rows(self, words: List[Dict], y_tolerance: int = 10) -> List[List[Dict]]:
        """Group OCR words into rows based on vertical position"""
        if not words:
            return []
        
        # Sort by Y coordinate
        sorted_words = sorted(words, key=lambda w: w['y'])
        
        rows = []
        current_row = []
        current_y = None
        
        for word in sorted_words:
            if current_y is None:
                current_y = word['y']
                current_row = [word]
            elif abs(word['y'] - current_y) <= y_tolerance:
                current_row.append(word)
            else:
                if current_row:
                    # Sort row by X coordinate
                    current_row.sort(key=lambda w: w['x'])
                    rows.append(current_row)
                current_row = [word]
                current_y = word['y']
        
        if current_row:
            current_row.sort(key=lambda w: w['x'])
            rows.append(current_row)
        
        return rows
    
    def _identify_ocr_table_structures(self, rows: List[List[Dict]]) -> List[List[List[str]]]:
        """Identify table structures from OCR rows"""
        if len(rows) < 2:
            return []
        
        tables = []
        current_table = []
        
        for row in rows:
            row_texts = [word['text'] for word in row]
            
            # Check if this looks like a table row
            if self._is_ocr_table_row(row_texts, row):
                current_table.append(row_texts)
            else:
                if len(current_table) >= 2:
                    tables.append(current_table)
                current_table = []
        
        if len(current_table) >= 2:
            tables.append(current_table)
        
        return tables
    
    def _is_ocr_table_row(self, row_texts: List[str], word_objects: List[Dict]) -> bool:
        """Determine if OCR row looks like a table row"""
        if len(row_texts) < 2:
            return False
        
        text = " ".join(row_texts).upper()
        
        # Municipal table patterns
        municipal_patterns = [
            'PERMITTED', 'CONDITIONAL', 'PROHIBITED', 'P', 'NP', 'SUR',
            'FEET', 'FT', 'MINIMUM', 'MAXIMUM', 'SETBACK', 'HEIGHT'
        ]
        
        if any(pattern in text for pattern in municipal_patterns):
            return True
        
        # Check for column-like spacing
        if len(word_objects) >= 3:
            x_positions = [word['x'] for word in word_objects]
            spacings = [x_positions[i] - x_positions[i-1] for i in range(1, len(x_positions))]
            avg_spacing = sum(spacings) / len(spacings)
            
            if avg_spacing > 50:  # Significant spacing suggests table columns
                return True
        
        return False
    
    def _convert_ocr_table_to_markdown(self, table_data: List[List[str]]) -> str:
        """Convert OCR table data to markdown format"""
        if not table_data or len(table_data) < 2:
            return ""
        
        # Find maximum columns
        max_cols = max(len(row) for row in table_data)
        
        # Pad rows
        padded_data = []
        for row in table_data:
            padded_row = row + [""] * (max_cols - len(row))
            padded_data.append(padded_row)
        
        # Build markdown
        md_table = ""
        header = padded_data[0]
        md_table += "| " + " | ".join(header) + " |\n"
        md_table += "| " + " | ".join(["---"] * len(header)) + " |\n"
        
        for row in padded_data[1:]:
            md_table += "| " + " | ".join(row) + " |\n"
        
        return md_table
    
    def _calculate_ocr_confidence(self, table_data: List[List[str]]) -> float:
        """Calculate overall confidence score for OCR-extracted table"""
        if not table_data:
            return 0.0
        
        # Simple confidence based on text quality indicators
        total_chars = sum(len("".join(row)) for row in table_data)
        
        if total_chars == 0:
            return 0.0
        
        # Base confidence for having substantial content
        confidence = min(0.8, total_chars / 100)
        
        # Boost for municipal patterns
        text = str(table_data).upper()
        if re.search(r'\b(P|NP|SUR)\b', text):
            confidence += 0.1
        if any(term in text for term in ['PERMITTED', 'ZONE', 'DISTRICT']):
            confidence += 0.1
        
        return min(1.0, confidence)
    
    def _apply_municipal_specific_templates(self, tables: List[Dict]) -> List[Dict]:
        """
        Apply municipal-specific table templates and formatting
        
        This method recognizes common municipal table types and applies
        specialized formatting and structure recognition.
        """
        enhanced_tables = []
        
        for table in tables:
            try:
                # Create enhanced copy
                enhanced_table = table.copy()
                
                # Detect table type and apply appropriate template
                table_type = self._classify_municipal_table_type(table)
                enhanced_table["metadata"]["table_type"] = table_type
                
                if table_type == "permitted_uses":
                    enhanced_table = self._apply_permitted_uses_template(enhanced_table)
                elif table_type == "dimensional_standards":
                    enhanced_table = self._apply_dimensional_standards_template(enhanced_table)
                elif table_type == "parking_requirements":
                    enhanced_table = self._apply_parking_requirements_template(enhanced_table)
                elif table_type == "fee_schedule":
                    enhanced_table = self._apply_fee_schedule_template(enhanced_table)
                else:
                    enhanced_table = self._apply_generic_municipal_template(enhanced_table)
                
                enhanced_tables.append(enhanced_table)
                
            except Exception as e:
                logger.warning(f"Template application failed for table: {e}")
                enhanced_tables.append(table)  # Fallback to original
        
        return enhanced_tables
    
    def _classify_municipal_table_type(self, table: Dict) -> str:
        """Classify the type of municipal table"""
        content = table.get("content", "").upper()
        metadata = table.get("metadata", {})
        
        # Check for Section 4.0100 permitted uses patterns
        if ("4.0100" in content or 
            metadata.get("is_section_4_table") or 
            metadata.get("is_municipal_uses")):
            return "permitted_uses"
        
        # Check for dimensional standards
        if any(term in content for term in [
            "SETBACK", "HEIGHT", "COVERAGE", "DENSITY", "FEET", "FT", "MINIMUM", "MAXIMUM"
        ]):
            return "dimensional_standards"
        
        # Check for parking requirements
        if any(term in content for term in [
            "PARKING", "SPACE", "STALL", "VEHICLE"
        ]):
            return "parking_requirements"
        
        # Check for fee schedules
        if "$" in content and any(term in content for term in [
            "FEE", "COST", "CHARGE", "TYPE I", "TYPE II"
        ]):
            return "fee_schedule"
        
        return "general_municipal"
    
    def _apply_permitted_uses_template(self, table: Dict) -> Dict:
        """Apply specialized formatting for permitted uses tables (Section 4.0100)"""
        content = table.get("content", "")
        
        # Enhanced formatting for P/NP/SUR codes
        enhanced_content = self._enhance_pnp_formatting(content)
        
        # Add specialized metadata
        table["metadata"]["specialized_formatting"] = "permitted_uses"
        table["metadata"]["code_legend"] = {
            "P": "Permitted",
            "NP": "Not Permitted", 
            "SUR": "Special Use Review Required",
            "L1": "Limited Use Level 1",
            "L2": "Limited Use Level 2"
        }
        
        table["content"] = enhanced_content
        
        return table
    
    def _enhance_pnp_formatting(self, content: str) -> str:
        """Enhance P/NP/SUR code formatting for better readability"""
        # Replace short codes with more descriptive text in a copy for display
        enhanced = content
        
        # Add explanatory headers if missing
        lines = enhanced.split('\n')
        if lines and not any('Zone' in line or 'District' in line for line in lines[:2]):
            # Try to detect and enhance zone headers
            for i, line in enumerate(lines):
                if re.search(r'\|\s*(LDR|MDR|HDR|NC|GC|CC|TC|DMU|CM|CI|LI|HI)', line):
                    # This looks like a zone abbreviation header
                    enhanced_line = line
                    zone_expansions = {
                        'LDR': 'LDR (Low Density Residential)',
                        'MDR': 'MDR (Medium Density Residential)', 
                        'HDR': 'HDR (High Density Residential)',
                        'NC': 'NC (Neighborhood Commercial)',
                        'GC': 'GC (General Commercial)',
                        'CC': 'CC (Community Commercial)',
                        'TC': 'TC (Town Center)',
                        'DMU': 'DMU (Downtown Mixed Use)',
                        'CM': 'CM (Commercial Mixed)',
                        'CI': 'CI (Commercial Industrial)',
                        'LI': 'LI (Light Industrial)',
                        'HI': 'HI (Heavy Industrial)'
                    }
                    
                    for abbrev, expansion in zone_expansions.items():
                        enhanced_line = enhanced_line.replace(f' {abbrev} ', f' {expansion} ')
                    
                    lines[i] = enhanced_line
                    break
        
        return '\n'.join(lines)
    
    def _apply_dimensional_standards_template(self, table: Dict) -> Dict:
        """Apply formatting for dimensional standards tables"""
        table["metadata"]["specialized_formatting"] = "dimensional_standards"
        table["metadata"]["common_dimensions"] = [
            "Front Setback", "Side Setback", "Rear Setback", 
            "Maximum Height", "Lot Coverage", "Density"
        ]
        
        return table
    
    def _apply_parking_requirements_template(self, table: Dict) -> Dict:
        """Apply formatting for parking requirements tables"""
        table["metadata"]["specialized_formatting"] = "parking_requirements" 
        table["metadata"]["parking_metrics"] = [
            "Required Spaces", "Space Dimensions", "Aisle Width"
        ]
        
        return table
    
    def _apply_fee_schedule_template(self, table: Dict) -> Dict:
        """Apply formatting for fee schedule tables"""
        table["metadata"]["specialized_formatting"] = "fee_schedule"
        table["metadata"]["fee_structure"] = [
            "Application Type", "Base Fee", "Additional Charges"
        ]
        
        return table
    
    def _apply_generic_municipal_template(self, table: Dict) -> Dict:
        """Apply generic municipal table formatting"""
        table["metadata"]["specialized_formatting"] = "general_municipal"
        
        return table