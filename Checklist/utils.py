"""
Portfolio Analysis Utilities Module - Compatibility Wrapper

This module maintains backward compatibility while the code has been refactored into
separate utilities modules for better organization.

All functionality has been moved to the utilities package:
- utilities.logging_config: Logging setup
- utilities.cache_manager: Caching system
- utilities.sec_client: SEC filing access
- utilities.nlp_analyzer: NLP analysis framework
- utilities.text_processor: Text processing utilities
- utilities.financial_analyzer: Financial data processing
- utilities.revenue_analyzer: Recurring revenue analysis
- utilities.top_dog_analyzer: Top dog analysis

This file serves as a compatibility wrapper to maintain existing imports.
"""

from .utilities.logging_config import (
    setup_logging, get_logger, log_debug, log_data_issue, log_score, 
    log_segment_start, log_segment_complete
)
from .utilities.cache_manager import get_cached_data, load_cache, save_cache
from .utilities.sec_client import fetch_10k_filing, get_latest_10k, get_cash_flow_data, dataframe_to_dict, dict_to_dataframe
from .utilities.nlp_analyzer import (
    NLPAnalyzer, extract_percentage_sentences, extract_dollar_sentences, is_nlp_available,
    TextFinding, ContextFinding, nlp_analyzer
)
from .utilities.text_processor import extract_10k_section, extract_mda_section, analyze_text_with_keywords
from .utilities.financial_analyzer import (
    extract_revenue_recognition_note, extract_financial_statement_items, analyze_revenue_timing_disclosures
)
from .utilities.revenue_analyzer import (
    comprehensive_recurring_revenue_analysis, extract_recurring_revenue_percentage,
    score_recurring_revenue_by_percentage, extract_revenue_breakdown_from_financials,
    analyze_revenue_recognition_disclosures, detect_consumption_based_saas,
    RECURRING_REVENUE_KEYWORDS
)
from .utilities.top_dog_analyzer import (
    analyze_top_dog_with_spacy, EMERGING_INDUSTRY_TERMS, TOP_DOG_PATTERNS, TOP_DOG_KEYWORDS
)

# Re-export everything for backward compatibility
__all__ = [
    # Logging
    'setup_logging', 'get_logger', 'log_debug', 'log_data_issue', 'log_score',
    'log_segment_start', 'log_segment_complete',
    
    # Caching
    'get_cached_data', 'load_cache', 'save_cache',
    
    # SEC Client
    'fetch_10k_filing', 'get_latest_10k', 'get_cash_flow_data', 'dataframe_to_dict', 'dict_to_dataframe',
    
    # NLP Analyzer
    'NLPAnalyzer', 'extract_percentage_sentences', 'extract_dollar_sentences', 'is_nlp_available',
    'TextFinding', 'ContextFinding', 'nlp_analyzer',
    
    # Text Processor
    'extract_10k_section', 'extract_mda_section', 'analyze_text_with_keywords',
    
    # Financial Analyzer
    'extract_revenue_recognition_note', 'extract_financial_statement_items', 'analyze_revenue_timing_disclosures',
    
    # Revenue Analyzer
    'comprehensive_recurring_revenue_analysis', 'extract_recurring_revenue_percentage',
    'score_recurring_revenue_by_percentage', 'extract_revenue_breakdown_from_financials',
    'analyze_revenue_recognition_disclosures', 'detect_consumption_based_saas',
    'RECURRING_REVENUE_KEYWORDS',
    
    # Top Dog Analyzer
    'analyze_top_dog_with_spacy', 'EMERGING_INDUSTRY_TERMS', 'TOP_DOG_PATTERNS', 'TOP_DOG_KEYWORDS'
]

# Setup logging when utils is imported (maintains original behavior)
setup_logging()