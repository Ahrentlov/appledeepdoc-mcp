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

## Contributing

This project is provided as-is in its current state. While I've done my best to make it useful for accessing Apple's deeper documentation layers, there may be rough edges or areas for improvement.

Suggestions and pull requests are more than welcome! If you have ideas for new features, find bugs, or want to contribute improvements, please feel free to open an issue or submit a PR.

## License

MIT
