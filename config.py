"""
Configuration module for Xcode Documentation MCP Server.
"""

import logging
import os
from pathlib import Path
from typing import List, Dict

# Get logger instance (uses default or parent configuration)
logger = logging.getLogger(__name__)


class Config:
    """Configuration and state management for the documentation server."""

    # Global documentation cache
    DOCS_CACHE: Dict = {}
    DOC_PATHS: List[Path] = []

    # Server configuration
    SERVER_NAME = "xcode-doc-server"

    # Tool exposure mode configuration
    # When CODE_EXECUTION_MODE is True:
    #   - Only code execution tools are exposed (execute_documentation_code, etc.)
    #   - Legacy individual tools are hidden
    # When CODE_EXECUTION_MODE is False (default):
    #   - Only legacy tools are exposed (search_docs, fetch_apple_documentation, etc.)
    #   - Code execution tools are hidden
    # This is configured via environment variable for MCP client setup
    CODE_EXECUTION_MODE: bool = os.environ.get("CODE_EXECUTION_MODE", "").lower() in ("true", "1", "yes")

    # Computed inverse for convenience
    @classmethod
    def legacy_tools_enabled(cls) -> bool:
        """Returns True if legacy (individual) tools should be exposed."""
        return not cls.CODE_EXECUTION_MODE

    @classmethod
    def execution_tools_enabled(cls) -> bool:
        """Returns True if code execution tools should be exposed."""
        return cls.CODE_EXECUTION_MODE

    # Sandbox configuration for code execution
    SANDBOX_ENABLED = True
    SANDBOX_TIMEOUT_SECONDS = 5
    SANDBOX_MAX_MEMORY_MB = 50
    SANDBOX_MAX_OUTPUT_BYTES = 10 * 1024  # 10KB
    SANDBOX_MAX_CODE_LENGTH = 10000
    
    # Documentation search patterns
    XCODE_PATTERNS = ["Xcode*.app", "Xcode.app"]
    APPLICATIONS_DIR = Path("/Applications")
    DOC_SUBPATH = "Contents/PlugIns/IDEIntelligenceChat.framework/Versions/A/Resources/AdditionalDocumentation"
    
    # Search configuration
    MAX_MATCHES_PER_FILE = 5
    CONTEXT_CHARS_BEFORE = 100
    CONTEXT_CHARS_AFTER = 100
    TOPIC_PREVIEW_CHARS = 1000
    MAX_TOPICS = 5
    
    @classmethod
    def find_xcode_documentation_paths(cls) -> List[Path]:
        """Find all Xcode installations with additional documentation."""
        doc_paths = []
        
        for pattern in cls.XCODE_PATTERNS:
            for xcode_app in cls.APPLICATIONS_DIR.glob(pattern):
                # Build the documentation path
                doc_path = xcode_app / cls.DOC_SUBPATH
                
                if doc_path.exists() and doc_path.is_dir():
                    # Check if it actually contains markdown files
                    md_files = list(doc_path.glob("*.md"))
                    if md_files:
                        doc_paths.append(doc_path)
                        logger.info(f"Found documentation in: {xcode_app.name}")
        
        return doc_paths
    
    @classmethod
    def get_documentation_paths(cls) -> List[Path]:
        """Get documentation paths, checking environment variable first."""
        # Allow override via environment variable for specific path
        custom_path = os.environ.get("XCODE_DOC_PATH")
        
        if custom_path:
            # Use custom path if provided
            custom_path = Path(custom_path)
            if not custom_path.exists():
                raise ValueError(f"Custom documentation path does not exist: {custom_path}")
            return [custom_path]
        else:
            # Auto-discover Xcode installations
            doc_paths = cls.find_xcode_documentation_paths()
            
            if not doc_paths:
                raise ValueError(
                    "No Xcode installations with additional documentation found. "
                    "Searched in /Applications for Xcode*.app. "
                    "You can set XCODE_DOC_PATH environment variable to specify a custom path."
                )
            
            return doc_paths
    
    @classmethod
    def get_xcode_name_from_path(cls, path: Path) -> str:
        """Extract Xcode app name from documentation path."""
        # Navigate up from documentation path to find the .app directory
        for parent in path.parents:
            if parent.suffix == '.app':
                return parent.name
        # Fallback if not found
        return path.parts[2] if len(path.parts) > 2 else "Xcode"