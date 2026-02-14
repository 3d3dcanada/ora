"""
ora.tools.web_search
====================

Web Search Tool - Internet access with rate limiting.

Port from BUZZ Neural Core with simplified implementation for Phase 3.
A2 authority required.
"""

import aiohttp
import asyncio
import re
from typing import Dict, Any, List, Optional
import urllib.parse
import json
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class WebSearchTool:
    """
    Web search tool with rate limiting.
    
    A2 authority required.
    Uses DuckDuckGo Instant Answer API (free, no API key required).
    """
    
    def __init__(self, rate_limit_per_minute: int = 10):
        """
        Initialize web search tool.
        
        Args:
            rate_limit_per_minute: Maximum searches per minute (default: 10)
        """
        self.rate_limit_per_minute = rate_limit_per_minute
        self.request_times: List[datetime] = []
        
        logger.info(f"WebSearchTool initialized with rate limit: {rate_limit_per_minute}/min")
    
    def _check_rate_limit(self) -> bool:
        """
        Check if request is within rate limit.
        
        Returns:
            True if request is allowed
        """
        now = datetime.now()
        
        # Remove old request times (older than 1 minute)
        self.request_times = [
            t for t in self.request_times 
            if now - t < timedelta(minutes=1)
        ]
        
        # Check if we're at the limit
        if len(self.request_times) >= self.rate_limit_per_minute:
            return False
        
        # Add current request time
        self.request_times.append(now)
        return True
    
    async def search(self, query: str, max_results: int = 10) -> Dict[str, Any]:
        """
        Perform web search using DuckDuckGo Instant Answer API.
        
        Args:
            query: Search query
            max_results: Maximum number of results (default: 10)
            
        Returns:
            Dictionary with search results
        """
        # Check rate limit
        if not self._check_rate_limit():
            return {
                "success": False,
                "error": "Rate limit exceeded (10 searches per minute)",
                "operation": "search"
            }
        
        if not query:
            return {
                "success": False,
                "error": "Missing query parameter",
                "operation": "search"
            }
        
        try:
            # DuckDuckGo Instant Answer API (free, no API key required)
            url = "https://api.duckduckgo.com/"
            params_dict = {
                "q": query,
                "format": "json",
                "no_html": "1",
                "skip_disambig": "1"
            }
            
            logger.info(f"Searching web for: {query}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params_dict, timeout=30) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        results = []
                        
                        # Abstract (featured snippet)
                        if data.get("Abstract"):
                            results.append({
                                "title": data.get("Heading", query),
                                "snippet": data["Abstract"],
                                "url": data.get("AbstractURL", ""),
                                "source": data.get("AbstractSource", ""),
                                "type": "abstract"
                            })
                        
                        # Related topics
                        for topic in data.get("RelatedTopics", [])[:max_results]:
                            if isinstance(topic, dict) and "Text" in topic:
                                results.append({
                                    "title": topic.get("Text", "").split(" - ")[0],
                                    "snippet": topic.get("Text", ""),
                                    "url": topic.get("FirstURL", ""),
                                    "source": "DuckDuckGo",
                                    "type": "related_topic"
                                })
                        
                        # If no results from DuckDuckGo, provide a fallback
                        if not results:
                            results.append({
                                "title": f"Search results for: {query}",
                                "snippet": f"No instant answer found for '{query}'. Try refining your search terms.",
                                "url": f"https://duckduckgo.com/?q={urllib.parse.quote(query)}",
                                "source": "DuckDuckGo",
                                "type": "fallback"
                            })
                        
                        return {
                            "success": True,
                            "query": query,
                            "results": results,
                            "count": len(results),
                            "operation": "search"
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"Search API returned status {response.status}",
                            "operation": "search"
                        }
                    
        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": "Search request timed out after 30 seconds",
                "operation": "search"
            }
        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "operation": "search"
            }
    
    async def fetch_webpage(self, url: str) -> Dict[str, Any]:
        """
        Fetch and parse webpage content.
        
        Args:
            url: URL to fetch
            
        Returns:
            Dictionary with webpage content
        """
        # Check rate limit
        if not self._check_rate_limit():
            return {
                "success": False,
                "error": "Rate limit exceeded (10 requests per minute)",
                "operation": "fetch_webpage"
            }
        
        if not url:
            return {
                "success": False,
                "error": "Missing url parameter",
                "operation": "fetch_webpage"
            }
        
        try:
            # Validate URL
            if not url.startswith(("http://", "https://")):
                url = f"https://{url}"
            
            logger.info(f"Fetching webpage: {url}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=30) as response:
                    if response.status == 200:
                        content = await response.text()
                        
                        # Extract title from HTML
                        title = "Webpage"
                        title_match = re.search(r'<title[^>]*>(.*?)</title>', content, re.IGNORECASE)
                        if title_match:
                            title = title_match.group(1).strip()
                        
                        # Extract meta description
                        description = ""
                        desc_match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\'](.*?)["\']', content, re.IGNORECASE)
                        if desc_match:
                            description = desc_match.group(1).strip()
                        
                        # Extract main content (simplified)
                        # Remove scripts, styles, and excessive whitespace
                        content_clean = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL | re.IGNORECASE)
                        content_clean = re.sub(r'<style[^>]*>.*?</style>', '', content_clean, flags=re.DOTALL | re.IGNORECASE)
                        content_clean = re.sub(r'<[^>]+>', ' ', content_clean)
                        content_clean = re.sub(r'\s+', ' ', content_clean).strip()
                        
                        # Limit content length
                        if len(content_clean) > 5000:
                            content_clean = content_clean[:5000] + "..."
                        
                        return {
                            "success": True,
                            "url": url,
                            "title": title,
                            "description": description,
                            "content": content_clean,
                            "content_length": len(content_clean),
                            "operation": "fetch_webpage"
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"HTTP {response.status}",
                            "url": url,
                            "operation": "fetch_webpage"
                        }
                    
        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": "Webpage fetch timed out after 30 seconds",
                "operation": "fetch_webpage"
            }
        except Exception as e:
            logger.error(f"Webpage fetch failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "operation": "fetch_webpage"
            }
    
    async def execute(self, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute web search operation.
        
        Args:
            action: Operation to execute (search, fetch_webpage)
            parameters: Operation parameters
            
        Returns:
            Dictionary with success status and result
        """
        if action == "search":
            query = parameters.get("query")
            max_results = parameters.get("max_results", 10)
            
            if not query:
                return {"success": False, "error": "Missing query parameter"}
            
            return await self.search(query, max_results)
        
        elif action == "fetch_webpage":
            url = parameters.get("url")
            
            if not url:
                return {"success": False, "error": "Missing url parameter"}
            
            return await self.fetch_webpage(url)
        
        else:
            return {"success": False, "error": f"Unknown action: {action}"}