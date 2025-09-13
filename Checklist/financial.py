"""
Financial Analysis Module

This module calculates financial health scores including resilience, profitability, 
and growth metrics with clean, business-focused logging.
"""

from yfinance import Ticker
from Checklist.utilities.logging_config import get_logger, log_score, log_data_issue, log_segment_start, log_segment_complete, log_debug
from Checklist.settings import (
    DEBT_TO_EQUITY_THRESHOLD,
    ASSETS_TO_DEBT_RATIO,
    CONSECUTIVE_GROWTH_QUARTERS,
    GROSS_MARGIN_HIGH,
    GROSS_MARGIN_MED,
    GROSS_MARGIN_LOW,
    ROE_HIGH,
    ROE_LOW,
    SEGMENT_MAX_SCORES
)

logger = get_logger(__name__)


def calculate_resilience(stock, ticker: str):
    """
    Calculates the **Resilience Score** for a stock.

    **Score Breakdown:**
    - **+2** if `cash > total_debt` (Company has enough cash to cover debt)
    - **+1** if `debt_to_equity < DEBT_TO_EQUITY_THRESHOLD` (Low debt-to-equity ratio)
    - **+1** if `preferred_stock == 0` (Company isn't over-leveraged with preferred stock)
    - **+1** if `total_assets / total_debt > ASSETS_TO_DEBT_RATIO` (Assets cover debt adequately)
    - **+1** if `retained_earnings` show **consecutive quarterly growth**.

    **Returns:** `int` - Resilience score between **0 and 5**.
    """
    log_debug(f"Calculating resilience for {ticker}")
    
    try:
        debt_to_equity = stock.info.get("debtToEquity")
        
        balance_sheet = stock.quarterly_balance_sheet
        if balance_sheet.empty:
            log_data_issue(ticker, "No quarterly balance sheet data available", "Resilience score = 0")
            return 0
        
        total_assets = balance_sheet.loc["Total Assets"].iloc[0] if "Total Assets" in balance_sheet.index else None
        total_debt = balance_sheet.loc["Total Debt"].iloc[0] if "Total Debt" in balance_sheet.index else None
        preferred_stock = balance_sheet.loc["Preferred Stock"].iloc[0] if "Preferred Stock" in balance_sheet.index else None
        cash = balance_sheet.loc["Cash And Cash Equivalents"].iloc[0] if "Cash And Cash Equivalents" in balance_sheet.index else None
        retained_earnings = balance_sheet.loc["Retained Earnings"] if "Retained Earnings" in balance_sheet.index else None

        resilience_score = 0
        key_strengths = []

        if cash and total_debt and cash > total_debt:
            resilience_score += 2
            key_strengths.append("Strong cash position")
        
        if debt_to_equity and debt_to_equity < DEBT_TO_EQUITY_THRESHOLD:
            resilience_score += 1
            key_strengths.append("Low debt-to-equity")
        
        if preferred_stock is None or preferred_stock == 0:
            resilience_score += 1
            key_strengths.append("No preferred stock overhang")
        
        if total_assets and total_debt and total_assets / total_debt > ASSETS_TO_DEBT_RATIO:
            resilience_score += 1
            key_strengths.append("Strong asset coverage")
        
        # Check retained earnings growth
        if retained_earnings is not None and len(retained_earnings) >= CONSECUTIVE_GROWTH_QUARTERS:
            retained_earnings_sorted = retained_earnings[::-1]
            consecutive_growth = retained_earnings_sorted.diff().iloc[-CONSECUTIVE_GROWTH_QUARTERS:].gt(0).all()
            if consecutive_growth:
                resilience_score += 1
                key_strengths.append("Consistent earnings growth")
        
        # Cap score at 5
        final_score = min(resilience_score, 5)
        reasoning = "; ".join(key_strengths) if key_strengths else "Limited financial resilience indicators"
        
        log_score(ticker, "Resilience Score", final_score, 5, reasoning)
        return final_score
        
    except Exception as e:
        logger.error(f"Error calculating resilience for {ticker}: {e}")
        log_data_issue(ticker, f"Resilience calculation failed: {str(e)}", "Score = 0")
        return 0


def calculate_gross_margin(stock, ticker: str):
    """
    Calculates the **Gross Margin Score** based on the company's profitability.

    **Formula:** `Gross Margin = Gross Profit / Revenue`

    **Score Breakdown:**
    - **3** if `gross_margin > GROSS_MARGIN_HIGH` (>80%)
    - **2** if `GROSS_MARGIN_MED <= gross_margin <= GROSS_MARGIN_HIGH` (50-80%)
    - **1** if `gross_margin >= GROSS_MARGIN_LOW` (≥30%)
    - **0** otherwise

    **Returns:** `int` - Gross margin score between **0 and 3**.
    """
    log_debug(f"Calculating gross margin for {ticker}")
    
    try:
        gross_profit = stock.info.get("grossProfits")
        revenue = stock.info.get("totalRevenue")

        if not gross_profit or not revenue:
            log_data_issue(ticker, "Missing gross profit or revenue data", "Gross margin score = 0")
            return 0
        
        gross_margin = gross_profit / revenue
        gross_margin_pct = gross_margin * 100
        
        # Determine score based on margin thresholds
        if gross_margin > GROSS_MARGIN_HIGH:
            score = 3
            reasoning = f"Excellent margin ({gross_margin_pct:.1f}%)"
        elif gross_margin >= GROSS_MARGIN_MED:
            score = 2
            reasoning = f"Good margin ({gross_margin_pct:.1f}%)"
        elif gross_margin >= GROSS_MARGIN_LOW:
            score = 1
            reasoning = f"Moderate margin ({gross_margin_pct:.1f}%)"
        else:
            score = 0
            reasoning = f"Low margin ({gross_margin_pct:.1f}%)"
        
        log_score(ticker, "Gross Margin Score", score, 3, reasoning)
        return score
        
    except Exception as e:
        logger.error(f"Error calculating gross margin for {ticker}: {e}")
        log_data_issue(ticker, f"Gross margin calculation failed: {str(e)}", "Score = 0")
        return 0


def calculate_roe(stock, ticker: str):
    """
    Calculates the **Return on Equity (ROE) Score**.

    **Formula:** `ROE = Net Income / Shareholders' Equity`

    **Score Breakdown:**
    - **2** if `roe > ROE_HIGH` (>15%)
    - **1** if `roe >= ROE_LOW` (≥8%)
    - **+1** if ROE has **grown consecutively over the last few quarters**.

    **Returns:** `int` - ROE score between **0 and 3**.
    """
    log_debug(f"Calculating ROE for {ticker}")
    
    try:
        roe = stock.info.get("returnOnEquity")
        if not roe:
            log_data_issue(ticker, "No ROE data available", "ROE score = 0")
            return 0
        
        roe_pct = roe * 100
        roe_score = 0
        strengths = []
        
        # Base ROE score
        if roe > ROE_HIGH:
            roe_score = 2
            strengths.append(f"Excellent ROE ({roe_pct:.1f}%)")
        elif roe >= ROE_LOW:
            roe_score = 1
            strengths.append(f"Good ROE ({roe_pct:.1f}%)")
        else:
            strengths.append(f"Low ROE ({roe_pct:.1f}%)")

        # Check for ROE growth trend
        try:
            financials = stock.financials
            balance_sheet = stock.balance_sheet
            
            if (not financials.empty and not balance_sheet.empty and 
                "Net Income" in financials.index and "Stockholders Equity" in balance_sheet.index):
                
                net_income = financials.loc["Net Income"]
                equity = balance_sheet.loc["Stockholders Equity"]
                historical_roe = net_income / equity
                
                if len(historical_roe) >= CONSECUTIVE_GROWTH_QUARTERS:
                    roe_growth = historical_roe.diff().iloc[-CONSECUTIVE_GROWTH_QUARTERS:].gt(0).all()
                    if roe_growth:
                        roe_score += 1
                        strengths.append("Growing consistently")
        except:
            pass  # ROE trend analysis failed, continue with base score

        reasoning = "; ".join(strengths)
        log_score(ticker, "ROE Score", roe_score, 3, reasoning)
        return roe_score
        
    except Exception as e:
        logger.error(f"Error calculating ROE for {ticker}: {e}")
        log_data_issue(ticker, f"ROE calculation failed: {str(e)}", "Score = 0")
        return 0


def calculate_fcf_and_eps(stock, ticker: str):
    """
    Calculates **Free Cash Flow (FCF) Score** and **Earnings Per Share (EPS) Score**.

    **Scoring Criteria:**
    - **FCF Score:**
      - **2** if `FCF > 0`
      - **+1** if **FCF has grown for consecutive quarters**.

    - **EPS Score:**
      - **2** if `EPS > 0`
      - **+1** if **EPS has grown for consecutive quarters**.

    **Returns:** `(int, int)` - Tuple containing **(FCF Score, EPS Score)**.
    """
    log_debug(f"Calculating FCF and EPS for {ticker}")
    
    try:
        cashflow = stock.cashflow
        financials = stock.financials
        
        fcf_score = 0
        eps_score = 0
        fcf_strengths = []
        eps_strengths = []
        
        # FCF Analysis
        if not cashflow.empty and "Free Cash Flow" in cashflow.index:
            fcf_data = cashflow.loc["Free Cash Flow"]
            fcf_mean = fcf_data.mean()
            
            if fcf_mean > 0:
                fcf_score = 2
                fcf_strengths.append(f"Positive FCF (${fcf_mean/1e9:.1f}B avg)")
                
                # Check for FCF growth trend
                if len(fcf_data) >= CONSECUTIVE_GROWTH_QUARTERS:
                    fcf_growth = fcf_data.diff().iloc[-CONSECUTIVE_GROWTH_QUARTERS:].gt(0).all()
                    if fcf_growth:
                        fcf_score += 1
                        fcf_strengths.append("Growing consistently")
            else:
                fcf_strengths.append(f"Negative FCF (${fcf_mean/1e9:.1f}B avg)")
        else:
            log_data_issue(ticker, "No FCF data available", "FCF score = 0")

        # EPS Analysis
        if not financials.empty and "Basic EPS" in financials.index:
            eps_data = financials.loc["Basic EPS"]
            eps_mean = eps_data.mean()
            
            if eps_mean > 0:
                eps_score = 2
                eps_strengths.append(f"Positive EPS (${eps_mean:.2f} avg)")
                
                # Check for EPS growth trend
                if len(eps_data) >= CONSECUTIVE_GROWTH_QUARTERS:
                    eps_growth = eps_data.diff().iloc[-CONSECUTIVE_GROWTH_QUARTERS:].gt(0).all()
                    if eps_growth:
                        eps_score += 1
                        eps_strengths.append("Growing consistently")
            else:
                eps_strengths.append(f"Negative EPS (${eps_mean:.2f} avg)")
        else:
            log_data_issue(ticker, "No EPS data available", "EPS score = 0")

        # Log final scores
        fcf_reasoning = "; ".join(fcf_strengths) if fcf_strengths else "No FCF data"
        eps_reasoning = "; ".join(eps_strengths) if eps_strengths else "No EPS data"
        
        log_score(ticker, "FCF Score", fcf_score, 3, fcf_reasoning)
        log_score(ticker, "EPS Score", eps_score, 3, eps_reasoning)
        
        return fcf_score, eps_score
        
    except Exception as e:
        logger.error(f"Error calculating FCF and EPS for {ticker}: {e}")
        log_data_issue(ticker, f"FCF/EPS calculation failed: {str(e)}", "Scores = 0")
        return 0, 0


def fetch_and_score_financials(ticker):
    """
    Fetches financial metrics for a given ticker and calculates all scores.

    **Returns:** `dict` - A dictionary containing all calculated scores.
    """
    log_segment_start(ticker, "FINANCIAL")
    
    try:
        stock = Ticker(ticker)
        
        # Calculate all financial scores
        resilience_score = calculate_resilience(stock, ticker)
        gross_margin_score = calculate_gross_margin(stock, ticker)
        roe_score = calculate_roe(stock, ticker)
        fcf_score, eps_score = calculate_fcf_and_eps(stock, ticker)
        
        scores = {
            "Resilience Score": resilience_score,
            "Gross Margin Score": gross_margin_score,
            "ROE Score": roe_score,
            "FCF Score": fcf_score,
            "EPS Score": eps_score
        }
        
        total_score = sum(v for v in scores.values() if isinstance(v, (int, float)))
        max_score = SEGMENT_MAX_SCORES["Financials"]
        log_score(ticker, "Financials", total_score, max_score, f"Total Financials segment score out of {max_score}")
        log_segment_complete(ticker, "Financials", total_score, max_score)
        return scores
        
    except Exception as e:
        logger.error(f"Error processing financial data for {ticker}: {e}")
        log_data_issue(ticker, f"Financial analysis failed: {str(e)}", "All scores = 0")
        return {
            "Resilience Score": 0,
            "Gross Margin Score": 0,
            "ROE Score": 0,
            "FCF Score": 0,
            "EPS Score": 0
        }
