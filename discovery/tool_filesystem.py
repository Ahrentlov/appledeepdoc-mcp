"""
Virtual Tool Filesystem
=======================

Provides a virtual filesystem interface for tool discovery, following
Anthropic's "Code Execution with MCP" pattern. LLMs can navigate this
filesystem to discover available tools on-demand, reducing token overhead.

The filesystem structure:
/tools/
├── README.md
├── apple_documentation/
│   ├── README.md
│   └── fetch_documentation.py
└── swift_evolution/
    ├── README.md
    ├── search_proposals.py
    └── get_proposal.py
"""

from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class FileEntry:
    """Represents a file or directory in the virtual filesystem."""
    name: str
    entry_type: str  # "file" or "directory"
    description: str
    size: Optional[int] = None


class ToolFilesystem:
    """
    Virtual filesystem that presents tools as navigable files.

    This enables lazy tool discovery - agents explore the structure
    on-demand rather than loading all definitions upfront.
    """

    # Root README content
    ROOT_README = """# Apple Deep Docs - Available Tools

This filesystem contains documentation APIs for use in the code execution sandbox.

## Available Modules

### apple_documentation/
Access Apple's official developer documentation. Fetch structured data including
method signatures, parameters, and detailed descriptions.

### swift_evolution/
Search and explore 500+ Swift Evolution proposals. Understand the "why" behind
Swift language features and their implementation history.

## Usage

1. Navigate to a module directory to see available functions
2. Read function files (.py) to see interface definitions
3. Use functions in execute_documentation_code() calls

## Example

```python
# After discovering fetch_documentation via the filesystem:
doc = fetch_documentation("https://developer.apple.com/documentation/swiftui/view")
result = {"title": doc["title"], "declaration": doc["declaration"]}
```
"""

    # Module README templates
    APPLE_DOCS_README = """# Apple Documentation Module

Provides access to Apple's official developer documentation through their JSON API.

## Available Functions

### fetch_documentation.py
Fetch structured documentation from any developer.apple.com URL.
Returns: title, abstract, declaration, discussion, parameters, returns

## Usage

```python
doc = fetch_documentation("https://developer.apple.com/documentation/swiftui/view")
```
"""

    SWIFT_EVOLUTION_README = """# Swift Evolution Module

Search and explore Swift Evolution proposals from swift.org.

## Available Functions

### search_proposals.py
Search proposals by feature name, Swift version, or status.
Returns: matching proposals with SE numbers, titles, status, summaries

### get_proposal.py
Get detailed information about a specific proposal.
Returns: full proposal details including authors and links

## Usage

```python
# Search for async-related proposals
results = search_proposals("async")

# Get specific proposal
proposal = get_proposal("SE-0413")
```
"""

    # Inline function documentation (replaces external tool_definitions files)
    FETCH_DOC_CONTENT = """# fetch_documentation(url: str) -> Dict

Fetch structured documentation from Apple Developer website.

## Parameters
- url: Full Apple documentation URL (must start with https://developer.apple.com/documentation/)

## Returns
Dict with: title, abstract, declaration, discussion, parameters, returns, url, json_url

## Example
```python
doc = fetch_documentation("https://developer.apple.com/documentation/swiftui/view")
result = {"title": doc["title"], "signature": doc["declaration"]}
```
"""

    SEARCH_PROPOSALS_CONTENT = """# search_proposals(feature: str) -> Dict

Search 500+ Swift Evolution proposals.

## Parameters
- feature: Feature name, Swift version, or concept (e.g., 'async', 'Swift 6')

## Returns
Dict with: feature, total_found, proposals (list), available_versions

## Example
```python
results = search_proposals("async")
implemented = [p for p in results["proposals"] if p["status"] == "implemented"]
```
"""

    GET_PROPOSAL_CONTENT = """# get_proposal(se_number: str) -> Dict

Get details of a specific Swift Evolution proposal.

## Parameters
- se_number: Proposal number (e.g., 'SE-0413' or '413')

## Returns
Dict with: se_number, title, status, version, summary, authors, github_url

## Example
```python
proposal = get_proposal("SE-0413")
print(f"{proposal['title']} - {proposal['status']}")
```
"""

    def __init__(self):
        """Initialize the virtual filesystem structure."""
        # Virtual directory structure (all content inline, no external files)
        self._structure = {
            "/tools": {
                "type": "directory",
                "entries": ["README.md", "apple_documentation", "swift_evolution"]
            },
            "/tools/README.md": {
                "type": "file",
                "content": self.ROOT_README
            },
            "/tools/apple_documentation": {
                "type": "directory",
                "entries": ["README.md", "fetch_documentation.py"]
            },
            "/tools/apple_documentation/README.md": {
                "type": "file",
                "content": self.APPLE_DOCS_README
            },
            "/tools/apple_documentation/fetch_documentation.py": {
                "type": "file",
                "content": self.FETCH_DOC_CONTENT
            },
            "/tools/swift_evolution": {
                "type": "directory",
                "entries": ["README.md", "search_proposals.py", "get_proposal.py"]
            },
            "/tools/swift_evolution/README.md": {
                "type": "file",
                "content": self.SWIFT_EVOLUTION_README
            },
            "/tools/swift_evolution/search_proposals.py": {
                "type": "file",
                "content": self.SEARCH_PROPOSALS_CONTENT
            },
            "/tools/swift_evolution/get_proposal.py": {
                "type": "file",
                "content": self.GET_PROPOSAL_CONTENT
            }
        }

        # File descriptions for directory listings
        self._descriptions = {
            "README.md": "Module documentation and usage examples",
            "apple_documentation": "Apple Developer documentation access",
            "swift_evolution": "Swift Evolution proposals search",
            "fetch_documentation.py": "Fetch structured docs from developer.apple.com",
            "search_proposals.py": "Search 500+ Swift Evolution proposals",
            "get_proposal.py": "Get details of a specific SE proposal"
        }

    def list_directory(self, path: str = "/tools") -> Dict:
        """
        List contents of a virtual directory.

        Args:
            path: Directory path to list (e.g., "/tools", "/tools/apple_documentation")

        Returns:
            Dictionary containing:
            - path: Current directory path
            - entries: List of entries with name, type, and description
        """
        # Normalize path
        path = self._normalize_path(path)

        if path not in self._structure:
            return {
                "error": "Directory not found",
                "path": path,
                "suggestion": "Start with /tools to see available modules"
            }

        entry = self._structure[path]
        if entry["type"] != "directory":
            return {
                "error": "Not a directory",
                "path": path,
                "suggestion": "Use read_file to read file contents"
            }

        entries = []
        for name in entry["entries"]:
            entry_path = f"{path}/{name}".replace("//", "/")
            entry_info = self._structure.get(entry_path, {})
            entry_type = "directory" if entry_info.get("type") == "directory" else "file"

            entries.append({
                "name": name,
                "type": entry_type,
                "description": self._descriptions.get(name, "")
            })

        return {
            "path": path,
            "entries": entries
        }

    def read_file(self, path: str) -> Dict:
        """
        Read contents of a virtual file.

        Args:
            path: File path to read

        Returns:
            Dictionary containing:
            - path: File path
            - content: File contents
            - name: File name
            - (for .py files) input_schema, output_schema
        """
        # Normalize path
        path = self._normalize_path(path)

        if path not in self._structure:
            return {
                "error": "File not found",
                "path": path,
                "suggestion": "Use list_directory to see available files"
            }

        entry = self._structure[path]
        if entry["type"] != "file":
            return {
                "error": "Not a file",
                "path": path,
                "suggestion": "Use list_directory to list directory contents"
            }

        # Get file content (all content is now inline)
        content = entry.get("content", "# No content available")

        result = {
            "path": path,
            "name": path.split("/")[-1],
            "content": content
        }

        # Add schema info for Python files
        if path.endswith(".py"):
            result["language"] = "python"
            # Extract type hints from content
            schemas = self._extract_schemas(content)
            if schemas:
                result.update(schemas)

        return result

    def _normalize_path(self, path: str) -> str:
        """Normalize a filesystem path."""
        # Ensure leading slash
        if not path.startswith("/"):
            path = "/" + path

        # Remove trailing slash (except for root)
        if path != "/" and path.endswith("/"):
            path = path[:-1]

        # Handle /tools as default
        if path == "/":
            path = "/tools"

        return path

    def _extract_schemas(self, content: str) -> Dict:
        """
        Extract input/output schemas from TypedDict definitions.

        Args:
            content: Python file content

        Returns:
            Dictionary with input_schema and output_schema if found
        """
        schemas = {}

        # Simple extraction of parameter info from docstring
        if "Parameters:" in content:
            params_start = content.find("Parameters:")
            params_end = content.find("Returns:", params_start)
            if params_end > params_start:
                schemas["parameters_doc"] = content[params_start:params_end].strip()

        if "Returns:" in content:
            returns_start = content.find("Returns:")
            # Find next major section
            returns_end = content.find("Example", returns_start)
            if returns_end == -1:
                returns_end = content.find("---", returns_start)
            if returns_end > returns_start:
                schemas["returns_doc"] = content[returns_start:returns_end].strip()

        return schemas


# Module-level instance
tool_filesystem = ToolFilesystem()
