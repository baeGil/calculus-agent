"""
Wolfram Alpha tool for algebraic calculations.
"""
import os
import httpx
from typing import Optional
from backend.utils.rate_limit import wolfram_limiter, query_cache


WOLFRAM_BASE_URL = "https://api.wolframalpha.com/v2/query"


async def query_wolfram_alpha(
    query: str,
    max_retries: int = 3
) -> tuple[bool, str]:
    """
    Query Wolfram Alpha for algebraic calculations.
    Includes rate limiting (2000/month) and caching.
    
    Returns:
        tuple[bool, str]: (success, result_or_error_message)
    """
    # Check cache first to save API calls
    cached = query_cache.get(query, context="wolfram")
    if cached:
        return True, f"(Cached) {cached}"
    
    # Check monthly rate limit
    can_proceed, limit_msg, remaining = wolfram_limiter.can_make_request()
    if not can_proceed:
        return False, limit_msg
    
    app_id = os.getenv("WOLFRAM_ALPHA_APP_ID")
    if not app_id:
        return False, "Wolfram Alpha APP_ID not configured"
    
    params = {
        "appid": app_id,
        "input": query,
        "format": "plaintext",
        "output": "json",
    }
    
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(WOLFRAM_BASE_URL, params=params)
                response.raise_for_status()
                
                # Record usage only on successful API call
                wolfram_limiter.record_usage()
                
                data = response.json()
                
                if data.get("queryresult", {}).get("success"):
                    pods = data["queryresult"].get("pods", [])
                    results = []
                    
                    for pod in pods:
                        title = pod.get("title", "")
                        subpods = pod.get("subpods", [])
                        for subpod in subpods:
                            plaintext = subpod.get("plaintext", "")
                            if plaintext:
                                results.append(f"**{title}**: {plaintext}")
                    
                    if results:
                        result_text = "\n\n".join(results)
                        # Cache successful result
                        query_cache.set(query, result_text, context="wolfram")
                        
                        # Add warning if running low on quota
                        if remaining <= 100:
                            result_text += f"\n\n⚠️ {limit_msg}"
                        
                        return True, result_text
                    else:
                        return False, "No results found from Wolfram Alpha"
                else:
                    # Don't retry if query was understood but no answer
                    return False, "Wolfram Alpha could not interpret the query"
                    
        except httpx.TimeoutException:
            if attempt == max_retries - 1:
                return False, "Wolfram Alpha request timed out after 3 attempts"
            continue
        except httpx.HTTPStatusError as e:
            if attempt == max_retries - 1:
                return False, f"Wolfram Alpha HTTP error: {e.response.status_code}"
            continue
        except Exception as e:
            if attempt == max_retries - 1:
                return False, f"Wolfram Alpha error: {str(e)}"
            continue
    
    return False, "Wolfram Alpha failed after maximum retries"


def get_wolfram_status() -> dict:
    """Get Wolfram API usage status."""
    return wolfram_limiter.get_status()
