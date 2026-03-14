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
from config import Config

# Import specialized modules - each handles a specific documentation source
# These modules are designed to be independent and maintainable
from docs.local_docs import local_docs      # Xcode's hidden local documentation
from docs.apple_docs import apple_docs      # Apple Developer website API access
from evolution.swift_evolution import evolution  # Swift language evolution tracking
from repos.swift_repos import swift_repos   # GitHub repository searching
from wwdc.wwdc_notes import wwdc_notes      # WWDC session notes and transcripts
from design.human_interface_guidelines import human_interface_guidelines  # Human Interface Guidelines
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
# LOCAL DOCUMENTATION TOOLS (Legacy Mode)
# ============================================================================

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


def list_documents(filter: Optional[str] = None) -> List[Dict]:
    """
    List all available Xcode hidden documentation files.
    
    Args:
        filter: Optional filter string to match document names
    
    Returns:
        List of documents with names, topics, versions, and sizes
    """
    return local_docs.list_documents(filter)


def get_xcode_versions() -> List[str]:
    """
    Get list of installed Xcode versions with hidden documentation.
    
    Returns:
        List of Xcode version identifiers (e.g., ['Xcode-26.0.0.app'])
    """
    return local_docs.get_xcode_versions()


# ============================================================================
# APPLE DEVELOPER DOCUMENTATION TOOLS (Legacy Mode)
# ============================================================================

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
# SWIFT EVOLUTION & LANGUAGE REFERENCE TOOLS (Legacy Mode)
# ============================================================================

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


def get_swift_evolution_proposal(se_number: str) -> Dict:
    """
    Get details of a specific Swift Evolution proposal.

    Args:
        se_number: Proposal number (e.g., 'SE-0413' or just '0413')

    Returns:
        Full details of the proposal including title, status, and summary
    """
    return evolution.get_proposal(se_number)


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
# WWDC SESSION NOTES & TRANSCRIPTS (Legacy Mode)
# ============================================================================

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
# HUMAN INTERFACE GUIDELINES TOOLS (Legacy Mode)
# ============================================================================

def search_human_interface_guidelines(query: str, platform: Optional[str] = None) -> Dict:
    """
    Search Apple's Human Interface Guidelines for design patterns and best practices.

    Find design guidance for creating exceptional user experiences across all Apple
    platforms including iOS, macOS, tvOS, watchOS, and visionOS.

    Example queries:
    - "navigation" - Find navigation design patterns
    - "buttons" - Button design guidelines
    - "dark mode" - Dark mode design guidance
    - "accessibility" - Accessibility best practices
    - "color" - Color usage guidelines
    - "typography" - Typography and font guidance

    Args:
        query: Design topic or keyword to search for
        platform: Optional platform filter (ios, macos, tvos, watchos, visionos)

    Returns:
        Dictionary containing:
        - query: The search term used
        - platform: Platform filter if specified
        - base_url: Human Interface Guidelines home page
        - search_url: Google site search URL for the query
        - direct_link: Direct link to Human Interface Guidelines
        - platform_url: Platform-specific URL (if platform specified)
        - platform_search: Platform-filtered search URL (if platform specified)
    """
    # Input validation
    if not query or not query.strip():
        return {
            "error": "Empty query",
            "message": "Please provide a design topic or keyword to search for"
        }

    if len(query) > 500:
        return {
            "error": "Query too long",
            "message": "Maximum query length is 500 characters"
        }

    # Validate platform if provided
    if platform and platform.lower() not in ["ios", "macos", "tvos", "watchos", "visionos"]:
        return {
            "error": "Invalid platform",
            "message": "Platform must be one of: ios, macos, tvos, watchos, visionos"
        }

    results = human_interface_guidelines.search_guidelines(query.strip(), platform)
    return add_suggestions(results, "search_human_interface_guidelines", query)


def list_human_interface_guidelines_platforms() -> List[Dict]:
    """
    List all Apple platforms with their Human Interface Guidelines links.

    Returns:
        List of platforms with URLs to their specific design guidelines
    """
    return human_interface_guidelines.list_platforms()


# ============================================================================
# CODE EXECUTION & DISCOVERY TOOLS (Execution Mode)
# ============================================================================
# These tools implement the "Code Execution with MCP" pattern from Anthropic's
# engineering blog, enabling lazy tool discovery and sandboxed code execution.
# Only exposed when CODE_EXECUTION_MODE=true

# Lazy initialization for execution mode dependencies
_sandbox = None
_tool_filesystem = None


def _init_execution_mode():
    """Initialize execution mode dependencies (lazy loading)."""
    global _sandbox, _tool_filesystem

    if _sandbox is not None:
        return  # Already initialized

    from execution.sandbox import SandboxExecutor
    from execution.api_bridge import documentation_api
    from discovery.tool_filesystem import tool_filesystem

    _tool_filesystem = tool_filesystem

    # API handlers for the sandbox - these get called via IPC when sandbox code
    # calls functions like fetch_documentation(), search_proposals(), etc.
    api_handlers = {
        # Apple Documentation
        "fetch_documentation": documentation_api.fetch_documentation,
        "search_apple_online": documentation_api.search_apple_online,
        "get_framework_info": documentation_api.get_framework_info,
        # Swift Evolution
        "search_proposals": documentation_api.search_proposals,
        "get_proposal": documentation_api.get_proposal,
        # Local Xcode Docs
        "search_docs": documentation_api.search_docs,
        "get_document": documentation_api.get_document,
        "list_documents": documentation_api.list_documents,
        "get_xcode_versions": documentation_api.get_xcode_versions,
        # Swift Repos
        "search_swift_repos": documentation_api.search_swift_repos,
        "fetch_github_file": documentation_api.fetch_github_file,
        # WWDC Notes
        "search_wwdc_notes": documentation_api.search_wwdc_notes,
        "get_wwdc_session": documentation_api.get_wwdc_session,
        # Human Interface Guidelines
        "search_hig": documentation_api.search_hig,
        "list_hig_platforms": documentation_api.list_hig_platforms,
    }

    # Initialize sandbox with configuration and API handlers
    _sandbox = SandboxExecutor(
        timeout=Config.SANDBOX_TIMEOUT_SECONDS,
        max_memory_mb=Config.SANDBOX_MAX_MEMORY_MB,
        max_output_bytes=Config.SANDBOX_MAX_OUTPUT_BYTES,
        api_handlers=api_handlers
    )


def list_tool_directory(path: str = "/tools") -> Dict:
    """
    List contents of the tool filesystem directory.

    Navigate the tool filesystem to discover available documentation APIs.
    Start with "/tools" to see available tool categories.

    This enables lazy tool discovery - explore the structure on-demand
    rather than loading all definitions upfront.

    Args:
        path: Directory path to list (e.g., "/tools", "/tools/apple_documentation")

    Returns:
        Dictionary containing:
        - path: Current directory path
        - entries: List of files/directories with type and description
    """
    _init_execution_mode()
    return _tool_filesystem.list_directory(path)


def read_tool_definition(path: str) -> Dict:
    """
    Read a tool definition file to understand its interface.

    Use this to discover function signatures, parameters, return types,
    and usage examples before writing code for execute_documentation_code.

    Args:
        path: Path to tool definition file
              (e.g., "/tools/apple_documentation/fetch_documentation.py")

    Returns:
        Dictionary containing:
        - path: File path
        - content: Full file content with interface definition
        - name: File name
        - language: Programming language (for .py files)
        - parameters_doc: Parameter documentation (if available)
        - returns_doc: Return value documentation (if available)
    """
    # Security: Prevent path traversal
    if ".." in path:
        return {
            "error": "Invalid path",
            "message": "Path traversal is not allowed"
        }

    _init_execution_mode()
    return _tool_filesystem.read_file(path)


def execute_documentation_code(code: str) -> Dict:
    """
    Execute Python code in a sandboxed environment with documentation API access.

    This tool enables you to write code that fetches and processes documentation
    data, reducing token overhead by filtering results before they're returned.

    Available functions in the sandbox:

    Apple Documentation:
    - fetch_documentation(url: str) -> Dict: Fetch Apple Developer documentation
    - search_apple_online(query: str, platform?: str) -> Dict: Search Apple docs online
    - get_framework_info(framework: str) -> Dict: Get framework documentation URL

    Swift Evolution:
    - search_proposals(feature: str) -> Dict: Search Swift Evolution proposals
    - get_proposal(se_number: str) -> Dict: Get specific proposal details

    Local Xcode Docs:
    - search_docs(query: str, case_sensitive?: bool) -> Dict: Search local Xcode docs
    - get_document(name: str, xcode_version?: str) -> Dict: Get document content
    - list_documents(filter?: str) -> List: List available documents
    - get_xcode_versions() -> List: Get installed Xcode versions

    Swift Repos:
    - search_swift_repos(query: str) -> Dict: Search Apple/SwiftLang GitHub repos
    - fetch_github_file(url: str) -> Dict: Fetch file from GitHub

    WWDC Notes:
    - search_wwdc_notes(query: str) -> Dict: Search WWDC session notes
    - get_wwdc_session(session_id: str) -> Dict: Get WWDC session info

    Human Interface Guidelines:
    - search_hig(query: str, platform?: str) -> Dict: Search HIG
    - list_hig_platforms() -> List: List HIG platforms

    Available builtins:
    - Data types: list, dict, set, tuple, str, int, float, bool, bytes
    - Iteration: len, range, enumerate, zip, map, filter, reversed, sorted
    - Aggregation: min, max, sum, any, all
    - Math: abs, round, pow
    - Type checking: isinstance, type
    - Output: print, repr

    IMPORTANT: Your code must assign the final result to a variable named 'result'.

    Example:
        ```python
        # Fetch documentation and extract specific fields
        doc = fetch_documentation("https://developer.apple.com/documentation/swiftui/view")
        result = {
            "title": doc.get("title"),
            "declaration": doc.get("declaration")
        }
        ```

        ```python
        # Search proposals and filter to Swift 6
        data = search_proposals("async")
        swift6 = [p for p in data.get("proposals", []) if "6" in p.get("version", "")]
        result = {"count": len(swift6), "proposals": swift6[:5]}
        ```

    Args:
        code: Python code to execute. Must assign result to 'result' variable.

    Returns:
        Dictionary containing:
        - success: Whether execution completed successfully
        - result: Value of 'result' variable (your processed data)
        - stdout: Any print() output from your code
        - error: Error message if execution failed
        - error_type: Type of error (ValidationError, TimeoutError, etc.)
        - execution_time_ms: Time taken to execute
        - validation_warnings: Any warnings from code validation
    """
    # Validate code length
    if not code or not code.strip():
        return {
            "success": False,
            "error": "Empty code provided",
            "error_type": "ValidationError"
        }

    if len(code) > Config.SANDBOX_MAX_CODE_LENGTH:
        return {
            "success": False,
            "error": f"Code too long: {len(code)} chars (max {Config.SANDBOX_MAX_CODE_LENGTH})",
            "error_type": "ValidationError"
        }

    # Initialize sandbox on first use
    _init_execution_mode()

    # Execute in sandbox with IPC-based API access
    # The sandbox uses subprocess isolation with stdin/stdout IPC for API calls,
    # allowing dynamic/chained calls like: get_proposal(search_results["proposals"][0]["se"])
    result = _sandbox.execute(code)

    return result.to_dict()


# ============================================================================
# CONDITIONAL TOOL REGISTRATION
# ============================================================================
# Register tools based on CODE_EXECUTION_MODE configuration.
# - Legacy mode (default): Individual documentation tools exposed
# - Execution mode: Only code execution sandbox tools exposed

# Legacy tools - individual documentation access tools
_LEGACY_TOOLS = [
    # Local Documentation
    search_docs,
    get_document,
    list_documents,
    get_xcode_versions,
    # Apple Developer Documentation
    fetch_apple_documentation,
    search_apple_online,
    get_framework_info,
    # Swift Evolution
    search_swift_evolution,
    get_swift_evolution_proposal,
    # Swift Repos
    search_swift_repos,
    fetch_github_file,
    # WWDC Notes
    search_wwdc_notes,
    get_wwdc_session,
    # Human Interface Guidelines
    search_human_interface_guidelines,
    list_human_interface_guidelines_platforms,
]

# Execution tools - sandbox-based code execution
_EXECUTION_TOOLS = [
    list_tool_directory,
    read_tool_definition,
    execute_documentation_code,
]


def _register_tools():
    """
    Register tools based on configuration mode.

    This function is called at module load time to register the appropriate
    set of tools with the MCP server based on CODE_EXECUTION_MODE.
    """
    from config import logger

    if Config.execution_tools_enabled():
        # Code execution mode - register only sandbox tools
        logger.info("Tool mode: CODE_EXECUTION (sandbox tools only)")
        for tool_func in _EXECUTION_TOOLS:
            mcp.tool()(tool_func)
            logger.debug(f"  Registered: {tool_func.__name__}")
    else:
        # Legacy mode (default) - register individual documentation tools
        logger.info("Tool mode: LEGACY (individual documentation tools)")
        for tool_func in _LEGACY_TOOLS:
            mcp.tool()(tool_func)
            logger.debug(f"  Registered: {tool_func.__name__}")


# Register tools on module load
_register_tools()
