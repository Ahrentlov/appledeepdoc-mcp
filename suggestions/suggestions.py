"""
Simplified Suggestion Engine - provides next-step recommendations for MCP tools.
"""

from typing import Dict, List
import re


class SuggestionEngine:
    """Simple, efficient suggestion engine for tool recommendations."""

    def __init__(self):
        # Tool progression: what to try next when current tool has no/few results
        self.fallbacks = {
            "search_docs": ["search_apple_online", "search_wwdc_notes"],
            "search_apple_online": ["search_wwdc_notes", "search_swift_repos"],
            "search_swift_evolution": ["search_swift_repos", "fetch_github_file"],
            "search_swift_repos": ["fetch_github_file"],
            "search_wwdc_notes": ["search_swift_repos"],
            "search_human_interface_guidelines": ["search_docs", "search_apple_online"],
        }

        # Simple keyword to tool mapping
        self.keywords = {
            "performance|optimize|fast": ["search_wwdc_notes", "search_swift_repos"],
            "how|implement|build": ["search_swift_repos", "search_wwdc_notes"],
            "why|design|rationale": ["search_swift_evolution"],
            "class|struct|protocol": ["fetch_apple_documentation", "search_apple_online"],
            "design|ui|ux|interface|button|navigation|layout|color|typography": ["search_human_interface_guidelines"],
        }

    def get_suggestions(self, context: Dict) -> List[Dict]:
        """
        Get up to 3 relevant tool suggestions based on context.

        Args:
            context: Dict with current_tool, query, results_count
        Returns:
            List of suggestions with tool name and simple reason
        """
        suggestions = []
        current_tool = context.get("current_tool", "")
        query = context.get("query", "").lower()
        results_count = context.get("results_count", 0)

        # If no results, suggest fallback tools
        if results_count == 0 and current_tool in self.fallbacks:
            for tool in self.fallbacks[current_tool][:2]:
                suggestions.append({
                    "tool": tool,
                    "reason": self._get_reason(tool)
                })

        # Add keyword-based suggestions if not already present
        for pattern, tools in self.keywords.items():
            if re.search(pattern, query):
                for tool in tools:
                    if tool != current_tool and not any(s["tool"] == tool for s in suggestions):
                        suggestions.append({
                            "tool": tool,
                            "reason": self._get_reason(tool)
                        })
                        if len(suggestions) >= 3:
                            return suggestions[:3]

        return suggestions[:3]

    def _get_reason(self, tool: str) -> str:
        """Simple one-line reasons for each tool."""
        reasons = {
            "search_apple_online": "Search Apple's online documentation",
            "search_wwdc_notes": "Check WWDC sessions for detailed explanations",
            "search_swift_repos": "Find implementation examples",
            "fetch_github_file": "Fetch specific source files",
            "search_swift_evolution": "Understand feature design rationale",
            "fetch_apple_documentation": "Get detailed API documentation",
            "search_human_interface_guidelines": "Find design patterns and UI best practices",
        }
        return reasons.get(tool, f"Try {tool}")


# Global instance
suggestion_engine = SuggestionEngine()