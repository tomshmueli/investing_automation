import os
import textwrap

import yfinance as yf
import requests
from bs4 import BeautifulSoup
from Checklist.settings import MISSION_STATEMENTS_FILE, RESULTS_DIR, SEGMENT_MAX_SCORES
from Checklist.utilities.logging_config import get_logger, log_score, log_data_issue, log_segment_start, log_segment_complete, log_debug

logger = get_logger(__name__)

def get_soul_in_the_game_score(ticker):
    """
    Soul in the Game Score – Manual Entry for Now.

    Manual Process:
    - Visit https://simplywall.st/stocks/ and search for the stock.
    - Navigate to the "Management" tab.
    - Assess CEO tenure, founder status, and long-term leadership.
    - Assign a score manually (0 to 4).

    Returns:
        int: Placeholder score or None, depending on manual input later.
    """
    log_debug(f"Calculating soul in the game score for {ticker}")
    log_score(ticker, "Soul in the Game Score", "MANUAL", None, "Requires manual evaluation of CEO tenure, founder status, and leadership")
    return None

def get_inside_ownership_score(ticker):
    """
    Calculates the Inside Ownership Score based on % insider ownership and absolute value.

    Scoring System (0-3):
    1. % Insider Ownership (Base Score):
        - >10% -> 2 points
        - 1% – 10% -> 1 point
        - <1% -> 0 points
    2. Value of Insider Holdings (Bonus):
        - > $50M -> +1 point

    Returns:
        int: Inside Ownership Score (0-3).
    """
    log_debug(f"Calculating inside ownership for {ticker}")
    
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        insider_ownership_pct = info.get("heldPercentInsiders", None)
        market_cap = info.get("marketCap", None)

        if insider_ownership_pct is None or market_cap is None:
            log_data_issue(ticker, "Ownership data missing", "Using neutral score of 1")
            return 1

        insider_ownership_pct *= 100
        insider_value = (insider_ownership_pct / 100) * market_cap

        if insider_ownership_pct > 10:
            base_score = 2
        elif 1 <= insider_ownership_pct <= 10:
            base_score = 1
        else:
            base_score = 0

        bonus_score = 1 if insider_value > 50_000_000 else 0
        final_score = base_score + bonus_score
        
        reasoning = f"{insider_ownership_pct:.1f}% insider ownership"
        if bonus_score > 0:
            reasoning += f", ${insider_value/1e6:.0f}M value"
        
        log_score(ticker, "Inside Ownership Score", final_score, 3, reasoning)
        return final_score

    except Exception as e:
        logger.error(f"Error fetching inside ownership for {ticker}: {e}")
        log_data_issue(ticker, f"Inside ownership calculation failed: {str(e)}", "Score = 1")
        return 1

def get_glassdoor_ratings_score(ticker):
    """
    Calculates employee sentiment score using a hybrid approach of automated Yahoo Finance metrics
    and recommended manual Glassdoor verification.
    
    **Manual Verification (Glassdoor Guidelines):**
    For more accurate scoring, manually check Glassdoor for:
    - Overall Company Rating (1-5 stars)
    - CEO Approval Percentage
    - Recommend to Friend Percentage
    
    Manual Scoring Override Guidelines:
    - 0: Rating < 3.0 OR CEO approval < 50%
    - 2: Rating 3.0-3.9 AND CEO approval 50-75%
    - 4: Rating ≥ 4.0 AND CEO approval > 75%
    
    Returns:
        int: Score between 0 and 4 based on Yahoo Finance metrics, or None for manual fields
    """
    log_debug(f"Calculating glassdoor ratings for {ticker}")
    
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        board_risk = info.get('boardRisk', 5)
        comp_risk = info.get('compensationRisk', 5)
        overall_risk = info.get('overallRisk', 5)
        
        score = 4
        
        if board_risk > 5:
            score -= 1
        if comp_risk > 5:
            score -= 1
        if overall_risk > 5:
            score -= 2
            
        log_score(ticker, "Glassdoor Ratings Score", "MANUAL", None, f"Requires manual Glassdoor verification (Risk metrics: Board={board_risk}, Comp={comp_risk}, Overall={overall_risk})")
        
        return None
        
    except Exception as e:
        logger.error(f"Error calculating employee sentiment for {ticker}: {e}")
        log_data_issue(ticker, f"Glassdoor ratings calculation failed: {str(e)}", "Manual review required")
        return None


def get_mission_statement(ticker):
    """
    Fetches the 'Business Summary' from Yahoo Finance Profile Page.
    Often reflects the company's mission or business focus.

    Manual Scoring After Extraction (Guideline):
    - 0: No mission / confusing / purely profit-driven.
    - 1: Basic / vague mission.
    - 2: Clear but uninspiring.
    - 3: Simple, inspiring, and aligns with company values.

    Returns:
        str: Mission statement text or None
    """
    log_debug(f"Fetching mission statement for {ticker}")
    
    try:
        url = f"https://finance.yahoo.com/quote/{ticker}/profile"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            log_data_issue(ticker, f"Failed to fetch mission statement", f"Status code: {response.status_code}")
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        description_section = soup.find("section", {"data-testid": "description"})
        
        if description_section:
            paragraph = description_section.find("p")
            if paragraph:
                mission_statement = paragraph.get_text(strip=True)
                log_debug(f"Successfully fetched mission statement for {ticker}")
                return mission_statement

        log_data_issue(ticker, "No mission statement found", "Description section not found")
        return None

    except Exception as e:
        logger.error(f"Error fetching mission statement for {ticker}: {e}")
        log_data_issue(ticker, f"Mission statement fetch failed: {str(e)}", "Manual review required")
        return None

def save_mission_statement(ticker, mission_statement):
    """
    Saves the mission statement to a text file for future reference.
    """
    results_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'results', 'mission_statements.txt')

    with open(results_path, 'a', encoding='utf-8') as file:  # <-- 'a' for append instead of 'w'
        file.write(f"{ticker.upper()}:\n")
        file.write(textwrap.fill(mission_statement, width=100))
        file.write("\n" + "-" * 50 + "\n")

def clear_mission_statements_file():
    results_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'results', 'mission_statements.txt')
    open(results_path, 'w').close()



def fetch_and_score_management(ticker):
    """
    Fetches all management-related scores for a company.
    Currently includes:
    - Soul in the Game: Manual (Placeholder)
    - Inside Ownership: Automated

    Returns:
        dict: Management scores.
    """
    log_segment_start(ticker, "Management")
    
    try:
        soul_score = get_soul_in_the_game_score(ticker)
        ownership_score = get_inside_ownership_score(ticker)
        glassdoor_score = get_glassdoor_ratings_score(ticker)
        mission_statement = get_mission_statement(ticker)

        if mission_statement:
            save_mission_statement(ticker, mission_statement)

        scores = {
            "Soul in the Game Score": soul_score,
            "Inside Ownership Score": ownership_score,
            "Glassdoor Ratings Score": glassdoor_score,
            "Mission Statement": None
        }
        
        total_score = sum(v for v in scores.values() if isinstance(v, (int, float)))
        max_score = SEGMENT_MAX_SCORES["Management & Culture"]
        log_score(ticker, "Management & Culture", total_score, max_score, f"Total Management & Culture segment score out of {max_score}")
        log_segment_complete(ticker, "Management & Culture", total_score, max_score)
        return scores
        
    except Exception as e:
        logger.error(f"Error processing management data for {ticker}: {e}")
        log_data_issue(ticker, f"Management analysis failed: {str(e)}", "Returning None")
        return None


if __name__ == "__main__":
    symbol = "pltr"
    print(fetch_and_score_management(symbol))
