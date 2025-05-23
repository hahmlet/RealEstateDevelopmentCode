#!/usr/bin/env python3
"""
Municipal Document MCP Server v1.0
Version: 1.0
Date: May 23, 2025

Serves municipal development code via Model Context Protocol (MCP)
with special handling for tables and structured content.
"""

import json
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional
import asyncio
from dataclasses import dataclass
import logging
import sys
import os

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MunicipalMCPServer")

@dataclass
class DocumentChunk:
    id: str
    content: str
    metadata: Dict[str, Any]
    
class MunicipalMCPServer:
    """MCP Server for Municipal Development Code"""
    
    def __init__(self, rag_data_dir: str):
        self.rag_data_dir = Path(rag_data_dir)
        self.db_path = self.rag_data_dir / "chunks.db"
        self._init_database()
        self._load_chunks()
    
    def _init_database(self):
        """Initialize SQLite database for fast chunk retrieval"""
        
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chunks (
                id TEXT PRIMARY KEY,
                content TEXT,
                chunk_type TEXT,
                document_id TEXT,
                section_index INTEGER,
                chunk_index INTEGER,
                jurisdiction TEXT,
                document_type TEXT,
                title TEXT,
                metadata TEXT
            )
        ''')
        
        # Create indices for fast searching
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_document_id ON chunks(document_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_jurisdiction ON chunks(jurisdiction)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_content ON chunks(content)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_chunk_type ON chunks(chunk_type)')
        
        conn.commit()
        conn.close()
    
    def _load_chunks(self):
        """Load chunks from JSONL file into database"""
        
        chunks_file = self.rag_data_dir / "accurate_chunks.jsonl"
        if not chunks_file.exists():
            logger.warning(f"No chunks file found at {chunks_file}")
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Clear existing data
        cursor.execute('DELETE FROM chunks')
        
        # Load new data
        chunk_count = 0
        with open(chunks_file, 'r') as f:
            for line in f:
                chunk_data = json.loads(line.strip())
                
                # Create a unique ID if not present
                if 'id' not in chunk_data:
                    chunk_data['id'] = f"chunk_{chunk_count}"
                
                metadata = chunk_data.get('metadata', {})
                
                cursor.execute('''
                    INSERT INTO chunks 
                    (id, content, chunk_type, document_id, section_index, chunk_index, 
                     jurisdiction, document_type, title, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    chunk_data['id'],
                    chunk_data['content'],
                    chunk_data.get('type', 'text'),
                    metadata.get('document_id', ''),
                    metadata.get('section_index', 0),
                    metadata.get('chunk_index', 0),
                    metadata.get('jurisdiction', ''),
                    metadata.get('document_type', ''),
                    metadata.get('title', ''),
                    json.dumps(metadata)
                ))
                chunk_count += 1
        
        conn.commit()
        conn.close()
        logger.info(f"Loaded {chunk_count} chunks into database: {self.db_path}")
    
    async def search_chunks(self, query: str, limit: int = 10, include_tables: bool = True) -> List[DocumentChunk]:
        """Search for relevant chunks based on query"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        results = []
        
        # Search text chunks
        cursor.execute('''
            SELECT id, content, metadata, chunk_type 
            FROM chunks 
            WHERE content LIKE ? AND chunk_type = 'text'
            ORDER BY length(content) ASC 
            LIMIT ?
        ''', (f'%{query}%', limit))
        
        for row in cursor.fetchall():
            chunk_id, content, metadata_json, chunk_type = row
            metadata = json.loads(metadata_json)
            
            results.append(DocumentChunk(
                id=chunk_id,
                content=content,
                metadata=metadata
            ))
        
        # Search table chunks if requested
        if include_tables:
            cursor.execute('''
                SELECT id, content, metadata, chunk_type 
                FROM chunks 
                WHERE content LIKE ? AND chunk_type = 'table'
                LIMIT ?
            ''', (f'%{query}%', limit // 2))  # Limit table results to half of text
            
            for row in cursor.fetchall():
                chunk_id, content, metadata_json, chunk_type = row
                metadata = json.loads(metadata_json)
                
                results.append(DocumentChunk(
                    id=chunk_id,
                    content=content,
                    metadata=metadata
                ))
        
        conn.close()
        return results
    
    async def get_document_chunks(self, document_id: str) -> List[DocumentChunk]:
        """Get all chunks for a specific document"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, content, metadata, chunk_type 
            FROM chunks 
            WHERE document_id = ? 
            ORDER BY chunk_type, section_index, chunk_index
        ''', (document_id,))
        
        results = []
        for row in cursor.fetchall():
            chunk_id, content, metadata_json, chunk_type = row
            metadata = json.loads(metadata_json)
            
            results.append(DocumentChunk(
                id=chunk_id,
                content=content,
                metadata=metadata
            ))
        
        conn.close()
        return results
    
    async def get_table_chunks(self) -> List[DocumentChunk]:
        """Get all table chunks"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, content, metadata 
            FROM chunks 
            WHERE chunk_type = 'table'
        ''')
        
        results = []
        for row in cursor.fetchall():
            chunk_id, content, metadata_json = row
            metadata = json.loads(metadata_json)
            
            results.append(DocumentChunk(
                id=chunk_id,
                content=content,
                metadata=metadata
            ))
        
        conn.close()
        return results
    
    async def get_context_for_query(self, query: str, max_context_length: int = 4000) -> str:
        """Get contextual information for an AI query"""
        
        # Search for relevant chunks
        chunks = await self.search_chunks(query, limit=20)
        
        if not chunks:
            return "No relevant municipal code sections found."
        
        # Build context with metadata
        context_parts = []
        current_length = 0
        
        # First add text chunks
        text_chunks = [c for c in chunks if c.metadata.get('content_type', '') == 'text']
        for chunk in text_chunks:
            chunk_context = f"""
Document: {chunk.metadata.get('title', 'Untitled')} (Section {chunk.metadata.get('document_id', '')})
Jurisdiction: {chunk.metadata.get('jurisdiction', 'Oregon/Gresham')}

{chunk.content}

---
"""
            
            if current_length + len(chunk_context) > max_context_length:
                break
                
            context_parts.append(chunk_context)
            current_length += len(chunk_context)
        
        # Then add table chunks if there's room
        table_chunks = [c for c in chunks if c.metadata.get('content_type', '') == 'table']
        for chunk in table_chunks:
            table_context = f"""
TABLE:
Document: {chunk.metadata.get('title', 'Untitled')} (Section {chunk.metadata.get('document_id', '')})
Table ID: {chunk.metadata.get('table_id', 'Unknown')}

{chunk.content}

---
"""
            
            if current_length + len(table_context) > max_context_length:
                break
                
            context_parts.append(table_context)
            current_length += len(table_context)
        
        return ''.join(context_parts)

# MCP Protocol Implementation
class MCPProtocolHandler:
    """Handles MCP protocol communication"""
    
    def __init__(self, server: MunicipalMCPServer):
        self.server = server
    
    async def handle_request(self, request: Dict) -> Dict:
        """Handle incoming MCP requests"""
        
        method = request.get('method')
        params = request.get('params', {})
        
        if method == 'search':
            query = params.get('query', '')
            limit = params.get('limit', 10)
            include_tables = params.get('include_tables', True)
            chunks = await self.server.search_chunks(query, limit, include_tables)
            
            return {
                'result': [
                    {
                        'id': chunk.id,
                        'content': chunk.content,
                        'metadata': chunk.metadata
                    }
                    for chunk in chunks
                ]
            }
        
        elif method == 'get_context':
            query = params.get('query', '')
            max_length = params.get('max_length', 4000)
            context = await self.server.get_context_for_query(query, max_length)
            
            return {
                'result': {
                    'context': context,
                    'query': query
                }
            }
        
        elif method == 'get_document':
            document_id = params.get('document_id', '')
            chunks = await self.server.get_document_chunks(document_id)
            
            return {
                'result': [
                    {
                        'id': chunk.id,
                        'content': chunk.content,
                        'metadata': chunk.metadata
                    }
                    for chunk in chunks
                ]
            }
        
        elif method == 'get_tables':
            chunks = await self.server.get_table_chunks()
            
            return {
                'result': [
                    {
                        'id': chunk.id,
                        'content': chunk.content,
                        'metadata': chunk.metadata
                    }
                    for chunk in chunks
                ]
            }
        
        else:
            return {'error': f'Unknown method: {method}'}

if __name__ == "__main__":
    # Check if RAG data exists
    rag_data_dir = Path("/workspace/RealEstateDevelopmentCode/rag_data_accurate/Oregon/gresham")
    
    if not rag_data_dir.exists() or not (rag_data_dir / "accurate_chunks.jsonl").exists():
        logger.error("RAG data not found! Please run the accurate_municipal_rag.py script first.")
        sys.exit(1)
    
    # Initialize MCP server
    server = MunicipalMCPServer(str(rag_data_dir))
    handler = MCPProtocolHandler(server)
    
    # Example usage
    async def test_server():
        # Test search
        chunks = await server.search_chunks("zoning", limit=5)
        logger.info(f"Found {len(chunks)} chunks for 'zoning'")
        
        # Test context generation
        context = await server.get_context_for_query("What are the parking requirements?")
        logger.info(f"Context length: {len(context)} characters")
    
    asyncio.run(test_server())