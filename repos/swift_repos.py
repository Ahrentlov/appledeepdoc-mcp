"""
Swift Repositories Module
=========================

Provides dynamic searching and fetching capabilities for Apple's open-source
Swift ecosystem on GitHub. This module enables:
1. Web-based searching across all Apple/SwiftLang repositories
2. Direct source code fetching from GitHub files
3. Intelligent caching to reduce network requests

Key Design Decisions:
- Uses GitHub web search instead of API (no rate limits, no auth needed)
- Dynamically discovers repositories (no hardcoded lists)
- Supports both apple/ and swiftlang/ GitHub organizations
- Implements LRU-style caching for fetched files
"""

import urllib.request
import urllib.parse
import json
import re
from typing import Dict, Optional

class SwiftRepos:
    """
    Search and fetch from Apple's Swift open source repositories.

    This class provides methods to search across all Apple and SwiftLang
    repositories using GitHub's web search, and fetch actual source code
    from specific files. It avoids API rate limits by using web URLs.

    Attributes:
        cache: Dictionary storing fetched file contents (LRU-style)
        cache_ttl: Time-to-live for cached content (unused currently)
    """

    def __init__(self):
        """Initialize with empty cache for fetched files."""
        self.cache = {}              # Cache for fetched file contents
        self.cache_ttl = 3600        # TTL placeholder for future implementation

    def search_repos(self, query: str) -> Dict:
        """
        Search across all Apple and SwiftLang Swift repositories.

        Args:
            query: Your question or search term (e.g., "Can I use SPM for applications?")

        Returns:
            Dictionary with multiple search strategies
        """
        # URL-encode the query to handle special characters safely
        encoded_query = urllib.parse.quote(query)

        # Return multiple search URLs with different scopes
        # This approach lets GitHub's intelligent search do the heavy lifting
        # while avoiding API rate limits entirely
        return {
            'query': query,
            'search_urls': {
                # Primary search - combines both orgs, searches all code
                'github_search': f"https://github.com/search?q={encoded_query}+org:apple+org:swiftlang&type=code",

                # Language-specific - filters to Swift files only
                'swift_code': f"https://github.com/search?q={encoded_query}+language:Swift+org:apple+org:swiftlang&type=code",

                # Repository search - finds relevant projects by name/description
                'repositories': f"https://github.com/search?q={encoded_query}+org:apple+org:swiftlang&type=repositories",

                # Issues/discussions - valuable for finding design decisions
                'issues': f"https://github.com/search?q={encoded_query}+org:apple+org:swiftlang&type=issues",

                # Organization-specific searches for targeted exploration
                'apple_org': f"https://github.com/search?q={encoded_query}+org:apple&type=code",
                'swiftlang_org': f"https://github.com/search?q={encoded_query}+org:swiftlang&type=code",
            },
            'note': 'GitHub\'s search algorithm will automatically find relevant code, types, and discussions.',
            'tip': 'Start with "github_search" - it searches across code, comments, and documentation. Use "repositories" to find relevant projects.'
        }

    def fetch_github_file(self, url: str) -> Dict:
        """
        Fetch source code from a GitHub file (apple or swiftlang organizations only).

        Fetches actual implementation code from Swift repositories to understand
        how features are implemented in the compiler, standard library, or frameworks.

        Args:
            url: GitHub file URL (e.g., https://github.com/apple/swift/blob/main/stdlib/public/Concurrency/Task.swift)

        Returns:
            Dictionary containing:
            - content: The file content
            - url: Original URL provided
            - raw_url: The raw content URL used
            - language: Detected file language
            - repo: Repository name
            - path: File path within repo
            - size: Content size in bytes
            - lines: Number of lines

            Or error dictionary if fetch fails
        """
        # Security: Only allow fetching from Apple's official organizations
        # This prevents potential abuse by fetching from arbitrary repositories
        if not ('github.com/apple/' in url or 'github.com/swiftlang/' in url or
                'raw.githubusercontent.com/apple/' in url or 'raw.githubusercontent.com/swiftlang/' in url):
            return {
                "error": "Invalid URL",
                "message": "URL must be from github.com/apple/ or github.com/swiftlang/ organizations",
                "suggestion": "Example: https://github.com/apple/swift/blob/main/stdlib/public/Concurrency/Task.swift"
            }

        try:
            # Parse the URL to extract organization, repository, branch, and file path
            repo_info = self._parse_github_url(url)
            if not repo_info:
                return {
                    "error": "Invalid GitHub URL format",
                    "message": "Could not parse repository and file information from URL",
                    "url": url,
                    "suggestion": "URL should be in format: github.com/{org}/{repo}/blob/{branch}/{path}"
                }

            # Convert GitHub web URL to raw content URL for direct file access
            # Example: github.com/apple/swift/blob/main/file.swift -> raw.githubusercontent.com/apple/swift/main/file.swift
            raw_url = self._convert_to_raw_url(url)
            if not raw_url:
                return {
                    "error": "Invalid GitHub URL format",
                    "message": "Could not convert URL to raw content URL",
                    "url": url
                }

            # Check if we've already fetched this file recently
            if raw_url in self.cache:
                return self.cache[raw_url]

            # Prepare HTTP request with appropriate headers
            # User-Agent is required by GitHub to prevent abuse
            req = urllib.request.Request(
                raw_url,
                headers={
                    'User-Agent': 'AppleDeepDocs-MCP/1.0',
                    'Accept': 'text/plain, */*'
                }
            )

            with urllib.request.urlopen(req, timeout=15) as response:
                if response.status != 200:
                    return {
                        "error": f"HTTP {response.status}",
                        "message": "Failed to fetch file from GitHub",
                        "url": url
                    }

                content = response.read().decode('utf-8')

                # Build comprehensive result dictionary
                result = {
                    "content": content,
                    "url": url,
                    "raw_url": raw_url,
                    "language": self._detect_language(repo_info['path']),
                    "repo": f"{repo_info['org']}/{repo_info['repo']}",
                    "path": repo_info['path'],
                    "size": len(content),
                    "lines": content.count('\n') + 1
                }

                # Store in cache for faster repeated access
                self.cache[raw_url] = result

                # Implement simple LRU-style cache management
                # Keep only the most recent 25 files when cache exceeds 50
                if len(self.cache) > 50:
                    self.cache = dict(list(self.cache.items())[-25:])

                return result

        except urllib.error.HTTPError as e:
            return {
                "error": f"HTTP {e.code}",
                "message": str(e.reason),
                "url": url,
                "suggestion": "Check if the URL is correct and the file exists. Note: Only public files can be fetched."
            }
        except urllib.error.URLError as e:
            return {
                "error": "Network error",
                "message": str(e.reason),
                "url": url
            }
        except Exception as e:
            return {
                "error": "Fetch failed",
                "message": str(e),
                "url": url
            }

    def _parse_github_url(self, url: str) -> Optional[Dict]:
        """
        Parse GitHub URL to extract organization, repo, branch, and path.

        Returns dict with: org, repo, branch, path
        """
        # Pattern: github.com/{org}/{repo}/blob/{branch}/{path}
        pattern = r'github\.com/(apple|swiftlang)/([^/]+)/blob/([^/]+)/(.+)'
        match = re.search(pattern, url)

        if match:
            org, repo, branch, path = match.groups()
            return {
                'org': org,
                'repo': repo,
                'branch': branch,
                'path': path
            }

        # Also handle raw URLs
        # Pattern: raw.githubusercontent.com/{org}/{repo}/{branch}/{path}
        pattern_raw = r'raw\.githubusercontent\.com/(apple|swiftlang)/([^/]+)/([^/]+)/(.+)'
        match = re.search(pattern_raw, url)

        if match:
            org, repo, branch, path = match.groups()
            return {
                'org': org,
                'repo': repo,
                'branch': branch,
                'path': path
            }

        return None

    def _convert_to_raw_url(self, url: str) -> Optional[str]:
        """
        Convert a GitHub URL to raw content URL.

        Examples:
        - https://github.com/apple/swift/blob/main/README.md
          -> https://raw.githubusercontent.com/apple/swift/main/README.md
        - https://raw.githubusercontent.com/apple/swift/main/README.md
          -> unchanged (already raw)
        """
        # Already a raw URL
        if 'raw.githubusercontent.com' in url:
            return url

        # Convert github.com URL to raw URL
        info = self._parse_github_url(url)
        if info:
            return f"https://raw.githubusercontent.com/{info['org']}/{info['repo']}/{info['branch']}/{info['path']}"

        return None

    def _detect_language(self, path: str) -> str:
        """Detect programming language from file extension."""
        if path.endswith('.swift'):
            return 'swift'
        elif path.endswith('.md'):
            return 'markdown'
        elif path.endswith('.py'):
            return 'python'
        elif path.endswith('.cpp') or path.endswith('.cc') or path.endswith('.cxx'):
            return 'cpp'
        elif path.endswith('.c'):
            return 'c'
        elif path.endswith('.h') or path.endswith('.hpp'):
            return 'header'
        elif path.endswith('.json'):
            return 'json'
        elif path.endswith('.yaml') or path.endswith('.yml'):
            return 'yaml'
        elif path.endswith('.sh'):
            return 'shell'
        elif path.endswith('.txt'):
            return 'text'
        else:
            return 'unknown'

# Module-level instance
swift_repos = SwiftRepos()
