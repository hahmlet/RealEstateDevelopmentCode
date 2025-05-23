#!/usr/bin/env python3
"""
Multi-Jurisdiction MCP Server
Version: 1.0
Date: May 23, 2025

Serves municipal development code via Model Context Protocol (MCP)
with support for multiple jurisdictions and special handling for tables.
"""

import json
import logging
import asyncio
import os
import sys
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("mcp.server")

# Add current directory to path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Import local modules
try:
    from config import HOST, PORT, DEFAULT_CHUNK_LIMIT, DEFAULT_CONTEXT_LENGTH, AVAILABLE_JURISDICTIONS
    from database import get_database
except ImportError as e:
    logger.error(f"Failed to import local modules: {e}")
    sys.exit(1)

@dataclass
class DocumentChunk:
    """Represents a document chunk with content and metadata"""
    id: str
    jurisdiction: str
    content: str
    metadata: Dict[str, Any]
    chunk_type: str = "text"

class MunicipalMCPServer:
    """MCP Server for multiple municipal development code jurisdictions"""
    
    def __init__(self):
        self.db = get_database()
        self.jurisdictions = AVAILABLE_JURISDICTIONS
        self._load_all_jurisdictions()
    
    def _load_all_jurisdictions(self):
        """Load chunks from all available jurisdictions"""
        for code in self.jurisdictions:
            count, errors = self.db.load_jurisdiction_chunks(code)
            logger.info(f"Loaded jurisdiction {code}: {count} chunks, {errors} errors")
    
    async def search_chunks(self, query: str, jurisdiction: Optional[str] = None, 
                          limit: int = DEFAULT_CHUNK_LIMIT, 
                          include_tables: bool = True) -> List[DocumentChunk]:
        """Search for relevant chunks based on query"""
        
        results = []
        
        # Search text chunks
        text_results = self.db.search_chunks(
            query=query,
            jurisdiction=jurisdiction,
            chunk_type="text",
            limit=limit
        )
        
        results.extend([
            DocumentChunk(
                id=chunk['id'],
                jurisdiction=chunk['jurisdiction'],
                content=chunk['content'],
                metadata=chunk['metadata'],
                chunk_type="text"
            ) for chunk in text_results
        ])
        
        # Search table chunks if requested
        if include_tables:
            table_limit = max(limit // 3, 2)  # Allocate ~1/3 of results to tables, min 2
            table_results = self.db.search_chunks(
                query=query,
                jurisdiction=jurisdiction,
                chunk_type="table",
                limit=table_limit
            )
            
            results.extend([
                DocumentChunk(
                    id=chunk['id'],
                    jurisdiction=chunk['jurisdiction'],
                    content=chunk['content'],
                    metadata=chunk['metadata'],
                    chunk_type="table"
                ) for chunk in table_results
            ])
        
        return results
    
    async def get_document_chunks(self, document_id: str, jurisdiction: str) -> List[DocumentChunk]:
        """Get all chunks for a specific document"""
        
        chunks = self.db.get_document_chunks(document_id, jurisdiction)
        
        return [
            DocumentChunk(
                id=chunk['id'],
                jurisdiction=chunk['jurisdiction'],
                content=chunk['content'],
                metadata=chunk['metadata'],
                chunk_type=chunk['chunk_type']
            ) for chunk in chunks
        ]
    
    async def get_context_for_query(self, query: str, jurisdiction: Optional[str] = None,
                                 max_context_length: int = DEFAULT_CONTEXT_LENGTH) -> str:
        """Get contextual information for an AI query"""
        
        # Search for relevant chunks
        chunks = await self.search_chunks(
            query=query, 
            jurisdiction=jurisdiction,
            limit=20  # Higher limit for more context options
        )
        
        if not chunks:
            if jurisdiction:
                return f"No relevant municipal code sections found in {jurisdiction}."
            else:
                return "No relevant municipal code sections found."
        
        # Build context with metadata
        context_parts = []
        current_length = 0
        
        # First add text chunks
        text_chunks = [c for c in chunks if c.chunk_type == "text"]
        for chunk in text_chunks:
            jurisdiction_name = self.jurisdictions.get(chunk.jurisdiction, {}).get('name', chunk.jurisdiction)
            chunk_context = f"""
MUNICIPAL CODE SECTION:
Jurisdiction: {jurisdiction_name}
Document: {chunk.metadata.get('title', 'Untitled')} (Section {chunk.metadata.get('document_id', '')})

{chunk.content}

---
"""
            
            if current_length + len(chunk_context) > max_context_length:
                break
                
            context_parts.append(chunk_context)
            current_length += len(chunk_context)
        
        # Then add table chunks if there's room
        table_chunks = [c for c in chunks if c.chunk_type == "table"]
        for chunk in table_chunks:
            jurisdiction_name = self.jurisdictions.get(chunk.jurisdiction, {}).get('name', chunk.jurisdiction)
            table_context = f"""
TABLE:
Jurisdiction: {jurisdiction_name}
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
    
    async def compare_jurisdictions(self, query: str, jurisdictions: List[str], 
                                  max_context_length: int = DEFAULT_CONTEXT_LENGTH) -> str:
        """Compare multiple jurisdictions for a query"""
        
        if not jurisdictions or len(jurisdictions) < 2:
            return "Please provide at least two jurisdictions to compare."
        
        all_chunks = []
        
        # Get chunks from each jurisdiction
        for jurisdiction in jurisdictions:
            chunks = await self.search_chunks(
                query=query,
                jurisdiction=jurisdiction,
                limit=5  # Limit per jurisdiction for comparison
            )
            all_chunks.extend(chunks)
        
        if not all_chunks:
            return f"No relevant content found for query '{query}' in the specified jurisdictions."
        
        # Build comparison context
        context_parts = [f"COMPARISON OF MUNICIPAL CODES FOR: {query}\n\n"]
        current_length = len(context_parts[0])
        
        # Group chunks by jurisdiction
        by_jurisdiction = {}
        for chunk in all_chunks:
            if chunk.jurisdiction not in by_jurisdiction:
                by_jurisdiction[chunk.jurisdiction] = []
            by_jurisdiction[chunk.jurisdiction].append(chunk)
        
        # Add context for each jurisdiction
        for jurisdiction, chunks in by_jurisdiction.items():
            jurisdiction_name = self.jurisdictions.get(jurisdiction, {}).get('name', jurisdiction)
            
            section = f"\n{jurisdiction_name} MUNICIPAL CODE:\n"
            section += "=" * len(section) + "\n\n"
            
            # Add text chunks first
            text_chunks = [c for c in chunks if c.chunk_type == "text"]
            for chunk in text_chunks[:2]:  # Limit to 2 chunks per jurisdiction
                section += f"Document: {chunk.metadata.get('title', 'Untitled')} (Section {chunk.metadata.get('document_id', '')})\n\n"
                section += f"{chunk.content}\n\n"
            
            # Add table chunks if available
            table_chunks = [c for c in chunks if c.chunk_type == "table"]
            if table_chunks:
                section += "TABLES:\n"
                for chunk in table_chunks[:1]:  # Limit to 1 table per jurisdiction
                    section += f"{chunk.content}\n\n"
            
            # Check if adding this section exceeds the max length
            if current_length + len(section) > max_context_length:
                # Add a truncation notice
                context_parts.append("\n[Content truncated due to length limits]")
                break
                
            context_parts.append(section)
            current_length += len(section)
        
        return ''.join(context_parts)
    
    async def get_available_jurisdictions(self) -> Dict[str, Any]:
        """Get information about available jurisdictions"""
        return self.db.get_jurisdiction_info()
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get server statistics"""
        stats = self.db.get_statistics()
        stats['server_info'] = {
            'version': '1.0',
            'available_jurisdictions': list(self.jurisdictions.keys()),
        }
        return stats

# MCP Protocol Handler
class MCPProtocolHandler:
    """Handles MCP protocol communication"""
    
    def __init__(self, server: MunicipalMCPServer):
        self.server = server
    
    async def handle_request(self, request: Dict) -> Dict:
        """Handle incoming MCP requests"""
        
        method = request.get('method')
        params = request.get('params', {})
        
        try:
            if method == 'search':
                query = params.get('query', '')
                jurisdiction = params.get('jurisdiction')
                limit = params.get('limit', DEFAULT_CHUNK_LIMIT)
                include_tables = params.get('include_tables', True)
                
                chunks = await self.server.search_chunks(
                    query=query,
                    jurisdiction=jurisdiction,
                    limit=limit,
                    include_tables=include_tables
                )
                
                return {
                    'result': [
                        {
                            'id': chunk.id,
                            'jurisdiction': chunk.jurisdiction,
                            'content': chunk.content,
                            'metadata': chunk.metadata,
                            'chunk_type': chunk.chunk_type
                        }
                        for chunk in chunks
                    ]
                }
            
            elif method == 'get_context':
                query = params.get('query', '')
                jurisdiction = params.get('jurisdiction')
                max_length = params.get('max_length', DEFAULT_CONTEXT_LENGTH)
                
                context = await self.server.get_context_for_query(
                    query=query,
                    jurisdiction=jurisdiction,
                    max_context_length=max_length
                )
                
                return {
                    'result': {
                        'context': context,
                        'query': query,
                        'jurisdiction': jurisdiction
                    }
                }
            
            elif method == 'get_document':
                document_id = params.get('document_id', '')
                jurisdiction = params.get('jurisdiction')
                
                if not jurisdiction:
                    return {'error': 'jurisdiction parameter is required'}
                
                chunks = await self.server.get_document_chunks(document_id, jurisdiction)
                
                return {
                    'result': [
                        {
                            'id': chunk.id,
                            'jurisdiction': chunk.jurisdiction,
                            'content': chunk.content,
                            'metadata': chunk.metadata,
                            'chunk_type': chunk.chunk_type
                        }
                        for chunk in chunks
                    ]
                }
            
            elif method == 'compare':
                query = params.get('query', '')
                jurisdictions = params.get('jurisdictions', [])
                max_length = params.get('max_length', DEFAULT_CONTEXT_LENGTH)
                
                context = await self.server.compare_jurisdictions(
                    query=query,
                    jurisdictions=jurisdictions,
                    max_context_length=max_length
                )
                
                return {
                    'result': {
                        'context': context,
                        'query': query,
                        'jurisdictions': jurisdictions
                    }
                }
            
            elif method == 'get_jurisdictions':
                jurisdictions = await self.server.get_available_jurisdictions()
                
                return {
                    'result': {
                        'jurisdictions': jurisdictions
                    }
                }
            
            elif method == 'get_statistics':
                stats = await self.server.get_statistics()
                
                return {
                    'result': {
                        'statistics': stats
                    }
                }
            
            else:
                return {'error': f'Unknown method: {method}'}
                
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            return {'error': f'Internal server error: {str(e)}'}

# HTTP Server implementation (can be replaced with any async HTTP server)
async def start_http_server():
    """Start the HTTP server"""
    
    try:
        import aiohttp
        from aiohttp import web
    except ImportError:
        logger.error("aiohttp package is required for HTTP server.")
        logger.error("Install with: pip install aiohttp")
        return
    
    server = MunicipalMCPServer()
    protocol_handler = MCPProtocolHandler(server)
    
    # Create HTTP app
    app = web.Application()
    
    # Define routes
    async def handle_mcp_request(request):
        """Handle MCP requests via HTTP"""
        try:
            data = await request.json()
            response = await protocol_handler.handle_request(data)
            return web.json_response(response)
        except Exception as e:
            logger.error(f"Error handling HTTP request: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    app.router.add_post('/mcp', handle_mcp_request)
    
    # Add a simple status endpoint
    async def handle_status(request):
        """Simple status endpoint"""
        stats = await server.get_statistics()
        return web.json_response({
            'status': 'running',
            'statistics': stats
        })
    
    app.router.add_get('/', handle_status)
    
    # Start server
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, HOST, PORT)
    
    logger.info(f"Starting MCP server on http://{HOST}:{PORT}")
    await site.start()
    
    # Keep the server running
    while True:
        await asyncio.sleep(3600)  # Sleep for 1 hour

# Command-line interface
def main():
    """Main entry point"""
    
    # Check if aiohttp is available
    try:
        import aiohttp
    except ImportError:
        logger.error("aiohttp package is required for HTTP server.")
        logger.error("Install with: pip install aiohttp")
        return 1
    
    logger.info("Starting Multi-Jurisdiction MCP Server...")
    
    # Create database folder
    database_dir = current_dir / "database"
    database_dir.mkdir(exist_ok=True)
    
    # Create logs folder
    logs_dir = current_dir / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    try:
        # Start HTTP server
        asyncio.run(start_http_server())
    except KeyboardInterrupt:
        logger.info("Server stopped by user.")
    except Exception as e:
        logger.error(f"Server error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
