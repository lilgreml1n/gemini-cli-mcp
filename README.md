# Gemini CLI - Free Alternative to Claude + MCP Support

Save your Claude tokens! Use Gemini's free tier for general queries WITH MCP tool access.

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
- `inventory` - Inventory management (list, search, update items)
- `vanna-ai` - SQL queries via natural language

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

MCP servers are configured in `main_mcp.py`:
- inventory: `/Users/raven/Documents/CURRENT_PROJECTS/inventory-mcp/launch-inventory-mcp.sh`
- vanna-ai: uv run in vanna-mcp-server directory

## Notes

- MCP mode requires both inventory-mcp and vanna-mcp servers running on DGX
- Uses Gemini 2.0 Flash with function calling
- Automatic tool selection based on your queries
- Keep Claude Desktop for complex workflows; use this for quick queries!
