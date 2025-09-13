"""
Utilities Package for Portfolio Automation Checklist

This package contains utility modules for various analysis tasks including
financial analysis, caching, logging, and LLM integration.
"""

# Core utilities
from .cache_manager import (
    get_cached_data, load_cache, save_cache
)
from .financial_analyzer import (
    extract_revenue_recognition_note,
    extract_financial_statement_items,
    analyze_revenue_timing_disclosures
)
from .logging_config import setup_logging
from .sec_client import get_latest_10k, get_cash_flow_data
from .text_processor import extract_10k_section, extract_mda_section
from .nlp_analyzer import NLPAnalyzer
from .revenue_analyzer import comprehensive_recurring_revenue_analysis
from .top_dog_analyzer import analyze_top_dog_with_spacy


__all__ = [
    # Core utilities
    "get_cached_data",
    "load_cache", 
    "save_cache",
    "extract_revenue_recognition_note",
    "extract_financial_statement_items",
    "analyze_revenue_timing_disclosures",
    "setup_logging",
    "get_latest_10k",
    "get_cash_flow_data",
    "extract_10k_section",
    "extract_mda_section",
    "NLPAnalyzer",
    "comprehensive_recurring_revenue_analysis",
    "analyze_top_dog_with_spacy",
    
] 