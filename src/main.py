import os
import asyncio
from typing_extensions import Never
from agent_framework import WorkflowBuilder, WorkflowContext, WorkflowOutputEvent, executor
from agent_framework.devui import serve
import logging
from dotenv import load_dotenv
from github_mcp_client import call_github_mcp
from dataclasses import dataclass

load_dotenv(override=True)

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


@dataclass
class CheckRepositoryInput:
    repository_url: str


@dataclass
class CheckRepositoryOutput:
    iac_type: str
    cloud_provider: str

# Step 1: Check repository for infrastructure code


@executor(id="check_repository")
async def check_repository(input: CheckRepositoryInput, ctx: WorkflowContext[CheckRepositoryOutput]) -> None:
    """Check repository for infrastructure code.

    Args:
        ctx (WorkflowContext): The workflow context.    
    Returns:
        str: The type of infrastructure code found ('bicep', 'terraform', or 'none').
    """
    prompt = (f"""              
            Search through repository files in {input.repository_url} repository.
            If any .bicep file is present return 'bicep' and 'azure'.
            If any .tf file is present, check the terraform provider for aws or azure and return 'terraform' and 'azure' or 'terraform' and 'aws' accordingly.
            If none of these files are present, return 'none' and 'none'.
            The output structure must be two just words separated by a comma: '<iac_type>,<cloud_provider>'.
            No further explanations are needed.
        """)
    ctx.set_shared_state("repository_url", input.repository_url)

    print("Checking repository:", input.repository_url)
    result = await call_github_mcp(prompt)
    iac_type, cloud_provider = str(result).split(",")
    print("Infrastructure type found:", iac_type,
          "Cloud provider:", cloud_provider)
    await ctx.send_message(CheckRepositoryOutput(iac_type=iac_type, cloud_provider=cloud_provider))


# Conditional Step 2: Call GitHub Coding Agent for Azure infrastructure code
@executor(id="call_github_coding_agent_for_azure")
async def call_github_coding_agent_for_azure(input: CheckRepositoryOutput, ctx: WorkflowContext[Never, str]) -> None:
    """Prepare infrastructure prompt based on predefined templates.

    Args:
        ctx (WorkflowContext): The workflow context.

    Returns:
        str: A message containing the prepared infrastructure code.
    """
    repository_url = ctx.get_shared_state("repository_url")
    print("Repository URL from shared state:", repository_url)

    if input.iac_type == "bicep":
        prompt = "Prepared Bicep infrastructure code."
    else:  # terraform
        prompt = "Prepared Terraform infrastructure code."

    await ctx.send_message(prompt)

# Conditional Step 2: Call GitHub Coding Agent for AWS infrastructure code


@executor(id="call_github_coding_agent_for_aws")
async def call_github_coding_agent_for_aws(input: CheckRepositoryOutput, ctx: WorkflowContext[Never, str]) -> None:
    """Prepare infrastructure prompt based on predefined templates.

    Args:
        ctx (WorkflowContext): The workflow context.

    Returns:
        str: A message containing the prepared infrastructure code.
    """
    repository_url = ctx.get_shared_state("repository_url")
    print("Repository URL from shared state:", repository_url)

    prompt = "Prepared Terraform infrastructure code."

    await ctx.send_message(prompt)

# Step 3: Notify about workflow completion


@executor(id="notify")
async def notify(input: CheckRepositoryOutput, ctx: WorkflowContext[Never, str]) -> None:
    """Send notification about workflow completion.

    Args:
        ctx (WorkflowContext): The workflow context.

    Returns:
        str: A message indicating the workflow has completed.
    """

    result = f"Workflow completed successfully. Infrastructure type: {input.iac_type}, Cloud provider: {input.cloud_provider}"
    logger.info(result)
    await ctx.yield_output(result)


def create_workflow() -> WorkflowBuilder:
    workflow = (
        WorkflowBuilder(
            name="VM Snoozing POC DevUI Workflow",
            description="A branching workflow demonstrating VM snoozing POC using different infrastructure code templates.",
        )
        .add_edge(check_repository, notify, condition=lambda output: output.iac_type == "none")
        .add_edge(check_repository, call_github_coding_agent_for_azure, condition=lambda output: output.iac_type != "none" and output.cloud_provider == "azure")
        .add_edge(check_repository, call_github_coding_agent_for_aws, condition=lambda output: output.iac_type != "none" and output.cloud_provider == "aws")
        .add_edge(call_github_coding_agent_for_azure, notify)
        .add_edge(call_github_coding_agent_for_aws, notify)
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
