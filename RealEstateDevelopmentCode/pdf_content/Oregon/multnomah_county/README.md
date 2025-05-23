# Multnomah County Document Sources

Place your Multnomah County development code documents here:
- PDF files in `/workspace/RealEstateDevelopmentCode/raw_pdfs/Oregon/multnomah_county/`
- Extracted JSON content in this directory

## Processing
After adding your documents, process them using:
```bash
cd /workspace/RealEstateDevelopmentCode/chunking
python build_rag_system.py --jurisdiction="Oregon/multnomah_county" --source="$(pwd)"
```

## Required Documents
For a complete Multnomah County code representation, you'll need:
- Zoning code documents
- Land use regulations
- Development standards
- Building requirements
- Planning documents
