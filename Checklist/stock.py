import pandas as pd
from yfinance import Ticker
import json
from datetime import datetime, timedelta
from pathlib import Path
from Checklist.settings import (
    SP500_TICKER, 
    PERFORMANCE_MARGIN_INLINE, 
    PERFORMANCE_THRESHOLD_50, 
    PERFORMANCE_THRESHOLD_100,
    CACHE_EXPIRY_DAYS,
    SEGMENT_MAX_SCORES
)
from Checklist.utils import (
    get_cached_data,
    dataframe_to_dict,
    dict_to_dataframe,
    get_cash_flow_data
)
from Checklist.utilities.logging_config import get_logger, log_score, log_data_issue, log_segment_start, log_segment_complete, log_debug

logger = get_logger(__name__)

# Cache file path
PERFORMANCE_CACHE_PATH = Path(__file__).parent / "cache" / "performance_cache.json"

def load_performance_cache():
    """Load performance data from cache file."""
    try:
        if PERFORMANCE_CACHE_PATH.exists():
            with open(PERFORMANCE_CACHE_PATH, 'r') as f:
                cache = json.load(f)
                last_updated = datetime.fromisoformat(cache['last_updated'])
                if datetime.now() - last_updated < timedelta(days=CACHE_EXPIRY_DAYS):
                    return cache
        return {"last_updated": "", "data": {}}
    except Exception as e:
        logger.error(f"Error loading performance cache: {e}")
        return {"last_updated": "", "data": {}}

def save_performance_cache(cache):
    """Save performance data to cache file."""
    try:
        cache['last_updated'] = datetime.now().isoformat()
        with open(PERFORMANCE_CACHE_PATH, 'w') as f:
            json.dump(cache, f, indent=4)
    except Exception as e:
        logger.error(f"Error saving performance cache: {e}")

def fetch_stock_performance(ticker, period="5y"):
    """Fetch stock performance data from API."""
    stock = Ticker(ticker)
    sp500 = Ticker(SP500_TICKER)
    
    stock_history = stock.history(period=period)
    if stock_history.empty:
        logger.warning(f"No historical data found for {ticker}")
        return None
        
    start_date = stock_history.index[0]
    sp500_history = sp500.history(start=start_date)
    
    if sp500_history.empty:
        logger.warning(f"Could not fetch S&P 500 data for comparison period")
        return None
    
    stock_dict = dataframe_to_dict(stock_history)
    sp500_dict = dataframe_to_dict(sp500_history)
    
    return {
        'stock_history': stock_dict,
        'sp500_history': sp500_dict,
        'start_date': start_date.isoformat()
    }

def get_stock_performance(ticker, period="5y"):
    """
    Get stock performance data, using cache if available.
    Returns tuple of (stock_history, sp500_history, start_date)
    """
    cache_key = f"{ticker.lower()}_{period}"
    data, _ = get_cached_data("performance_cache.json", cache_key, fetch_stock_performance, ticker, period)
    
    if data is None:
        return None, None, None
        
    stock_history = dict_to_dataframe(data['stock_history'])
    sp500_history = dict_to_dataframe(data['sp500_history'])
    start_date = pd.Timestamp(data['start_date'])
    
    return stock_history, sp500_history, start_date

def calculate_5_year_performance_vs_sp500(ticker):
    """
    Calculates the 5-Year Performance Score compared to S&P 500.

    **Score Breakdown:**
    - **0:** Underperformed or negative return
    - **1:** Inline with S&P 500 (within ±10%)
    - **2:** Outperformed by +50%
    - **3:** Outperformed by +100%
    - **4:** Significantly above +100%

    **Returns:** `int` - Performance score between **0 and 4**.
    """
    log_debug(f"Calculating 5-year performance for {ticker}")
    
    try:
        stock_history, sp500_history, _ = get_stock_performance(ticker, "5y")
        
        if stock_history is None or sp500_history is None:
            log_data_issue(ticker, "Insufficient performance data", "Performance score = 0")
            return 0

        stock_start_price = stock_history['Close'].iloc[0]
        stock_end_price = stock_history['Close'].iloc[-1]
        stock_performance = (stock_end_price - stock_start_price) / stock_start_price

        sp500_start_price = sp500_history['Close'].iloc[0]
        sp500_end_price = sp500_history['Close'].iloc[-1]
        sp500_performance = (sp500_end_price - sp500_start_price) / sp500_start_price

        performance_diff = stock_performance - sp500_performance

        if stock_performance <= 0 or performance_diff < -PERFORMANCE_MARGIN_INLINE:
            score = 0
            reasoning = f"Underperformed S&P 500 ({stock_performance*100:.1f}% vs {sp500_performance*100:.1f}%)"
        elif abs(performance_diff) <= PERFORMANCE_MARGIN_INLINE:
            score = 1
            reasoning = f"Inline with S&P 500 ({stock_performance*100:.1f}% vs {sp500_performance*100:.1f}%)"
        elif performance_diff > PERFORMANCE_THRESHOLD_100:
            score = 4
            reasoning = f"Significantly outperformed S&P 500 (+{performance_diff*100:.1f}%)"
        elif performance_diff > PERFORMANCE_THRESHOLD_50:
            score = 3
            reasoning = f"Outperformed S&P 500 (+{performance_diff*100:.1f}%)"
        else:
            score = 2
            reasoning = f"Moderately outperformed S&P 500 (+{performance_diff*100:.1f}%)"

        log_score(ticker, "5-Year Performance Score", score, 4, reasoning)
        return score

    except Exception as e:
        logger.error(f"Error calculating performance for {ticker}: {e}")
        log_data_issue(ticker, f"Performance calculation failed: {str(e)}", "Score = 0")
        return 0

def calculate_shareholder_friendly_actions(ticker):
    """
    Calculates the Shareholder Friendly Actions Score based on buybacks, dividends, and debt repayment.

    **Score Breakdown:**
    - **0:** No consistent shareholder-friendly actions
    - **1:** 1 out of 3 factors consistent (buybacks, dividends, debt repayment)
    - **2:** 2 out of 3 factors consistent
    - **3:** All 3 factors consistent

    **Returns:** `int` - Score between **0 and 3**.
    """
    log_debug(f"Calculating shareholder friendly actions for {ticker}")
    
    try:
        cashflow = get_cash_flow_data(ticker)
        if cashflow is None:
            log_data_issue(ticker, "Cash flow data unavailable", "Shareholder actions score = 0")
            return 0

        def is_consistent(series):
            negative_years = series.head(4).fillna(0).lt(0).sum()
            return negative_years >= 3

        def is_dividend_stable(series):
            series = series.head(4).fillna(0)
            negative_years = series.lt(0).sum()
            avg_dividend = abs(series.mean())
            return negative_years >= 3 and avg_dividend > 0

        buybacks_consistent = is_consistent(cashflow.loc["Repurchase Of Capital Stock"]) if "Repurchase Of Capital Stock" in cashflow.index else False
        dividends_stable = is_dividend_stable(cashflow.loc["Cash Dividends Paid"]) if "Cash Dividends Paid" in cashflow.index else False
        debt_repayment_consistent = is_consistent(cashflow.loc["Repayment Of Debt"]) if "Repayment Of Debt" in cashflow.index else False

        consistent_factors = sum([buybacks_consistent, dividends_stable, debt_repayment_consistent])
        
        actions = []
        if buybacks_consistent:
            actions.append("buybacks")
        if dividends_stable:
            actions.append("dividends")
        if debt_repayment_consistent:
            actions.append("debt repayment")
        
        reasoning = f"{consistent_factors}/3 factors consistent: {', '.join(actions)}" if actions else "No consistent shareholder-friendly actions"
        
        log_score(ticker, "Shareholder Friendly Actions Score", consistent_factors, 3, reasoning)
        return consistent_factors

    except Exception as e:
        logger.error(f"Error calculating shareholder-friendly actions for {ticker}: {e}")
        log_data_issue(ticker, f"Shareholder actions calculation failed: {str(e)}", "Score = 0")
        return 0


def calculate_beats_expectations(ticker):
    """
    Calculates the Consistently Beats Expectations Score based on earnings history.
    
    **Scoring Criteria:**
    - Base Score (0-2 points): Percentage of beats in last 4 quarters
        * 75%+ beats -> 2 points
        * 50%+ beats -> 1 point
        * <50% beats -> 0 points
    
    - Magnitude Bonus (0-2 points):
        * Average surprise > 15% -> 2 points
        * Average surprise > 5%  -> 1 point
        * Negative surprises     -> 0 points
    
    **Returns:** `int` - Score between **0 and 4**.
    """
    log_debug(f"Calculating beats expectations for {ticker}")
    
    try:
        stock = Ticker(ticker)
        
        earnings = stock.earnings_history
        
        if earnings.empty or len(earnings) < 4:
            log_data_issue(ticker, "Insufficient earnings history", "Beats expectations score = 0")
            return 0
            
        recent_earnings = earnings.head(4)
        
        beats = 0
        valid_quarters = 0
        total_surprise_pct = 0
        
        for _, quarter in recent_earnings.iterrows():
            estimate = quarter.get('epsEstimate', None)
            actual = quarter.get('epsActual', None)
            
            if estimate is not None and actual is not None:
                valid_quarters += 1
                if actual > estimate:
                    beats += 1
                    
                if estimate != 0:
                    surprise_pct = ((actual - estimate) / abs(estimate)) * 100
                    total_surprise_pct += surprise_pct
        
        if valid_quarters == 0:
            log_data_issue(ticker, "No valid earnings data found", "Beats expectations score = 0")
            return 0
            
        beat_percentage = (beats / valid_quarters) * 100
        if beat_percentage >= 75:
            base_score = 2
        elif beat_percentage >= 50:
            base_score = 1
        else:
            base_score = 0
            
        avg_surprise = total_surprise_pct / valid_quarters
        
        if avg_surprise > 15:
            magnitude_bonus = 2
        elif avg_surprise > 5:
            magnitude_bonus = 1
        else:
            magnitude_bonus = 0
            
        final_score = base_score + magnitude_bonus
        
        reasoning = f"{beat_percentage:.1f}% beat rate, {avg_surprise:+.1f}% avg surprise (Base: {base_score}, Magnitude: {magnitude_bonus})"
        
        log_score(ticker, "Consistently Beats Expectations Score", final_score, 4, reasoning)
        return final_score

    except Exception as e:
        logger.error(f"Error calculating beats expectations for {ticker}: {e}")
        log_data_issue(ticker, f"Beats expectations calculation failed: {str(e)}", "Score = 0")
        return 0


def fetch_and_score_stock(ticker):
    """
    Analyzes stock performance, shareholder-friendly actions, and earnings consistency.
    """
    log_segment_start(ticker, "Stock Analysis")
    
    try:
        performance_score = calculate_5_year_performance_vs_sp500(ticker)
        shareholder_actions_score = calculate_shareholder_friendly_actions(ticker)
        beats_expectations_score = calculate_beats_expectations(ticker)

        scores = {
            "5-Year Performance Score": performance_score,
            "Shareholder Friendly Actions Score": shareholder_actions_score,
            "Consistently Beats Expectations Score": beats_expectations_score
        }
        
        total_score = sum(v for v in scores.values() if isinstance(v, (int, float)))
        max_score = SEGMENT_MAX_SCORES["Stock"]
        log_score(ticker, "Stock", total_score, max_score, f"Total Stock segment score out of {max_score}")
        log_segment_complete(ticker, "Stock", total_score, max_score)
        return scores
        
    except Exception as e:
        logger.error(f"Error processing stock {ticker}: {e}")
        log_data_issue(ticker, f"Stock analysis failed: {str(e)}", "Returning None")
        return None


if __name__ == "__main__":
    symbol = "xom"
    scores = fetch_and_score_stock(symbol)
    print(f"Stock Analysis Results for {symbol}: {scores}")