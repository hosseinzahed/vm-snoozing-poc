import os
import asyncio
from typing_extensions import Never
from agent_framework import WorkflowBuilder, WorkflowContext, WorkflowOutputEvent, executor
from agent_framework.devui import serve
import logging
from dotenv import load_dotenv
from github_mcp_client import call_github_mcp

load_dotenv(override=True)

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


# Step 1: Check repository for infrastructure code


@executor(id="check_repository")
async def check_repository(repository_url: str, ctx: WorkflowContext[str]) -> None:
    """Check repository for infrastructure code.

    Args:
        ctx (WorkflowContext): The workflow context.    
    Returns:
        str: The type of infrastructure code found ('bicep', 'terraform', or 'none').
    """
    prompt = (f"""              
        Search through repository files in {repository_url} repository. 
        You must return only one word: 'terraform' if any .tf file is present, 
        'bicep' if any .bicep file is present, 
        or 'none' otherwise.
        """)

    infra_type = await call_github_mcp(prompt)
    logger.info("Infrastructure type found: %s", infra_type)
    await ctx.send_message(infra_type)


# Step 2: Prepare infrastructure prompt based on predefined templates
@executor(id="prepare_infrastructure_prompt_executor")
async def prepare_infrastructure_prompt(infra_type: str, ctx: WorkflowContext[Never, str]) -> None:
    """Prepare infrastructure prompt based on predefined templates.

    Args:
        ctx (WorkflowContext): The workflow context.

    Returns:
        str: A message containing the prepared infrastructure code.
    """

    if infra_type == "Bicep":
        result = "Prepared Bicep infrastructure code."
    elif infra_type == "Terraform":
        result = "Prepared Terraform infrastructure code."
    else:
        result = "No infrastructure code prepared."

    await ctx.send_message(result)

# Step 3: Call GitHub Coding Agent to generate infrastructure code


@executor(id="call_gh_coding_agent_executor")
async def call_gh_coding_agent(infra_prompt: str, ctx: WorkflowContext[Never]) -> None:
    """Call GitHub Coding Agent to generate infrastructure code.

    Args:
        ctx (WorkflowContext): The workflow context.

    Returns:
        Never
    """

    # Placeholder for actual GitHub Coding Agent call logic
    await ctx.send_message("GitHub Coding Agent called with prompt: " + infra_prompt)


@executor(id="notify")
async def notify(infra_type: str, ctx: WorkflowContext[Never, str]) -> None:
    """Send notification about workflow completion.

    Args:
        ctx (WorkflowContext): The workflow context.

    Returns:
        str: A message indicating the workflow has completed.
    """

    result = f"Workflow completed successfully. - infra_type: {infra_type}"
    logger.info(result)
    await ctx.send_message(result)


def create_workflow() -> WorkflowBuilder:
    workflow = (
        WorkflowBuilder(
            name="VM Snoozing POC DevUI Workflow",
            description="A branching workflow demonstrating VM snoozing POC using different infrastructure code templates.",
        )
        .add_edge(check_repository, notify)
        .set_start_executor(check_repository)
        .build()
    )
    return workflow


def main():
    """Launch the branching workflow in DevUI."""

    logger.info("Starting VM Snoozing POC DevUI...")
    logger.info("Available at: http://localhost:8093")
    logger.info("\nThis workflow demonstrates:")

    # Create the workflow
    workflow = create_workflow()

    # Serve the workflow in DevUI
    serve(entities=[workflow], port=8093, auto_open=True)


if __name__ == "__main__":
    asyncio.run(main())
