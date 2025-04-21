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
from pydantic_ai import Agent # type: ignore
from pydantic_ai.mcp import MCPServerStdio # type: ignore
from typing import List, Dict, Any
import json
import argparse
import sys
import requests # type: ignore
import re
import traceback

# Check if OPENAI_API_KEY is set
if not os.environ["OPENAI_API_KEY"]:
    raise EnvironmentError("OPENAI_API_KEY environment variable is not set.")

DEFAULT_MODEL = "gpt-4o"
DEFAULT_SYSTEM_PROMPT = "You are a helpful assistant. Use tools to achieve the user's goal."

class SearchResult:
    def __init__(self, title: str, url: str, snippet: str):
        self.title = title
        self.url = url
        self.snippet = snippet
    
    def to_dict(self) -> Dict[str, str]:
        """Convert the search result to a dictionary."""
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet
        }

class MCPAgent:
    def __init__(self):
        # Initialize API keys from environment variables
        self.brave_api_key = os.environ.get("BRAVE_API_KEY", "")
        self.mcp_server_url = os.environ.get("MCP_SERVER_URL", "http://localhost:8000")
        
        # Verify required environment variables
        if not self.brave_api_key:
            print("Warning: Brave API key not set. Search functionality will be limited.")
    
    def fetch_url(self, url: str, model: str = DEFAULT_MODEL, system_prompt: str = None, verbose: bool = False) -> Dict[str, Any]:
        """
        Fetch and summarize content from a URL using the MCP server fetch tool.
        
        Args:
            url: The URL to fetch and summarize
            model: The model to use for summarization
            system_prompt: System prompt to guide the summarization
            verbose: Whether to enable verbose output
            
        Returns:
            Dictionary with the URL, summary, and model information
        """
        try:
            # Get the command to execute the MCP server
            command = os.environ.get("MCP_FETCH_COMMAND", "uvx")
                        
            # Create the fetch integration
            fetch_integration = FetchIntegration(
                url=url,
                command=command,
                model=model,
                system_prompt=system_prompt or "You are a helpful assistant that summarizes web content. Provide a comprehensive summary of the webpage.",
                verbose=verbose
            )
            
            # Run the integration and get the result
            summary = asyncio.run(fetch_integration.run())
            
            # Return the result as a dictionary
            return {
                "url": url,
                "summary": summary,
                "model": model
            }
        except Exception as e:
            error_message = f"Error fetching URL {url}: {str(e)}"
            if verbose:
                print(error_message)
                traceback_info = traceback.format_exc()
                print(f"Traceback: {traceback_info}")
            
            return {
                "url": url,
                "error": error_message,
                "model": model
            }
    
    def search(self, query: str, num_results: int = 5) -> List[SearchResult]:
        """
        Perform a web search using Brave Search API.
        
        Args:
            query: The search query
            num_results: Number of results to return (default: 5)
            
        Returns:
            List of SearchResult objects
        """
        if not self.brave_api_key:
            print("Error: Brave API key not set. Set BRAVE_API_KEY environment variable.")
            return []
        
        url = "https://api.search.brave.com/res/v1/web/search"
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": self.brave_api_key
        }
        params = {
            "q": query,
            "count": num_results
        }
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            results = response.json()
            
            search_results = []
            if "web" in results and "results" in results["web"]:
                for item in results["web"]["results"]:
                    result = SearchResult(
                        title=item.get("title", ""),
                        url=item.get("url", ""),
                        snippet=item.get("description", "")
                    )
                    search_results.append(result)
            
            return search_results
        except Exception as e:
            print(f"Error performing search: {e}")
            return []
    
    def extract_urls(self, text: str) -> List[str]:
        """Extract URLs from text using regex."""
        url_pattern = r'https?://[^\s]+'
        return re.findall(url_pattern, text)
    
    def summarize_url(self, url: str) -> str:
        """
        Fetch and summarize content from a URL using the MCP server.
        
        Args:
            url: The URL to summarize
            
        Returns:
            Summarized content from the URL
        """
        try:
            # Send request to MCP server for summarization
            summarize_endpoint = f"{self.mcp_server_url}/summarize"
            response = requests.post(
                summarize_endpoint,
                json={"url": url}
            )
            response.raise_for_status()
            result = response.json()
            
            # Extract summary from the response
            if "summary" in result:
                return result["summary"]
            elif "content" in result:
                # If no summary but content is available, return truncated content
                content = result["content"]
                return content[:2000] + "..." if len(content) > 2000 else content
            else:
                return "Failed to summarize URL content."
        except Exception as e:
            print(f"Error summarizing URL {url}: {e}")
            return f"Error: Failed to summarize URL content. {str(e)}"
    
    def process_query(self, query: str, force_search: bool = False, system_prompt: str = None, count: int = 5) -> Dict[str, Any]:
        """
        Process a user query by performing search and URL extraction/summarization.
        
        Args:
            query: The user's query
            force_search: Force a search even without search keywords
            system_prompt: Optional system prompt to guide the processing
            count: Number of search results to return
            
        Returns:
            Dictionary with search results and URL summaries
        """
        response = {
            "query": query,
            "search_results": [],
            "url_summaries": []
        }
        
        if system_prompt:
            response["system_prompt"] = system_prompt
        
        # Check if query contains search intent
        search_keywords = ["search", "find", "look up", "google", "information about"]
        needs_search = force_search or any(keyword in query.lower() for keyword in search_keywords)
        
        # Extract URLs from query
        urls = self.extract_urls(query)
        
        # Perform search if needed
        if needs_search:
            search_query = query
            # Try to extract the actual search query if it follows a search keyword
            for keyword in search_keywords:
                if keyword in query.lower():
                    search_parts = query.lower().split(keyword, 1)
                    if len(search_parts) > 1 and search_parts[1].strip():
                        search_query = search_parts[1].strip()
                        break
            
            search_results = self.search(search_query, num_results=count)
            response["search_results"] = [result.to_dict() for result in search_results]
        
        # Process URLs found in the query
        for url in urls:
            summary = self.summarize_url(url)
            if summary:
                response["url_summaries"].append({
                    "url": url,
                    "content": summary
                })
        
        return response

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

def main():
    """
    Multi-Channel Processor (MCP) Agent
    
    Usage:
      mcp_agent.py fetch <url> [--model=<model>] [--system-prompt=<prompt>]
      mcp_agent.py search <query> [--model=<model>] [--system-prompt=<prompt>] [--count=<count>]
      mcp_agent.py summarize <query> [--model=<model>] [--system-prompt=<prompt>]
      mcp_agent.py <query> [--search] [--json-only] [--model=<model>] [--system-prompt=<prompt>] [--count=<count>]
      mcp_agent.py (-h | --help)
    
    Options:
      -h --help                     Show this help message and exit
      --search                      Force search functionality
      --json-only                   Only output JSON result
      --system-prompt=<prompt>      System prompt for the agent
      --count=<count>               Number of results for search queries [default: 5]
      --model=<model>               Model to use for the agent [default: gpt-4o]
    """
    try:
        from docopt import docopt # type: ignore
        args = docopt(main.__doc__)
        
        # Initialize MCPAgent
        agent = MCPAgent()
        
        # Determine the query and whether to force search
        query = None
        url = None
        force_search = False
        system_prompt = args.get('--system-prompt')
        count = int(args.get('--count', 5))  # Parse the count option
        model = args.get('--model', DEFAULT_MODEL)
        
        if args.get('fetch'):
            # Using the command format: mcp_agent.py fetch "url"
            url = args.get('<url>')
            print(f"Fetching content from {url} using model {model}...")
            
            # Use the fetch_url method from MCPAgent class
            result = agent.fetch_url(
                url=url,
                model=model,
                system_prompt=system_prompt,
                verbose=True
            )
            
            # Display the result
            if "error" not in result:
                print("\n=== Fetched Content Summary ===\n")
                print(result["summary"])
            
            # Output JSON
            #print("\n=== JSON Result ===\n")
            #print(json.dumps(result, indent=2))
            
            return
        elif args.get('search'):
            # Using the command format: mcp_agent.py search "query"
            query = args.get('<query>')
            count = int(args.get('--count', 5))
            force_search = True
        elif args.get('summarize'):
            # Using the command format: mcp_agent.py summarize "query" 
            query = args.get('<query>')
            force_search = False
        else:
            # Using the option format: mcp_agent.py "query" --search
            query = args.get('<query>')
            force_search = args.get('--search', False)
        
        if not query:
            print(main.__doc__)
            return
        
        # Process the query
        result = agent.process_query(query, force_search=force_search, system_prompt=system_prompt, count=count)
        
        # Print the result in a nicely formatted way if not json-only
        if not args.get('--json-only'):
            print(f"\nQuery: {result['query']}\n")
            
            if system_prompt:
                print(f"System Prompt: {system_prompt}\n")
            
            if result["search_results"]:
                print("\n=== Search Results ===\n")
                for i, res in enumerate(result["search_results"], 1):
                    print(f"{i}. {res['title']}")
                    print(f"   URL: {res['url']}")
                    print(f"   {res['snippet']}\n")
            
            if result["url_summaries"]:
                print("\n=== URL Content ===\n")
                for i, summary in enumerate(result["url_summaries"], 1):
                    print(f"{i}. Content from {summary['url']}:")
                    content_preview = summary['content'][:500]
                    print(f"   {content_preview}...\n")
        
        # Always output JSON at the end
        #print(json.dumps(result, indent=2))
        
    except ImportError:
        print("The docopt package is required. Please install it with: pip install docopt")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 