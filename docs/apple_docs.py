"""
Apple Developer Documentation Module
=====================================

Provides access to Apple's official developer documentation through their
undocumented JSON API endpoints. This module enables:
- Structured data extraction from documentation pages
- Framework and API reference lookups
- Intelligent URL generation for searches
- TTL-based caching for performance

Key Features:
- Converts documentation URLs to JSON API endpoints automatically
- Parses Apple's complex JSON structure into usable format
- Extracts method signatures, parameters, and return values
- Handles multiple JSON endpoint formats

Technical Details:
- Uses undocumented endpoints like /tutorials/data/documentation/{path}.json
- Falls back to alternative formats when primary fails
- Implements sliding window cache to limit memory usage
"""

import json
import urllib.request
import urllib.parse
import time
from typing import Dict, Optional, List
from config import logger

class AppleDocsAPI:
    """
    Interface to Apple Developer documentation via JSON API.

    This class provides methods to fetch and parse Apple's developer
    documentation using their internal JSON endpoints. It handles URL
    conversion, data parsing, and result caching.

    Attributes:
        cache: Time-keyed cache for fetched JSON data
        cache_ttl: Time-to-live for cached entries (1 hour)
        base_url: Base URL for Apple Developer documentation
    """

    def __init__(self):
        """Initialize API client with empty cache and base URL."""
        self.cache = {}          # Time-keyed cache for JSON responses
        self.cache_ttl = 3600    # Cache expires after 1 hour
        self.base_url = "https://developer.apple.com/documentation/"
    
    def _fetch_json(self, url: str) -> Optional[Dict]:
        """
        Fetch JSON data from URL with caching.
        
        Args:
            url: URL to fetch JSON from
            
        Returns:
            Parsed JSON data or None if failed
        """
        # Create time-based cache key that expires every hour
        # This ensures fresh data while reducing API calls
        cache_key = f"{url}:{int(time.time() // self.cache_ttl)}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        try:
            # Prepare request with browser-like headers
            # User-Agent is required to avoid 403 errors
            req = urllib.request.Request(
                url,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
                    'Accept': 'application/json'
                }
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    data = json.loads(response.read())
                    # Store in cache with time-based key
                    self.cache[cache_key] = data

                    # Implement sliding window cache management
                    # Keep only the 50 most recent entries when cache exceeds 100
                    if len(self.cache) > 100:
                        self.cache = dict(list(self.cache.items())[-50:])
                    return data
                    
        except Exception as e:
            logger.error(f"Failed to fetch {url}: {e}")
        
        return None
    
    def _parse_documentation_json(self, data: Dict) -> Dict:
        """
        Parse Apple's documentation JSON format.
        
        Args:
            data: Raw JSON data from Apple
            
        Returns:
            Parsed documentation with key information
        """
        # Initialize result structure with default values
        result = {
            "title": "Unknown",
            "abstract": "",
            "declaration": "",
            "discussion": "",
            "parameters": [],
            "returns": ""
        }

        # Extract title from metadata section
        if "metadata" in data:
            result["title"] = data["metadata"].get("title", "Unknown")

        # Parse primaryContentSections - contains declarations and content
        if "primaryContentSections" in data:
            for section in data["primaryContentSections"]:
                if section.get("kind") == "declarations":
                    # Reconstruct method/type declaration from token array
                    # Apple splits declarations into tokens for syntax highlighting
                    for declaration in section.get("declarations", []):
                        for token in declaration.get("tokens", []):
                            result["declaration"] += token.get("text", "")

                elif section.get("kind") == "content":
                    # Extract main discussion/description text
                    for content in section.get("content", []):
                        if content.get("type") == "paragraph":
                            # Navigate nested structure to get actual text
                            inline_content = content.get("inlineContent", [{}])
                            if inline_content:
                                result["discussion"] += inline_content[0].get("text", "")

        # Extract abstract - brief summary shown at top of documentation
        if "abstract" in data:
            for item in data["abstract"]:
                if item.get("type") == "text":
                    result["abstract"] += item.get("text", "")
        
        # Extract parameters and return value
        if "sections" in data:
            for section in data["sections"]:
                if section.get("title") == "Parameters":
                    result["parameters"] = section.get("items", [])
                elif section.get("title") == "Return Value":
                    result["returns"] = section.get("content", "")
        
        return result
    
    def fetch_documentation(self, url: str) -> Dict:
        """
        Fetch and parse documentation from Apple Developer website.
        
        Args:
            url: Apple documentation URL
            
        Returns:
            Parsed documentation with structured information
        """
        if not url.startswith("https://developer.apple.com/documentation/"):
            return {
                "error": "Invalid URL",
                "message": "URL must be from developer.apple.com/documentation/"
            }
        
        # Convert documentation URL to JSON API endpoint
        # Apple has undocumented JSON endpoints for all documentation pages
        try:
            # Extract path component after /documentation/
            # Example: "swiftui/view/onappear(perform:)" from full URL
            path = url.split("/documentation/", 1)[1].rstrip('/')

            # Try primary JSON endpoint format (most common)
            # This format is used for most API documentation
            json_url = f"https://developer.apple.com/tutorials/data/documentation/{path}.json"

            # Attempt to fetch JSON data
            data = self._fetch_json(json_url)

            if not data:
                # Fallback to alternative endpoint format
                # Some pages use this older format
                json_url = f"https://developer.apple.com/documentation/{path}/data.json"
                data = self._fetch_json(json_url)
            
            if not data:
                return {
                    "error": "Failed to fetch",
                    "url": url,
                    "suggestion": "Check if the URL is correct and the page exists"
                }
            
            # Parse the JSON data
            parsed = self._parse_documentation_json(data)
            parsed["url"] = url
            parsed["json_url"] = json_url
            
            return parsed
            
        except Exception as e:
            logger.error(f"Error processing {url}: {e}")
            return {
                "error": str(e),
                "url": url
            }
    
    def search_online(self, query: str, platform: Optional[str] = None) -> Dict:
        """
        Generate search URLs for Apple documentation.
        
        Args:
            query: Search term
            platform: Optional platform filter (ios, macos, etc.)
            
        Returns:
            Search URLs for different sources
        """
        encoded_query = urllib.parse.quote(query)
        
        # Generate search URLs dynamically
        search_urls = {
            "apple_direct": f"{self.base_url}technologies?filter={encoded_query}",
            "google": f"https://www.google.com/search?q=site:developer.apple.com+{encoded_query}",
            "github": f"https://github.com/search?q={encoded_query}+language:swift&type=code"
        }
        
        if platform:
            search_urls["apple_direct"] += f"+{platform}"
            search_urls["google"] += f"+{platform}"
        
        return {
            "query": query,
            "platform": platform,
            "search_urls": search_urls
        }
    
    def get_framework_info(self, framework: str) -> Dict:
        """
        Get documentation URL for a framework.
        
        Args:
            framework: Framework name
            
        Returns:
            Framework information with documentation URL
        """
        # Simply generate the URL based on the framework name
        framework_path = framework.lower().replace(" ", "").replace("-", "")
        
        return {
            "name": framework,
            "url": f"{self.base_url}{framework_path}",
            "note": "Direct link to framework documentation"
        }

# Module-level instance
apple_docs = AppleDocsAPI()