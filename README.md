# Gemini CLI - Free Alternative to Claude + MCP Support

**Purpose:**  
A command-line interface for Google's Gemini models that supports the Model Context Protocol (MCP), allowing it to use the same tools as Claude Desktop.

**Why this exists:**  
To provide a cost-effective, high-speed, and local-first alternative to Claude Desktop for interacting with the [DGX ecosystem](../sparkforge/README.md). It leverages Gemini's free tier to perform inventory checks and database queries without incurring per-token costs.

## 🎯 Two Modes

### 1. Basic Mode (Simple Chat)
```bash
uv run python main.py
```

### 2. MCP Mode (With Tool Servers) ⭐ NEW!
```bash
./gemini-mcp.sh
# or
uv run python main_mcp.py
```

## ✨ MCP Mode Features

**Connected MCP Servers:**
- `inventory` - Inventory management (list, search, update items) via [inventory-mcp](../inventory-mcp/README.md).
- `vanna-ai` - SQL queries via natural language.

**Available Tools:**
- List/search inventory items
- Check stock levels
- Query databases with natural language
- Generate SQL queries
- And more!

## Quick Start (MCP Mode)

```bash
# Install dependencies with uv
uv pip install google-generativeai python-dotenv rich prompt-toolkit mcp httpx

# Run MCP-enabled CLI
./gemini-mcp.sh
```

## Usage Examples

```
You: Show me 5 inventory items
Gemini: [calls inventory_list_inventory tool]

You: Search for Nike products
Gemini: [calls inventory_search_inventory tool]

You: What tables are in the database?
Gemini: [calls vanna-ai_get_training_data tool]
```

## Commands

- `exit` / `quit` - Exit the CLI
- `clear` - Clear conversation history
- `tools` - Show all available MCP tools
- `help` - Show help message

## Cost Savings

- Claude Sonnet: $3-15 per million tokens
- Gemini Flash: **FREE** ✨ (1500 req/day)

## Configuration

MCP servers are configured in `main_mcp.py`. To replicate the setup:
1.  Ensure `inventory-mcp` is set up and pointing to your DGX.
2.  Update the path in `main_mcp.py` to point to your `inventory-mcp/run.sh` script.

## Notes

- MCP mode requires both inventory-mcp and vanna-mcp servers running (or reachable).
- Uses Gemini 2.0 Flash with function calling.
- Automatic tool selection based on your queries.
