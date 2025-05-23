#!/usr/bin/env python3
"""
MCP Server Database Module
Version: 1.0
Date: May 23, 2025

Database handling for the multi-jurisdiction MCP server.
"""

import json
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import logging

from config import DATABASE_PATH, AVAILABLE_JURISDICTIONS

logger = logging.getLogger("mcp.database")

class MCPDatabase:
    """Database manager for MCP server"""
    
    def __init__(self, db_path=DATABASE_PATH):
        self.db_path = Path(db_path)
        self.jurisdictions = AVAILABLE_JURISDICTIONS
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database structure"""
        
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create chunks table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chunks (
                id TEXT,
                jurisdiction TEXT,
                content TEXT,
                chunk_type TEXT,
                document_id TEXT,
                section_index INTEGER,
                chunk_index INTEGER,
                document_type TEXT,
                title TEXT,
                metadata TEXT,
                PRIMARY KEY (id, jurisdiction)
            )
        ''')
        
        # Create jurisdictions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS jurisdictions (
                code TEXT PRIMARY KEY,
                name TEXT,
                state TEXT,
                data_path TEXT,
                chunks_file TEXT,
                last_updated TEXT
            )
        ''')
        
        # Create indices for fast searching
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_jurisdiction ON chunks(jurisdiction)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_document_id ON chunks(document_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_content ON chunks(content)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_chunk_type ON chunks(chunk_type)')
        
        # Register jurisdictions
        for code, info in self.jurisdictions.items():
            cursor.execute('''
                INSERT OR REPLACE INTO jurisdictions 
                (code, name, state, data_path, chunks_file)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                code, 
                info.get('name', ''), 
                info.get('state', ''),
                str(info.get('data_path', '')),
                info.get('chunks_file', 'accurate_chunks.jsonl')
            ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Database initialized at {self.db_path}")
    
    def load_jurisdiction_chunks(self, jurisdiction_code: str) -> Tuple[int, int]:
        """Load chunks from a jurisdiction into the database"""
        
        if jurisdiction_code not in self.jurisdictions:
            logger.error(f"Unknown jurisdiction: {jurisdiction_code}")
            return (0, 0)
        
        info = self.jurisdictions[jurisdiction_code]
        data_path = info['data_path']
        chunks_file = data_path / info['chunks_file']
        
        if not chunks_file.exists():
            logger.warning(f"No chunks file found at {chunks_file}")
            return (0, 0)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Clear existing jurisdiction data
        cursor.execute('DELETE FROM chunks WHERE jurisdiction = ?', (jurisdiction_code,))
        
        # Load new data
        chunk_count = 0
        error_count = 0
        
        with open(chunks_file, 'r') as f:
            for line in f:
                try:
                    chunk_data = json.loads(line.strip())
                    
                    # Create a unique ID if not present
                    if 'id' not in chunk_data:
                        chunk_data['id'] = f"{jurisdiction_code}_{chunk_count}"
                    
                    metadata = chunk_data.get('metadata', {})
                    
                    cursor.execute('''
                        INSERT INTO chunks 
                        (id, jurisdiction, content, chunk_type, document_id, section_index, 
                         chunk_index, document_type, title, metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        chunk_data['id'],
                        jurisdiction_code,
                        chunk_data['content'],
                        chunk_data.get('type', 'text'),
                        metadata.get('document_id', ''),
                        metadata.get('section_index', 0),
                        metadata.get('chunk_index', 0),
                        metadata.get('document_type', ''),
                        metadata.get('title', ''),
                        json.dumps(metadata)
                    ))
                    chunk_count += 1
                except Exception as e:
                    logger.error(f"Error processing chunk: {e}")
                    error_count += 1
        
        # Update last_updated timestamp
        cursor.execute('''
            UPDATE jurisdictions
            SET last_updated = datetime('now')
            WHERE code = ?
        ''', (jurisdiction_code,))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Loaded {chunk_count} chunks for {jurisdiction_code} (errors: {error_count})")
        return (chunk_count, error_count)
    
    def search_chunks(self, query: str, jurisdiction: Optional[str] = None, 
                     chunk_type: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """Search for chunks matching query"""
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        cursor = conn.cursor()
        
        # Build the query based on parameters
        sql_query = 'SELECT * FROM chunks WHERE content LIKE ?'
        params = [f'%{query}%']
        
        if jurisdiction:
            sql_query += ' AND jurisdiction = ?'
            params.append(jurisdiction)
            
        if chunk_type:
            sql_query += ' AND chunk_type = ?'
            params.append(chunk_type)
            
        sql_query += ' LIMIT ?'
        params.append(limit)
        
        cursor.execute(sql_query, params)
        
        results = []
        for row in cursor.fetchall():
            row_dict = dict(row)
            row_dict['metadata'] = json.loads(row_dict['metadata'])
            results.append(row_dict)
        
        conn.close()
        return results
    
    def get_document_chunks(self, document_id: str, jurisdiction: str) -> List[Dict]:
        """Get all chunks for a specific document"""
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM chunks 
            WHERE document_id = ? AND jurisdiction = ?
            ORDER BY section_index, chunk_index
        ''', (document_id, jurisdiction))
        
        results = []
        for row in cursor.fetchall():
            row_dict = dict(row)
            row_dict['metadata'] = json.loads(row_dict['metadata'])
            results.append(row_dict)
        
        conn.close()
        return results
    
    def get_jurisdiction_info(self, jurisdiction_code: Optional[str] = None) -> Dict:
        """Get info about available jurisdictions"""
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if jurisdiction_code:
            cursor.execute('SELECT * FROM jurisdictions WHERE code = ?', (jurisdiction_code,))
            row = cursor.fetchone()
            result = dict(row) if row else {}
        else:
            cursor.execute('SELECT * FROM jurisdictions')
            result = {row['code']: dict(row) for row in cursor.fetchall()}
        
        conn.close()
        return result
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        stats = {
            'total_chunks': 0,
            'jurisdictions': {},
            'chunk_types': {},
        }
        
        # Get total chunks
        cursor.execute('SELECT COUNT(*) FROM chunks')
        stats['total_chunks'] = cursor.fetchone()[0]
        
        # Get chunks per jurisdiction
        cursor.execute('''
            SELECT jurisdiction, COUNT(*) as count 
            FROM chunks 
            GROUP BY jurisdiction
        ''')
        for row in cursor.fetchall():
            stats['jurisdictions'][row[0]] = row[1]
        
        # Get chunks per type
        cursor.execute('''
            SELECT chunk_type, COUNT(*) as count 
            FROM chunks 
            GROUP BY chunk_type
        ''')
        for row in cursor.fetchall():
            stats['chunk_types'][row[0]] = row[1]
        
        conn.close()
        return stats


# Singleton instance
def get_database():
    """Get or create the database instance"""
    if not hasattr(get_database, 'instance'):
        get_database.instance = MCPDatabase()
    return get_database.instance
