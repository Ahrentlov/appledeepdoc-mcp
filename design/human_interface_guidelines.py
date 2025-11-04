"""
Human Interface Guidelines Module
===================================

Provides access to Apple's Human Interface Guidelines for iOS, macOS, tvOS,
watchOS, and visionOS. This module helps developers find design patterns,
best practices, and platform-specific guidance for creating exceptional
user experiences.

Key Features:
- Search across all Human Interface Guidelines content
- Platform-specific design guidance
- Direct access to design documentation
- Simple, generic search approach using Google site search

Technical Details:
- Uses Google site search for comprehensive coverage
- Provides direct links to Human Interface Guidelines
- Platform-aware search capabilities
- Respects robots.txt through Google's indexing
"""

import urllib.parse
from typing import Dict, Optional, List
from config import logger


class HumanInterfaceGuidelines:
    """
    Interface to Apple's Human Interface Guidelines documentation.

    This class provides methods to search and navigate Apple's design
    documentation, helping developers find the right design patterns
    and best practices for their applications.

    Attributes:
        base_url: Base URL for Human Interface Guidelines
        platforms: Supported Apple platforms
    """

    def __init__(self):
        """Initialize with Human Interface Guidelines base URL and platform list."""
        self.base_url = "https://developer.apple.com/design/human-interface-guidelines"
        self.platforms = ["ios", "macos", "tvos", "watchos", "visionos"]

    def search_guidelines(self, query: str, platform: Optional[str] = None) -> Dict:
        """
        Search Human Interface Guidelines by topic or keyword.

        Args:
            query: Search term (e.g., "navigation", "buttons", "dark mode")
            platform: Optional platform filter (ios, macos, tvos, watchos, visionos)

        Returns:
            Dictionary with search URLs and platform links
        """
        encoded_query = urllib.parse.quote(query)

        results = {
            "query": query,
            "platform": platform,
            "base_url": self.base_url,
            "search_url": f"https://www.google.com/search?q=site:developer.apple.com/design/human-interface-guidelines+{encoded_query}",
            "direct_link": self.base_url
        }

        # Add platform-specific search if specified
        if platform and platform.lower() in self.platforms:
            platform_lower = platform.lower()
            results["platform_url"] = f"{self.base_url}/platforms/{platform_lower}"
            results["platform_search"] = (
                f"https://www.google.com/search?q=site:developer.apple.com/design/human-interface-guidelines+{platform_lower}+{encoded_query}"
            )

        return results

    def list_platforms(self) -> List[Dict]:
        """
        List all supported Apple platforms with Human Interface Guidelines links.

        Returns:
            List of platforms with their URLs
        """
        return [
            {
                "platform": platform,
                "name": platform.upper() if platform != "visionos" else "visionOS",
                "url": f"{self.base_url}/platforms/{platform}"
            }
            for platform in self.platforms
        ]


# Module-level instance
human_interface_guidelines = HumanInterfaceGuidelines()
