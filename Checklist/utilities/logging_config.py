"""
Comprehensive Logging Configuration Module

This module provides a clean, business-focused logging system:
- INFO level: Segment summaries and final scores for client export
- DEBUG level: Concise system operations only
- Clean separation between business insights and technical details
"""

import logging
import logging.handlers
import os
import sys
from typing import Optional, Dict, Any
from ..settings import LOG_LEVEL, LOG_FORMAT, LOG_FILE, LOG_TO_CONSOLE


class BusinessContextFilter(logging.Filter):
    """Filter to add business context to log records"""
    
    def filter(self, record):
        # Add ticker context if not present
        if not hasattr(record, 'ticker'):
            record.ticker = getattr(record, 'ticker', 'UNKNOWN')
        
        # Add business segment context
        if not hasattr(record, 'segment'):
            record.segment = self._determine_segment(record.name)
        
        return True
    
    def _determine_segment(self, logger_name: str) -> str:
        """Determine business segment from logger name"""
        if 'financial' in logger_name.lower():
            return 'FINANCIAL'
        elif 'potential' in logger_name.lower():
            return 'POTENTIAL'
        elif 'customer' in logger_name.lower():
            return 'CUSTOMERS'
        elif 'management' in logger_name.lower():
            return 'MANAGEMENT'
        elif 'stock' in logger_name.lower():
            return 'STOCK'
        elif 'penalties' in logger_name.lower():
            return 'PENALTIES'
        elif 'specific' in logger_name.lower():
            return 'SPECIFIC_FACTORS'
        else:
            return 'SYSTEM'


class PortfolioLoggerAdapter(logging.LoggerAdapter):
    """
    Custom logger adapter for clean, business-focused logging
    """
    
    def __init__(self, logger, extra=None):
        super().__init__(logger, extra or {})
    
    def process(self, msg, kwargs):
        """Add extra context to log messages"""
        extra = kwargs.get('extra', {})
        if self.extra:
            extra.update(self.extra)
        kwargs['extra'] = extra
        return msg, kwargs
    
    def segment_start(self, ticker: str, segment: str):
        """Log start of segment analysis"""
        self.info(f"[{ticker}] Starting {segment} analysis")
    
    def segment_complete(self, ticker: str, segment: str, total_score: int, max_score: int):
        """Log completion of segment analysis"""
        percentage = (total_score / max_score * 100) if max_score > 0 else 0
        self.info(f"[{ticker}] {segment} analysis complete: {total_score}/{max_score} ({percentage:.0f}%)")
    
    def score_result(self, ticker: str, section: str, score: Any, max_score: int = None, reasoning: str = ""):
        """Log final score for a section"""
        if max_score:
            score_display = f"{score}/{max_score}"
        else:
            score_display = str(score)
        
        msg = f"[{ticker}] {section}: {score_display}"
        if reasoning:
            msg += f" - {reasoning}"
        self.info(msg)
    
    def data_issue(self, ticker: str, issue: str, impact: str = ""):
        """Log data issues that affect scoring"""
        msg = f"[{ticker}] Data issue: {issue}"
        if impact:
            msg += f" - {impact}"
        self.warning(msg)
    
    def debug_system(self, message: str):
        """Log concise system/technical information"""
        self.debug(message)


def setup_logging(level: str = None, log_file: str = None, console_output: bool = None) -> None:
    """
    Setup clean, focused logging configuration
    """
    # Use settings defaults if not provided
    level = level or LOG_LEVEL
    log_file = log_file or LOG_FILE
    console_output = console_output if console_output is not None else LOG_TO_CONSOLE
    
    # Get root logger and clear existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # Create business context filter
    business_filter = BusinessContextFilter()
    
    # Console handler - clean business format
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        console_handler.addFilter(business_filter)
        root_logger.addHandler(console_handler)
    
    # File handler - detailed for debugging
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, 
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(getattr(logging, level.upper()))
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(segment)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        file_handler.addFilter(business_filter)
        root_logger.addHandler(file_handler)
        
        # Business summary file - clean for client export
        business_file = log_file.replace('.log', '_business.log')
        business_handler = logging.handlers.RotatingFileHandler(
            business_file,
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3
        )
        business_handler.setLevel(logging.INFO)
        business_formatter = logging.Formatter(
            '%(asctime)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        business_handler.setFormatter(business_formatter)
        
        # Only business-relevant messages
        class BusinessOnlyFilter(logging.Filter):
            def filter(self, record):
                # Only allow INFO+ messages that look like business insights
                return (record.levelno >= logging.INFO and 
                        any(keyword in record.getMessage().lower() 
                            for keyword in ['analysis', 'score', 'complete', 'issue']))
        
        business_handler.addFilter(BusinessOnlyFilter())
        root_logger.addHandler(business_handler)
    
    # Reduce noise from external libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('yfinance').setLevel(logging.WARNING)


def get_logger(name: str, ticker: str = None) -> PortfolioLoggerAdapter:
    """
    Get a configured logger for business analysis
    
    Args:
        name: Logger name (usually module name)
        ticker: Optional ticker symbol for context
    
    Returns:
        PortfolioLoggerAdapter: Business-focused logger
    """
    base_logger = logging.getLogger(name)
    extra = {}
    if ticker:
        extra['ticker'] = ticker
    
    return PortfolioLoggerAdapter(base_logger, extra)


def get_business_logger(ticker: str) -> PortfolioLoggerAdapter:
    """
    Get a logger specifically for business analysis
    
    Args:
        ticker: Ticker symbol for context
    
    Returns:
        PortfolioLoggerAdapter: Business-focused logger
    """
    return get_logger('business_analysis', ticker)


# Simplified logging functions for clean usage
def log_segment_start(ticker: str, segment: str):
    """Log start of segment analysis"""
    logger = get_business_logger(ticker)
    logger.segment_start(ticker, segment)


def log_segment_complete(ticker: str, segment: str, total_score: int, max_score: int):
    """Log completion of segment analysis"""
    logger = get_business_logger(ticker)
    logger.segment_complete(ticker, segment, total_score, max_score)


def log_score(ticker: str, section: str, score: Any, max_score: int = None, reasoning: str = ""):
    """Log final score for a section"""
    logger = get_business_logger(ticker)
    logger.score_result(ticker, section, score, max_score, reasoning)


def log_data_issue(ticker: str, issue: str, impact: str = ""):
    """Log data issues that affect scoring"""
    logger = get_business_logger(ticker)
    logger.data_issue(ticker, issue, impact)


def log_debug(message: str):
    """Log system/technical information"""
    logger = get_logger(__name__)
    logger.debug_system(message) 