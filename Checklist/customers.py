from yfinance import Ticker
from Checklist.utilities.logging_config import get_logger, log_score, log_data_issue, log_segment_start, log_segment_complete, log_debug
from Checklist.settings import SEGMENT_MAX_SCORES

logger = get_logger(__name__)

def calculate_acquisitions_score(stock, ticker: str):
    """
    Calculates the **Acquisitions Score** based on Sales & Marketing Expense as a % of Gross Profit.

    **Score Breakdown:**
    - 5: < 10%
    - 4: 10% – 20%
    - 3: 20% – 35%
    - 2: 35% – 50%
    - 1: 50% – 70%
    - 0: > 70%

    **Fallback:** Use SG&A Expense if S&M is unavailable.

    **Returns:** `int` - Acquisitions score (0-5).
    """
    log_debug(f"Calculating acquisitions score for {ticker}")
    
    try:
        financials = stock.financials
        income_statement = stock.income_stmt

        gross_profit = financials.loc['Gross Profit'].iloc[0] if 'Gross Profit' in financials.index else None
        sm_expense = safe_lookup(income_statement, [
            "Selling And Marketing Expense",
            "Sales and Marketing",
            "Selling & Marketing Expense"
        ])

        sga_expense = safe_lookup(income_statement, [
            "Selling General And Administration",
            "Selling General and Administrative Expense",
            "SG&A Expense"
        ])

        if gross_profit is None:
            log_data_issue(ticker, "Gross Profit data unavailable", "Using neutral score of 2")
            return 2

        expense = sm_expense if sm_expense is not None else sga_expense
        if expense is None:
            log_data_issue(ticker, "Both S&M and SG&A data unavailable", "Using neutral score of 2")
            return 2

        percentage = (expense / gross_profit) * 100

        if percentage < 10:
            score = 5
            reasoning = f"Excellent efficiency ({percentage:.1f}% < 10%)"
        elif percentage < 20:
            score = 4
            reasoning = f"Good efficiency ({percentage:.1f}% < 20%)"
        elif percentage < 35:
            score = 3
            reasoning = f"Moderate efficiency ({percentage:.1f}% < 35%)"
        elif percentage < 50:
            score = 2
            reasoning = f"Below average efficiency ({percentage:.1f}% < 50%)"
        elif percentage < 70:
            score = 1
            reasoning = f"Poor efficiency ({percentage:.1f}% < 70%)"
        else:
            score = 0
            reasoning = f"Very poor efficiency ({percentage:.1f}% ≥ 70%)"

        log_score(ticker, "Acquisitions Score", score, 5, reasoning)
        return score

    except Exception as e:
        logger.error(f"Error calculating acquisitions score for {ticker}: {e}")
        log_data_issue(ticker, f"Acquisitions calculation failed: {str(e)}", "Score = 2")
        return 2

def safe_lookup(df, possible_keys):
    for key in possible_keys:
        if key in df.index:
            return df.loc[key].iloc[0]
    return None

def calculate_dependence_score(stock, ticker: str):
    """
    Calculates the **Dependence Score** - manual evaluation of cyclical dependence.

    **Returns:** `None` - Requires manual evaluation.
    """
    log_debug(f"Calculating dependence score for {ticker}")
    log_score(ticker, "Dependence Score", "MANUAL", None, "Requires manual evaluation of cyclical dependence (Highly Cyclical / Moderate / Recession Proof)")
    return None


def fetch_and_score_customers(ticker):
    """
    Analyzes customer acquisition efficiency and cyclical dependence metrics.
    """
    log_segment_start(ticker, "Customers Analysis")
    
    stock = Ticker(ticker)
    try:
        scores = {
            "Acquisitions Score": calculate_acquisitions_score(stock, ticker),
            "Dependence Score": calculate_dependence_score(stock, ticker)
        }
        total_score = sum(v for v in scores.values() if isinstance(v, (int, float)))
        max_score = SEGMENT_MAX_SCORES["Customers"]
        log_score(ticker, "Customers", total_score, max_score, f"Total Customers segment score out of {max_score}")
        log_segment_complete(ticker, "Customers Analysis", total_score, max_score)
        return scores
        
    except Exception as e:
        logger.error(f"Error processing customers data for {ticker}: {e}")
        log_data_issue(ticker, f"Customers analysis failed: {str(e)}", "Returning None")
        return None

if __name__ == "__main__":
    symbol = "inmd"
    scores = fetch_and_score_customers(symbol)
    print(f"Customers Analysis Results for {symbol}: {scores}")
