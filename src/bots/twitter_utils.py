"""
Glitch Bot Twitter API Helpers
"""
# Move all Twitter API helper functions and classes from enhanced_glitch_bot_v2.py here.
# Example placeholder (replace with actual Twitter code):

from twitter_plugin_gamesdk.twitter_plugin import TwitterPlugin
from src.bots.config import TWITTER_TOKEN
import time
import random

# Helper: Rate limit/backoff wrapper for API calls
def call_with_rate_limit_handling(api_func, *args, max_retries=5, base_sleep=300, **kwargs):
    """
    Calls an API function, handling 429 Too Many Requests errors with backoff.
    Sleeps for 5 minutes (300s) on first 429, doubles on each subsequent 429 up to max_retries.
    """
    retries = 0
    while retries <= max_retries:
        try:
            return api_func(*args, **kwargs)
        except Exception as e:
            err_str = str(e)
            if '429' in err_str or 'Too Many Requests' in err_str:
                sleep_time = base_sleep * (2 ** retries)
                print(f"[RateLimit] 429 detected. Sleeping for {sleep_time//60} min (retry {retries+1}/{max_retries})...")
                time.sleep(sleep_time + random.uniform(0, 30))
                retries += 1
            else:
                raise
    print(f"[RateLimit] Max retries exceeded for API call: {api_func.__name__}")
    raise Exception("Max retries exceeded for API call due to repeated 429 errors.")

# Twitter client setup
def get_twitter_client():
    """Initialize Twitter client"""
    options = {
        "credentials": {
            "game_twitter_access_token": TWITTER_TOKEN
        }
    }
    twitter_plugin = TwitterPlugin(options)
    return twitter_plugin.twitter_client

# Add any other Twitter helper functions/classes below... 