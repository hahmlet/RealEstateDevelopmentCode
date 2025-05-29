# Oregon/gresham Municipal Code RAG Data

## System Overview
- Built: 2025-05-26 17:44:24
- Documents processed: 83
- Tables extracted: 342
- Text chunks: 4571

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
