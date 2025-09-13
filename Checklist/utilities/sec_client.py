"""
SEC Client Module

This module provides SEC filing access and processing functionality.
Extracted from utils.py to provide better organization and separation of concerns.
"""

import requests
import time
import pandas as pd
from yfinance import Ticker
from .cache_manager import get_cached_data
from .logging_config import get_logger, log_debug, log_data_issue

logger = get_logger(__name__)


def fetch_10k_filing(ticker):
    """
    Fetches the latest 10-K filing for a given ticker using SEC EDGAR API.
    If 10-K is not found, falls back to Form 20-F for foreign companies.
    
    Args:
        ticker (str): The stock ticker symbol
        
    Returns:
        dict: Contains filing data with keys:
            - 'text': Full text of the filing
            - 'filing_date': Date of the filing
            - 'filing_url': Direct link to the filing
            - 'form_type': Type of form (10-K or 20-F)
        or None if no filing found
    """
    try:
        # First get the CIK number
        cik_lookup_url = "https://www.sec.gov/files/company_tickers.json"
        
        # Headers required by SEC
        headers = {
            'User-Agent': 'Portfolio Analysis Tool (tomwork737@gmail.com)',
            'Accept-Encoding': 'gzip, deflate'
        }
        
        # Get CIK from ticker lookup
        response = requests.get(cik_lookup_url, headers=headers)
        if response.status_code != 200:
            logger.error(f"Failed to get CIK lookup data. Status: {response.status_code}")
            return None
            
        companies = response.json()
        ticker_info = None
        
        # Find the matching ticker
        for _, company in companies.items():
            if company['ticker'].upper() == ticker.upper():
                ticker_info = company
                break
                
        if not ticker_info:
            log_data_issue(ticker, "Could not find CIK for ticker", "No SEC filing available")
            return None
            
        cik = str(ticker_info['cik_str']).zfill(10)
        log_debug(f"Found CIK {cik} for {ticker}")
        
        # Get the company submissions feed
        submissions_url = f"https://data.sec.gov/submissions/CIK{cik}.json"
        
        # Need to wait to respect SEC rate limits
        time.sleep(0.1)  # SEC requires 10 requests per second max
        
        response = requests.get(submissions_url, headers=headers)
        if response.status_code != 200:
            logger.error(f"Failed to get submissions for {ticker}. Status: {response.status_code}")
            return None
            
        submissions_data = response.json()
        
        # Find most recent 10-K or 20-F
        recent_filings = submissions_data.get('filings', {}).get('recent', {})
        if not recent_filings:
            log_data_issue(ticker, "No recent filings found", "No SEC filing available")
            return None
            
        # Get indices of 10-K and 20-F filings
        form_types = recent_filings.get('form', [])
        accession_numbers = recent_filings.get('accessionNumber', [])
        filing_dates = recent_filings.get('filingDate', [])
        primary_docs = recent_filings.get('primaryDocument', [])
        
        # Try to find 10-K first
        ten_k_indices = [i for i, form in enumerate(form_types) if form == '10-K']
        if ten_k_indices:
            latest_index = ten_k_indices[0]
            form_type = '10-K'
        else:
            # Fallback to 20-F if no 10-K found
            twenty_f_indices = [i for i, form in enumerate(form_types) if form == '20-F']
            if not twenty_f_indices:
                log_data_issue(ticker, "No 10-K or 20-F filings found", "No SEC filing available")
                return None
            latest_index = twenty_f_indices[0]
            form_type = '20-F'
        
        accession_number = accession_numbers[latest_index].replace('-', '')
        filing_date = filing_dates[latest_index]
        primary_doc = primary_docs[latest_index]
        
        log_debug(f"Found {form_type} filing for {ticker} dated {filing_date}")
        
        # Construct the correct URL for the filing
        base_url = "https://www.sec.gov/Archives/edgar/data"
        filing_url = f"{base_url}/{int(cik)}/{accession_number}/{primary_doc}"
        
        # Need to wait to respect SEC rate limits
        time.sleep(0.1)  # SEC requires 10 requests per second max
        
        response = requests.get(filing_url, headers=headers)
        if response.status_code != 200:
            # Try alternative URL format
            filing_url = f"{base_url}/{int(cik)}/{accession_number}/R1.htm"
            response = requests.get(filing_url, headers=headers)
            
            if response.status_code != 200:
                logger.error(f"Failed to get {form_type} text for {ticker}. Status: {response.status_code}")
                return None
        
        return {
            'text': response.text,
            'filing_date': filing_date,
            'filing_url': filing_url,
            'form_type': form_type
        }
        
    except Exception as e:
        logger.error(f"Error fetching filing for {ticker}: {e}")
        return None


def get_latest_10k(ticker):
    """
    Gets the latest annual filing (10-K or 20-F) for a ticker, using cache if available.
    This is the main interface function that handles both cache and API calls.
    
    Args:
        ticker (str): The stock ticker symbol
        
    Returns:
        dict: Contains filing data with keys:
            - 'text': Full text of the filing
            - 'filing_date': Date of the filing
            - 'filing_url': Direct link to the filing
            - 'form_type': Type of form (10-K or 20-F)
        or None if no filing found
    """
    try:
        # Normalize ticker to lowercase for cache consistency
        data, _ = get_cached_data("10k_cache.json", ticker.lower(), fetch_10k_filing, ticker)
        if data is None:
            log_data_issue(ticker, "Could not fetch annual filing (10-K/20-F)", "No SEC filing available")
            return None
            
        # Log the type of filing found
        form_type = data.get('form_type', '10-K')
        log_debug(f"Retrieved {form_type} filing for {ticker} filed on {data['filing_date']}")
        return data
        
    except Exception as e:
        logger.error(f"Error getting annual filing for {ticker}: {e}")
        return None


def dataframe_to_dict(df):
    """Convert DataFrame to dict with ISO formatted timestamps."""
    return {
        col: {k.isoformat(): v for k, v in series.to_dict().items()}
        for col, series in df.items()
    }


def dict_to_dataframe(data_dict):
    """Convert dict with ISO formatted timestamps back to DataFrame."""
    df = pd.DataFrame(data_dict)
    df.index = pd.to_datetime(df.index, utc=True)
    return df


def get_cash_flow_data(ticker):
    """
    Gets cash flow data for a ticker, using cache if available.
    This data can be used for both shareholder actions and share dilution analysis.
    
    Args:
        ticker (str): The stock ticker symbol
        
    Returns:
        pd.DataFrame: Cash flow data or None if not available
    """
    try:
        def fetch_cash_flow(ticker):
            stock = Ticker(ticker)
            cashflow = stock.cashflow
            if cashflow.empty:
                return None
            # Convert DataFrame to dict with string keys
            return {
                'data': {str(k): v.to_dict() for k, v in cashflow.items()},
                'index': cashflow.index.tolist()
            }
            
        # Normalize ticker to lowercase for cache consistency
        data, _ = get_cached_data("cash_flow_cache.json", ticker.lower(), fetch_cash_flow, ticker)
        if data is None:
            log_data_issue(ticker, "Could not fetch cash flow data", "No cash flow data available")
            return None
            
        # Reconstruct DataFrame from cached data
        df = pd.DataFrame(data['data'])
        df.index = data['index']
        log_debug(f"Retrieved cash flow data for {ticker}")
        return df
        
    except Exception as e:
        logger.error(f"Error getting cash flow data for {ticker}: {e}")
        return None 