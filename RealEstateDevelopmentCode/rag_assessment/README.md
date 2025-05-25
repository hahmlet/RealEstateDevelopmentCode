# RAG Assessment Suite

This directory contains tools for comprehensively testing the accuracy and quality of the Municipal Development Code RAG processing system.

## Tools Overview

### 1. `test_rag_accuracy.py` - Comprehensive Assessment
**Main accuracy testing suite** that runs a complete analysis of the processed RAG data.

**Features:**
- Overall statistics and chunk distribution analysis
- Table extraction quality assessment
- Municipal code topic coverage verification
- Chunk quality and metadata validation
- Source file accuracy comparison
- Sample query generation for retrieval testing

**Usage:**
```bash
cd /workspace/RealEstateDevelopmentCode/rag_assessment
python3 test_rag_accuracy.py
```

**Outputs:**
- `accuracy_assessment_results.json` - Complete results data
- `accuracy_assessment_summary.md` - Human-readable summary report

### 2. `quick_check.py` - Fast Quality Check
**Quick overview** of RAG data quality for rapid assessment.

**Features:**
- Basic statistics (chunk counts, sizes)
- Table formatting quality check
- Municipal code coverage overview
- Quality issues detection
- Sample content preview

**Usage:**
```bash
python3 quick_check.py
```

### 3. `manual_inspector.py` - Interactive Content Review
**Interactive tool** for manual content inspection and quality verification.

**Features:**
- Browse random chunks and tables
- Search content by keywords
- Filter by source files
- Identify quality issues
- Detailed chunk metadata display

**Usage:**
```bash
python3 manual_inspector.py
```

## Assessment Categories

### 📊 Overall Statistics
- Total chunks processed
- Table vs text chunk distribution
- Chunk size analysis
- Source file coverage
- Jurisdiction mapping

### 📋 Table Extraction Quality
- Total tables extracted
- Extraction method comparison
- Markdown formatting assessment
- Municipal table type identification
- Table structure validation

### 🏛️ Municipal Code Coverage
Tests coverage of critical municipal development code topics:
- Zoning regulations
- Parking requirements  
- Setback requirements
- Building height limits
- Landscaping requirements
- Sign regulations
- Subdivision rules
- Conditional use permits
- Variances and appeals
- Enforcement procedures

### ✅ Chunk Quality Assessment
- Content length validation
- Metadata completeness check
- Encoding and formatting issues
- Structural integrity verification

### 🔍 Source Accuracy Verification
- Comparison with original JSON files
- Missing file detection
- Content consistency validation

## Expected Quality Metrics

### 🎯 Target Benchmarks
- **Table Extraction**: >80% of municipal tables captured
- **Table Formatting**: >70% in proper markdown format
- **Content Coverage**: All major municipal topics represented
- **Chunk Quality**: <10% quality issues
- **Metadata Completeness**: >95% chunks with complete metadata

### 🚨 Quality Issue Types
- Empty or extremely short chunks
- Missing metadata fields
- Malformed content (encoding issues)
- Oversized chunks (>5000 characters)
- Improperly extracted tables

## Usage Workflow

### Step 1: Quick Assessment
```bash
python3 quick_check.py
```
Get a rapid overview of data quality.

### Step 2: Comprehensive Analysis
```bash
python3 test_rag_accuracy.py
```
Run full accuracy assessment and generate detailed reports.

### Step 3: Manual Verification
```bash
python3 manual_inspector.py
```
Manually inspect specific content areas and edge cases.

### Step 4: Review Reports
- Check `accuracy_assessment_summary.md` for human-readable results
- Review `accuracy_assessment_results.json` for detailed metrics
- Identify areas needing improvement

## Interpreting Results

### ✅ Good Results Indicators
- High table extraction counts (>100 tables for Gresham)
- Good markdown formatting percentage (>70%)
- Complete municipal topic coverage
- Low quality issue count (<10% of chunks)
- Reasonable chunk size distribution

### ⚠️ Warning Signs
- Many empty or very short chunks
- Low table extraction count
- Missing municipal code topics
- High percentage of quality issues
- Inconsistent metadata

### 🔧 Common Fixes
- **Short chunks**: Adjust chunking parameters
- **Missing tables**: Review table extraction patterns
- **Metadata issues**: Check source file processing
- **Content issues**: Verify JSON parsing logic

## Integration with Development

### Before MCP Server Development
1. Run comprehensive assessment
2. Fix any critical quality issues
3. Verify municipal code coverage
4. Validate table extraction accuracy

### During Agent Development
1. Use sample queries for retrieval testing
2. Monitor chunk relevance to queries
3. Validate agent responses against source content

### Production Monitoring
1. Regular quality checks on new data
2. Track processing success rates
3. Monitor for content drift or issues

## Configuration

Edit the file paths in each script to match your environment:

```python
# Default paths (modify as needed)
rag_data_dir = "/workspace/RealEstateDevelopmentCode/rag_data_accurate/Oregon/gresham"
source_json_dir = "/workspace/RealEstateDevelopmentCode/pdf_content/Oregon/gresham"
output_dir = "/workspace/RealEstateDevelopmentCode/rag_assessment"
```

## Dependencies

All tools use standard Python libraries:
- `json` - JSON file processing
- `pathlib` - File path handling  
- `collections` - Counter and defaultdict
- `random` - Sampling
- `re` - Regular expressions

No additional packages required beyond the base RAG system dependencies.
