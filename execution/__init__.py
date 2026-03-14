"""
Code Execution Subsystem for Apple Deep Docs MCP
=================================================

This module provides a sandboxed Python execution environment that allows
LLMs to write code that processes documentation data, following the pattern
described in Anthropic's "Code Execution with MCP" article.

Components:
- security.py: AST-based code validation and security policies
- sandbox.py: Subprocess-based Python executor with resource limits
- api_bridge.py: Safe wrappers around documentation APIs

The execution environment provides:
- Isolated subprocess execution (not in-process)
- Resource limits (CPU time, memory)
- Restricted builtins (no file I/O, no imports)
- Pre-loaded documentation APIs
"""

from .security import CodeValidator
from .sandbox import SandboxExecutor
from .api_bridge import DocumentationAPI

__all__ = ['CodeValidator', 'SandboxExecutor', 'DocumentationAPI']
