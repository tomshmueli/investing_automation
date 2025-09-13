"""
Cache Manager Module

This module provides a generic caching system for API calls and data persistence.
Supports general caching and specialized LLM response caching with structured format.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any
from ..settings import CACHE_EXPIRY_DAYS
from .logging_config import get_logger, log_debug, log_data_issue

logger = get_logger(__name__)


def get_cached_data(cache_file, cache_key, fetch_function, *args, **kwargs):
    """
    Generic cache handler that attempts to get data from cache first,
    then falls back to API if cache is missing or expired.
    
    Args:
        cache_file (str): Path to cache file
        cache_key (str): Key to store/retrieve data in cache
        fetch_function (callable): Function to call if cache miss
        *args, **kwargs: Arguments to pass to fetch_function
        
    Returns:
        tuple: (data, timestamp) or (None, None) if both cache and API fail
    """
    try:
        # Load cache
        cache_path = Path(__file__).parent.parent / "cache" / cache_file
        cache = load_cache(cache_path)
        
        # Check if data exists and is not expired
        if cache_key in cache.get('data', {}):
            cached_data = cache['data'][cache_key]
            if datetime.fromisoformat(cached_data['timestamp']) + timedelta(days=CACHE_EXPIRY_DAYS) > datetime.now():
                log_debug(f"Cache hit for {cache_key}")
                return cached_data['data'], datetime.fromisoformat(cached_data['timestamp'])
        
        # If cache miss or expired, fetch new data
        log_debug(f"Cache miss for {cache_key}, fetching new data")
        new_data = fetch_function(*args, **kwargs)
        
        if new_data is not None:
            # Update cache
            if 'data' not in cache:
                cache['data'] = {}
            cache['data'][cache_key] = {
                'timestamp': datetime.now().isoformat(),
                'data': new_data
            }
            save_cache(cache_path, cache)
            return new_data, datetime.now()
        
        log_data_issue("SYSTEM", f"No data available for {cache_key} after fetch attempt", "Cache miss")
        return None, None
        
    except Exception as e:
        logger.error(f"Error in cache handler for {cache_key}: {str(e)}")
        return None, None




def load_cache(cache_path):
    """Load cache from file."""
    try:
        if cache_path.exists():
            with open(cache_path, 'r') as f:
                cache = json.load(f)
                if not isinstance(cache, dict):
                    log_debug(f"Cache file {cache_path} is not a valid JSON object")
                    return {"last_updated": "", "data": {}}
                if 'data' not in cache:
                    cache['data'] = {}
                return cache
    except json.JSONDecodeError:
        log_debug(f"Cache file {cache_path} is corrupted")
    except Exception as e:
        logger.error(f"Error loading cache from {cache_path}: {str(e)}")
    return {"last_updated": "", "data": {}}


def save_cache(cache_path, cache):
    """Save cache to file."""
    try:
        # Ensure directory exists
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        
        cache['last_updated'] = datetime.now().isoformat()
        with open(cache_path, 'w') as f:
            json.dump(cache, f, indent=4)
    except Exception as e:
        logger.error(f"Error saving cache to {cache_path}: {e}") 