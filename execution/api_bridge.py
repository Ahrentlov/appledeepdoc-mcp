"""
Documentation API Bridge for Sandbox Execution
===============================================

Provides safe, serializable wrappers around the documentation APIs
that can be used within the sandboxed execution environment.

The bridge:
1. Calls the existing module instances (all documentation sources)
2. Returns plain dictionaries (JSON-serializable)
3. Handles errors gracefully
4. Provides utility functions for data processing

These functions are designed to be called from the sandbox subprocess
via IPC (stdin/stdout JSON protocol).

Available APIs:
- Apple Documentation: fetch_documentation, search_apple_online, get_framework_info
- Swift Evolution: search_proposals, get_proposal
- Local Xcode Docs: search_docs, get_document, list_documents, get_xcode_versions
- Swift Repos: search_swift_repos, fetch_github_file
- WWDC Notes: search_wwdc_notes, get_wwdc_session
- HIG: search_hig, list_hig_platforms
"""

import sys
import os
from typing import Dict, List, Callable, Any, Optional, TypedDict


# =============================================================================
# TYPE DEFINITIONS
# =============================================================================
# TypedDict definitions for all API return types. These provide:
# - Static analysis support for IDEs
# - Self-documenting API contracts
# - Type safety for callers


class ErrorResult(TypedDict, total=False):
    """Standard error response structure."""
    error: str
    message: str
    suggestion: str


class DocumentationResult(TypedDict, total=False):
    """Result from fetch_documentation()."""
    title: str
    abstract: str
    declaration: str
    discussion: str
    parameters: List[Dict]
    returns: str
    url: str
    json_url: str
    # Error fields
    error: str
    message: str
    suggestion: str


class SearchDocsResult(TypedDict, total=False):
    """Result from search_docs()."""
    query: str
    total_results: int
    results: List[Dict]  # Each has: document, xcode_version, matches, total_matches
    # Error fields
    error: str
    message: str


class DocumentContentResult(TypedDict, total=False):
    """Result from get_document()."""
    name: str
    content: str
    length: int
    # Error fields
    error: str
    message: str


class DocumentListResult(TypedDict, total=False):
    """Result from list_documents()."""
    documents: List[Dict]  # Each has: name, topics, size, xcode_versions
    count: int
    # Error fields
    error: str
    message: str


class XcodeVersionsResult(TypedDict, total=False):
    """Result from get_xcode_versions()."""
    versions: List[str]
    count: int
    # Error fields
    error: str
    message: str


class ProposalResult(TypedDict, total=False):
    """A single Swift Evolution proposal."""
    se_number: str
    title: str
    status: str
    version: str
    summary: str
    github_url: str
    relevance_score: int


class SearchProposalsResult(TypedDict, total=False):
    """Result from search_proposals()."""
    feature: str
    total_found: int
    proposals: List[ProposalResult]
    available_versions: List[str]
    # Error fields
    error: str
    message: str
    suggestion: str


class ProposalDetailResult(TypedDict, total=False):
    """Result from get_proposal()."""
    se_number: str
    title: str
    status: str
    version: str
    summary: str
    authors: List[str]
    github_url: str
    raw_url: str
    swift_org_url: str
    # Error fields
    error: str
    message: str
    suggestion: str


class SearchReposResult(TypedDict, total=False):
    """Result from search_swift_repos()."""
    query: str
    search_urls: Dict[str, str]  # all_repos, apple_only, swiftlang_only
    note: str
    tip: str
    # Error fields
    error: str
    message: str


class GitHubFileResult(TypedDict, total=False):
    """Result from fetch_github_file()."""
    content: str
    url: str
    raw_url: str
    language: str
    repo: str
    path: str
    size: int
    lines: int
    # Error fields
    error: str
    message: str
    suggestion: str


class WWDCSearchResult(TypedDict, total=False):
    """Result from search_wwdc_notes()."""
    query: str
    search_url: str
    categories: List[str]
    note: str
    # Error fields
    error: str
    message: str


class WWDCSessionResult(TypedDict, total=False):
    """Result from get_wwdc_session()."""
    session_id: str
    notes_url: str
    video_url: str
    apple_url: str
    # Error fields
    error: str
    message: str


class HIGSearchResult(TypedDict, total=False):
    """Result from search_hig()."""
    query: str
    platform: Optional[str]
    base_url: str
    search_url: str
    direct_link: str
    platform_url: str
    platform_search: str
    # Error fields
    error: str
    message: str


class HIGPlatform(TypedDict):
    """A single HIG platform entry."""
    name: str
    url: str
    description: str


class HIGPlatformsResult(TypedDict, total=False):
    """Result from list_hig_platforms()."""
    platforms: List[HIGPlatform]
    count: int
    # Error fields
    error: str
    message: str


class FrameworkInfoResult(TypedDict, total=False):
    """Result from get_framework_info()."""
    name: str
    url: str
    note: str
    # Error fields
    error: str
    message: str


class SearchAppleOnlineResult(TypedDict, total=False):
    """Result from search_apple_online()."""
    query: str
    platform: Optional[str]
    apple_url: str
    google_url: str
    github_url: str
    # Error fields
    error: str
    message: str


# =============================================================================
# MODULE IMPORTS
# =============================================================================

# Add parent directory to path for imports when used standalone
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from docs.apple_docs import apple_docs
from docs.local_docs import local_docs
from evolution.swift_evolution import evolution
from repos.swift_repos import swift_repos
from wwdc.wwdc_notes import wwdc_notes
from design.human_interface_guidelines import human_interface_guidelines


class DocumentationAPI:
    """
    Bridge class that wraps documentation modules for sandbox use.

    This class provides methods that:
    - Are safe to expose to sandboxed code
    - Return JSON-serializable data
    - Handle errors without exposing internals

    Available functions:
    - fetch_documentation(url) - Apple Developer docs
    - search_apple_online(query, platform?) - Combined local + online search
    - get_framework_info(framework) - Framework documentation URL
    - search_proposals(feature) - Swift Evolution search
    - get_proposal(se_number) - Swift Evolution proposal details
    - search_docs(query, case_sensitive?) - Local Xcode docs search
    - get_document(name, xcode_version?) - Local Xcode doc content
    - list_documents(filter?) - List local Xcode docs
    - get_xcode_versions() - List Xcode versions
    - search_swift_repos(query) - Search Apple/SwiftLang GitHub repos
    - fetch_github_file(url) - Fetch file from Apple/SwiftLang repos
    - search_wwdc_notes(query) - Search WWDC session notes
    - get_wwdc_session(session_id) - Get WWDC session info
    - search_hig(query, platform?) - Search Human Interface Guidelines
    - list_hig_platforms() - List HIG platforms
    """

    def __init__(self):
        """Initialize with references to existing module instances."""
        self._apple_docs = apple_docs
        self._local_docs = local_docs
        self._evolution = evolution
        self._swift_repos = swift_repos
        self._wwdc_notes = wwdc_notes
        self._hig = human_interface_guidelines

    def fetch_documentation(self, url: str) -> DocumentationResult:
        """
        Fetch Apple Developer documentation.

        Wrapper around apple_docs.fetch_documentation() that ensures
        safe, serializable return values.

        Args:
            url: Apple documentation URL

        Returns:
            Dictionary with documentation data or error information
        """
        if not url or not isinstance(url, str):
            return {"error": "Invalid URL", "message": "URL must be a non-empty string"}

        if not url.startswith("https://developer.apple.com/documentation/"):
            return {
                "error": "Invalid URL",
                "message": "URL must start with https://developer.apple.com/documentation/"
            }

        try:
            result = self._apple_docs.fetch_documentation(url)
            return self._ensure_serializable(result)
        except Exception as e:
            return {"error": "Fetch failed", "message": str(e)}

    def search_proposals(self, feature: str) -> SearchProposalsResult:
        """
        Search Swift Evolution proposals.

        Wrapper around evolution.search_proposals() that ensures
        safe, serializable return values.

        Args:
            feature: Feature name or Swift version to search for

        Returns:
            Dictionary with matching proposals or error information
        """
        if not feature or not isinstance(feature, str):
            return {"error": "Invalid feature", "message": "Feature must be a non-empty string"}

        if len(feature) > 500:
            return {"error": "Query too long", "message": "Maximum query length is 500 characters"}

        try:
            result = self._evolution.search_proposals(feature)
            return self._ensure_serializable(result)
        except Exception as e:
            return {"error": "Search failed", "message": str(e)}

    def get_proposal(self, se_number: str) -> ProposalDetailResult:
        """
        Get details of a specific Swift Evolution proposal.

        Wrapper around evolution.get_proposal() that ensures
        safe, serializable return values.

        Args:
            se_number: Proposal number (e.g., 'SE-0413' or '0413')

        Returns:
            Dictionary with proposal details or error information
        """
        if not se_number or not isinstance(se_number, str):
            return {"error": "Invalid SE number", "message": "SE number must be a non-empty string"}

        try:
            result = self._evolution.get_proposal(se_number)
            return self._ensure_serializable(result)
        except Exception as e:
            return {"error": "Lookup failed", "message": str(e)}

    def search_docs(self, query: str, case_sensitive: bool = False) -> SearchDocsResult:
        """
        Search local Xcode documentation.

        Wrapper around local_docs.search() that ensures
        safe, serializable return values.

        Args:
            query: Search term to find in documentation
            case_sensitive: Whether to perform case-sensitive search

        Returns:
            Dictionary with search results or error information
        """
        if not query or not isinstance(query, str):
            return {"error": "Invalid query", "message": "Query must be a non-empty string"}

        if len(query) > 500:
            return {"error": "Query too long", "message": "Maximum query length is 500 characters"}

        try:
            result = self._local_docs.search(query, case_sensitive)
            return self._ensure_serializable(result)
        except Exception as e:
            return {"error": "Search failed", "message": str(e)}

    def get_document(self, name: str, xcode_version: Optional[str] = None) -> DocumentContentResult:
        """
        Get full content of a local Xcode documentation file.

        Wrapper around local_docs.get_document() that ensures
        safe, serializable return values. Note: Returns raw string
        from underlying API, wrapped in dict.

        Args:
            name: Document name (e.g., 'SwiftUI-Implementing-Liquid-Glass-Design')
            xcode_version: Optional specific Xcode version

        Returns:
            Dictionary with document content or error information
        """
        if not name or not isinstance(name, str):
            return {"error": "Invalid name", "message": "Name must be a non-empty string"}

        try:
            content = self._local_docs.get_document(name, xcode_version)
            return {
                "name": name,
                "content": content,
                "length": len(content)
            }
        except Exception as e:
            return {"error": "Fetch failed", "message": str(e)}

    def list_documents(self, filter: Optional[str] = None) -> DocumentListResult:
        """
        List all available Xcode hidden documentation files.

        Wrapper around local_docs.list_documents() that ensures
        safe, serializable return values.

        Args:
            filter: Optional filter string to match document names

        Returns:
            Dictionary with document list or error information
        """
        try:
            result = self._local_docs.list_documents(filter)
            # Ensure consistent dict return format
            if isinstance(result, list):
                return {"documents": self._ensure_serializable(result), "count": len(result)}
            return self._ensure_serializable(result)
        except Exception as e:
            return {"error": "List failed", "message": str(e)}

    def get_xcode_versions(self) -> XcodeVersionsResult:
        """
        Get list of installed Xcode versions with hidden documentation.

        Wrapper around local_docs.get_xcode_versions() that ensures
        safe, serializable return values.

        Returns:
            Dictionary with Xcode versions or error information
        """
        try:
            result = self._local_docs.get_xcode_versions()
            # Ensure consistent dict return format
            if isinstance(result, list):
                return {"versions": self._ensure_serializable(result), "count": len(result)}
            return self._ensure_serializable(result)
        except Exception as e:
            return {"error": "Lookup failed", "message": str(e)}

    def search_apple_online(self, query: str, platform: Optional[str] = None) -> SearchAppleOnlineResult:
        """
        Search both local Xcode docs and Apple's online documentation.

        Wrapper around apple_docs.search_online() that ensures
        safe, serializable return values.

        Args:
            query: Search term (e.g., 'liquid glass', 'async await')
            platform: Optional platform filter (ios, macos, tvos, watchos, visionos)

        Returns:
            Dictionary with search results and URLs or error information
        """
        if not query or not isinstance(query, str):
            return {"error": "Invalid query", "message": "Query must be a non-empty string"}

        if len(query) > 500:
            return {"error": "Query too long", "message": "Maximum query length is 500 characters"}

        try:
            result = self._apple_docs.search_online(query, platform)
            return self._ensure_serializable(result)
        except Exception as e:
            return {"error": "Search failed", "message": str(e)}

    def get_framework_info(self, framework: str) -> FrameworkInfoResult:
        """
        Get direct documentation URL for an Apple framework.

        Wrapper around apple_docs.get_framework_info() that ensures
        safe, serializable return values.

        Args:
            framework: Framework name (e.g., 'SwiftUI', 'UIKit', 'Foundation')

        Returns:
            Dictionary with framework URL or error information
        """
        if not framework or not isinstance(framework, str):
            return {"error": "Invalid framework", "message": "Framework must be a non-empty string"}

        try:
            result = self._apple_docs.get_framework_info(framework)
            return self._ensure_serializable(result)
        except Exception as e:
            return {"error": "Lookup failed", "message": str(e)}

    def search_swift_repos(self, query: str) -> SearchReposResult:
        """
        Search across all Apple and SwiftLang open source Swift repositories.

        Wrapper around swift_repos.search_repos() that ensures
        safe, serializable return values.

        Args:
            query: Code or concept to search for

        Returns:
            Dictionary with search URLs or error information
        """
        if not query or not isinstance(query, str):
            return {"error": "Invalid query", "message": "Query must be a non-empty string"}

        if len(query) > 500:
            return {"error": "Query too long", "message": "Maximum query length is 500 characters"}

        try:
            result = self._swift_repos.search_repos(query)
            return self._ensure_serializable(result)
        except Exception as e:
            return {"error": "Search failed", "message": str(e)}

    def fetch_github_file(self, url: str) -> GitHubFileResult:
        """
        Fetch source code from Apple or SwiftLang GitHub repositories.

        Wrapper around swift_repos.fetch_github_file() that ensures
        safe, serializable return values. Note: Returns dict already.

        Args:
            url: GitHub file URL from apple or swiftlang organizations

        Returns:
            Dictionary with file content or error information
        """
        if not url or not isinstance(url, str):
            return {"error": "Invalid URL", "message": "URL must be a non-empty string"}

        if not url.startswith("https://github.com/"):
            return {
                "error": "Invalid URL",
                "message": "URL must start with https://github.com/"
            }

        try:
            result = self._swift_repos.fetch_github_file(url)
            return self._ensure_serializable(result)
        except Exception as e:
            return {"error": "Fetch failed", "message": str(e)}

    def search_wwdc_notes(self, query: str) -> WWDCSearchResult:
        """
        Search WWDC session notes for topics not in regular documentation.

        Wrapper around wwdc_notes.search_sessions() that ensures
        safe, serializable return values.

        Args:
            query: Topic to search for (e.g., 'performance', 'swift concurrency')

        Returns:
            Dictionary with search URLs and categories or error information
        """
        if not query or not isinstance(query, str):
            return {"error": "Invalid query", "message": "Query must be a non-empty string"}

        if len(query) > 500:
            return {"error": "Query too long", "message": "Maximum query length is 500 characters"}

        try:
            result = self._wwdc_notes.search_sessions(query)
            return self._ensure_serializable(result)
        except Exception as e:
            return {"error": "Search failed", "message": str(e)}

    def get_wwdc_session(self, session_id: str) -> WWDCSessionResult:
        """
        Get WWDC session URLs from session ID.

        Wrapper around wwdc_notes.get_session_info() that ensures
        safe, serializable return values.

        Args:
            session_id: Format 'wwdc2023-10154' or 'wwdc2023/10154'

        Returns:
            Dictionary with session URLs or error information
        """
        if not session_id or not isinstance(session_id, str):
            return {"error": "Invalid session ID", "message": "Session ID must be a non-empty string"}

        try:
            result = self._wwdc_notes.get_session_info(session_id)
            return self._ensure_serializable(result)
        except Exception as e:
            return {"error": "Lookup failed", "message": str(e)}

    def search_hig(self, query: str, platform: Optional[str] = None) -> HIGSearchResult:
        """
        Search Apple's Human Interface Guidelines for design patterns.

        Wrapper around hig.search_guidelines() that ensures
        safe, serializable return values.

        Args:
            query: Design topic or keyword to search for
            platform: Optional platform filter (ios, macos, tvos, watchos, visionos)

        Returns:
            Dictionary with search URLs or error information
        """
        if not query or not isinstance(query, str):
            return {"error": "Invalid query", "message": "Query must be a non-empty string"}

        if len(query) > 500:
            return {"error": "Query too long", "message": "Maximum query length is 500 characters"}

        try:
            result = self._hig.search_guidelines(query, platform)
            return self._ensure_serializable(result)
        except Exception as e:
            return {"error": "Search failed", "message": str(e)}

    def list_hig_platforms(self) -> HIGPlatformsResult:
        """
        List all Apple platforms with their Human Interface Guidelines links.

        Wrapper around hig.list_platforms() that ensures
        safe, serializable return values.

        Returns:
            Dictionary with platform list or error information
        """
        try:
            result = self._hig.list_platforms()
            # Ensure consistent dict return format
            if isinstance(result, list):
                return {"platforms": self._ensure_serializable(result), "count": len(result)}
            return self._ensure_serializable(result)
        except Exception as e:
            return {"error": "List failed", "message": str(e)}

    def _ensure_serializable(self, data: Any) -> Any:
        """
        Ensure data is JSON-serializable.

        Recursively processes data to ensure it can be serialized to JSON.

        Args:
            data: Data to process

        Returns:
            JSON-serializable version of data
        """
        if data is None:
            return None
        if isinstance(data, (str, int, float, bool)):
            return data
        if isinstance(data, dict):
            return {str(k): self._ensure_serializable(v) for k, v in data.items()}
        if isinstance(data, (list, tuple)):
            return [self._ensure_serializable(item) for item in data]
        # Convert other types to string
        return str(data)

    def get_api_context(self) -> Dict[str, Any]:
        """
        Get the API context for sandbox injection.

        Returns a dictionary of API data that can be serialized and
        injected into the sandbox subprocess.

        Note: Functions cannot be serialized, so we provide the data
        and let the sandbox script call back to this process via
        the pre-loaded API functions.

        Returns:
            Dictionary of API configuration and metadata
        """
        return {
            "api_version": "1.0",
            "available_functions": [
                "fetch_documentation",
                "search_proposals",
                "get_proposal",
                "search_docs",
                "get_document",
                "list_documents",
                "get_xcode_versions",
                "search_apple_online",
                "get_framework_info",
                "search_swift_repos",
                "fetch_github_file",
                "search_wwdc_notes",
                "get_wwdc_session",
                "search_hig",
                "list_hig_platforms",
                "filter_results",
                "extract_fields"
            ],
            "documentation_base_url": "https://developer.apple.com/documentation/",
            "evolution_base_url": "https://www.swift.org/swift-evolution/"
        }


# Utility functions that can be injected into sandbox namespace
# These work on data that's already been fetched

def filter_results(data: List[Dict], key: str, value: Any) -> List[Dict]:
    """
    Filter a list of dictionaries by key-value match.

    Utility function for processing search results in the sandbox.

    Args:
        data: List of dictionaries to filter
        key: Key to check in each dictionary
        value: Value to match (uses 'in' for strings, == for others)

    Returns:
        Filtered list of dictionaries
    """
    if not isinstance(data, list):
        return []

    results = []
    for item in data:
        if not isinstance(item, dict):
            continue
        item_value = item.get(key)
        if item_value is None:
            continue
        # String contains check
        if isinstance(value, str) and isinstance(item_value, str):
            if value.lower() in item_value.lower():
                results.append(item)
        # Exact match for other types
        elif item_value == value:
            results.append(item)

    return results


def extract_fields(data: List[Dict], fields: List[str]) -> List[Dict]:
    """
    Extract specific fields from a list of dictionaries.

    Utility function for reducing data size in sandbox results.

    Args:
        data: List of dictionaries to process
        fields: List of field names to extract

    Returns:
        List of dictionaries with only specified fields
    """
    if not isinstance(data, list) or not isinstance(fields, list):
        return []

    return [
        {k: item.get(k) for k in fields if k in item}
        for item in data
        if isinstance(item, dict)
    ]


# Module-level instance
documentation_api = DocumentationAPI()
