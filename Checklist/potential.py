"""
Potential Analysis Module

This module evaluates company growth potential through optionality scoring, 
revenue growth analysis, top dog indicators, and operating leverage metrics
with comprehensive business-focused logging.
"""

import logging
import yfinance as yf
from datetime import datetime
from Checklist.utilities.logging_config import get_logger, log_score, log_data_issue, log_segment_start, log_segment_complete, log_debug
from Checklist.settings import (
    MIN_REVENUE_CHANGE,
    SEGMENT_MAX_SCORES
)
from Checklist.utils import (
    setup_logging, 
    get_cached_data,
    get_latest_10k, 
    extract_10k_section, 
    analyze_top_dog_with_spacy
)

# Get logger for this module
logger = get_logger(__name__)

# Setup logging (backward compatibility)
setup_logging()


def calculate_optionality(ticker: str):
    """
    Logs that **Optionality** is a **manual field**.
    """
    log_debug(f"Optionality calculation requested for {ticker}")
    log_score(ticker, "Optionality Score", "MANUAL", None, "Requires manual evaluation of strategic options and future opportunities")
    return None  # Placeholder for future implementation

def calculate_organic_growth_score(ticker: str):
    """
    Logs that Organic Growth is a manual field.

    Returns:
        None
    """
    log_debug(f"Organic growth calculation requested for {ticker}")
    log_score(ticker, "Organic Growth Score", "MANUAL", None, "Requires manual evaluation of projected revenue growth")
    return None

    

def calculate_top_dog(ticker: str):
    """
    Calculates the **Top Dog / First Mover Score** using NLP analysis of 10-K filings,
    focusing specifically on emerging markets and industry disruptors.
    
    **Methodology:**
    1. Fetches the latest 10-K filing for the company
    2. Extracts "Business" and "Risk Factors" sections
    3. Uses context-aware NER analysis to identify:
       - Market Leader indicators in emerging markets
       - First Mover indicators in new technologies/markets
       - Emerging Industry indicators (specific emerging industries)
       - Industry Disruptor indicators (transforming traditional industries)
    4. Distinguishes between positive mentions (company as innovator) and negative mentions (risks)
    5. Assigns score 0-3 based on strength of indicators and presence in emerging industries
    
    **Scoring Logic:**
    - 3 points: Strong evidence of being Top Dog AND First Mover in specific emerging/disruptive industry
    - 2 points: Strong evidence of 2 criteria (e.g., Market Leader + Emerging Industry)
    - 1 point: Evidence of 1 criterion with moderate strength
    - 0 points: Little to no evidence of Top Dog/First Mover status in emerging markets
    
    **Returns:** `int` - Top Dog score between **0 and 3**.
    """
    log_debug(f"Calculating top dog analysis for {ticker}")
    
    try:
        filing = get_latest_10k(ticker)
        if not filing:
            log_data_issue(ticker, "No 10-K filing available", "Top dog score = 0")
            return 0
        
        business_section = extract_10k_section(filing['text'], 'business')
        risk_factors_section = extract_10k_section(filing['text'], 'risk_factors')
        
        if not business_section and not risk_factors_section:
            log_data_issue(ticker, "No business or risk factors sections found", "Top dog score = 0")
            return 0
        
        combined_text = business_section + " " + risk_factors_section
        log_debug(f"Analyzing {len(combined_text):,} characters from 10-K filing for {ticker}")
        
        matches = analyze_top_dog_with_spacy(combined_text, ticker)
        if matches is None:
            log_data_issue(ticker, "Text analysis failed", "Top dog score = 0")
            return 0
        
        score = 0
        strengths = []
        
        emerging_industries = matches.get('EMERGING_INDUSTRIES', {})
        is_emerging_industry = len(emerging_industries) > 0
        
        if not is_emerging_industry:
            max_possible_score = 1
        else:
            max_possible_score = 3
            industries = list(emerging_industries.keys())
            total_mentions = sum(emerging_industries.values())
            
            if total_mentions >= 10:
                score += 1
                strengths.append(f"Strong presence in emerging industries ({total_mentions} mentions)")
            elif total_mentions >= 5:
                score += 0.5
                strengths.append(f"Moderate presence in emerging industries ({total_mentions} mentions)")
        
        market_leader_count = matches.get("MARKET_LEADER", 0)
        if market_leader_count >= 3 and is_emerging_industry:
            score += 1
            strengths.append(f"Market leader in emerging industry ({market_leader_count} indicators)")
        elif market_leader_count >= 1:
            score += 0.5
            strengths.append(f"Potential market leader ({market_leader_count} indicators)")
        
        first_mover_count = matches.get("FIRST_MOVER", 0)
        if first_mover_count >= 5:
            score += 1
            strengths.append(f"First mover advantage ({first_mover_count} indicators)")
        elif first_mover_count >= 2:
            score += 0.5
            strengths.append(f"First mover indicators ({first_mover_count} mentions)")
        
        disruptor_count = matches.get("DISRUPTOR", 0)
        if disruptor_count >= 5:
            score += 1
            strengths.append(f"Industry disruptor ({disruptor_count} indicators)")
        elif disruptor_count >= 2:
            score += 0.5
            strengths.append(f"Disruption indicators ({disruptor_count} mentions)")
        
        final_score = min(max_possible_score, int(round(score)))
        reasoning = "; ".join(strengths) if strengths else "No significant top dog indicators"
        
        log_score(ticker, "Top Dog Score", final_score, 3, reasoning)
        return final_score
        
    except Exception as e:
        logger.error(f"Error calculating top dog score for {ticker}: {e}")
        log_data_issue(ticker, f"Top dog analysis failed: {str(e)}", "Score = 0")
        return 0

def extract_financial_data(ticker: str):
    """
    Extracts revenue and operating income data considering reporting gaps.

    **Returns:**
        - Revenue and Operating Income for TTM and the last 3 years.
    """
    yf_stock = yf.Ticker(ticker)

    financials = yf_stock.financials.T
    quarterly_financials = yf_stock.quarterly_financials.T

    revenue_annual = financials['Total Revenue']
    op_income_annual = financials['Operating Income']

    revenue_annual = revenue_annual.sort_index(ascending=False)
    op_income_annual = op_income_annual.sort_index(ascending=False)

    most_recent_annual_year = revenue_annual.index[0].year
    current_year = datetime.now().year

    if current_year <= most_recent_annual_year + 1:
        revenue_ttm, revenue_1y, revenue_2y, revenue_3y = revenue_annual.iloc[:4]
        op_income_ttm, op_income_1y, op_income_2y, op_income_3y = op_income_annual.iloc[:4]
    else:
        revenue_ttm = quarterly_financials['Total Revenue'].iloc[:4].sum()
        op_income_ttm = quarterly_financials['Operating Income'].iloc[:4].sum()
        revenue_1y, revenue_2y, revenue_3y = revenue_annual.iloc[:3]
        op_income_1y, op_income_2y, op_income_3y = op_income_annual.iloc[:3]

    return revenue_ttm, revenue_1y, revenue_2y, revenue_3y, op_income_ttm, op_income_1y, op_income_2y, op_income_3y


def calculate_operating_leverage(ticker: str):
    """
    Calculates the **Operating Leverage Score** based on revenue and operating income growth.

    **Returns:** `int` - Operating Leverage score between **0 and 4**.
    """
    log_debug(f"Calculating operating leverage for {ticker}")
    
    try:
        revenue_ttm, revenue_1y, revenue_2y, revenue_3y, op_income_ttm, op_income_1y, op_income_2y, op_income_3y = extract_financial_data(ticker)

        rev_change_ttm = (revenue_ttm - revenue_1y) / revenue_1y
        op_change_ttm = (op_income_ttm - op_income_1y) / op_income_1y

        rev_change_1y = (revenue_1y - revenue_2y) / revenue_2y
        op_change_1y = (op_income_1y - op_income_2y) / op_income_2y

        rev_change_2y = (revenue_2y - revenue_3y) / revenue_3y
        op_change_2y = (op_income_2y - op_income_3y) / op_income_3y

        ol_ttm = (op_change_ttm / rev_change_ttm) if rev_change_ttm > MIN_REVENUE_CHANGE else 0
        ol_1y = (op_change_1y / rev_change_1y) if rev_change_1y > MIN_REVENUE_CHANGE else 0
        ol_2y = (op_change_2y / rev_change_2y) if rev_change_2y > MIN_REVENUE_CHANGE else 0

        final_ol = abs(0.4 * ol_ttm) + abs(0.3 * ol_1y) + abs(0.2 * ol_2y)

        if final_ol <= 0:
            score = 0
            reasoning = "No operating leverage"
        elif final_ol <= 1:
            score = 1
            reasoning = f"Low operating leverage ({final_ol:.2f})"
        elif final_ol <= 2:
            score = 2
            reasoning = f"Moderate operating leverage ({final_ol:.2f})"
        elif final_ol <= 3:
            score = 3
            reasoning = f"High operating leverage ({final_ol:.2f})"
        else:
            score = 4
            reasoning = f"Exceptional operating leverage ({final_ol:.2f})"

        log_score(ticker, "Operating Leverage Score", score, 4, reasoning)
        return score

    except Exception as e:
        logger.error(f"Error calculating operating leverage for {ticker}: {e}")
        log_data_issue(ticker, f"Operating leverage calculation failed: {str(e)}", "Score = 0")
        return 0

def fetch_and_score_potential(ticker):
    """
    Analyzes company growth potential through optionality, organic growth, 
    top dog indicators, and operating leverage metrics.
    """
    log_segment_start(ticker, "Potential Analysis")
    
    try:
        scores = {
            "Optionality Score": calculate_optionality(ticker),
            "Organic Growth Score": calculate_organic_growth_score(ticker),
            "Top Dog Score": calculate_top_dog(ticker),
            "Operating Leverage Score": calculate_operating_leverage(ticker)
        }
        
        total_score = sum(v for v in scores.values() if isinstance(v, (int, float)))
        max_score = SEGMENT_MAX_SCORES["Potential"]
        log_score(ticker, "Potential", total_score, max_score, f"Total Potential segment score out of {max_score}")
        log_segment_complete(ticker, "Potential", total_score, max_score)
        return scores
        
    except Exception as e:
        logger.error(f"Error processing potential data for {ticker}: {e}")
        log_data_issue(ticker, f"Potential analysis failed: {str(e)}", "Returning None")
        return None

if __name__ == "__main__":
    symbol = "baba"
    scores = fetch_and_score_potential(symbol)
    print(f"Potential Analysis Results for {symbol}: {scores}")
