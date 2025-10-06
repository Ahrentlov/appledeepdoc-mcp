"""
Apple Deep Docs MCP Server
==========================

An optimized Model Context Protocol (MCP) server providing comprehensive access to
Apple's development documentation ecosystem through a modular architecture.

Architecture Overview:
- tools.py: MCP tool definitions and input validation (this file)
- docs/: Documentation access modules (local Xcode docs, Apple Developer API)
- evolution/: Swift Evolution proposal tracking
- repos/: Swift open-source repository searching
- config.py: Central configuration management

Each module handles its own caching, error handling, and business logic,
while this file focuses on MCP interface definition and input sanitization.
"""

from typing import Dict, List, Optional
from fastmcp import FastMCP
from config import Config, logger

# Import specialized modules - each handles a specific documentation source
# These modules are designed to be independent and maintainable
from docs.local_docs import local_docs      # Xcode's hidden local documentation
from docs.apple_docs import apple_docs      # Apple Developer website API access
from evolution.swift_evolution import evolution  # Swift language evolution tracking
from repos.swift_repos import swift_repos   # GitHub repository searching
from wwdc.wwdc_notes import wwdc_notes      # WWDC session notes and transcripts
from suggestions.suggestions import suggestion_engine   # Centralized suggestion system

# Initialize the FastMCP server with configuration
mcp = FastMCP(Config.SERVER_NAME)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def add_suggestions(results: Dict, tool_name: str, query: str) -> Dict:
    """Add suggestions to results if applicable."""
    suggestions = suggestion_engine.get_suggestions({
        "current_tool": tool_name,
        "query": query,
        "results_count": results.get("total_results", results.get("total_found", 1))
    })
    if suggestions:
        results["suggestions"] = suggestions
    return results

# ============================================================================
# LOCAL DOCUMENTATION TOOLS
# ============================================================================

@mcp.tool()
def search_docs(query: str, case_sensitive: bool = False) -> Dict:
    """
    Search through Xcode's hidden local documentation for design patterns and implementation guides.

    This tool searches the AdditionalDocumentation folder in Xcode.framework which contains:
    - Liquid Glass design implementation guides for iOS 18+
    - Advanced SwiftUI patterns and best practices
    - Framework-specific implementation details not in public docs
    - Performance optimization techniques
    - Accessibility implementation guides

    Example queries:
    - "liquid glass" - Find glass morphism design guides
    - "TabBar" - Implementation patterns for tab bars
    - "performance" - Optimization techniques
    - "SwiftUI animation" - Animation implementation guides

    Args:
        query: Search term to find in documentation (e.g., "liquid glass", "TabBar")
        case_sensitive: Whether to perform case-sensitive search (default: False)

    Returns:
        Dictionary containing:
        - query: The search term used
        - total_results: Number of matching documents
        - results: List of documents with:
            - document: Document name
            - xcode_version: Which Xcode version contains this doc
            - matches: Context snippets showing where query was found
            - total_matches: Number of matches in this document
    """
    # Input validation - ensure query is meaningful
    if not query or not query.strip():
        return {
            "error": "Empty query",
            "message": "Please provide a non-empty search term"
        }

    # Prevent potential DoS with extremely long queries
    if len(query) > 500:
        return {
            "error": "Query too long",
            "message": "Maximum query length is 500 characters"
        }

    # Delegate to local_docs module which handles file I/O and caching
    results = local_docs.search(query.strip(), case_sensitive)
    return add_suggestions(results, "search_docs", query)


@mcp.tool()
def get_document(name: str, xcode_version: Optional[str] = None) -> str:
    """
    Retrieve full content of a local Xcode documentation file.

    Args:
        name: Document name (e.g., 'SwiftUI-Implementing-Liquid-Glass-Design')
        xcode_version: Optional specific Xcode version (e.g., 'Xcode-26.0.0.app')

    Returns:
        Full markdown content of the documentation file
    """
    # Security: Prevent path traversal attacks by blocking directory navigation
    # Check for '..' (parent dir), '/' (Unix path), '\\' (Windows path)
    if not name or '..' in name or '/' in name or '\\' in name:
        return "Error: Invalid document name. Use document name only, without path separators."

    # File system limitation - most systems limit filename to 255 chars
    if len(name) > 255:
        return "Error: Document name too long (max 255 characters)."

    # Safe to delegate - name has been sanitized
    return local_docs.get_document(name, xcode_version)


@mcp.tool()
def list_documents(filter: Optional[str] = None) -> List[Dict]:
    """
    List all available Xcode hidden documentation files.
    
    Args:
        filter: Optional filter string to match document names
    
    Returns:
        List of documents with names, topics, versions, and sizes
    """
    return local_docs.list_documents(filter)


@mcp.tool()
def get_xcode_versions() -> List[str]:
    """
    Get list of installed Xcode versions with hidden documentation.
    
    Returns:
        List of Xcode version identifiers (e.g., ['Xcode-26.0.0.app'])
    """
    return local_docs.get_xcode_versions()


# ============================================================================
# APPLE DEVELOPER DOCUMENTATION TOOLS
# ============================================================================

@mcp.tool()
def fetch_apple_documentation(url: str) -> Dict:
    """
    Fetch and parse structured documentation from Apple Developer website.

    This tool accesses Apple's internal JSON API to retrieve detailed documentation
    including method signatures, parameters, return values, and code examples.
    Works with any developer.apple.com/documentation URL.

    Example URLs:
    - https://developer.apple.com/documentation/swiftui/view
    - https://developer.apple.com/documentation/uikit/uiviewcontroller
    - https://developer.apple.com/documentation/swift/array/contains(_:)

    Args:
        url: Full Apple documentation URL (must start with https://developer.apple.com/documentation/)

    Returns:
        Dictionary containing:
        - title: API or type name
        - abstract: Brief description
        - declaration: Full method/type signature
        - discussion: Detailed explanation
        - parameters: List of parameter descriptions
        - returns: Return value description
        - url: Original documentation URL
        - json_url: API endpoint used

        Or error dictionary if fetch fails:
        - error: Error type
        - message: Detailed error message
        - suggestion: How to fix the issue
    """
    # Basic validation - check for empty or whitespace-only URLs
    if not url or not url.strip():
        return {
            "error": "Empty URL",
            "message": "Please provide a valid Apple Developer documentation URL",
            "suggestion": "Example: https://developer.apple.com/documentation/swiftui/view"
        }

    url = url.strip()

    # Ensure URL is for Apple Developer documentation specifically
    # This prevents accidental requests to other Apple domains
    if not url.startswith("https://developer.apple.com/documentation/"):
        return {
            "error": "Invalid URL",
            "message": "URL must start with https://developer.apple.com/documentation/",
            "suggestion": "Example: https://developer.apple.com/documentation/swiftui/view"
        }

    # Additional security: validate URL structure to prevent URL injection
    from urllib.parse import urlparse
    try:
        parsed = urlparse(url)
        # Double-check the domain to prevent bypasses
        if parsed.netloc != "developer.apple.com":
            return {
                "error": "Invalid URL",
                "message": "URL must be from developer.apple.com domain"
            }
    except Exception:
        return {
            "error": "Malformed URL",
            "message": "The provided URL is not valid"
        }

    # URL is validated - delegate to apple_docs for API access
    return apple_docs.fetch_documentation(url)


@mcp.tool()
def search_apple_online(query: str, platform: Optional[str] = None) -> Dict:
    """
    Search both local Xcode docs and Apple's online documentation.
    
    This tool combines local hidden documentation search with online search URLs.
    It first checks local Xcode docs for relevant content, then provides search
    URLs for Apple Developer site, Google, and GitHub code examples.
    
    Args:
        query: Search term (e.g., 'liquid glass', 'async await', 'Int128')
        platform: Optional platform filter (ios, macos, tvos, watchos, visionos)
    
    Returns:
        Dictionary containing:
        - query: Search term used
        - platform: Platform filter applied
        - local_docs: Local search results with found count and top 5 results
        - online: Search URLs for Apple, Google, and GitHub
    """
    # First, check local Xcode documentation for immediate results
    local_results = local_docs.search(query)

    # Generate online search URLs for broader exploration
    online_results = apple_docs.search_online(query, platform)

    # Combine both sources - local for speed, online for completeness
    combined_results = {
        "query": query,
        "platform": platform,
        "local_docs": {
            "found": local_results["total_results"],
            # Limit to top 5 results to keep response concise
            "results": local_results["results"][:5] if local_results["total_results"] > 0 else []
        },
        "online": online_results
    }

    # Add intelligent suggestions using centralized engine
    suggestions = suggestion_engine.get_suggestions({
        "current_tool": "search_apple_online",
        "query": query,
        "results_count": local_results["total_results"]
    })

    if suggestions:
        combined_results["suggestions"] = suggestions

    return combined_results


@mcp.tool()
def get_framework_info(framework: str) -> Dict:
    """
    Get direct documentation URL for an Apple framework.
    
    Generates the official Apple Developer documentation URL for any framework.
    The tool normalizes the framework name and constructs the appropriate URL.
    
    Args:
        framework: Framework name (e.g., 'SwiftUI', 'UIKit', 'Foundation')
    
    Returns:
        Dictionary containing:
        - name: Framework name as provided
        - url: Direct documentation URL
        - note: Additional information about the link
    """
    return apple_docs.get_framework_info(framework)


# ============================================================================
# SWIFT EVOLUTION & LANGUAGE REFERENCE TOOLS  
# ============================================================================

@mcp.tool()
def search_swift_evolution(feature: str) -> Dict:
    """
    Search 500+ Swift Evolution proposals to understand the "why" behind language features.

    Fetches live data from swift.org's evolution.json feed for design rationale,
    history, and implementation details of Swift language features.

    Args:
        feature: Feature or concept to search for (e.g., 'async', 'actors', 'sendable', 'Swift 6')

    Returns:
        Matching proposals with SE numbers, titles, status (Swift version), and summaries
    """
    results = evolution.search_proposals(feature)
    return add_suggestions(results, "search_swift_evolution", feature)


@mcp.tool()
def get_swift_evolution_proposal(se_number: str) -> Dict:
    """
    Get details of a specific Swift Evolution proposal.

    Args:
        se_number: Proposal number (e.g., 'SE-0413' or just '0413')

    Returns:
        Full details of the proposal including title, status, and summary
    """
    return evolution.get_proposal(se_number)


@mcp.tool()
def search_swift_repos(query: str) -> Dict:
    """
    Search across all Apple and SwiftLang open source Swift repositories.

    This tool searches the entire Apple/SwiftLang Swift ecosystem including:
    - Core: swift, swift-syntax, swift-driver
    - Libraries: swift-nio, swift-collections, swift-algorithms
    - Tools: swift-package-manager, swift-format, swift-docc
    - Foundation: swift-foundation, swift-corelibs-*
    - Async: swift-distributed-actors, swift-async-algorithms
    - Testing: swift-testing, swift-corelibs-xctest
    - And 50+ more repositories

    Dynamically searches ALL current Swift repos without needing to maintain a list.
    Discovers new repositories automatically as Apple/SwiftLang adds them.

    Example queries:
    - "async actor" - Find actor usage patterns
    - "property wrapper" - See real implementations
    - "URLSession" - Find networking code
    - "XCTest" - Discover testing patterns

    Args:
        query: Code or concept to search for across all Swift repositories

    Returns:
        Dictionary containing:
        - search_urls: Different search scopes (all repos, apple only, swiftlang only)
        - note: How to use the search
        - tip: Additional search guidance
    """
    results = swift_repos.search_repos(query)
    return add_suggestions(results, "search_swift_repos", query)


@mcp.tool()
def fetch_github_file(url: str) -> Dict:
    """
    Fetch source code from Apple or SwiftLang GitHub repositories.

    Use this tool to retrieve actual implementation code to understand how
    Swift features are implemented in the compiler, standard library, or frameworks.

    Workflow:
    1. Use search_swift_repos() to find relevant code
    2. Click search URLs to browse GitHub and find the file you need
    3. Use this tool to fetch the actual source code

    Example URLs:
    - https://github.com/apple/swift/blob/main/stdlib/public/Concurrency/Task.swift
    - https://github.com/swiftlang/swift-package-manager/blob/main/Sources/PackageModel/Manifest.swift
    - https://github.com/apple/swift-nio/blob/main/Sources/NIO/EventLoop.swift

    Args:
        url: GitHub file URL from apple or swiftlang organizations

    Returns:
        Dictionary containing:
        - content: The complete file source code
        - url: Original URL provided
        - raw_url: The raw content URL used for fetching
        - language: Detected programming language
        - repo: Repository name (e.g., "apple/swift")
        - path: File path within repository
        - size: Content size in bytes
        - lines: Number of lines in the file

        Or error dictionary if fetch fails:
        - error: Error type
        - message: Detailed error message
        - suggestion: How to fix the issue
    """
    # Validate that a URL was provided
    if not url or not url.strip():
        return {
            "error": "Empty URL",
            "message": "Please provide a GitHub file URL",
            "suggestion": "Example: https://github.com/apple/swift/blob/main/stdlib/public/Concurrency/Task.swift"
        }

    # Delegate to swift_repos which handles GitHub URL parsing and fetching
    # The module validates org membership (apple/swiftlang) internally
    return swift_repos.fetch_github_file(url.strip())


# ============================================================================
# WWDC SESSION NOTES & TRANSCRIPTS
# ============================================================================

@mcp.tool()
def search_wwdc_notes(query: str) -> Dict:
    """
    Search WWDC session notes for topics not in regular documentation.

    Covers performance optimization, architecture patterns, debugging, and new features
    through community-curated session summaries.

    Args:
        query: Topic to search for (e.g., 'performance', 'swift concurrency')

    Returns:
        Search URLs and relevant categories
    """
    results = wwdc_notes.search_sessions(query)
    return add_suggestions(results, "search_wwdc_notes", query)


@mcp.tool()
def get_wwdc_session(session_id: str) -> Dict:
    """
    Get WWDC session URLs from session ID.

    Args:
        session_id: Format 'wwdc2023-10154' or 'wwdc2023/10154'

    Returns:
        Session URLs for notes and videos
    """
    return wwdc_notes.get_session_info(session_id)


# ============================================================================
# SERVER INITIALIZATION
# ============================================================================

if __name__ == "__main__":
    logger.info("Initializing Apple Documentation MCP Server...")
    logger.info("Loading modules:")
    logger.info("  ✓ Local documentation search (docs/local_docs.py)")
    logger.info("  ✓ Apple API fetching (docs/apple_docs.py)")
    logger.info("  ✓ Swift Evolution proposals (evolution/swift_evolution.py)")
    logger.info("  ✓ Swift repositories search (repos/swift_repos.py)")
    logger.info("  ✓ WWDC session notes (wwdc/wwdc_notes.py)")
    logger.info("  ✓ Suggestion engine (suggestions.py)")
    logger.info("MCP server ready with intelligent tool suggestions")
    mcp.run()