import asyncio
from agent_framework import ChatAgent, MCPStreamableHTTPTool
from agent_framework.azure import AzureAIAgentClient

async def http_mcp_example():
    """Example using an HTTP-based MCP server."""
    async with (        
        MCPStreamableHTTPTool(
            name="Microsoft Learn MCP",
            url="https://api.githubcopilot.com/mcp",
            headers={"Authorization": ""},
        ) as mcp_server,
        ChatAgent(
            chat_client=AzureAIAgentClient( 
                                           
                endpoint="https://models.github.ai/inference",
                deployment_name="openai/gpt-4.1-mini",
                api_key=""
            ),
            name="DocsAgent",
            instructions="You help with Microsoft documentation questions.",
        ) as agent,
    ):
        result = await agent.run(
            "Get latest commits from https://github.com/hosseinzahed/STU-Copilot repository",
            tools=mcp_server
        )
        print(result)

if __name__ == "__main__":
    asyncio.run(http_mcp_example())