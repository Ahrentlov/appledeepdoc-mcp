"""
Tool Discovery Subsystem for Apple Deep Docs MCP
=================================================

This module provides a virtual filesystem that presents MCP tools as
navigable files, following the pattern from Anthropic's "Code Execution
with MCP" article. This enables lazy tool discovery - agents can explore
the tool structure on-demand rather than loading all definitions upfront.

Components:
- tool_filesystem.py: Virtual filesystem representation
- tool_definitions/: Interface definitions for each tool

The virtual filesystem structure:
/tools/
├── README.md                    # Overview of available tools
├── apple_documentation/
│   ├── README.md               # Module description
│   └── fetch_documentation.py  # Tool interface
└── swift_evolution/
    ├── README.md               # Module description
    ├── search_proposals.py     # Tool interface
    └── get_proposal.py         # Tool interface
"""

from .tool_filesystem import ToolFilesystem

__all__ = ['ToolFilesystem']
