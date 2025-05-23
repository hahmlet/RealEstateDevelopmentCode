#!/usr/bin/env python3
"""
Enhanced script to analyze the Table of Contents and verify it against our file collection.
Improves on the previous version with more sophisticated matching algorithms.
"""

import json
import sys
import os
from pathlib import Path
import re
import logging
from typing import Dict, List, Any, Optional, Tuple
import difflib
import datetime

# Configure logging to output to console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("toc_analyzer")
logger.setLevel(logging.INFO)

# Set working directory to /workspace/data
os.chdir('/workspace/data')
print("Working directory set to: ", os.getcwd())

# Constants
PDF_CONTENT_DIR = Path("/workspace/data/pdf_content/Oregon/gresham")
TOC_FILE = PDF_CONTENT_DIR / "dc-table-of-contents.json"
RAW_PDF_DIR = Path("/workspace/data/raw_pdfs/Oregon/gresham")
OUTPUT_DIR = Path("/workspace/data/reports/Oregon/gresham")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def load_toc() -> Optional[str]:
    """Load and parse the TOC file."""
    logger.info(f"Looking for TOC file at: {TOC_FILE}")
    if not TOC_FILE.exists():
        logger.error(f"TOC file not found: {TOC_FILE}")
        return None
    
    try:
        with open(TOC_FILE, 'r', encoding='utf-8') as f:
            toc_data = json.load(f)
            
        # Extract text content
        toc_text = ""
        for page in toc_data.get("pages", []):
            toc_text += page.get("text", "")
        
        logger.info(f"TOC text length: {len(toc_text)} characters")
        return toc_text
    except Exception as e:
        logger.error(f"Error loading TOC file: {e}")
        return None

def extract_toc_entries(toc_text: str) -> List[Dict[str, Any]]:
    """Extract entries from the TOC text using improved regexes."""
    if not toc_text:
        return []
    
    toc_entries = []
    
    # Enhanced section patterns to capture more format variations
    section_patterns = [
        # Format: Section 10.0101 Title...[Article]-Page
        r'(?:Section)?\s*(\d+\.\d+)\s+([^\.\n]+?)\.+\s*\[([^\]]+)\]-(\d+)',
        # Format: Section 10.0101 Title...Page
        r'(?:Section)?\s*(\d+\.\d+)\s+([^\.\n]+?)\.+\s*(\d+(?:-\d+)?)',
        # Format: Section 10.0101 Title (no page or article reference)
        r'(?:Section)?\s*(\d+\.\d+)\s+([^\.\n]+?)\s*$',
        # Format: Section 10.0101 with double decimal
        r'(?:Section)?\s*(\d+\.\d+\.\d+)\s+([^\.\n]+?)\.+\s*\[([^\]]+)\]-(\d+)',
        # Format: Section 10.0101 with double decimal, no article reference
        r'(?:Section)?\s*(\d+\.\d+\.\d+)\s+([^\.\n]+?)\.+\s*(\d+(?:-\d+)?)',
    ]
    
    # Article patterns
    article_patterns = [
        # Format: Article # TITLE...[Section Reference]-Page
        r'Article\s+(\d+)(?:\s+|\.)([^\.\n]+?)\.+\s*\[([^\]]+)\]-(\d+)',
        # Format: Article # TITLE...Page
        r'Article\s+(\d+)(?:\s+|\.)([^\.\n]+?)\.+\s*(\d+(?:-\d+)?)',
        # Format: ARTICLE # TITLE
        r'ARTICLE\s+(\d+)(?:\s+|\.)([^\.\n]+?)\s*$',
    ]
    
    # Appendix patterns
    appendix_patterns = [
        # Format: Appendix #.000 TITLE...[Section Reference]-Page
        r'Appendix\s+(\d+\.\d+)(?:\s+|\.)([^\.\n]+?)\.+\s*\[([^\]]+)\]-(\d+)',
        # Format: Appendix #.000 TITLE...Page
        r'Appendix\s+(\d+\.\d+)(?:\s+|\.)([^\.\n]+?)\.+\s*(\d+(?:-\d+)?)',
        # Format: Appendix #.000 TITLE
        r'Appendix\s+(\d+\.\d+)(?:\s+|\.)([^\.\n]+?)\s*$',
        # Format: APPENDIX #.000 TITLE
        r'APPENDIX\s+(\d+(?:\.\d+)?)(?:\s+|\.)([^\.\n]+?)\s*$',
        # Format: Appendix # (without decimal)
        r'Appendix\s+(\d+)(?:\s+|\.)([^\.\n]+?)\.+\s*\[([^\]]+)\]-(\d+)',
        # Format: Appendix # (without decimal)...Page
        r'Appendix\s+(\d+)(?:\s+|\.)([^\.\n]+?)\.+\s*(\d+(?:-\d+)?)',
    ]
    
    # Subsection patterns - for hierarchical structure
    subsection_patterns = [
        # Format: A. Title...Page
        r'^\s*([A-Z])\.\s+([^\.\n]+?)\.+\s*(\d+(?:-\d+)?)',
        # Format: 1. Title...Page
        r'^\s*(\d+)\.\s+([^\.\n]+?)\.+\s*(\d+(?:-\d+)?)',
        # Format: a. Title...Page
        r'^\s*([a-z])\.\s+([^\.\n]+?)\.+\s*(\d+(?:-\d+)?)',
    ]
    
    # Process each pattern type
    for pattern_list, entry_type in [
        (section_patterns, "section"),
        (article_patterns, "article"),
        (appendix_patterns, "appendix"),
        (subsection_patterns, "subsection")
    ]:
        for pattern in pattern_list:
            matches = re.finditer(pattern, toc_text, re.MULTILINE)
            for match in matches:
                groups = match.groups()
                entry = {
                    "type": entry_type,
                    "number": groups[0],
                    "title": groups[1].strip(),
                    "section_ref": "",
                    "page": ""
                }
                
                # Add section reference and page if available
                if len(groups) > 3:
                    entry["section_ref"] = groups[2]
                    entry["page"] = groups[3]
                elif len(groups) > 2:
                    entry["page"] = groups[2]
                
                toc_entries.append(entry)
    
    # Special case for other entry types
    other_patterns = [
        # Format: TITLE...Page (for general entries, table of contents, etc.)
        r'^(?!Article|Appendix|Section|\s*[A-Za-z0-9]\.)([A-Z][^\.]+?)\.+\s*(\d+)$',
    ]
    
    for pattern in other_patterns:
        matches = re.finditer(pattern, toc_text, re.MULTILINE)
        for match in matches:
            groups = match.groups()
            if len(groups) > 0:
                entry = {
                    "type": "other",
                    "number": "",
                    "title": groups[0].strip(),
                    "section_ref": "",
                    "page": groups[1] if len(groups) > 1 else ""
                }
                toc_entries.append(entry)
    
    # Categorize by type for logging
    section_count = sum(1 for e in toc_entries if e["type"] == "section")
    article_count = sum(1 for e in toc_entries if e["type"] == "article")
    appendix_count = sum(1 for e in toc_entries if e["type"] == "appendix")
    subsection_count = sum(1 for e in toc_entries if e["type"] == "subsection")
    other_count = sum(1 for e in toc_entries if e["type"] == "other")
    
    logger.info(f"Extracted {len(toc_entries)} entries from TOC:")
    logger.info(f"- {section_count} sections")
    logger.info(f"- {article_count} articles")
    logger.info(f"- {appendix_count} appendices")
    logger.info(f"- {subsection_count} subsections")
    logger.info(f"- {other_count} other entries")
    
    return toc_entries

def find_all_pdf_files() -> Dict[str, List[str]]:
    """Find all PDF content files in the workspace."""
    section_files = []
    article_files = []
    appendix_files = []
    other_files = []
    all_files = []
    
    # Look for JSON files in the PDF content directory
    for file_path in PDF_CONTENT_DIR.glob("*.json"):
        # Skip the table of contents file
        if file_path.stem == "dc-table-of-contents":
            continue
        
        filename = file_path.stem
        all_files.append(filename)
        
        if "section" in filename.lower():
            section_files.append(filename)
        elif "article" in filename.lower():
            article_files.append(filename)
        elif "appendix" in filename.lower():
            appendix_files.append(filename)
        else:
            other_files.append(filename)
    
    logger.info(f"Found {len(all_files)} PDF content files:")
    logger.info(f"- {len(section_files)} section files")
    logger.info(f"- {len(article_files)} article files")
    logger.info(f"- {len(appendix_files)} appendix files")
    logger.info(f"- {len(other_files)} other files")
    
    return {
        "all": all_files,
        "sections": section_files,
        "articles": article_files,
        "appendices": appendix_files,
        "others": other_files
    }

def normalize_number(number: str, doc_type: str = None) -> str:
    """Normalize document numbers for consistent comparison."""
    if not number:
        return ""
    
    # Special handling for section numbers in format XX.XXXX
    if doc_type == "section" and "." in number:
        parts = number.split('.')
        main_part = parts[0]  # e.g., "10"
        sub_part = parts[1]   # e.g., "0410" or "04" or "0400"
        
        # Make sure we're dealing with the right format
        if sub_part.isdigit():
            # If it's a subsection (e.g., 10.0410), map it to its parent document (10.0400)
            # All entries between XX.XX00 and XX.XX99 belong to document XX.XX00
            if len(sub_part) >= 2:
                # Extract the first two digits and pad with zeros to create the parent document number
                first_two_digits = sub_part[:2]
                return f"{main_part}.{first_two_digits}00"
            else:
                # If it's too short, pad with zeros
                return f"{main_part}.{sub_part.ljust(2, '0')}00"
    
    # For non-section types or non-decimal numbers, just return as is
    return number

def extract_number_from_file(filename: str) -> Optional[Dict[str, str]]:
    """Extract document type and number from filename with improved pattern matching."""
    if not filename:
        return None
    
    # Check for section numbers in format dc-section-10.0100
    section_match = re.search(r'(?:dc-)?section-(\d+\.\d+)', filename, re.IGNORECASE)
    if section_match:
        number = section_match.group(1)
        # Normalize section number for better matching
        normalized_num = normalize_number(number, "section")
        result = {
            "type": "section",
            "number": number,
            "normalized": normalized_num,
            "base_number": number.split('.')[0] if '.' in number else number
        }
        return result
    
    # Check for article numbers in format dc-article-3
    article_match = re.search(r'(?:dc-)?article-(\d+)', filename, re.IGNORECASE)
    if article_match:
        number = article_match.group(1)
        result = {
            "type": "article",
            "number": number,
            "normalized": normalize_number(number),
            "base_number": number
        }
        return result
    
    # Check for appendix numbers in format dc-appendix-5.000
    appendix_match = re.search(r'(?:dc-)?appendix-(\d+(?:\.\d+)?)', filename, re.IGNORECASE)
    if appendix_match:
        number = appendix_match.group(1)
        result = {
            "type": "appendix",
            "number": number,
            "normalized": normalize_number(number),
            "base_number": number.split('.')[0] if '.' in number else number
        }
        return result
    
    return None

def get_file_document_info(available_files: Dict[str, List[str]]) -> Dict[str, Dict]:
    """Create a mapping of detailed document information for each file."""
    file_info = {}
    for filename in available_files["all"]:
        doc_info = extract_number_from_file(filename)
        if doc_info:
            file_info[filename] = doc_info
    
    return file_info

def find_closest_match(entry_number: str, entry_type: str, available_files_info: Dict[str, Dict]) -> List[Tuple[str, float]]:
    """Find the closest matching files for a TOC entry using flexible matching."""
    matches = []
    
    if not entry_number or not entry_type:
        return matches
    
    # Normalize the entry number to map it to its parent document (XX.XX00)
    normalized_entry_num = normalize_number(entry_number, entry_type)
    base_entry_num = entry_number.split('.')[0] if '.' in entry_number else entry_number
    
    for filename, file_info in available_files_info.items():
        if file_info["type"] != entry_type:
            continue
        
        file_num = file_info["number"]
        normalized_file_num = file_info["normalized"]
        base_file_num = file_info["base_number"]
        
        # Exact document match (e.g., 10.0400 === 10.0400) scores highest
        if file_num == entry_number:
            matches.append((filename, 1.0))
            continue
        
        # Parent document match (e.g., entry 10.0410 -> document 10.0400)
        # This is the key matching logic for our use case
        if normalized_file_num == normalized_entry_num:
            # This is a high confidence match because we're following the rule that
            # all entries from XX.XX00 to XX.XX99 belong to document XX.XX00
            matches.append((filename, 0.95))
            continue
            
        # Base number match for fallback (e.g., "10" from "10.0100")
        if base_file_num == base_entry_num:
            # Still give it a low score as a fallback
            matches.append((filename, 0.3))
            continue
    
    # Sort by score (highest first)
    matches.sort(key=lambda x: x[1], reverse=True)
    return matches

def match_files_to_toc_enhanced(toc_entries: List[Dict[str, Any]], available_files: Dict[str, List[str]]) -> Dict[str, Any]:
    """Match TOC entries to available files using enhanced matching algorithm."""
    matched = []
    unmatched_toc = []
    matched_files = set()
    
    # Get detailed document info for each file
    file_document_info = get_file_document_info(available_files)
    
    # Fuzzy matching thresholds
    high_confidence_threshold = 0.9  # Consider high confidence match
    medium_confidence_threshold = 0.7  # Consider acceptable but not perfect
    low_confidence_threshold = 0.5  # Potential match, but needs verification
    
    # First pass: Process each TOC entry
    for entry in toc_entries:
        entry_type = entry["type"]
        entry_number = entry["number"]
        
        # Skip entries without proper type or number
        if not entry_type or not entry_number or entry_type == "other":
            unmatched_toc.append({"toc_entry": entry, "match_score": 0})
            continue
        
        # Find matching files using the updated matching logic
        potential_matches = find_closest_match(entry_number, entry_type, file_document_info)
        
        # Use matches above the threshold
        valid_matches = [(f, s) for f, s in potential_matches if s >= low_confidence_threshold]
        matching_files = [f for f, _ in valid_matches]
        match_score = max([s for _, s in valid_matches]) if valid_matches else 0
        
        # Determine confidence level
        confidence = "none"
        if match_score >= high_confidence_threshold:
            confidence = "high"
        elif match_score >= medium_confidence_threshold:
            confidence = "medium"
        elif match_score >= low_confidence_threshold:
            confidence = "low"
        
        # Create match entry
        match_entry = {
            "toc_entry": entry,
            "matching_files": matching_files,
            "match_score": match_score,
            "confidence": confidence
        }
        
        # Add to appropriate list
        if matching_files:
            matched.append(match_entry)
            # Update tracking of matched files
            for filename in matching_files:
                matched_files.add(filename)
        else:
            unmatched_toc.append(match_entry)
    
    
    # Second pass: Try content-based matching for unmatched entries
    # Create a list of unmatched files
    unmatched_files = [f for f in available_files["all"] if f not in matched_files]
    
    # Get content-based matches for unmatched TOC entries
    remaining_unmatched_toc = []
    for match_entry in unmatched_toc:
        # Skip if unmatched files list is empty
        if not unmatched_files:
            remaining_unmatched_toc.append(match_entry)
            continue
            
        # Try to find content-based matches
        content_matches = find_content_based_matches(match_entry["toc_entry"], unmatched_files)
        
        # If content matches found, update the entry
        if content_matches:
            content_match_files = [f for f, score in content_matches if score >= medium_confidence_threshold]
            
            if content_match_files:
                # Update match entry with content-based matches
                match_entry["matching_files"] = content_match_files
                match_entry["match_score"] = max([score for _, score in content_matches])
                match_entry["confidence"] = "content-based"
                match_entry["match_method"] = "content-based"
                
                # Move entry from unmatched to matched
                matched.append(match_entry)
                
                # Update tracking of matched files
                for filename in content_match_files:
                    matched_files.add(filename)
                    # Remove from unmatched files list
                    if filename in unmatched_files:
                        unmatched_files.remove(filename)
            else:
                # No content matches above threshold
                remaining_unmatched_toc.append(match_entry)
        else:
            # No content matches found
            remaining_unmatched_toc.append(match_entry)
    
    # Update unmatched_toc with entries that couldn't be matched using content
    unmatched_toc = remaining_unmatched_toc
    
    # Determine which files weren't matched to any TOC entry
    not_in_toc = []
    for f in available_files["all"]:
        if f not in matched_files:
            file_info = file_document_info.get(f, {})
            not_in_toc.append({
                "filename": f,
                "type": file_info.get("type", "unknown"),
                "number": file_info.get("number", "")
            })
    
    # Sort results
    matched.sort(key=lambda x: (x['toc_entry']['type'], x['toc_entry']['number']))
    unmatched_toc.sort(key=lambda x: (x['toc_entry']['type'] if 'type' in x['toc_entry'] else "", 
                                       x['toc_entry']['number'] if 'number' in x['toc_entry'] else ""))
    not_in_toc.sort(key=lambda x: x['filename'])
    
    return {
        "matched": matched,
        "unmatched_toc": unmatched_toc,
        "not_in_toc": not_in_toc
    }

def analyze_match_quality(match_results: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze the quality of matches and provide detailed statistics."""
    total_entries = len(match_results["matched"]) + len(match_results["unmatched_toc"])
    match_rate = len(match_results["matched"]) / total_entries if total_entries > 0 else 0
    
    # Analyze match scores
    perfect_matches = sum(1 for m in match_results["matched"] if m["match_score"] >= 0.95)
    good_matches = sum(1 for m in match_results["matched"] if 0.8 <= m["match_score"] < 0.95)
    fair_matches = sum(1 for m in match_results["matched"] if 0.6 <= m["match_score"] < 0.8)
    poor_matches = sum(1 for m in match_results["matched"] if m["match_score"] < 0.6)
    
    # Count by confidence level
    high_confidence = sum(1 for m in match_results["matched"] if m["confidence"] == "high")
    medium_confidence = sum(1 for m in match_results["matched"] if m["confidence"] == "medium")
    low_confidence = sum(1 for m in match_results["matched"] if m["confidence"] == "low")
    content_based = sum(1 for m in match_results["matched"] if m["confidence"] == "content-based")
    
    # Analyze by entry type
    entry_types = {}
    for entry_type in ["section", "article", "appendix"]:
        matched_count = sum(1 for m in match_results["matched"] if m["toc_entry"]["type"] == entry_type)
        unmatched_count = sum(1 for m in match_results["unmatched_toc"] if m["toc_entry"]["type"] == entry_type)
        
        entry_types[entry_type] = {
            "matched": matched_count,
            "unmatched": unmatched_count,
            "total": matched_count + unmatched_count,
            "match_rate": matched_count / (matched_count + unmatched_count) if (matched_count + unmatched_count) > 0 else 0
        }
    
    # Files not in TOC
    files_not_in_toc = len(match_results["not_in_toc"])
    files_not_in_toc_by_type = {}
    for file_info in match_results["not_in_toc"]:
        file_type = file_info.get("type", "unknown")
        if file_type in files_not_in_toc_by_type:
            files_not_in_toc_by_type[file_type] += 1
        else:
            files_not_in_toc_by_type[file_type] = 1
    
    return {
        "total_entries": total_entries,
        "matched_entries": len(match_results["matched"]),
        "unmatched_entries": len(match_results["unmatched_toc"]),
        "match_rate": match_rate,
        "match_quality": {
            "perfect": perfect_matches,
            "good": good_matches,
            "fair": fair_matches,
            "poor": poor_matches
        },
        "confidence_levels": {
            "high": high_confidence,
            "medium": medium_confidence,
            "low": low_confidence,
            "content_based": content_based
        },
        "by_type": entry_types,
        "files_not_in_toc": {
            "total": files_not_in_toc,
            "by_type": files_not_in_toc_by_type
        }
    }

def generate_html_report(match_results: Dict[str, Any], quality_stats: Dict[str, Any]) -> str:
    """Generate a comprehensive HTML report of the TOC analysis."""
    match_rate_percentage = quality_stats["match_rate"] * 100
    perfect_matches = quality_stats["match_quality"]["perfect"]
    good_matches = quality_stats["match_quality"]["good"]
    fair_matches = quality_stats["match_quality"]["fair"]
    poor_matches = quality_stats["match_quality"]["poor"]
    files_not_in_toc = len(match_results["not_in_toc"])
    
    # Create HTML content
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gresham Development Code TOC Analysis</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; }}
        h1, h2, h3 {{ color: #333; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .stats {{ display: flex; flex-wrap: wrap; margin-bottom: 20px; }}
        .stat-card {{ 
            flex: 1; min-width: 200px; margin: 10px; 
            padding: 15px; border-radius: 8px; 
            background: #f5f5f5; box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .stat-value {{ font-size: 24px; font-weight: bold; margin: 10px 0; }}
        .summary {{ margin: 20px 0; padding: 15px; background: #f9f9f9; border-left: 4px solid #3498db; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #f2f2f2; }}
        tr:hover {{ background-color: #f5f5f5; }}
        .score-perfect {{ color: #2ecc71; }}
        .score-good {{ color: #3498db; }}
        .score-fair {{ color: #f39c12; }}
        .score-poor {{ color: #e74c3c; }}
        .confidence-high {{ color: #2ecc71; }}
        .confidence-medium {{ color: #f39c12; }}
        .confidence-low {{ color: #e74c3c; }}
        .confidence-content-based {{ color: #9b59b6; }}
        .tabs {{ display: flex; margin: 20px 0; }}
        .tab {{ 
            padding: 10px 20px; 
            background: #f5f5f5; 
            border: 1px solid #ddd; 
            cursor: pointer;
            margin-right: -1px;
        }}
        .tab.active {{ 
            background: #fff; 
            border-bottom: 1px solid #fff;
            font-weight: bold;
        }}
        .tab-content {{ 
            display: none; 
            border: 1px solid #ddd; 
            padding: 20px;
            margin-top: -1px;
        }}
        .tab-content.active {{ display: block; }}
        .search-box {{ margin: 10px 0; padding: 10px; }}
        .search-box input {{ padding: 8px; width: 100%; max-width: 300px; }}
        .highlight {{ background-color: yellow; }}
        .type-filter {{ margin: 10px 0; }}
        .type-filter button {{ 
            padding: 5px 10px; 
            margin-right: 5px; 
            background: #f2f2f2; 
            border: 1px solid #ddd;
            cursor: pointer;
        }}
        .type-filter button.active {{ 
            background: #3498db; 
            color: white;
            border-color: #2980b9;
        }}
        .chart-container {{ 
            width: 100%; 
            height: 300px; 
            margin: 20px 0;
            display: flex;
        }}
        .chart-bar {{ 
            display: flex;
            flex-direction: column;
            justify-content: flex-end;
            margin: 0 10px;
            flex: 1;
        }}
        .bar {{ 
            background-color: #3498db;
            width: 100%;
            transition: height 0.5s;
        }}
        .bar-label {{ 
            text-align: center;
            padding: 5px 0;
            font-weight: bold;
        }}
        footer {{ 
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            text-align: center;
            color: #777;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Gresham Development Code TOC Analysis</h1>
        <p>Generated on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <div class="summary">
            <h2>Executive Summary</h2>
            <p>Analysis of the Gresham Development Code Table of Contents found {quality_stats["total_entries"]} entries, 
            of which {quality_stats["matched_entries"]} ({match_rate_percentage:.1f}%) were matched to existing files.</p>
            <p>Match quality: {perfect_matches} perfect, {good_matches} good, {fair_matches} fair, and {poor_matches} poor matches.</p>
            <p>There are {files_not_in_toc} files in the system that were not matched to any TOC entry.</p>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <h3>Total Entries</h3>
                <div class="stat-value">{quality_stats["total_entries"]}</div>
            </div>
            <div class="stat-card">
                <h3>Match Rate</h3>
                <div class="stat-value">{match_rate_percentage:.1f}%</div>
            </div>
            <div class="stat-card">
                <h3>Perfect Matches</h3>
                <div class="stat-value">{perfect_matches}</div>
            </div>
            <div class="stat-card">
                <h3>Files Not in TOC</h3>
                <div class="stat-value">{files_not_in_toc}</div>
            </div>
        </div>
        
        <div class="chart-container">
            <div class="chart-bar">
                <div class="bar" style="height: {(quality_stats["by_type"]["section"]["match_rate"] * 100)}%;"></div>
                <div class="bar-label">Sections<br>{quality_stats["by_type"]["section"]["match_rate"]:.1%}</div>
            </div>
            <div class="chart-bar">
                <div class="bar" style="height: {(quality_stats["by_type"]["article"]["match_rate"] * 100)}%;"></div>
                <div class="bar-label">Articles<br>{quality_stats["by_type"]["article"]["match_rate"]:.1%}</div>
            </div>
            <div class="chart-bar">
                <div class="bar" style="height: {(quality_stats["by_type"]["appendix"]["match_rate"] * 100)}%;"></div>
                <div class="bar-label">Appendices<br>{quality_stats["by_type"]["appendix"]["match_rate"]:.1%}</div>
            </div>
            <div class="chart-bar">
                <div class="bar" style="height: {(quality_stats["match_rate"] * 100)}%;"></div>
                <div class="bar-label">Overall<br>{quality_stats["match_rate"]:.1%}</div>
            </div>
        </div>
        
        <div class="tabs">
            <div class="tab active" onclick="openTab(event, 'matched')">Matched Entries</div>
            <div class="tab" onclick="openTab(event, 'unmatched')">Unmatched Entries</div>
            <div class="tab" onclick="openTab(event, 'not-in-toc')">Files Not in TOC</div>
            <div class="tab" onclick="openTab(event, 'statistics')">Statistics</div>
        </div>
        
        <div id="matched" class="tab-content active">
            <div class="search-box">
                <input type="text" id="matchedSearch" placeholder="Search..." onkeyup="searchTable('matchedSearch', 'matchedTable')">
            </div>
            <div class="type-filter">
                <button class="active" onclick="filterTable('matchedTable', 'all')">All</button>
                <button onclick="filterTable('matchedTable', 'section')">Sections</button>
                <button onclick="filterTable('matchedTable', 'article')">Articles</button>
                <button onclick="filterTable('matchedTable', 'appendix')">Appendices</button>
            </div>
            <table id="matchedTable">
                <thead>
                    <tr>
                        <th>Type</th>
                        <th>Number</th>
                        <th>Title</th>
                        <th>Matching Files</th>
                        <th>Match Score</th>
                        <th>Confidence</th>
                    </tr>
                </thead>
                <tbody>
"""
    
    # Add rows for matched entries
    for match in match_results["matched"]:
        entry = match["toc_entry"]
        files = ", ".join(match["matching_files"])
        score = match["match_score"]
        confidence = match["confidence"]
        
        # Determine CSS class for score display
        if score >= 0.95:
            score_class = "score-perfect"
        elif score >= 0.8:
            score_class = "score-good"
        elif score >= 0.6:
            score_class = "score-fair"
        else:
            score_class = "score-poor"
            
        # Determine if this is a content-based match
        match_method = match.get("match_method", "")
        confidence_class = f"confidence-{confidence}"
        
        html += f"""
                    <tr class="entry-{entry['type']}">
                        <td>{entry['type']}</td>
                        <td>{entry['number']}</td>
                        <td>{entry['title']}</td>
                        <td>{files}</td>
                        <td class="{score_class}">{score:.2f}</td>
                        <td class="{confidence_class}">{confidence}{' (content-based)' if match_method == 'content-based' else ''}</td>
                    </tr>
"""
    
    html += """
                </tbody>
            </table>
        </div>
        
        <div id="unmatched" class="tab-content">
            <div class="search-box">
                <input type="text" id="unmatchedSearch" placeholder="Search..." onkeyup="searchTable('unmatchedSearch', 'unmatchedTable')">
            </div>
            <div class="type-filter">
                <button class="active" onclick="filterTable('unmatchedTable', 'all')">All</button>
                <button onclick="filterTable('unmatchedTable', 'section')">Sections</button>
                <button onclick="filterTable('unmatchedTable', 'article')">Articles</button>
                <button onclick="filterTable('unmatchedTable', 'appendix')">Appendices</button>
            </div>
            <table id="unmatchedTable">
                <thead>
                    <tr>
                        <th>Type</th>
                        <th>Number</th>
                        <th>Title</th>
                        <th>Page</th>
                    </tr>
                </thead>
                <tbody>
"""
    
    # Add rows for unmatched entries
    for match in match_results["unmatched_toc"]:
        entry = match["toc_entry"]
        html += f"""
                    <tr class="entry-{entry['type']}">
                        <td>{entry['type']}</td>
                        <td>{entry['number']}</td>
                        <td>{entry['title']}</td>
                        <td>{entry['page']}</td>
                    </tr>
"""
    
    html += """
                </tbody>
            </table>
        </div>
        
        <div id="not-in-toc" class="tab-content">
            <table id="notInTocTable">
                <thead>
                    <tr>
                        <th>Filename</th>
                        <th>Type</th>
                        <th>Number</th>
                    </tr>
                </thead>
                <tbody>
"""
    
    # Add rows for files not in TOC
    for file_info in match_results["not_in_toc"]:
        filename = file_info["filename"]
        file_type = file_info.get("type", "unknown")
        file_number = file_info.get("number", "")
        html += f"""
                    <tr>
                        <td>{filename}</td>
                        <td>{file_type}</td>
                        <td>{file_number}</td>
                    </tr>
"""
    
    html += """
                </tbody>
            </table>
        </div>
        
        <div id="statistics" class="tab-content">
            <h2>Match Quality Statistics</h2>
            <table>
                <tr>
                    <th>Quality Level</th>
                    <th>Count</th>
                    <th>Percentage</th>
                </tr>
"""
    
    # Add match quality statistics
    total_matched = quality_stats["matched_entries"]
    for level, count in quality_stats["match_quality"].items():
        percentage = (count / total_matched) * 100 if total_matched > 0 else 0
        html += f"""
                <tr>
                    <td>{level.capitalize()} Matches</td>
                    <td>{count}</td>
                    <td>{percentage:.1f}%</td>
                </tr>
"""
    
    html += """
            </table>
            
            <h2>Match Confidence Levels</h2>
            <table>
                <tr>
                    <th>Confidence Level</th>
                    <th>Count</th>
                    <th>Percentage</th>
                </tr>
"""
    
    # Add confidence level statistics
    for level, count in quality_stats["confidence_levels"].items():
        percentage = (count / total_matched) * 100 if total_matched > 0 else 0
        html += f"""
                <tr>
                    <td>{level.capitalize()} Confidence</td>
                    <td>{count}</td>
                    <td>{percentage:.1f}%</td>
                </tr>
"""
    
    html += """
            </table>
            
            <h2>Entry Type Statistics</h2>
            <table>
                <tr>
                    <th>Entry Type</th>
                    <th>Total</th>
                    <th>Matched</th>
                    <th>Unmatched</th>
                    <th>Match Rate</th>
                </tr>
"""
    
    # Add entry type statistics
    for entry_type, stats in quality_stats["by_type"].items():
        html += f"""
                <tr>
                    <td>{entry_type.capitalize()}</td>
                    <td>{stats['total']}</td>
                    <td>{stats['matched']}</td>
                    <td>{stats['unmatched']}</td>
                    <td>{stats['match_rate']:.1%}</td>
                </tr>
"""
    
    html += """
            </table>
            
            <h2>Files Not in TOC</h2>
            <table>
                <tr>
                    <th>File Type</th>
                    <th>Count</th>
                </tr>
"""
    
    # Add statistics for files not in TOC
    for file_type, count in quality_stats["files_not_in_toc"]["by_type"].items():
        html += f"""
                <tr>
                    <td>{file_type.capitalize()}</td>
                    <td>{count}</td>
                </tr>
"""
    
    html += """
            </table>
        </div>
        
        <footer>
            <p>Generated by TOC Analyzer &copy; 2025</p>
        </footer>
    </div>

    <script>
        function openTab(evt, tabName) {
            var i, tabcontent, tablinks;
            
            tabcontent = document.getElementsByClassName("tab-content");
            for (i = 0; i < tabcontent.length; i++) {
                tabcontent[i].classList.remove("active");
            }
            
            tablinks = document.getElementsByClassName("tab");
            for (i = 0; i < tablinks.length; i++) {
                tablinks[i].classList.remove("active");
            }
            
            document.getElementById(tabName).classList.add("active");
            evt.currentTarget.classList.add("active");
        }
        
        function searchTable(inputId, tableId) {
            var input, filter, table, tr, td, i, j, txtValue;
            input = document.getElementById(inputId);
            filter = input.value.toUpperCase();
            table = document.getElementById(tableId);
            tr = table.getElementsByTagName("tr");
            
            for (i = 1; i < tr.length; i++) {
                tr[i].style.display = "none";
                for (j = 0; j < tr[i].cells.length; j++) {
                    td = tr[i].cells[j];
                    if (td) {
                        txtValue = td.textContent || td.innerText;
                        if (txtValue.toUpperCase().indexOf(filter) > -1) {
                            tr[i].style.display = "";
                            break;
                        }
                    }
                }
            }
        }
        
        function filterTable(tableId, type) {
            var table, tr, i;
            table = document.getElementById(tableId);
            tr = table.getElementsByTagName("tr");
            
            // Update active button
            var buttons = document.querySelectorAll('.type-filter button');
            for (i = 0; i < buttons.length; i++) {
                buttons[i].classList.remove('active');
                if (buttons[i].textContent.toLowerCase() === type || 
                    (buttons[i].textContent.toLowerCase() === 'all' && type === 'all')) {
                    buttons[i].classList.add('active');
                }
            }
            
            // Filter table rows
            for (i = 1; i < tr.length; i++) {
                if (type === 'all') {
                    tr[i].style.display = "";
                } else if (tr[i].classList.contains('entry-' + type)) {
                    tr[i].style.display = "";
                } else {
                    tr[i].style.display = "none";
                }
            }
        }
    </script>
</body>
</html>
"""
    
    return html

def extract_title_from_pdf_content(filename: str) -> Optional[str]:
    """Extract the title from a PDF content file to enable title-based matching."""
    if not filename.endswith('.json'):
        filename += '.json'
    
    full_path = PDF_CONTENT_DIR / filename
    if not full_path.exists():
        logger.warning(f"File not found: {full_path}")
        return None
    
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content_data = json.load(f)
        
        # Extract title from the first page text content
        if content_data.get("pages") and len(content_data["pages"]) > 0:
            first_page_text = content_data["pages"][0].get("text", "")
            
            # Look for typical section title patterns
            section_title_patterns = [
                # Common pattern: SECTION X.XXXX\nTITLE
                r'SECTION\s+(\d+\.\d+)\s*\n\s*([A-Z][A-Z\s]+)',
                # Alternative: SECTION X.XXXX TITLE
                r'SECTION\s+(\d+\.\d+)\s+([A-Z][A-Z\s]+)',
                # Fallback for other formats
                r'SECTION\s+(\d+\.\d+)(?:\s+|\n)([^\n]+)'
            ]
            
            for pattern in section_title_patterns:
                match = re.search(pattern, first_page_text)
                if match:
                    section_number = match.group(1)
                    section_title = match.group(2).strip()
                    return f"SECTION {section_number} {section_title}"
    
        # If we couldn't extract the title using patterns, try the metadata
        if content_data.get("metadata") and content_data["metadata"].get("title"):
            return content_data["metadata"]["title"]
                    
    except Exception as e:
        logger.error(f"Error extracting title from {filename}: {e}")
    
    return None

def find_content_based_matches(toc_entry: Dict[str, Any], unmatched_files: List[str]) -> List[Tuple[str, float]]:
    """Find matches based on title similarity when number-based matching fails."""
    matches = []
    toc_title = f"{toc_entry['type'].upper()} {toc_entry['number']} {toc_entry['title']}"
    
    for filename in unmatched_files:
        pdf_title = extract_title_from_pdf_content(filename)
        if not pdf_title:
            continue
        
        # Calculate similarity between TOC title and PDF title
        similarity = difflib.SequenceMatcher(None, toc_title.lower(), pdf_title.lower()).ratio()
        
        # Consider it a match if similarity is above threshold
        if similarity >= 0.7:  # Adjust threshold as needed
            matches.append((filename, similarity))
    
    # Sort by similarity score (highest first)
    matches.sort(key=lambda x: x[1], reverse=True)
    return matches

def main():
    """Main function to run the TOC analysis."""
    logger.info("Starting TOC analysis")
    
    # Load TOC
    toc_text = load_toc()
    if not toc_text:
        logger.error("Failed to load TOC text. Exiting.")
        return
    
    # Extract TOC entries
    toc_entries = extract_toc_entries(toc_text)
    if not toc_entries:
        logger.error("Failed to extract entries from TOC. Exiting.")
        return
    
    # Find all PDF files
    available_files = find_all_pdf_files()
    if not available_files["all"]:
        logger.error("No PDF files found. Exiting.")
        return
    
    # Match files to TOC
    logger.info("Matching files to TOC entries...")
    match_results = match_files_to_toc_enhanced(toc_entries, available_files)
    
    # Analyze match quality
    logger.info("Analyzing match quality...")
    quality_stats = analyze_match_quality(match_results)
    
    # Generate and save reports
    logger.info("Generating reports...")
    
    # Save JSON report
    output_json_path = OUTPUT_DIR / "toc_analysis_enhanced.json"
    print(f"Saving JSON report to: {output_json_path}")
    with open(output_json_path, "w") as f:
        json.dump({
            "matched": [{
                "toc_entry": match["toc_entry"],
                "matching_files": match["matching_files"],
                "match_score": match["match_score"],
                "confidence": match["confidence"]
            } for match in match_results["matched"]],
            "unmatched_toc": [{
                "toc_entry": match["toc_entry"],
                "match_score": match["match_score"] if "match_score" in match else 0
            } for match in match_results["unmatched_toc"]],
            "not_in_toc": match_results["not_in_toc"],
            "quality_stats": quality_stats
        }, f, indent=2)
    
    # Generate and save HTML report
    html_report = generate_html_report(match_results, quality_stats)
    output_html_path = OUTPUT_DIR / "toc_analysis_enhanced.html"
    print(f"Saving HTML report to: {output_html_path}")
    with open(output_html_path, "w") as f:
        f.write(html_report)
    
    logger.info(f"\nResults saved to {output_json_path}")
    logger.info(f"HTML Report saved to {output_html_path}")
    logger.info("--- Analysis complete ---")

if __name__ == "__main__":
    main()
