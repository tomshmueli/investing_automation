"""
Text Processor Module

This module provides text processing and section extraction utilities for SEC filings.
Extracted from utils.py to provide better organization and separation of concerns.
"""

import re
from .logging_config import get_logger, log_debug, log_data_issue

logger = get_logger(__name__)


def extract_10k_section(filing_text, section_name):
    """
    Extract specific sections from 10-K filings for efficient processing.
    
    Args:
        filing_text (str): Full 10-K filing text
        section_name (str): Section to extract ('mda', 'risk_factors', 'business', 'legal')
    
    Returns:
        str: Extracted section text, or empty string if not found
    """
    try:
        filing_lower = filing_text.lower()
        
        # Define section patterns
        section_patterns = {
            'mda': [
                r"item\s+2\s*[\.\-\s]*management['\s]*s\s+discussion\s+and\s+analysis",
                r"management['\s]*s\s+discussion\s+and\s+analysis",
                r"item\s+2\s*[\.\-\s]*results\s+of\s+operations",
                r"md&a"
            ],
            'risk_factors': [
                r"item\s+1a\s*[\.\-\s]*risk\s+factors",
                r"risk\s+factors",
                r"item\s+1a\s*[\.\-\s]*risks?\s+relating\s+to"
            ],
            'business': [
                r"item\s+1\s*[\.\-\s]*business",
                r"item\s+1\s*[\.\-\s]*general",
                r"business\s+overview"
            ],
            'legal': [
                r"item\s+3\s*[\.\-\s]*legal\s+proceedings",
                r"legal\s+proceedings"
            ]
        }
        
        patterns = section_patterns.get(section_name.lower(), [])
        if not patterns:
            log_debug(f"Unknown section name: {section_name}")
            return ""
        
        # Find section start
        section_start = None
        for pattern in patterns:
            match = re.search(pattern, filing_lower)
            if match:
                section_start = match.start()
                break
        
        if not section_start:
            log_debug(f"{section_name} section not found in filing")
            return ""
        
        # Find section end based on next major item
        next_section_patterns = {
            'mda': [r"item\s+3\s*[\.\-\s]*legal\s+proceedings", r"item\s+4\s*[\.\-\s]*mine\s+safety", r"item\s+[3-9][a-c]?[\.\s]"],
            'risk_factors': [r"item\s+1b\s*[\.\-\s]*unresolved", r"item\s+2\s*[\.\-\s]*", r"item\s+[2-9][a-c]?[\.\s]"],
            'business': [r"item\s+1a\s*[\.\-\s]*risk\s+factors", r"item\s+1b\s*[\.\-\s]*", r"item\s+[2-9][a-c]?[\.\s]"],
            'legal': [r"item\s+4\s*[\.\-\s]*mine\s+safety", r"item\s+[4-9][a-c]?[\.\s]"]
        }
        
        end_patterns = next_section_patterns.get(section_name.lower(), [r"item\s+[2-9][a-c]?[\.\s]"])
        
        section_end = len(filing_text)  # Default to end of document
        for pattern in end_patterns:
            next_match = re.search(pattern, filing_lower[section_start + 1000:])  # Skip first 1000 chars
            if next_match:
                section_end = section_start + 1000 + next_match.start()
                break
        
        # Limit section size for efficiency (max 150KB)
        section_end = min(section_end, section_start + 150000)
        
        section_text = filing_text[section_start:section_end]
        log_debug(f"Extracted {section_name} section: {len(section_text)} characters")
        return section_text
        
    except Exception as e:
        logger.error(f"Error extracting {section_name} section: {e}")
        return ""


def extract_mda_section(filing_text):
    """
    Convenience function to extract MD&A section specifically.
    
    Returns: str - MD&A section text
    """
    return extract_10k_section(filing_text, 'mda')


def analyze_text_with_keywords(text, keyword_groups, context_window=100):
    """
    Analyze text for keyword groups and return structured findings.
    
    Args:
        text (str): Text to analyze
        keyword_groups (dict): Dictionary of {group_name: [keywords]}
        context_window (int): Characters of context around matches
    
    Returns:
        dict: {group_name: {'count': int, 'contexts': [str]}}
    """
    try:
        text_lower = text.lower()
        results = {}
        
        for group_name, keywords in keyword_groups.items():
            matches = []
            contexts = []
            
            for keyword in keywords:
                # Find all occurrences of this keyword
                start = 0
                while True:
                    pos = text_lower.find(keyword, start)
                    if pos == -1:
                        break
                    
                    # Extract context around the match
                    context_start = max(0, pos - context_window)
                    context_end = min(len(text), pos + len(keyword) + context_window)
                    context = text[context_start:context_end].strip()
                    
                    matches.append(pos)
                    contexts.append(context)
                    start = pos + 1
            
            results[group_name] = {
                'count': len(matches),
                'contexts': contexts[:5]  # Limit to first 5 contexts
            }
        
        return results
        
    except Exception as e:
        logger.error(f"Error analyzing text with keywords: {e}")
        return {} 