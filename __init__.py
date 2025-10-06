"""
Apple Deep Docs MCP Server

An MCP server that searches and serves Apple documentation including:
- Hidden Xcode documentation
- Apple Developer API documentation
- Swift Evolution proposals
"""

__version__ = "1.0.0"
__author__ = "Patrick"

# Import Config for external use
from .config import Config

# Import main MCP instance
from .tools import mcp

__all__ = ['Config', 'mcp', '__version__', '__author__']