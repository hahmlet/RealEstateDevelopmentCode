# Municipal Code RAG System

## Overview
This system provides AI agents with access to municipal development codes through a standardized Model Context Protocol (MCP) interface. The architecture is designed to support multiple jurisdictions and ensures accurate representation of complex document structures including tables.

## Architecture

```
/workspace/RealEstateDevelopmentCode/
│
├── chunking/                   # Document processing tools
│   ├── accurate_municipal_rag.py  # Multi-tool extraction w/ table accuracy
│   ├── build_rag_system.py        # Builds RAG data for jurisdictions
│   ├── requirements.txt           # Chunking dependencies
│   └── README.md                  # Documentation
│
├── mcp_server/                 # Standalone MCP server
│   ├── server.py               # Main multi-jurisdiction server
│   ├── config.py               # Server configuration
│   ├── database.py             # Database module
│   ├── client_example.py       # Example client usage
│   ├── requirements.txt        # Server dependencies
│   └── README.md               # Server documentation
│
└── rag_data/                   # Processed data for all jurisdictions
    ├── Oregon/
    │   ├── gresham/            # City of Gresham data
    │   └── multnomah_county/   # Multnomah County data (when added)
    └── Washington/             # Could add more states/jurisdictions
        └── ...
```

## Components

### 1. Document Processing (`/chunking/`)
The chunking module processes raw documents and prepares them for RAG usage:

- **Multi-tool extraction** with Unstructured.io, Camelot, and Tabula
- **Table-optimized processing** for maximum accuracy
- **Structure preservation** with hierarchical chunking
- **Output to jurisdiction-specific directories** in the shared rag_data structure

### 2. MCP Server (`/mcp_server/`)
The standalone MCP server provides unified access to all jurisdictions:

- **Multi-jurisdiction support** in a single server
- **Cross-jurisdiction queries** for comparing different municipal codes
- **Efficient SQLite storage** for fast retrieval
- **Standard MCP API** for AI agent integration

## Usage

### 1. Process Documents for a Jurisdiction

```bash
cd /workspace/RealEstateDevelopmentCode/chunking
python build_rag_system.py --source=/path/to/docs --jurisdiction=State/locality
```

### 2. Start the MCP Server

```bash
cd /workspace/RealEstateDevelopmentCode/mcp_server
python server.py
```

### 3. Query from an AI Agent

```python
async def get_municipal_code_context(query, jurisdiction=None):
    response = await mcp_client.request('get_context', {
        'query': query,
        'jurisdiction': jurisdiction
    })
    return response['result']['context']
    
# Use in AI prompt
prompt = f"""
You are an expert on municipal development codes.
Use the following municipal code information to answer the question.

{await get_municipal_code_context('parking requirements', 'Oregon/gresham')}

QUESTION: What are the parking requirements for commercial buildings?
"""
```

## Adding New Jurisdictions

1. Process the jurisdiction:
   ```bash
   python chunking/build_rag_system.py --source=/path/to/docs --jurisdiction=State/locality
   ```

2. Update the server config:
   ```python
   # Edit mcp_server/config.py
   AVAILABLE_JURISDICTIONS = {
       # ...existing jurisdictions...
       "State/locality": {
           "name": "Locality Name",
           "state": "State",
           # ...
       }
   }
   ```

3. Restart the MCP server to load the new jurisdiction.

## Benefits of This Architecture

- **Unified API**: One endpoint for accessing all municipal codes
- **Cross-jurisdiction capability**: Compare different municipal policies
- **Centralized maintenance**: Update one server codebase
- **Optimal table handling**: Special processing for accurate tables
- **Modular design**: Add new jurisdictions easily

For more details, see the README files in each component directory.
