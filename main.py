#!/usr/bin/env python3
"""
Main entry point for Xcode Documentation MCP Server.
"""

import sys
from config import logger
from tools import mcp


def main():
    """Main entry point."""
    try:
        # Modules initialize themselves on import
        logger.info("Initializing Apple Documentation MCP Server...")
        logger.info("Loading modules:")
        logger.info("  ✓ Local documentation search (docs/local_docs.py)")
        logger.info("  ✓ Apple API fetching (docs/apple_docs.py)")
        logger.info("  ✓ Swift Evolution proposals (evolution/swift_evolution.py)")
        logger.info("  ✓ Swift repositories search (repos/swift_repos.py)")
        logger.info("  ✓ WWDC session notes (wwdc/wwdc_notes.py)")
        logger.info("  ✓ Human Interface Guidelines (design/human_interface_guidelines.py)")

        # Run the MCP server via stdio
        logger.info("Starting MCP server via stdio...")
        mcp.run()
        
    except ValueError as e:
        logger.error(f"Failed to initialize: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()