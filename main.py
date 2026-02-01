#!/usr/bin/env python3
"""
Gemini MCP Bridge - Interactive CLI using Gemini instead of Claude
Saves Claude tokens by using free Gemini API for general queries
"""

import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory

# Load environment variables
load_dotenv()

console = Console()

class GeminiCLI:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        
        if not self.api_key:
            console.print("[red]Error: GEMINI_API_KEY not found in .env file[/red]")
            sys.exit(1)
        
        # Configure Gemini
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(self.model_name)
        self.chat = self.model.start_chat(history=[])
        
        console.print(Panel.fit(
            f"[bold green]Gemini CLI Ready[/bold green]\n"
            f"Model: {self.model_name} (FREE tier)\n\n"
            f"Commands:\n"
            f"  [cyan]exit/quit[/cyan] - Exit\n"
            f"  [cyan]clear[/cyan] - Clear chat history\n"
            f"  [cyan]help[/cyan] - Show this help",
            title="🤖 Gemini AI",
            border_style="green"
        ))
    
    async def send_message(self, message: str) -> str:
        """Send message to Gemini and get response"""
        try:
            response = await asyncio.to_thread(
                self.chat.send_message, 
                message
            )
            return response.text
        except Exception as e:
            return f"Error: {str(e)}"
    
    def clear_history(self):
        """Clear chat history"""
        self.chat = self.model.start_chat(history=[])
        console.print("[yellow]Chat history cleared[/yellow]")
    
    def show_help(self):
        """Show help message"""
        help_text = """
## Gemini CLI Help

**Commands:**
- `exit` or `quit` - Exit the CLI
- `clear` - Clear conversation history  
- `help` - Show this help

**Features:**
- Free Gemini 1.5 Flash API (1500 requests/day)
- Markdown formatting for responses
- Persistent chat history
- Fast and cost-effective

**Cost Savings:**
- Claude Sonnet: $3-15/M tokens
- Gemini Flash: **FREE**

Just type your question and press Enter!
        """
        console.print(Markdown(help_text))
    
    async def run_interactive(self):
        """Run interactive chat session"""
        history_file = Path.home() / ".gemini_cli_history"
        session = PromptSession(history=FileHistory(str(history_file)))
        
        while True:
            try:
                # Get user input
                user_input = await session.prompt_async("\n[bold green]You:[/bold green] ")
                
                if not user_input.strip():
                    continue
                
                # Handle commands
                cmd = user_input.lower().strip()
                if cmd in ['exit', 'quit', 'q']:
                    console.print("\n[yellow]👋 Goodbye! Saved you some Claude tokens today![/yellow]")
                    break
                
                if cmd == 'clear':
                    self.clear_history()
                    continue
                
                if cmd == 'help':
                    self.show_help()
                    continue
                
                # Show thinking indicator
                with console.status("[bold cyan]Gemini thinking...", spinner="dots"):
                    response = await self.send_message(user_input)
                
                # Display response
                console.print("\n[bold cyan]Gemini:[/bold cyan]")
                console.print(Markdown(response))
                
            except KeyboardInterrupt:
                console.print("\n[yellow]Use 'exit' to quit[/yellow]")
                continue
            except EOFError:
                break
            except Exception as e:
                console.print(f"\n[red]Error: {e}[/red]")

async def main():
    cli = GeminiCLI()
    await cli.run_interactive()

if __name__ == "__main__":
    asyncio.run(main())
