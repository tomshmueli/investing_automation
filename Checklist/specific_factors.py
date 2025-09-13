"""
Specific Factors Analysis Module

This module implements analysis for specific investment factors that indicate
business quality and competitive advantages:

1. **Recurring Revenue Analysis**: 
   - Comprehensive multi-method analysis using 10-K filings
   - Financial statement revenue breakdown analysis
   - Revenue recognition disclosures (ASC 606)
   - MD&A narrative analysis with NLP
   - Consumption-based SaaS detection
   - Scoring: 0-5 based on percentage of recurring revenue

2. **Pricing Power Analysis**:
   - Rate-sensitive margin trend analysis
   - TTM vs annual margin comparison
   - Volatility-adjusted scoring
   - Multi-year trend direction analysis
   - Scoring: 0-5 based on margin trends and levels

Key Functions:
- calculate_recurring_revenue(): Main recurring revenue scoring function
- calculate_pricing_power(): Main pricing power scoring function
- fetch_and_score_specific_factors(): Entry point for all specific factors

Dependencies:
- Checklist.utils: For 10-K analysis and NLP utilities
- Checklist.settings: For scoring thresholds and configuration
- yfinance: For financial data access

Author: Portfolio Analysis System
"""

import pandas as pd
from yfinance import Ticker
from Checklist.utilities.logging_config import get_logger, log_score, log_data_issue, log_segment_start, log_segment_complete, log_debug

logger = get_logger(__name__)

from Checklist.settings import (
    PRICING_POWER_HIGH_MARGIN,
    PRICING_POWER_MODERATE_MARGIN,
    PRICING_POWER_LOW_MARGIN,
    PRICING_POWER_LOW_VOLATILITY,
    PRICING_POWER_HIGH_VOLATILITY,
    SEGMENT_MAX_SCORES
)

from Checklist.utils import (
    get_latest_10k, 
    analyze_text_with_keywords,
    comprehensive_recurring_revenue_analysis
)

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

# ============================================================================
# RECURRING REVENUE ANALYSIS
# ============================================================================

def calculate_recurring_revenue(stock, ticker: str):
    """
    Calculates recurring revenue score (0-5) using comprehensive multi-section analysis.
    
    **Scoring:** 
    - 5: ≥80% recurring (dominant model)
    - 4: 60-80% recurring (strong component) 
    - 3: 40-60% recurring (significant)
    - 2: 20-40% recurring (moderate)
    - 1: 5-20% recurring (minor)
    - 0: <5% or not mentioned
    
    **Returns:** int - Recurring revenue score (0-5)
    """
    log_debug(f"Calculating recurring revenue for {ticker}")
    
    try:
        business_summary = stock.info.get('longBusinessSummary', '')
        if business_summary:
            keyword_analysis = analyze_text_with_keywords(business_summary, RECURRING_REVENUE_KEYWORDS)
            strong_count = keyword_analysis['strong']['count']
            
            if strong_count >= 3:
                log_debug(f"High confidence indicators in business summary: {strong_count} strong keywords")
        
        filing_data = get_latest_10k(ticker)
        if not filing_data:
            log_data_issue(ticker, "No 10-K filing available", "Using business summary analysis only")
            if business_summary and strong_count >= 3:
                log_score(ticker, "Recurring Revenue Score", 3, 5, "Conservative score based on business summary keywords")
                return 3
            log_score(ticker, "Recurring Revenue Score", 0, 5, "No recurring revenue indicators found")
            return 0
        
        comprehensive_results = comprehensive_recurring_revenue_analysis(filing_data['text'], ticker)
        
        score = comprehensive_results.get('score', 0)
        percentage = comprehensive_results.get('recurring_revenue_percentage', None)
        confidence = comprehensive_results.get('confidence_level', 'low')
        methods = comprehensive_results.get('analysis_methods', [])
        
        if percentage:
            reasoning = f"{percentage}% recurring revenue (confidence: {confidence}/10, methods: {len(methods)})"
        else:
            reasoning = f"Score {score}/5 based on qualitative analysis (confidence: {confidence}/10)"
        
        log_score(ticker, "Recurring Revenue Score", score, 5, reasoning)
        return score
        
    except Exception as e:
        logger.error(f"Error calculating recurring revenue for {ticker}: {e}")
        log_data_issue(ticker, f"Recurring revenue calculation failed: {str(e)}", "Score = 0")
        return 0

# ============================================================================
# PRICING POWER ANALYSIS
# ============================================================================

def calculate_pricing_power(stock, ticker: str, margin_data=None):
    """
    Calculates pricing power score (0-5) using rate-sensitive margin trend analysis.

    **Scoring Components:**
    1. **Base Score (Trend + Rate):** Rising=3, Stable=1, Declining=0-2 (based on decline rate)
    2. **Margin Level:** Ultra-exceptional (85%+)=+3, Exceptional (70%+)=+2, High (50%+)=+1, Low (<20%)=-1
    3. **Volatility:** Low (<3)=+1, High (>5)=-1
    4. **Recent Trend:** Improving=+1, Declining=-1
    5. **TTM Adjustment:** TTM vs latest annual >1.5pp=±1

    **Returns:** int - Pricing power score (0-5)
    """
    log_debug(f"Calculating pricing power for {ticker}")
    
    try:
        if margin_data is None:
            margin_data = extract_gross_margin_trends(stock)
        
        if not margin_data:
            log_data_issue(ticker, "No gross margin data available", "Pricing power score = 0")
            return 0
        
        trend_analysis = analyze_margin_trends(margin_data, ticker)
        if not trend_analysis:
            log_data_issue(ticker, "Insufficient data for trend analysis", "Pricing power score = 0")
            return 0

        score = 0
        avg_margin = trend_analysis.get('avg_margin', 0)
        volatility = trend_analysis.get('volatility', 0)
        recent_trend = trend_analysis.get('recent_trend', 'stable')
        overall_change = trend_analysis.get('overall_change', 0)
        years_analyzed = trend_analysis.get('years_analyzed', 1)
        
        annual_change_rate = overall_change / max(years_analyzed - 1, 1) if years_analyzed > 1 else 0
        
        trend_direction = trend_analysis.get('trend_direction', 'stable')
        if trend_direction == 'rising':
            score = 3
        elif trend_direction == 'stable':
            score = 1
        elif trend_direction == 'declining':
            if abs(annual_change_rate) <= 2.0:
                score = 2
            elif abs(annual_change_rate) <= 4.0:
                score = 1
            else:
                score = 0

        if avg_margin > 85.0:
            score += 3
        elif avg_margin > PRICING_POWER_HIGH_MARGIN:
            score += 2
        elif avg_margin > PRICING_POWER_MODERATE_MARGIN:
            score += 1
        elif avg_margin < PRICING_POWER_LOW_MARGIN:
            score -= 1
        
        if volatility < PRICING_POWER_LOW_VOLATILITY:
            score += 1
        elif volatility > PRICING_POWER_HIGH_VOLATILITY:
            score -= 1
            
        if recent_trend == 'improving':
            score += 1
        elif recent_trend == 'declining':
            score -= 1
        
        ttm_margin = extract_ttm_gross_margin(stock)
        ttm_adjustment = 0
        
        if ttm_margin is not None and len(margin_data) > 0:
            latest_annual_margin = list(margin_data.values())[-1]
            ttm_vs_annual = ttm_margin - latest_annual_margin
            
            if ttm_vs_annual > 1.5:
                ttm_adjustment = 1
            elif ttm_vs_annual < -1.5:
                ttm_adjustment = -1
        
        score += ttm_adjustment
        final_score = max(0, min(score, 5))
        
        reasoning = f"{avg_margin:.1f}% avg margin, {trend_direction} trend ({annual_change_rate:+.1f}%/yr), {volatility:.1f} volatility"
        if ttm_margin:
            reasoning += f", TTM {ttm_margin:.1f}%"
        
        log_score(ticker, "Pricing Power Score", final_score, 5, reasoning)
        return final_score
        
    except Exception as e:
        logger.error(f"Error calculating pricing power for {ticker}: {e}")
        log_data_issue(ticker, f"Pricing power calculation failed: {str(e)}", "Score = 0")
        return 0


def extract_ttm_gross_margin(stock):
    """
    Extracts TTM gross margin from quarterly data (last 4 quarters).
    
    **Returns:** float - TTM gross margin percentage, or None if unavailable
    """
    try:
        quarterly_financials = stock.quarterly_financials
        
        if quarterly_financials.empty:
            return None
        
        revenue = None
        revenue_fields = ['Total Revenue', 'Revenue', 'Net Sales']
        for field in revenue_fields:
            if field in quarterly_financials.index:
                revenue = quarterly_financials.loc[field]
                break
        
        if revenue is None:
            return None
        
        cogs = None
        cogs_fields = ['Cost Of Goods Sold', 'Cost of Revenue', 'Cost Of Revenue', 'Total Costs']
        for field in cogs_fields:
            if field in quarterly_financials.index:
                cogs = quarterly_financials.loc[field]
                break
        
        if cogs is None:
            return None
        
        recent_quarters = min(4, len(revenue))
        
        ttm_revenue = 0
        ttm_cogs = 0
        quarters_used = 0
        
        for i in range(recent_quarters):
            rev_val = revenue.iloc[i] if revenue.iloc[i] and not pd.isna(revenue.iloc[i]) else 0
            cogs_val = cogs.iloc[i] if cogs.iloc[i] and not pd.isna(cogs.iloc[i]) else 0
            
            if rev_val > 0 and cogs_val >= 0:
                ttm_revenue += rev_val
                ttm_cogs += cogs_val
                quarters_used += 1
        
        if quarters_used >= 3 and ttm_revenue > 0:
            ttm_gross_profit = ttm_revenue - ttm_cogs
            ttm_margin = (ttm_gross_profit / ttm_revenue) * 100
            
            return round(ttm_margin, 2)
        else:
            return None
            
    except Exception as e:
        logger.error(f"Error extracting TTM gross margin: {e}")
        return None


def extract_gross_margin_trends(stock):
    """
    Extracts annual gross margin data from income statement (last 3-5 years).
    
    **Returns:** dict - {year: margin_percentage} or empty dict if unavailable
    """
    try:
        financials = stock.financials
        
        if financials.empty:
            return {}
        
        revenue = None
        revenue_fields = ['Total Revenue', 'Revenue', 'Net Sales']
        for field in revenue_fields:
            if field in financials.index:
                revenue = financials.loc[field]
                break
        
        if revenue is None:
            return {}
        
        cogs = None
        cogs_fields = ['Cost Of Goods Sold', 'Cost of Revenue', 'Cost Of Revenue', 'Total Costs']
        for field in cogs_fields:
            if field in financials.index:
                cogs = financials.loc[field]
                break
        
        if cogs is None:
            return {}
        
        margin_data = {}
        for year in revenue.index:
            try:
                rev_val = revenue[year] if revenue[year] and not pd.isna(revenue[year]) else None
                cogs_val = cogs[year] if cogs[year] and not pd.isna(cogs[year]) else None
                
                if rev_val and cogs_val and rev_val > 0:
                    gross_profit = rev_val - cogs_val
                    margin = (gross_profit / rev_val) * 100
                    margin_data[year.year] = round(margin, 2)
            except Exception as year_error:
                logger.warning(f"Error processing year {year}: {year_error}")
                continue
        
        margin_data = dict(sorted(margin_data.items()))
        return margin_data
        
    except Exception as e:
        logger.error(f"Error extracting gross margin trends: {e}")
        return {}


def analyze_margin_trends(margin_data, ticker):
    """
    Analyzes margin trends: direction, volatility, average, recent trend.
    
    **Returns:** dict - Analysis results or empty dict if insufficient data
    """
    try:
        if len(margin_data) < 2:
            logger.warning(f"Not enough margin data for trend analysis for {ticker}")
            return {}
        
        margins = list(margin_data.values())
        years = list(margin_data.keys())
        
        if len(margins) >= 2:
            overall_change = margins[-1] - margins[0]
            trend_direction = "rising" if overall_change > 1 else "declining" if overall_change < -1 else "stable"
        else:
            trend_direction = "insufficient_data"
        
        volatility = 0
        if len(margins) >= 3:
            n = len(margins)
            sum_x = sum(range(n))
            sum_y = sum(margins)
            sum_xy = sum(i * margins[i] for i in range(n))
            sum_x2 = sum(i * i for i in range(n))
            
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
            intercept = (sum_y - slope * sum_x) / n
            
            deviations = []
            for i, margin in enumerate(margins):
                expected = slope * i + intercept
                deviation = abs(margin - expected)
                deviations.append(deviation)
            
            volatility = round(sum(deviations) / len(deviations), 2)
        
        avg_margin = round(sum(margins) / len(margins), 2)
        
        recent_margins = margins[-3:] if len(margins) >= 3 else margins
        recent_trend = "improving" if len(recent_margins) >= 2 and recent_margins[-1] > recent_margins[0] else "declining" if len(recent_margins) >= 2 and recent_margins[-1] < recent_margins[0] else "stable"
        
        analysis = {
            "margin_data": margin_data,
            "trend_direction": trend_direction,
            "overall_change": round(overall_change, 2) if len(margins) >= 2 else 0,
            "volatility": volatility,
            "avg_margin": avg_margin,
            "recent_trend": recent_trend,
            "years_analyzed": len(margins)
        }
        
        return analysis
        
    except Exception as e:
        logger.error(f"Error analyzing margin trends for {ticker}: {e}")
        return {}

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def fetch_and_score_specific_factors(ticker):
    """
    Analyzes specific investment factors: recurring revenue and pricing power.
    """
    log_segment_start(ticker, "Specific Factors Analysis")
    
    stock = Ticker(ticker)
    try:
        scores = {
            "Recurring Revenue Score": calculate_recurring_revenue(stock, ticker),
            "Pricing Power Score": calculate_pricing_power(stock, ticker)
        }
        
        total_score = sum(v for v in scores.values() if isinstance(v, (int, float)))
        max_score = SEGMENT_MAX_SCORES["Company-specific factors"]
        log_score(ticker, "Company-specific factors", total_score, max_score, f"Total Company-specific factors segment score out of {max_score}")
        log_segment_complete(ticker, "Company-specific factors", total_score, max_score)
        return scores
        
    except Exception as e:
        logger.error(f"Error processing specific factors for {ticker}: {e}")
        log_data_issue(ticker, f"Specific factors analysis failed: {str(e)}", "Returning None")
        return None 