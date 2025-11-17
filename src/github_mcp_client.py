import os
import asyncio
from agent_framework import ChatAgent, MCPStreamableHTTPTool
from agent_framework.azure import AzureAIAgentClient
from azure.identity.aio import DefaultAzureCredential
from dotenv import load_dotenv

load_dotenv(override=True)

async def call_github_mcp(prompt: str) -> str:
    """Example using an HTTP-based MCP server."""
    async with (
        DefaultAzureCredential() as credential,
        MCPStreamableHTTPTool(
            name="GitHub MCP Server",
            url="https://api.githubcopilot.com/mcp",
            headers={
                "Authorization": f"Bearer {os.getenv('GITHUB_TOKEN')}",
                "Content-Type": "application/json"
            },
        ) as mcp_server,
        ChatAgent(
            chat_client=AzureAIAgentClient(
                async_credential=credential,
                model_deployment_name="gpt-4.1-mini"
            ),
            name="GitHub Agent",
            instructions="You help with GitHub related tasks.",
        ) as agent,
    ):
        print("Calling GitHub MCP Server...")
        result = await agent.run(
            messages=prompt,
            tools=mcp_server
        )        
        print("Result from GitHub MCP Server:", result)
        return result
        

if __name__ == "__main__":
    prompt = ("""              
        Search through repository files in https://github.com/HosseinZahed/stu-copilot repository. 
        You must return only one word: 'terraform' if any .tf file is present, 'bicep' if any .bicep file is present, or 'none' otherwise.
        """)
    result = asyncio.run(call_github_mcp(prompt))
    print("Result from GitHub MCP:", result)
