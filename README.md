> Available as an [Agent Skill](https://github.com/Ahrentlov/apple-docs-skill) — no MCP server setup required.

# Apple Deep Docs MCP

Access hidden Xcode documentation and Apple developer resources through the Model Context Protocol.

## Overview

Modern Apple documentation uses the DocC rendering system which requires JavaScript to dynamically load content, making it inaccessible to some LLMs. This MCP server circumvents that limitation by providing comprehensive access to Apple's development documentation ecosystem, including:

- **Hidden Xcode Documentation**: Searches the `AdditionalDocumentation` folder inside Xcode.app containing advanced SwiftUI patterns, Liquid Glass design guides for iOS 26+, and framework-specific implementation details not available on Apple's public developer site
- **Apple Developer API**: Fetches and parses structured documentation from developer.apple.com
- **Swift Evolution Proposals**: Searches 500+ proposals to understand the "why" behind language features
- **Swift Open Source Repositories**: Searches across all Apple/SwiftLang GitHub repositories for implementation examples
- **WWDC Session Notes**: Accesses community-curated WWDC session summaries for performance optimization and architecture patterns
- **Human Interface Guidelines**: Searches through the Human Interface Guidelines



## Requirements

- Python 3.10+
- Xcode installed (for local documentation features)

## Installation

1. Clone this repository:
```bash
git clone https://github.com/Ahrentlov/appledeepdoc-mcp.git
cd appledeepdoc-mcp
```

2. Set up the Python environment:
```bash
# Create virtual environment
python3 -m venv venv

# Install dependencies
./venv/bin/pip install fastmcp
```

## Configuration

### Claude Code
For Claude Code, you need to add the MCP server using the following CLI commands:

**Make sure run.sh is executable**
```bash
chmod +x /path/to/appledeepdoc-mcp/run.sh
```

**Add the MCP server to the local Claude Code project config**

Navigate to the project folder where you will be activating Claude Code, then run the following command to register the MCP server:
```bash
claude mcp add --transport stdio apple-deep-docs /path/to/appledeepdoc-mcp/run.sh
```

**Verify it was added**
```bash
claude mcp list
```

Now when you activate `claude` in this folder, it will have the MCP server available.

### Claude Desktop
Add to your Claude Desktop config file:

```json
{
  "mcpServers": {
    "apple-deep-docs": {
      "command": "/path/to/appledeepdoc-mcp/run.sh"
    }
  }
}
```

### GPT-Codex
Add to `~/.codex/config.toml`:

```toml
[mcp_servers.apple-deep-docs]
"command" = "/path/to/appledeepdoc-mcp/run.sh"
```

Replace `/path/to/appledeepdoc-mcp` with the full path where you cloned this repository. The `run.sh` script automatically handles the virtual environment.

**Config file locations:**
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

After updating the config, restart Claude Desktop to load the MCP server.

## Project Structure

```
├── main.py               # Entry point for the MCP server
├── config.py            # Configuration and Xcode path discovery
├── tools.py             # MCP tool definitions and input validation
├── docs/                # Documentation access modules
│   ├── local_docs.py    # Xcode's hidden local documentation
│   └── apple_docs.py    # Apple Developer website API access
├── evolution/           # Swift language evolution
│   └── swift_evolution.py
├── repos/               # GitHub repository searching
│   └── swift_repos.py
├── suggestions/         # Intelligent suggestion system
│   └── suggestions.py   # Centralized suggestion engine
├── wwdc/                # WWDC session resources
│   └── wwdc_notes.py
└── pyproject.toml       # Package configuration
```

## Available Tools

### Local Documentation
- `search_docs` - Search Xcode's hidden documentation
- `get_document` - Retrieve full content of a specific document
- `list_documents` - List all available documentation files
- `get_xcode_versions` - Get installed Xcode versions with documentation

### Apple Developer Resources
- `fetch_apple_documentation` - Fetch structured docs from developer.apple.com
- `search_apple_online` - Search both local and online Apple documentation
- `get_framework_info` - Get direct documentation URL for any framework

### Swift Evolution
- `search_swift_evolution` - Search Swift Evolution proposals
- `get_swift_evolution_proposal` - Get details of a specific proposal

### GitHub Resources
- `search_swift_repos` - Search across all Apple/SwiftLang repositories
- `fetch_github_file` - Fetch source code from GitHub repositories

### WWDC Resources
- `search_wwdc_notes` - Search WWDC session notes and transcripts
- `get_wwdc_session` - Get WWDC session URLs from session ID

### Human Interface Guidelines
- `search_human_interface_guidelines` - Search Apple's HIG for design patterns and best practices
- `list_human_interface_guidelines_platforms` - List all available platforms with HIG links

## Environment Variables

- `XCODE_DOC_PATH`: Override default Xcode documentation search path
- `CODE_EXECUTION_MODE`: Set to `true` to enable experimental code execution mode (see below)

## Experimental: Code Execution Mode

> Based on the approach described in [Code Execution with MCP: Building More Efficient Agents](https://www.anthropic.com/engineering/code-execution-with-mcp) from Anthropic Engineering.

This server also supports an alternative approach that replaces the 15+ individual MCP tools with a **sandboxed Python execution environment**. Instead of receiving large JSON responses and processing them externally, LLMs write Python code that fetches and filters data directly—significantly reducing token usage.

### Why Code Execution?

The standard mode exposes 15+ tools, each returning full JSON responses. For example, searching Swift Evolution proposals returns the entire matching dataset. With code execution mode:

1. **Fewer tools** - Only 3 tools instead of 15+, reducing tool listing overhead
2. **Filtered results** - LLMs write code to extract exactly what they need
3. **Composable queries** - Combine multiple API calls and filter in a single execution

### Available Tools in Code Execution Mode

| Tool | Purpose |
|------|---------|
| `list_tool_directory` | Browse the virtual filesystem to discover available APIs |
| `read_tool_definition` | Read function signatures and usage examples |
| `execute_documentation_code` | Run Python code in a sandboxed environment |

### Security Model

The sandbox provides defense-in-depth:
- **AST validation** - Blocks imports, `exec`, `eval`, and dangerous builtins
- **Subprocess isolation** - Code runs in a separate process
- **Resource limits** - 5 second timeout, 50MB memory limit
- **Restricted namespace** - Only safe builtins and documentation APIs available

### Enabling Code Execution Mode

Add the `CODE_EXECUTION_MODE` environment variable to your MCP configuration:

**Claude Code:**
```bash
claude mcp add apple-deep-docs-exec /path/to/appledeepdoc-mcp/run.sh --env CODE_EXECUTION_MODE=true
```

**Claude Desktop:**
```json
{
  "mcpServers": {
    "apple-deep-docs-exec": {
      "command": "/path/to/appledeepdoc-mcp/run.sh",
      "env": {
        "CODE_EXECUTION_MODE": "true"
      }
    }
  }
}
```

### Example: Filtering Swift Evolution Proposals

Instead of calling `search_swift_evolution` and receiving a large JSON response, the LLM executes:

```python
# Executed in sandbox via execute_documentation_code
proposals = search_proposals('async')
swift6 = [p for p in proposals.get('proposals', [])
          if p.get('version', '').startswith('6')]
result = {'swift6_async': swift6[:5], 'count': len(swift6)}
```

The LLM receives only the filtered 5 proposals, not the entire matching dataset.

### Available APIs in Sandbox

All documentation sources are available as functions:

| API | Functions |
|-----|-----------|
| **Apple Developer Docs** | `fetch_documentation(url)`, `search_apple_online(query)`, `get_framework_info(name)` |
| **Swift Evolution** | `search_proposals(feature)`, `get_proposal(se_number)` |
| **Local Xcode Docs** | `search_docs(query)`, `get_document(name)`, `list_documents()`, `get_xcode_versions()` |
| **GitHub Repos** | `search_swift_repos(query)`, `fetch_github_file(url)` |
| **WWDC Sessions** | `search_wwdc_notes(query)`, `get_wwdc_session(session_id)` |
| **Human Interface Guidelines** | `search_hig(query)`, `list_hig_platforms()` |

## Contributing

This project is provided as-is in its current state. While I've done my best to make it useful for accessing Apple's deeper documentation layers, there may be rough edges or areas for improvement.

Suggestions and pull requests are more than welcome! If you have ideas for new features, find bugs, or want to contribute improvements, please feel free to open an issue or submit a PR.

## License

MIT
