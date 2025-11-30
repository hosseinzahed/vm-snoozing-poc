import asyncio
from agent_framework import ChatAgent, MCPStreamableHTTPTool
from agent_framework.azure import AzureOpenAIChatClient
from dotenv import load_dotenv
load_dotenv(override=True)

async def use_github_mcp_server(query: str, github_token: str) -> str:
    """
    Consume GitHub MCP Server using Microsoft Agent Framework.
    
    Args:
        query: The question or task to ask the agent about GitHub repositories
        github_token: GitHub personal access token for authentication
        
    Returns:
        str: The agent's response
        
    Example:
        result = await use_github_mcp_server(
            "List all issues in my repository",
            "ghp_yourtoken"
        )
    """
    async with (
        MCPStreamableHTTPTool(
            name="github-mcp",
            url="https://api.githubcopilot.com/mcp",
            headers={
                "Authorization": f"Bearer {github_token}",
                "Content-Type": "application/json"
            },
        ) as mcp_server,
        ChatAgent(
            chat_client=AzureOpenAIChatClient(
                endpoint="https://models.github.ai/inference",
                deployment_name="openai/gpt-4.1-mini",
                api_key=github_token
            ),
            name="GitHubAgent",
            instructions="You are a helpful assistant that can interact with GitHub repositories. "
                        "Use the available GitHub MCP tools to help users with repository operations.",
        ) as agent,
    ):
        result = await agent.run(query, tools=mcp_server)
        return result


async def example_usage():
    """Example of how to use the GitHub MCP Server function."""
    github_token = "your-github-token-here"
    
    # Example queries
    queries = [
        "Does this repository have any Bicep or Terraform infrastructure code? https://github.com/hosseinzahed/STU-Copilot",
        "Show me recent issues in the repository",
        "List the branches in my repository"
    ]
    
    for query in queries:
        print(f"\nQuery: {query}")
        result = await use_github_mcp_server(query, github_token)
        print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(example_usage())
