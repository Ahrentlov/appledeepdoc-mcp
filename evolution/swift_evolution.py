"""
Swift Evolution Module
======================

Provides access to Swift Evolution proposals through swift.org's official JSON feed.
This module enables searching and retrieving information about Swift language
evolution proposals, including their status, implementation versions, and rationale.

Key Features:
- Live data from swift.org (no authentication required)
- Intelligent caching to minimize network requests
- Relevance-based search scoring
- Version-specific proposal filtering

Data Source:
https://download.swift.org/swift-evolution/v1/evolution.json
"""

import re
import urllib.request
import urllib.parse
import json
import time
from typing import Dict, Optional, List

class SwiftEvolution:
    """
    Search and analyze Swift Evolution proposals using swift.org data feed.

    This class provides methods to search proposals by feature name or Swift version,
    and retrieve detailed information about specific proposals. It implements a
    simple caching mechanism to reduce API calls and improve response times.

    Attributes:
        EVOLUTION_JSON_URL: Official swift.org JSON feed endpoint
        GITHUB_WEB_BASE: Base URL for viewing proposals on GitHub
        GITHUB_RAW_BASE: Base URL for raw proposal markdown content
    """

    EVOLUTION_JSON_URL = "https://download.swift.org/swift-evolution/v1/evolution.json"
    GITHUB_WEB_BASE = "https://github.com/swiftlang/swift-evolution"
    GITHUB_RAW_BASE = "https://raw.githubusercontent.com/swiftlang/swift-evolution/main/proposals"

    def __init__(self):
        """Initialize with empty cache and TTL settings."""
        self.cache = None          # Cached JSON data from swift.org
        self.cache_time = 0        # Timestamp of last cache update
        self.cache_ttl = 3600      # Cache Time-To-Live: 1 hour

    def _fetch_evolution_data(self) -> Optional[Dict]:
        """
        Fetch and cache the evolution.json data from swift.org.

        This method implements a simple TTL-based caching mechanism to avoid
        excessive network requests. The cache expires after 1 hour.

        Returns:
            Dict containing proposal data from swift.org, or None if fetch fails.
        """
        # Return cached data if still valid (within TTL window)
        if self.cache and (time.time() - self.cache_time) < self.cache_ttl:
            return self.cache

        try:
            # Create request with User-Agent header (required by some servers)
            req = urllib.request.Request(
                self.EVOLUTION_JSON_URL,
                headers={'User-Agent': 'AppleDeepDocs-MCP'}
            )

            # Fetch fresh data from swift.org
            with urllib.request.urlopen(req, timeout=15) as response:
                data = json.loads(response.read().decode('utf-8'))
                # Update cache with fresh data
                self.cache = data
                self.cache_time = time.time()
                return data

        except Exception as e:
            # Return None to indicate fetch failure
            # Caller should handle this gracefully
            return None

    def search_proposals(self, feature: str) -> Dict:
        """
        Search Swift Evolution proposals by feature name, version, or status.

        This method implements a relevance-based scoring system:
        - Exact version match: +100 points
        - Partial version match: +50 points
        - Status match: +15 points (e.g., 'rejected', 'withdrawn', 'returnedForRevision')
        - Feature in title: +10 points
        - Feature in summary: +5 points

        Args:
            feature: Feature name, Swift version, or proposal status to search for
                    Examples: 'async', 'Swift 6', 'actors', 'property wrapper',
                             'rejected', 'withdrawn', 'returnedForRevision'

        Returns:
            Dictionary containing:
            - feature: The search term used
            - total_found: Number of matching proposals
            - proposals: List of matching proposals sorted by relevance
            - available_versions: List of Swift versions with implemented proposals
        """
        data = self._fetch_evolution_data()

        if not data:
            return {
                'error': 'Failed to fetch Swift Evolution data',
                'feature': feature,
                'suggestion': 'Check your internet connection'
            }

        proposals = data.get('proposals', [])
        feature_lower = feature.lower()
        results = []

        # Extract version number if user is searching for a Swift version
        # Pattern matches: "swift 6", "Swift 6.0", "swift6.1", etc.
        version_match = re.search(r'swift\s*(\d+\.?\d*)', feature_lower)
        search_version = version_match.group(1) if version_match else None

        for proposal in proposals:
            score = 0
            status = proposal.get('status', {})
            impl_version = status.get('version', '')

            # Version-specific scoring
            if search_version:
                if impl_version == search_version:
                    score += 100  # Exact version match (e.g., "6.0" == "6.0")
                elif impl_version and impl_version.startswith(search_version):
                    score += 50   # Partial match (e.g., "6.0" matches "6")

            # Text-based scoring
            title = proposal.get('title', '').lower()
            summary = proposal.get('summary', '').lower()
            status_state = status.get('state', '').lower()

            if feature_lower in title:
                score += 10  # Title matches are more relevant
            if feature_lower in summary:
                score += 5   # Summary matches are less relevant
            if feature_lower in status_state:
                score += 15  # Status matches are highly relevant for finding proposals by state

            # Only include proposals with positive scores
            if score > 0:
                results.append({
                    'se_number': proposal.get('id', ''),
                    'title': proposal.get('title', ''),
                    'status': status.get('state', 'unknown'),
                    'version': impl_version or 'N/A',
                    # Truncate long summaries for readability
                    'summary': proposal.get('summary', '')[:200] + '...' if len(proposal.get('summary', '')) > 200 else proposal.get('summary', ''),
                    'github_url': f"{self.GITHUB_WEB_BASE}/blob/main/proposals/{proposal.get('link', '')}",
                    'relevance_score': score
                })

        # Sort by relevance score (highest first)
        results.sort(key=lambda x: x['relevance_score'], reverse=True)

        return {
            'feature': feature,
            'total_found': len(results),
            'proposals': results[:20],  # Top 20 results
            'available_versions': data.get('implementationVersions', [])
        }

    def get_proposal(self, se_number: str) -> Dict:
        """
        Get detailed information about a specific Swift Evolution proposal.

        This method handles various input formats for SE numbers:
        - Full format: 'SE-0413'
        - Short format: '0413' or '413'
        - Case insensitive: 'se-0413'

        Args:
            se_number: The Swift Evolution proposal number

        Returns:
            Dictionary containing:
            - se_number: Normalized proposal ID
            - title: Proposal title
            - status: Current state (e.g., 'implemented', 'accepted')
            - version: Swift version where implemented
            - summary: Full proposal summary
            - authors: List of proposal authors
            - github_url: Link to view on GitHub
            - raw_url: Direct link to markdown content
            - swift_org_url: Official swift.org link
        """
        data = self._fetch_evolution_data()

        if not data:
            return {
                'error': 'Failed to fetch Swift Evolution data',
                'se_number': se_number,
                'suggestion': 'Check your internet connection'
            }

        # Normalize SE number to standard format (SE-XXXX)
        se_num = se_number.upper()
        if not se_num.startswith('SE-'):
            # Pad with zeros to make 4 digits (e.g., '413' -> 'SE-0413')
            se_num = f'SE-{se_num.zfill(4)}'

        # Search for the proposal in the data
        proposals = data.get('proposals', [])
        proposal = next((p for p in proposals if p.get('id', '').upper() == se_num), None)

        if not proposal:
            return {
                'error': f'Proposal {se_num} not found',
                'se_number': se_num,
                'suggestion': f'Visit https://www.swift.org/swift-evolution/ to browse proposals'
            }

        status = proposal.get('status', {})
        authors = proposal.get('authors', [])

        return {
            'se_number': proposal.get('id', ''),
            'title': proposal.get('title', ''),
            'status': status.get('state', 'unknown'),
            'version': status.get('version', 'N/A'),
            'summary': proposal.get('summary', ''),
            'authors': [a.get('name', 'Unknown') for a in authors],
            'github_url': f"{self.GITHUB_WEB_BASE}/blob/main/proposals/{proposal.get('link', '')}",
            'raw_url': f"{self.GITHUB_RAW_BASE}/{proposal.get('link', '')}",
            'swift_org_url': f'https://www.swift.org/swift-evolution/#?id={proposal.get("id", "")}'
        }
    
# Module-level instance
evolution = SwiftEvolution()