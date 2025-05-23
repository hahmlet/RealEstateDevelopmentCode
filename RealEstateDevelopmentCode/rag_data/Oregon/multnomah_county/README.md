# Multnomah County Development Code RAG Data

## Jurisdiction Information
- **Name**: Multnomah County
- **State**: Oregon
- **Jurisdiction ID**: Oregon/multnomah_county
- **Date Processed**: May 23, 2025

## Processing Status
- ⚠️ **Pending Processing** - This jurisdiction is prepared for document processing
- 📋 **Documents Needed** - Place source documents in `/workspace/RealEstateDevelopmentCode/pdf_content/Oregon/multnomah_county/`

## How to Process
Process this jurisdiction's documents with:
```bash
cd /workspace/RealEstateDevelopmentCode/chunking
python build_rag_system.py --jurisdiction="Oregon/multnomah_county" --source="/workspace/RealEstateDevelopmentCode/pdf_content/Oregon/multnomah_county"
```

## Integration with MCP Server
Once processed, this jurisdiction will be automatically available through the MCP server alongside Gresham:

```python
# Example comparison query
response = await mcp_client.request('compare', {
    'query': 'zoning requirements',
    'jurisdictions': ['Oregon/gresham', 'Oregon/multnomah_county']
})
```

## Document Requirements
For optimal processing, documents should be in PDF format and contain:
- Clear text content (not just images)
- Tables with visible borders when possible
- Consistent section numbering
