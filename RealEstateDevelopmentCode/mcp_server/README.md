# Multi-Jurisdiction Municipal Code MCP Server

## Overview
This is a standalone Model Context Protocol (MCP) server that provides unified access to municipal development codes from multiple jurisdictions. It's designed to serve as the data backend for AI agents that need to work with municipal code data.

## Features

- **Multi-jurisdiction support**: One server handles multiple municipal codes
- **Cross-jurisdiction queries**: Compare codes across different municipalities
- **Table-optimized retrieval**: Special handling for tables and structured content
- **Efficient SQLite storage**: Fast and lightweight database for quick retrieval
- **MCP-compliant API**: Standard protocol for AI agent integration

## Directory Structure

```
/mcp_server/
├── server.py         # Main server implementation
├── config.py         # Server configuration
├── database.py       # Database handling
├── requirements.txt  # Dependencies
└── database/         # SQLite storage
    └── mcp_chunks.db # Chunk database
```

## Installation

```bash
cd /workspace/RealEstateDevelopmentCode/mcp_server
pip install -r requirements.txt
```

## Usage

### Starting the Server

```bash
cd /workspace/RealEstateDevelopmentCode/mcp_server
python server.py
```

The server will load data from all configured jurisdictions and start listening on port 8000.

### Available API Methods

#### Search for content
```json
{
  "method": "search",
  "params": {
    "query": "parking requirements",
    "jurisdiction": "Oregon/gresham",  
    "limit": 10,
    "include_tables": true
  }
}
```

#### Get AI context
```json
{
  "method": "get_context",
  "params": {
    "query": "setback requirements",
    "jurisdiction": "Oregon/gresham",
    "max_length": 4000
  }
}
```

#### Get document chunks
```json
{
  "method": "get_document",
  "params": {
    "document_id": "10.0500",
    "jurisdiction": "Oregon/gresham"
  }
}
```

#### Compare jurisdictions
```json
{
  "method": "compare",
  "params": {
    "query": "parking requirements",
    "jurisdictions": ["Oregon/gresham", "Oregon/multnomah_county"],
    "max_length": 5000
  }
}
```

#### Get available jurisdictions
```json
{
  "method": "get_jurisdictions",
  "params": {}
}
```

#### Get server statistics
```json
{
  "method": "get_statistics",
  "params": {}
}
```

## Adding New Jurisdictions

1. Process the jurisdiction's documents with the chunking tools:
   ```bash
   cd /workspace/RealEstateDevelopmentCode/chunking
   python accurate_municipal_rag.py --source_dir=/path/to/jurisdiction/docs --output_dir=/workspace/RealEstateDevelopmentCode/rag_data/State/jurisdiction
   ```

2. Update the `config.py` file to include the new jurisdiction:
   ```python
   AVAILABLE_JURISDICTIONS = {
       # ...existing jurisdictions...
       "State/jurisdiction": {
           "name": "Jurisdiction Name",
           "state": "State",
           "data_path": RAG_DATA_DIR / "State" / "jurisdiction",
           "chunks_file": "accurate_chunks.jsonl",
       }
   }
   ```

3. Restart the MCP server to load the new jurisdiction.

## Client Integration

```python
import aiohttp
import asyncio
import json

class MCPClient:
    def __init__(self, endpoint="http://localhost:8000/mcp"):
        self.endpoint = endpoint
        
    async def request(self, method, params=None):
        if params is None:
            params = {}
            
        request_data = {
            "method": method,
            "params": params
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(self.endpoint, json=request_data) as response:
                return await response.json()

async def example_usage():
    client = MCPClient()
    
    # Get context for an AI query
    context_result = await client.request('get_context', {
        'query': 'parking requirements for commercial buildings',
        'jurisdiction': 'Oregon/gresham',
        'max_length': 2000
    })
    
    # Use the context in your AI prompt
    prompt = f'''
You are an expert on municipal development codes.
Use the following municipal code information to answer the question.

{context_result['result']['context']}

QUESTION: What are the parking requirements for commercial buildings?
'''
    
    # Send this prompt to your AI model
    # ai_response = await your_ai_client.generate(prompt)
    
    print("Example integration complete")

if __name__ == "__main__":
    asyncio.run(example_usage())
```
