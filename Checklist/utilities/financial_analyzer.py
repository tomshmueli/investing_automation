"""
Financial Analyzer Module

This module provides financial data processing and analysis functionality.
Extracted from utils.py to provide better organization and separation of concerns.
"""

import re
from .logging_config import get_logger, log_debug, log_data_issue

logger = get_logger(__name__)


def extract_revenue_recognition_note(filing_text):
    """
    Extract the Revenue Recognition note from financial statements.
    This note contains detailed ASC 606 disclosures including revenue disaggregation.
    
    Returns: str - Revenue recognition note text
    """
    try:
        filing_lower = filing_text.lower()
        
        # Patterns for revenue recognition note
        patterns = [
            r"note\s+\d+\s*[\.\-\s]*revenue\s+recognition",
            r"note\s+\d+\s*[\.\-\s]*revenue\s+from\s+contracts",
            r"revenue\s+recognition\s+and\s+related\s+matters",
            r"revenue\s+from\s+contracts\s+with\s+customers",
            r"note\s+\d+\s*[\.\-\s]*revenues?",
            r"asc\s+606",
            r"topic\s+606"
        ]
        
        section_start = None
        for pattern in patterns:
            match = re.search(pattern, filing_lower)
            if match:
                section_start = match.start()
                log_debug(f"Found revenue recognition note starting at position {section_start}")
                break
        
        if not section_start:
            log_debug("Revenue recognition note not found")
            return ""
        
        # Find section end (next note or major section)
        end_patterns = [
            r"note\s+\d+\s*[\.\-\s]*(?!revenue)",  # Next note
            r"item\s+[2-9]",  # Next major item
            r"consolidated\s+statements?\s+of"  # Financial statements
        ]
        
        section_end = len(filing_text)
        for pattern in end_patterns:
            next_match = re.search(pattern, filing_lower[section_start + 1000:])
            if next_match:
                section_end = section_start + 1000 + next_match.start()
                break
        
        # Limit section size
        section_end = min(section_end, section_start + 100000)
        
        section_text = filing_text[section_start:section_end]
        log_debug(f"Extracted revenue recognition note: {len(section_text)} characters")
        return section_text
        
    except Exception as e:
        logger.error(f"Error extracting revenue recognition note: {e}")
        return ""


def extract_financial_statement_items(filing_text):
    """
    Extract key financial statement line items that indicate recurring revenue.
    
    Returns: dict - Financial metrics and their values
    """
    try:
        text_lower = filing_text.lower()
        findings = {}
        
        # Patterns for deferred revenue / contract liabilities
        deferred_patterns = [
            r"deferred\s+revenue[^$]*\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)",
            r"contract\s+liabilities[^$]*\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)",
            r"unearned\s+revenue[^$]*\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)",
            r"advance\s+payments[^$]*\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)"
        ]
        
        # Patterns for remaining performance obligations
        rpo_patterns = [
            r"remaining\s+performance\s+obligations[^$]*\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)",
            r"contracted\s+but\s+not\s+yet\s+recognized[^$]*\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)",
            r"future\s+contracted\s+revenue[^$]*\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)"
        ]
        
        # Extract deferred revenue amounts
        for pattern in deferred_patterns:
            matches = re.finditer(pattern, text_lower)
            for match in matches:
                amount_str = match.group(1).replace(',', '')
                try:
                    amount = float(amount_str)
                    if 'deferred_revenue' not in findings or amount > findings['deferred_revenue']:
                        findings['deferred_revenue'] = amount
                        log_debug(f"Found deferred revenue: ${amount:,.0f}")
                except ValueError:
                    continue
        
        # Extract remaining performance obligations
        for pattern in rpo_patterns:
            matches = re.finditer(pattern, text_lower)
            for match in matches:
                amount_str = match.group(1).replace(',', '')
                try:
                    amount = float(amount_str)
                    if 'remaining_performance_obligations' not in findings or amount > findings['remaining_performance_obligations']:
                        findings['remaining_performance_obligations'] = amount
                        log_debug(f"Found remaining performance obligations: ${amount:,.0f}")
                except ValueError:
                    continue
        
        return findings
        
    except Exception as e:
        logger.error(f"Error extracting financial statement items: {e}")
        return {}


def analyze_revenue_timing_disclosures(text):
    """
    Analyze ASC 606 revenue timing disclosures (over time vs. point in time).
    
    Returns: dict - Revenue timing analysis
    """
    try:
        text_lower = text.lower()
        findings = {}
        
        # Patterns for revenue timing disclosures
        timing_patterns = [
            # "X% of revenue recognized over time"
            r'(\d{1,3}(?:\.\d{1,2})?)\s*%[^.]{0,100}(?:revenue|sales)[^.]{0,100}(?:recognized|transferred)[^.]{0,100}over\s+time',
            
            # "Revenue recognized over time was $X or Y%"
            r'revenue[^.]{0,100}recognized[^.]{0,100}over\s+time[^.]{0,100}(\d{1,3}(?:\.\d{1,2})?)\s*%',
            
            # "Subscription revenue" or "recurring revenue" percentages
            r'(?:subscription|recurring)[^.]{0,100}revenue[^.]{0,100}(\d{1,3}(?:\.\d{1,2})?)\s*%',
            
            # Point in time vs over time comparisons
            r'(\d{1,3}(?:\.\d{1,2})?)\s*%[^.]{0,100}point\s+in\s+time[^.]{0,100}(\d{1,3}(?:\.\d{1,2})?)\s*%[^.]{0,100}over\s+time'
        ]
        
        for pattern in timing_patterns:
            matches = re.finditer(pattern, text_lower)
            for match in matches:
                # Extract context
                start_pos = max(0, match.start() - 200)
                end_pos = min(len(text), match.end() + 200)
                context = text[start_pos:end_pos].strip()
                
                # Extract percentages
                percentages = [float(g) for g in match.groups() if g and re.match(r'\d+', g)]
                
                for pct in percentages:
                    if 1 <= pct <= 100:  # Valid percentage range
                        if 'over_time_revenue_pct' not in findings or pct > findings['over_time_revenue_pct']:
                            findings['over_time_revenue_pct'] = pct
                            findings['timing_context'] = context[:300]
                            log_debug(f"Found revenue timing disclosure: {pct}% over time")
        
        return findings
        
    except Exception as e:
        logger.error(f"Error analyzing revenue timing disclosures: {e}")
        return {} 