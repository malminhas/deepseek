#!/usr/bin/env python
"""MCP Integration Probe.

This script integrates with the Model Context Protocol (MCP) using the pydantic_ai library.
MCP is a standardized protocol that allows AI applications to connect to external tools 
and services using a common interface.

As described at https://ai.pydantic.dev/mcp/, MCP enables different AI applications 
(including programmatic agents like PydanticAI, coding agents, and desktop applications) 
to connect to external tools and services using a common interface.

The protocol allows applications to speak to each other without specific integrations.
PydanticAI agents can act as MCP clients, connecting to MCP servers to use their tools.
PydanticAI comes with two ways to connect to MCP servers:
1. MCPServerHTTP which connects to an MCP server using the HTTP SSE transport
2. MCPServerStdio which runs the server as a subprocess and connects to it using the stdio transport

Usage:
  mcp_agent.py fetch <url> [options]
  mcp_agent.py search <query> [options]
  mcp_agent.py -h | --help

Commands:
  fetch           Use the MCP server fetch tool to get and summarize content from a URL
  search          Use the MCP server search tool to search the web using Brave

Options:
  -h --help                   Show this help message and exit.
  --model=<model>             Model to use for the agent [default: gpt-4o].
  --command=<cmd>             Command to execute the MCP server.
  --system-prompt=<prompt>    System prompt for the agent.
  --count=<count>             Number of results for search queries.
  --verbose                   Enable verbose output.

Examples:
  # Fetch and summarize a URL
  python mcp_agent.py fetch https://ai.pydantic.dev/mcp/

  # Use a different model with fetch
  python mcp_agent.py fetch https://github.com/pydantic/pydantic-ai --model=gpt-3.5-turbo

  # Search the web using Brave search
  python mcp_agent.py search "latest AI developments" --count=5 
  
  # Specify a custom system prompt for search
  python mcp_agent.py search "quantum computing advances" --system-prompt="You're a science expert. Extract key information about quantum computing."

  # Local trades search
  python mcp_agent.py search "Best plumber near me in Twyford, RG10, UK" --model=groq:deepseek-r1-distill-llama-70b

  # Latest news headlines:
  python mcp_agent.py search "latest headlines April 21 2025" --system-prompt="You're a journalist. Extract top 5 headlines."

MCP Information:
  The Model Context Protocol (MCP) is supported by PydanticAI in three ways:
  1. Agents act as MCP Clients, connecting to MCP servers to use their tools
  2. Agents can be used within MCP servers
  3. PydanticAI provides various MCP servers

  There is a great list of MCP servers at: github.com/modelcontextprotocol/servers
  
  The Brave Search MCP server requires an API key. You can get one by signing up at:
  https://brave.com/search/api/

OpenAI Models:
  - gpt-4o
  - gpt-4o-mini
  - gpt-3.5-turbo
Anthropic Models:
  - claude-3-5-sonnet-latest
  - claude-3-haiku-latest
Groq Models:
  - groq:llama-3.3-70b-versatile
  - groq:deepseek-r1-distill-llama-70b
"""

import asyncio
import os
import abc
from docopt import docopt # type: ignore
from pydantic_ai import Agent # type: ignore
from pydantic_ai.mcp import MCPServerStdio # type: ignore

# Check if OPENAI_API_KEY is set
if "OPENAI_API_KEY" not in os.environ or os.environ["OPENAI_API_KEY"] == "":
    raise EnvironmentError("OPENAI_API_KEY environment variable is not set.")

DEFAULT_MODEL = "gpt-4o"
DEFAULT_SYSTEM_PROMPT = "You are a helpful assistant. Use tools to achieve the user's goal."

class MCPServerIntegration(abc.ABC):
    """Base class for MCP server integrations."""

    def __init__(self, command, model=DEFAULT_MODEL, system_prompt=DEFAULT_SYSTEM_PROMPT, verbose=False):
        """Initialize the MCP server integration.
        
        Args:
            command: The command to execute the MCP server
            model: The model to use for the agent
            system_prompt: The system prompt for the agent
            verbose: Whether to enable verbose output
        """
        self.command = command
        self.model = model
        self.system_prompt = system_prompt
        self.verbose = verbose
        # Create environment variables to pass to the subprocess
        self.env_vars = os.environ.copy()
        
    @abc.abstractmethod
    def get_server_name(self):
        """Get the MCP server name."""
        pass
        
    @abc.abstractmethod
    def get_server_args(self):
        """Get the arguments for the MCP server."""
        pass
        
    @abc.abstractmethod
    def build_prompt(self):
        """Build the prompt to send to the agent."""
        pass
    
    async def run(self):
        """Run the MCP integration."""
        server_name = self.get_server_name()
        server_args = self.get_server_args()
        
        if self.verbose:
            print(f"Creating MCP server with command: {self.command}")
            print(f"Server: {server_name}")
            print(f"Arguments: {server_args}")
        
        # Create MCP server
        mcp_server = MCPServerStdio(
            command=self.command,
            args=[server_name] + server_args,
            env=self.env_vars  # Pass environment variables including the API key
        )
        
        try:
            if self.verbose:
                print(f"Creating agent with model: {self.model}")
            
            # Create agent with MCP server
            agent = Agent(
                self.model,
                system_prompt=self.system_prompt,
                mcp_servers=[mcp_server],
            )
            
            # Build the prompt
            prompt = self.build_prompt()
            
            if self.verbose:
                print(f"Running agent with prompt: {prompt}")
            
            # Run the agent
            async with agent.run_mcp_servers():
                result = await agent.run(prompt)
                
                # Check that we got a non-empty response
                assert result.output
                assert len(result.output) > 0
                
                return result.output
        except Exception as e:
            print(f"Error during agent execution: {e}")
            return f"Error: {str(e)}"


class FetchIntegration(MCPServerIntegration):
    """Integration for the MCP server fetch tool."""
    
    def __init__(self, url, command, model=DEFAULT_MODEL, system_prompt=DEFAULT_SYSTEM_PROMPT, verbose=False):
        """Initialize the fetch integration.
        
        Args:
            url: The URL to fetch and summarize
            command: The command to execute the MCP server
            model: The model to use for the agent
            system_prompt: The system prompt for the agent
            verbose: Whether to enable verbose output
        """
        super().__init__(command=command, model=model, system_prompt=system_prompt, verbose=verbose)
        self.url = url
        
    def get_server_name(self):
        """Get the MCP server name."""
        return "mcp-server-fetch"
        
    def get_server_args(self):
        """Get the arguments for the MCP server."""
        return []
        
    def build_prompt(self):
        """Build the prompt to send to the agent."""
        return f"Please get the content of {self.url} and provide a comprehensive summary."


class SearchIntegration(MCPServerIntegration):
    """Integration for the MCP server search tool using Brave search."""
    
    def __init__(self, query, count=None, command="npx", model=DEFAULT_MODEL, system_prompt=DEFAULT_SYSTEM_PROMPT, brave_api_key=None, verbose=False):
        """Initialize the search integration.
        
        Args:
            query: The search query
            count: Number of results to return (optional)
            command: The command to execute the MCP server
            model: The model to use for the agent
            system_prompt: The system prompt for the agent
            brave_api_key: API key for Brave search
            verbose: Whether to enable verbose output
        """
        super().__init__(command=command, model=model, system_prompt=system_prompt, verbose=verbose)
        self.query = query
        self.count = count
        
        # Set Brave API key in environment if provided
        if brave_api_key:
            self.env_vars["BRAVE_API_KEY"] = brave_api_key
        
    def get_server_name(self):
        """Get the MCP server name."""
        return "-y"
        
    def get_server_args(self):
        """Get the arguments for the MCP server."""
        args = ["@modelcontextprotocol/server-brave-search"]
        if self.count:
            args.append(f"--count={self.count}")
        return args
        
    def build_prompt(self):
        """Build the prompt to send to the agent."""
        return f"Please search the web for information about '{self.query}' and provide a comprehensive summary of the findings. \
        Ensure that all results are returned with URLs and that those URLs are valid and accessible."

async def main(args):
    """Main function."""
    # Get common options
    model = args["--model"] or DEFAULT_MODEL
    command = args["--command"]
    system_prompt = args["--system-prompt"] or DEFAULT_SYSTEM_PROMPT
    verbose = args["--verbose"]
    
    # Set up the integration based on the command
    if args["fetch"]:
        url = args["<url>"]
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url
            
        integration = FetchIntegration(
            url=url,
            command=command or "uvx",
            model=model,
            system_prompt=system_prompt,
            verbose=verbose
        )
        print(f"\n---------------------- MCP FETCH ----------------------")
        print(f"Model: {model}")
        print(f"MCP Server: {integration.get_server_name()}")
        print(f"Command: {integration.command}")
        print(f"URL: {url}")
        print("------------------------------------------------------------\n") 
                
    elif args["search"]:
        query = args["<query>"]
        count = args["--count"]
        brave_api_key = os.environ.get("BRAVE_API_KEY")
        
        if not brave_api_key:
            print("Warning: No Brave API key provided. Set it with --brave-api-key or the BRAVE_API_KEY environment variable.")
            print("You can get a Brave API key at: https://brave.com/search/api/")
        
        integration = SearchIntegration(
            query=query,
            count=count,
            command=command or "npx",
            model=model,
            system_prompt=system_prompt,
            brave_api_key=brave_api_key,
            verbose=verbose
        )
        print(f"\n---------------------- MCP SEARCH ----------------------")
        print(f"Model: {model}")
        print(f"MCP Server: {integration.get_server_name()}")
        print(f"Command: {integration.command}")
        print(f"Query: {query}")
        if count:
            print(f"Count: {count}")
        print("------------------------------------------------------------\n")
        
    # Run the integration
    result = await integration.run()
    
    print(f"\n--------------------- RESULT ---------------------\n{result}\n----------------------------------------------------------")


if __name__ == "__main__":
    # Parse command line arguments using docopt
    args = docopt(__doc__)
    
    # Run the main function
    asyncio.run(main(args)) 