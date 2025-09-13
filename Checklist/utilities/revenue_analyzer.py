"""
Revenue Analyzer Module

This module provides recurring revenue analysis and scoring functionality.
Extracted from utils.py to provide better organization and separation of concerns.
"""

import re
from .text_processor import extract_mda_section, analyze_text_with_keywords
from .financial_analyzer import extract_financial_statement_items, analyze_revenue_timing_disclosures
from .logging_config import get_logger, log_debug, log_data_issue

logger = get_logger(__name__)

# Recurring Revenue Business Logic Keywords
RECURRING_REVENUE_KEYWORDS = {
    'strong': [
        'subscription', 'recurring revenue', 'annual recurring revenue', 'monthly recurring revenue',
        'arr', 'mrr', 'saas', 'software as a service', 'subscription-based', 'recurring billing',
        'subscription model', 'recurring subscription', 'subscription fees', 'recurring fees'
    ],
    'moderate': [
        'long-term contract', 'multi-year contract', 'maintenance contract', 'service contract',
        'renewal rate', 'retention rate', 'contract renewal', 'recurring maintenance',
        'support contract', 'license fees', 'recurring license', 'membership fees'
    ],
    'weak': [
        'repeat customer', 'customer loyalty', 'repeat business', 'customer retention',
        'long-term relationship', 'ongoing relationship', 'repeat purchase'
    ]
}


def extract_recurring_revenue_percentage(text, symbol):
    """
    Extract explicit recurring revenue percentages from text using robust pattern matching.
    
    Args:
        text (str): Text to analyze (MD&A section)
        symbol (str): Stock symbol for logging
    
    Returns:
        list: [{'percentage': float, 'context': str, 'evidence_type': str}]
    """
    try:
        findings = []
        text_lower = text.lower()
        
        # Enhanced patterns to capture recurring revenue percentages
        patterns = [
            # Direct percentage statements
            r'(\d{1,3}(?:\.\d{1,2})?)\s*%[^.]{0,100}(?:of|from)[^.]{0,50}(?:revenue|sales)[^.]{0,100}(?:recurring|subscription|maintenance|service|contract)',
            r'(?:recurring|subscription|maintenance|service)[^.]{0,100}(?:revenue|sales)[^.]{0,100}(?:represented|accounted for|comprised)[^.]{0,50}(\d{1,3}(?:\.\d{1,2})?)\s*%',
            
            # Reverse patterns: "recurring revenue represented X%"
            r'(?:recurring|subscription|maintenance|service)[^.]{0,100}(?:revenue|sales)[^.]{0,100}(\d{1,3}(?:\.\d{1,2})?)\s*%',
            
            # ARR/MRR specific patterns
            r'(?:arr|mrr|annual recurring revenue|monthly recurring revenue)[^.]{0,100}(\d{1,3}(?:\.\d{1,2})?)\s*%',
            
            # Contract/subscription base patterns
            r'(\d{1,3}(?:\.\d{1,2})?)\s*%[^.]{0,100}(?:subscription|contract|recurring)',
            
            # Revenue mix patterns
            r'(?:approximately|about|roughly)?\s*(\d{1,3}(?:\.\d{1,2})?)\s*%[^.]{0,100}(?:recurring|subscription|maintenance)',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text_lower)
            for match in matches:
                # Extract the percentage
                percentage_groups = [g for g in match.groups() if g and re.match(r'\d+', g)]
                if not percentage_groups:
                    continue
                    
                percentage = float(percentage_groups[0])
                
                # Skip unrealistic percentages
                if percentage > 100 or percentage < 1:
                    continue
                
                # Extract context around the match (±300 characters)
                start_pos = max(0, match.start() - 300)
                end_pos = min(len(text), match.end() + 300)
                context = text[start_pos:end_pos].strip()
                
                # Clean up context for readability
                context = re.sub(r'\s+', ' ', context)
                
                findings.append({
                    'percentage': percentage,
                    'context': context[:400],  # Limit context length
                    'evidence_type': 'explicit_percentage'
                })
                
                log_debug(f"Found recurring revenue percentage for {symbol}: {percentage}%")
        
        # Remove duplicates (same percentage found multiple times)
        unique_findings = []
        seen_percentages = set()
        for finding in findings:
            pct = finding['percentage']
            if pct not in seen_percentages:
                unique_findings.append(finding)
                seen_percentages.add(pct)
        
        return unique_findings
        
    except Exception as e:
        logger.error(f"Error extracting recurring revenue percentages for {symbol}: {e}")
        return []


def score_recurring_revenue_by_percentage(percentage):
    """
    Score recurring revenue based on actual percentage of total revenue.
    
    Args:
        percentage (float): Percentage of revenue that is recurring
    
    Returns:
        int: Score 0-5 based on materiality
    """
    if percentage >= 80:
        return 5  # Dominant recurring revenue model
    elif percentage >= 60:
        return 4  # Strong recurring revenue component
    elif percentage >= 40:
        return 3  # Significant recurring revenue
    elif percentage >= 20:
        return 2  # Moderate recurring revenue
    elif percentage >= 5:
        return 1  # Minor recurring revenue
    else:
        return 0  # Negligible recurring revenue


def extract_revenue_breakdown_from_financials(filing_text, symbol):
    """
    Extract revenue breakdown from financial statements focusing on subscription/recurring revenue line items.
    This is the most reliable method for SaaS companies.
    
    Returns: dict - Revenue breakdown with percentages
    """
    try:
        text_lower = filing_text.lower()
        findings = {}
        
        # Look for consolidated income statement or revenue breakdown
        income_statement_patterns = [
            r"consolidated\s+statements?\s+of\s+(?:operations|income)",
            r"consolidated\s+statements?\s+of\s+(?:comprehensive\s+)?income",
            r"statements?\s+of\s+operations",
            r"income\s+statements?",
            r"revenue\s+breakdown",
            r"disaggregation\s+of\s+revenue",
            r"revenues?\s*:",  # Simple revenue section
            r"total\s+revenues?"
        ]
        
        statement_sections = []
        for pattern in income_statement_patterns:
            matches = re.finditer(pattern, text_lower)
            for match in matches:
                start_pos = max(0, match.start() - 1000)
                end_pos = min(len(filing_text), match.end() + 20000)
                section = filing_text[start_pos:end_pos]
                statement_sections.append(section)
        
        if not statement_sections:
            log_debug(f"No financial statement section found for {symbol}")
            return {}
        
        # Combine all statement sections for analysis
        combined_text = ' '.join(statement_sections)
        
        # Enhanced patterns for subscription/recurring revenue line items
        subscription_patterns = [
            # Salesforce style: "Subscription and support" with amounts or percentages
            r'subscription\s+and\s+support[^\n]*?(\d{1,3}(?:\.\d{1,2})?)\s*%',
            r'subscription\s+and\s+support[^\n]*?\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)',
            
            # Other common SaaS patterns
            r'subscription\s+revenue[^\n]*?(\d{1,3}(?:\.\d{1,2})?)\s*%',
            r'subscription\s+revenue[^\n]*?\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)',
            r'software\s+subscription[^\n]*?(\d{1,3}(?:\.\d{1,2})?)\s*%',
            r'software\s+subscription[^\n]*?\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)',
            r'recurring\s+revenue[^\n]*?(\d{1,3}(?:\.\d{1,2})?)\s*%',
            r'recurring\s+revenue[^\n]*?\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)',
            
            # License and maintenance
            r'license\s+and\s+maintenance[^\n]*?(\d{1,3}(?:\.\d{1,2})?)\s*%',
            r'license\s+and\s+maintenance[^\n]*?\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)',
            r'maintenance\s+and\s+support[^\n]*?(\d{1,3}(?:\.\d{1,2})?)\s*%',
            r'maintenance\s+and\s+support[^\n]*?\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)',
        ]
        
        # Service revenue patterns (non-recurring)
        service_patterns = [
            r'professional\s+services[^\n]*?(\d{1,3}(?:\.\d{1,2})?)\s*%',
            r'professional\s+services[^\n]*?\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)',
            r'consulting\s+services[^\n]*?(\d{1,3}(?:\.\d{1,2})?)\s*%',
            r'consulting\s+services[^\n]*?\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)',
        ]
        
        # Process subscription patterns
        for pattern in subscription_patterns:
            matches = re.finditer(pattern, combined_text, re.IGNORECASE)
            for match in matches:
                value = match.group(1)
                try:
                    if '%' in match.group(0):
                        findings['subscription_percentage'] = float(value)
                        log_debug(f"Found subscription revenue percentage for {symbol}: {value}%")
                    else:
                        # Handle comma-separated numbers properly
                        clean_value = value.replace(',', '')
                        findings['subscription_amount'] = float(clean_value)
                        log_debug(f"Found subscription revenue amount for {symbol}: ${value}")
                except ValueError as e:
                    log_debug(f"Could not convert value '{value}' to float for {symbol}: {e}")
                    continue
        
        # Process service patterns
        for pattern in service_patterns:
            matches = re.finditer(pattern, combined_text, re.IGNORECASE)
            for match in matches:
                value = match.group(1)
                try:
                    if '%' in match.group(0):
                        findings['service_percentage'] = float(value)
                        log_debug(f"Found service revenue percentage for {symbol}: {value}%")
                    else:
                        # Handle comma-separated numbers properly
                        clean_value = value.replace(',', '')
                        findings['service_amount'] = float(clean_value)
                        log_debug(f"Found service revenue amount for {symbol}: ${value}")
                except ValueError as e:
                    log_debug(f"Could not convert value '{value}' to float for {symbol}: {e}")
                    continue
        
        return findings
        
    except Exception as e:
        logger.error(f"Error extracting revenue breakdown for {symbol}: {e}")
        return {}


def analyze_revenue_recognition_disclosures(filing_text, symbol):
    """
    Analyze revenue recognition disclosures for recurring revenue indicators.
    
    Args:
        filing_text (str): Full text of the filing
        symbol (str): Stock symbol for logging
    
    Returns:
        dict: Analysis results with recurring revenue indicators
    """
    try:
        results = {
            'has_subscription_model': False,
            'has_deferred_revenue': False,
            'has_contract_liabilities': False,
            'revenue_recognition_method': 'unknown',
            'recurring_indicators': []
        }
        
        text_lower = filing_text.lower()
        
        # Look for subscription model indicators
        subscription_indicators = [
            'subscription revenue', 'subscription fees', 'subscription model',
            'recurring revenue', 'annual recurring revenue', 'monthly recurring revenue',
            'saas', 'software as a service', 'subscription-based'
        ]
        
        for indicator in subscription_indicators:
            if indicator in text_lower:
                results['has_subscription_model'] = True
                results['recurring_indicators'].append(indicator)
                log_debug(f"Found subscription indicator for {symbol}: {indicator}")
        
        # Look for deferred revenue indicators
        deferred_indicators = [
            'deferred revenue', 'unearned revenue', 'contract liabilities',
            'advance payments', 'prepaid subscriptions'
        ]
        
        for indicator in deferred_indicators:
            if indicator in text_lower:
                results['has_deferred_revenue'] = True
                results['recurring_indicators'].append(indicator)
                log_debug(f"Found deferred revenue indicator for {symbol}: {indicator}")
        
        # Analyze revenue recognition method
        if 'over time' in text_lower and 'performance obligation' in text_lower:
            results['revenue_recognition_method'] = 'over_time'
        elif 'point in time' in text_lower:
            results['revenue_recognition_method'] = 'point_in_time'
        elif 'ratably' in text_lower or 'straight-line' in text_lower:
            results['revenue_recognition_method'] = 'ratable'
        
        return results
        
    except Exception as e:
        logger.error(f"Error analyzing revenue recognition for {symbol}: {e}")
        return {}


def detect_consumption_based_saas(filing_text, symbol, existing_results):
    """
    Detect consumption-based SaaS models which may have variable recurring revenue.
    
    Args:
        filing_text (str): Full text of the filing
        symbol (str): Stock symbol for logging
        existing_results (dict): Existing analysis results to enhance
    
    Returns:
        dict: Enhanced results with consumption-based indicators
    """
    try:
        text_lower = filing_text.lower()
        
        # Consumption-based indicators
        consumption_indicators = [
            'usage-based', 'consumption-based', 'pay-as-you-go', 'pay-per-use',
            'variable pricing', 'usage pricing', 'metered billing', 'consumption pricing',
            'transaction-based', 'volume-based pricing', 'elastic pricing'
        ]
        
        consumption_score = 0
        found_indicators = []
        
        for indicator in consumption_indicators:
            if indicator in text_lower:
                consumption_score += 1
                found_indicators.append(indicator)
                log_debug(f"Found consumption indicator for {symbol}: {indicator}")
        
        # Enhanced results
        enhanced_results = existing_results.copy()
        enhanced_results['consumption_based_score'] = consumption_score
        enhanced_results['consumption_indicators'] = found_indicators
        enhanced_results['is_consumption_based'] = consumption_score >= 2
        
        return enhanced_results
        
    except Exception as e:
        logger.error(f"Error detecting consumption-based SaaS for {symbol}: {e}")
        return existing_results


def comprehensive_recurring_revenue_analysis(filing_text, symbol):
    """
    Comprehensive recurring revenue analysis combining multiple methods.
    
    Args:
        filing_text (str): Full text of the filing
        symbol (str): Stock symbol for logging
    
    Returns:
        dict: Comprehensive analysis results
    """
    try:
        log_debug(f"Starting comprehensive recurring revenue analysis for {symbol}")
        
        results = {
            'symbol': symbol,
            'analysis_methods': [],
            'recurring_revenue_percentage': None,
            'confidence_level': 'low',
            'evidence_sources': [],
            'business_model_type': 'unknown',
            'score': 0
        }
        
        # Method 1: Extract explicit percentages from MD&A
        percentage_findings = extract_recurring_revenue_percentage(filing_text, symbol)
        if percentage_findings:
            results['analysis_methods'].append('explicit_percentage')
            results['recurring_revenue_percentage'] = percentage_findings[0]['percentage']
            results['confidence_level'] = 'high'
            results['evidence_sources'].extend(percentage_findings)
            log_debug(f"Found explicit recurring revenue percentage for {symbol}: {percentage_findings[0]['percentage']}%")
        
        # Method 2: Financial statement analysis
        financial_breakdown = extract_revenue_breakdown_from_financials(filing_text, symbol)
        if financial_breakdown:
            results['analysis_methods'].append('financial_statements')
            if 'subscription_percentage' in financial_breakdown:
                if not results['recurring_revenue_percentage']:
                    results['recurring_revenue_percentage'] = financial_breakdown['subscription_percentage']
                    results['confidence_level'] = 'high'
                results['evidence_sources'].append({
                    'type': 'financial_statement',
                    'data': financial_breakdown
                })
        
        # Method 3: Revenue recognition analysis
        revenue_recognition = analyze_revenue_recognition_disclosures(filing_text, symbol)
        if revenue_recognition['has_subscription_model']:
            results['analysis_methods'].append('revenue_recognition')
            results['business_model_type'] = 'subscription'
            if results['confidence_level'] == 'low':
                results['confidence_level'] = 'medium'
        
        # Method 4: Consumption-based detection
        results = detect_consumption_based_saas(filing_text, symbol, results)
        if results.get('is_consumption_based'):
            results['business_model_type'] = 'consumption_based'
        
        # Calculate final score
        if results['recurring_revenue_percentage']:
            results['score'] = score_recurring_revenue_by_percentage(results['recurring_revenue_percentage'])
        elif results['business_model_type'] == 'subscription':
            results['score'] = 2  # Default score for subscription models without explicit percentage
        
        log_debug(f"Completed recurring revenue analysis for {symbol}: Score {results['score']}")
        return results
        
    except Exception as e:
        logger.error(f"Error in comprehensive recurring revenue analysis for {symbol}: {e}")
        return {
            'symbol': symbol,
            'analysis_methods': [],
            'recurring_revenue_percentage': None,
            'confidence_level': 'low',
            'evidence_sources': [],
            'business_model_type': 'unknown',
            'score': 0
        } 