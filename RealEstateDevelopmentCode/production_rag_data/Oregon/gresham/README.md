# Oregon/gresham Municipal Code RAG Data

## System Overview
- Built: 2025-05-29 20:13:43
- Documents processed: 83
- Tables extracted: 376
- Text chunks: 4943

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
{
  "method": "get_context",
  "params": {
    "query": "parking requirements",
    "jurisdiction": "Oregon/gresham",
    "max_length": 4000
  }
}
```

See the MCP server documentation for more details.
