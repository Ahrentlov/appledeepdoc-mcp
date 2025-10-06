"""
Local Xcode Documentation Module
=================================

Manages access to Xcode's hidden local documentation found in the
AdditionalDocumentation folder within Xcode.framework. This module provides:
- In-memory caching of all documentation for fast searching
- Relevance-based search results
- Multi-version Xcode support
- Efficient content indexing with topic extraction

The documentation includes:
- Liquid Glass design patterns (iOS 18+)
- Advanced SwiftUI implementation guides
- Internal framework documentation
- Performance optimization techniques
- Accessibility best practices

Architecture:
- All documents are loaded into memory at startup for speed
- Content is indexed with topics extracted from headers
- Composite keys track documents across multiple Xcode versions
"""

import re
from pathlib import Path
from typing import List, Dict, Optional
from config import Config, logger

class LocalDocsManager:
    """
    Manage local Xcode hidden documentation with in-memory caching.

    This class loads all documentation files from Xcode installations at startup
    and maintains them in memory for fast searching. It handles multiple Xcode
    versions and provides relevance-based search results.

    Attributes:
        content_cache: Full document content indexed by composite key
        docs_cache: Document metadata indexed by composite key
        doc_paths: List of paths to AdditionalDocumentation folders
    """

    def __init__(self):
        """Initialize manager and load all documentation into memory."""
        self.content_cache = {}  # Full content for fast searching
        self.docs_cache = {}     # Metadata about each document
        self.doc_paths = []      # Paths to documentation folders
        self.initialize()
    
    def initialize(self):
        """
        Initialize and cache all documentation on startup.

        This method loads all markdown files from Xcode's AdditionalDocumentation
        folders into memory. It extracts topics from headers and creates composite
        keys to track documents across multiple Xcode versions.
        """
        try:
            # Get paths to all installed Xcode documentation folders
            self.doc_paths = Config.get_documentation_paths()
        except ValueError as e:
            logger.error(str(e))
            self.doc_paths = []
            return

        # Index and cache all documentation files
        for doc_path in self.doc_paths:
            # Extract Xcode version from path (e.g., "Xcode-26.0.0.app")
            xcode_name = Config.get_xcode_name_from_path(doc_path)

            for md_file in doc_path.glob("*.md"):
                try:
                    # Load entire file content for searching
                    content = md_file.read_text(encoding='utf-8')

                    # Extract topic headers from first 500 chars for quick preview
                    # Pattern matches H1, H2, H3 headers (# ## ###)
                    headers = re.findall(r'^#{1,3}\s+(.+)$', content[:500], re.MULTILINE)

                    # Create composite key: "Xcode-26.0.0.app::SwiftUI-Liquid-Glass"
                    # This allows tracking same doc across different Xcode versions
                    key = f"{xcode_name}::{md_file.stem}"

                    # Store metadata for quick access
                    self.docs_cache[key] = {
                        "path": str(md_file),
                        "name": md_file.stem,
                        "size": md_file.stat().st_size,
                        "xcode_source": xcode_name,
                        "topics": headers[:5]  # First 5 topics as preview
                    }

                    # Store full content for searching
                    self.content_cache[key] = content
                except Exception as e:
                    logger.error(f"Error loading {md_file}: {e}")

        logger.info(f"Indexed {len(self.docs_cache)} documents from {len(self.doc_paths)} Xcode installation(s)")

        # Update global config cache for backward compatibility
        Config.DOCS_CACHE = self.docs_cache
    
    def search(self, query: str, case_sensitive: bool = False) -> Dict:
        """
        Search through cached documentation.
        
        Args:
            query: Search term to find in documentation
            case_sensitive: Whether to perform case-sensitive search
            
        Returns:
            Dictionary with matching documents and context
        """
        results = []
        # Compile regex pattern with appropriate flags
        # re.escape() prevents special chars from being interpreted as regex
        pattern = re.compile(re.escape(query), 0 if case_sensitive else re.IGNORECASE)

        for composite_key, doc_info in self.docs_cache.items():
            # Extract document name from composite key (after ::)
            doc_name = composite_key.split("::", 1)[1] if "::" in composite_key else composite_key
            matches = []

            # Priority 1: Search in filename (most relevant)
            if pattern.search(doc_name):
                matches.append({"type": "filename", "context": doc_name})

            # Priority 2: Search in document content
            content = self.content_cache.get(composite_key, "")
            if content:
                for match in pattern.finditer(content):
                    # Limit to 5 matches per document to avoid overwhelming results
                    if len(matches) >= 5:
                        break

                    # Extract context window around the match (±50 chars)
                    start = max(0, match.start() - 50)
                    end = min(len(content), match.end() + 50)
                    context = content[start:end].strip()

                    # Normalize whitespace for cleaner display
                    context = re.sub(r'\s+', ' ', context)

                    matches.append({
                        "type": "content",
                        "context": context,
                        "position": match.start()
                    })

            # Only include documents with at least one match
            if matches:
                results.append({
                    "document": doc_name,
                    "xcode_version": doc_info["xcode_source"],
                    "matches": matches,
                    "total_matches": len(matches)
                })

        # Sort by relevance:
        # 1. Documents with filename matches come first
        # 2. Then sort by total number of matches (descending)
        results.sort(key=lambda x: (
            not any(m["type"] == "filename" for m in x["matches"]),
            -x["total_matches"]
        ))
        
        return {
            "query": query,
            "total_results": len(results),
            "results": results[:20]  # Limit to 20 documents
        }
    
    def get_document(self, name: str, xcode_version: Optional[str] = None) -> str:
        """
        Retrieve full content of a documentation file.
        
        Args:
            name: Document name
            xcode_version: Optional specific Xcode version
            
        Returns:
            Full markdown content of the documentation file
        """
        # Find matching document
        for composite_key, doc_info in self.docs_cache.items():
            doc_name = composite_key.split("::", 1)[1] if "::" in composite_key else composite_key
            xcode_source = doc_info["xcode_source"]
            
            if doc_name == name or doc_info["name"] == name:
                if xcode_version and xcode_version != xcode_source:
                    continue
                
                content = self.content_cache.get(composite_key, "")
                if content:
                    return content
                
                # Fallback to reading from disk
                doc_path = Path(doc_info["path"])
                if doc_path.exists():
                    return doc_path.read_text(encoding='utf-8')
        
        return f"Document '{name}' not found" + (f" in {xcode_version}" if xcode_version else "")
    
    def list_documents(self, filter_str: Optional[str] = None) -> List[Dict]:
        """
        List all available documentation files.
        
        Args:
            filter_str: Optional filter string to match document names
            
        Returns:
            List of documents with metadata
        """
        documents = []
        seen_names = set()
        
        for composite_key, doc_info in self.docs_cache.items():
            doc_name = doc_info["name"]
            
            # Skip duplicates (same doc in multiple Xcode versions)
            if doc_name in seen_names:
                continue
            
            if filter_str and filter_str.lower() not in doc_name.lower():
                continue
            
            seen_names.add(doc_name)
            documents.append({
                "name": doc_name,
                "topics": doc_info["topics"],
                "size": doc_info["size"],
                "xcode_versions": self._get_versions_for_doc(doc_name)
            })
        
        # Sort by name
        documents.sort(key=lambda x: x["name"])
        return documents
    
    def _get_versions_for_doc(self, doc_name: str) -> List[str]:
        """Get all Xcode versions that contain a specific document."""
        versions = []
        for composite_key, doc_info in self.docs_cache.items():
            if doc_info["name"] == doc_name:
                versions.append(doc_info["xcode_source"])
        return sorted(set(versions))
    
    def get_xcode_versions(self) -> List[str]:
        """Get list of installed Xcode versions with documentation."""
        versions = set()
        for doc_info in self.docs_cache.values():
            versions.add(doc_info["xcode_source"])
        return sorted(versions)

# Module-level instance
local_docs = LocalDocsManager()