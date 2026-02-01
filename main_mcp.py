#!/usr/bin/env python3
"""
Gemini MCP Bridge - DGX Version
Uses local Docker containers for MCP servers
"""

import os
import sys
import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
import google.generativeai as genai
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Load environment variables
load_dotenv()

console = Console()

class MCPServerConnection:
    """Manages connection to a single MCP server"""
    def __init__(self, name: str, command: str, args: List[str] = None):
        self.name = name
        self.command = command
        self.args = args or []
        self.session: Optional[ClientSession] = None
        self.tools: List[Dict] = []
        self._client_context = None
        self._session_context = None
    
    async def connect(self):
        """Connect to the MCP server"""
        try:
            server_params = StdioServerParameters(
                command=self.command,
                args=self.args
            )
            
            self._client_context = stdio_client(server_params)
            read_stream, write_stream = await self._client_context.__aenter__()
            
            self._session_context = ClientSession(read_stream, write_stream)
            self.session = await self._session_context.__aenter__()
            
            await self.session.initialize()
            tools_response = await self.session.list_tools()
            self.tools = [
                {
                    'name': tool.name,
                    'description': tool.description,
                    'input_schema': tool.inputSchema
                }
                for tool in tools_response.tools
            ]
            
            console.print(f"[green]✓ Connected to {self.name}: {len(self.tools)} tools available[/green]")
            return True
        except Exception as e:
            console.print(f"[red]✗ Failed to connect to {self.name}: {e}[/red]")
            return False
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Call a tool on this MCP server"""
        if not self.session:
            return f"Error: Not connected to {self.name}"
        
        try:
            result = await self.session.call_tool(tool_name, arguments)
            if result.content:
                return "\n".join([
                    item.text if hasattr(item, 'text') else str(item)
                    for item in result.content
                ])
            return "Tool executed successfully"
        except Exception as e:
            return f"Error calling {tool_name}: {str(e)}"
    
    async def disconnect(self):
        """Disconnect from the MCP server"""
        if self._session_context:
            await self._session_context.__aexit__(None, None, None)
        if self._client_context:
            await self._client_context.__aexit__(None, None, None)

class GeminiMCPCLI:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
        
        if not self.api_key:
            console.print("[red]Error: GEMINI_API_KEY not found in .env file[/red]")
            sys.exit(1)
        
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(
            self.model_name,
            generation_config={
                "temperature": 0.7,
                "top_p": 0.95,
                "top_k": 40,
            }
        )
        
        self.mcp_servers: Dict[str, MCPServerConnection] = {}
        self.conversation_history = []
        
    async def load_mcp_servers(self):
        """Load and connect to local Docker MCP servers"""
        servers_config = [
            {
                "name": "inventory",
                "command": "docker",
                "args": ["exec", "-i", "inventory-mcp-server", "python", "main.py"]
            },
            {
                "name": "vanna-ai",
                "command": "docker",
                "args": ["exec", "-i", "vanna-mcp-server", "python", "main.py"]
            }
        ]
        
        console.print("\n[bold cyan]Connecting to local MCP servers...[/bold cyan]")
        
        for config in servers_config:
            server = MCPServerConnection(
                config["name"],
                config["command"],
                config.get("args", [])
            )
            
            if await server.connect():
                self.mcp_servers[config["name"]] = server
        
        if not self.mcp_servers:
            console.print("[yellow]Warning: No MCP servers connected[/yellow]")
    
    def clean_schema_for_gemini(self, schema: Dict) -> Dict:
        """Clean MCP schema to remove Gemini-incompatible fields"""
        if not isinstance(schema, dict):
            return schema
        
        cleaned = {}
        # Fields that Gemini accepts
        allowed_fields = {'type', 'properties', 'required', 'items', 'description', 'enum'}
        
        for key, value in schema.items():
            if key in allowed_fields:
                if key == 'properties' and isinstance(value, dict):
                    # Recursively clean each property
                    cleaned[key] = {
                        prop_name: self.clean_schema_for_gemini(prop_val)
                        for prop_name, prop_val in value.items()
                    }
                elif key == 'required' and isinstance(value, list):
                    # Only include required fields that exist in properties
                    if 'properties' in cleaned:
                        cleaned[key] = [
                            field for field in value 
                            if field in cleaned['properties']
                        ]
                    else:
                        cleaned[key] = value
                elif isinstance(value, dict):
                    cleaned[key] = self.clean_schema_for_gemini(value)
                elif isinstance(value, list):
                    cleaned[key] = [
                        self.clean_schema_for_gemini(item) if isinstance(item, dict) else item
                        for item in value
                    ]
                else:
                    cleaned[key] = value
        
        return cleaned
    
    def get_all_tools_for_gemini(self) -> List[Dict]:
        """Format all MCP tools for Gemini function calling"""
        gemini_tools = []
        
        for server_name, server in self.mcp_servers.items():
            for tool in server.tools:
                cleaned_schema = self.clean_schema_for_gemini(tool['input_schema'])
                gemini_tool = {
                    "name": f"{server_name}_{tool['name']}",
                    "description": f"[{server_name}] {tool['description']}",
                    "parameters": cleaned_schema
                }
                gemini_tools.append(gemini_tool)
        
        return gemini_tools
    
    async def execute_tool_call(self, function_name: str, function_args: Dict) -> str:
        """Execute a tool call from Gemini"""
        parts = function_name.split('_', 1)
        if len(parts) != 2:
            return f"Error: Invalid function name format: {function_name}"
        
        server_name, tool_name = parts
        
        if server_name not in self.mcp_servers:
            return f"Error: Server {server_name} not found"
        
        console.print(f"[dim]Calling {server_name}.{tool_name}({json.dumps(function_args, indent=2)})[/dim]")
        
        result = await self.mcp_servers[server_name].call_tool(tool_name, function_args)
        return result
    
    async def send_message(self, message: str) -> str:
        """Send message to Gemini with tool support"""
        try:
            self.conversation_history.append({
                "role": "user",
                "parts": [message]
            })
            
            tools = self.get_all_tools_for_gemini()
            
            if tools:
                chat = self.model.start_chat(
                    history=self.conversation_history[:-1],
                    enable_automatic_function_calling=False
                )
                
                response = await asyncio.to_thread(
                    chat.send_message,
                    message,
                    tools=[{
                        "function_declarations": tools
                    }] if tools else None
                )
                
                if response.candidates[0].content.parts:
                    for part in response.candidates[0].content.parts:
                        if hasattr(part, 'function_call'):
                            fc = part.function_call
                            tool_result = await self.execute_tool_call(
                                fc.name,
                                dict(fc.args)
                            )
                            
                            response = await asyncio.to_thread(
                                chat.send_message,
                                [{
                                    "function_response": {
                                        "name": fc.name,
                                        "response": {"result": tool_result}
                                    }
                                }]
                            )
                
                result_text = response.text
            else:
                chat = self.model.start_chat(history=self.conversation_history[:-1])
                response = await asyncio.to_thread(chat.send_message, message)
                result_text = response.text
            
            self.conversation_history.append({
                "role": "model",
                "parts": [result_text]
            })
            
            return result_text
            
        except Exception as e:
            console.print(f"[red]Error details: {str(e)}[/red]")
            return f"Error: {str(e)}"
    
    def clear_history(self):
        """Clear chat history"""
        self.conversation_history = []
        console.print("[yellow]Chat history cleared[/yellow]")
    
    def show_tools(self):
        """Show available MCP tools"""
        if not self.mcp_servers:
            console.print("[yellow]No MCP servers connected[/yellow]")
            return
        
        table = Table(title="Available MCP Tools")
        table.add_column("Server", style="cyan")
        table.add_column("Tool", style="green")
        table.add_column("Description", style="white")
        
        for server_name, server in self.mcp_servers.items():
            for tool in server.tools:
                table.add_row(
                    server_name,
                    tool['name'],
                    tool['description']
                )
        
        console.print(table)
    
    def show_help(self):
        """Show help message"""
        help_text = """
## Gemini MCP CLI Help (DGX Version)

**Commands:**
- `exit` or `quit` - Exit the CLI
- `clear` - Clear conversation history  
- `tools` - Show available MCP tools
- `help` - Show this help

**Features:**
- Free Gemini 2.0 Flash API
- Local Docker MCP servers
- Function calling support

**Connected MCP Servers:**
"""
        for server_name, server in self.mcp_servers.items():
            help_text += f"- **{server_name}**: {len(server.tools)} tools\n"
        
        help_text += """
**Example Queries:**
- "Show me 5 inventory items"
- "Search for Nike in inventory"
- "What SQL tables are available?"

Just ask naturally!
        """
        console.print(Markdown(help_text))
    
    async def run_interactive(self):
        """Run interactive chat session"""
        console.print(Panel.fit(
            f"[bold green]Gemini MCP CLI Ready (DGX)[/bold green]\n"
            f"Model: {self.model_name}\n"
            f"MCP Servers: {len(self.mcp_servers)}\n\n"
            f"Commands: [cyan]exit, clear, tools, help[/cyan]",
            title="🤖 Gemini AI + MCP",
            border_style="green"
        ))
        
        history_file = Path.home() / ".gemini_mcp_history"
        session = PromptSession(history=FileHistory(str(history_file)))
        
        while True:
            try:
                user_input = await session.prompt_async("\n[bold green]You:[/bold green] ")
                
                if not user_input.strip():
                    continue
                
                cmd = user_input.lower().strip()
                if cmd in ['exit', 'quit', 'q']:
                    console.print("\n[yellow]👋 Goodbye![/yellow]")
                    break
                
                if cmd == 'clear':
                    self.clear_history()
                    continue
                
                if cmd == 'tools':
                    self.show_tools()
                    continue
                
                if cmd == 'help':
                    self.show_help()
                    continue
                
                with console.status("[bold cyan]Gemini thinking...", spinner="dots"):
                    response = await self.send_message(user_input)
                
                console.print("\n[bold cyan]Gemini:[/bold cyan]")
                console.print(Markdown(response))
                
            except KeyboardInterrupt:
                console.print("\n[yellow]Use 'exit' to quit[/yellow]")
                continue
            except EOFError:
                break
            except Exception as e:
                console.print(f"\n[red]Error: {e}[/red]")
    
    async def cleanup(self):
        """Disconnect from all MCP servers"""
        console.print("\n[cyan]Disconnecting from MCP servers...[/cyan]")
        for server in self.mcp_servers.values():
            await server.disconnect()

async def main():
    cli = GeminiMCPCLI()
    
    try:
        await cli.load_mcp_servers()
        await cli.run_interactive()
    finally:
        await cli.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
