"""
WWDC Notes Module - Access to WWDC session information for topics not in regular docs.
"""

import urllib.parse
from typing import Dict


class WWDCNotes:
    """Simple interface to WWDC session search."""

    def __init__(self):
        self.base_url = "https://wwdcnotes.com"

    def search_sessions(self, query: str) -> Dict:
        """
        Generate search URLs for WWDC sessions.

        Args:
            query: Topic to search for

        Returns:
            Search URLs and topic detection
        """
        encoded_query = urllib.parse.quote(query)
        query_lower = query.lower()

        # Detect key topics
        is_performance = any(word in query_lower for word in ["performance", "optimize", "fast", "memory"])
        is_swift = "swift" in query_lower
        is_swiftui = "swiftui" in query_lower

        result = {
            "query": query,
            "search_urls": {
                "wwdcnotes": f"{self.base_url}/search?q={encoded_query}",
                "apple_videos": f"https://developer.apple.com/search/?q={encoded_query}&type=Videos",
            }
        }

        # Add context-specific tips
        if is_performance:
            result["tip"] = "WWDC has extensive performance sessions not found in regular docs"
            result["categories"] = ["Instruments", "App Performance", "Memory Management"]
        elif is_swift:
            result["categories"] = ["What's New in Swift", "Swift Concurrency"]
        elif is_swiftui:
            result["categories"] = ["SwiftUI Essentials", "SwiftUI Layout", "SwiftUI Animation"]

        return result

    def get_session_info(self, session_id: str) -> Dict:
        """
        Get session URLs from ID.

        Args:
            session_id: Format wwdc2023-10154

        Returns:
            Session URLs
        """
        # Simple parsing - wwdc2023-10154 or wwdc2023/10154
        parts = session_id.lower().replace("/", "-").split("-")
        if len(parts) >= 2 and "wwdc" in parts[0]:
            year = parts[0].replace("wwdc", "")
            number = parts[1]

            return {
                "session_id": f"wwdc{year}-{number}",
                "urls": {
                    "wwdcnotes": f"{self.base_url}/notes/wwdc{year}/{number}",
                    "apple_video": f"https://developer.apple.com/videos/play/wwdc{year}/{number}/",
                }
            }

        return {"error": "Invalid session ID format. Use: wwdc2023-10154"}


# Module instance
wwdc_notes = WWDCNotes()