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
            r'STREET CLASS\s+PARKING\s+PAVEMENT WIDTH[^\n]*?\n(?:[^\n]+?\n){1,15}?(?=\n\n|\n[0-9]+\.|\nE\.|\Z)'
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

if __name__ == "__main__":
    # Process with high accuracy for tables
    processor = AccurateMunicipalRAG(
        source_dir="/workspace/RealEstateDevelopmentCode/pdf_content/Oregon/gresham",
        output_dir="/workspace/RealEstateDevelopmentCode/rag_data_accurate/Oregon/gresham"
    )
    
    stats = processor.prepare_from_json_content()