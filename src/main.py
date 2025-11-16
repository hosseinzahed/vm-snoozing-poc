import os
import asyncio
from typing_extensions import Never
from agent_framework import WorkflowBuilder, WorkflowContext, WorkflowOutputEvent, executor
from agent_framework.azure import AzureOpenAIChatClient
from agent_framework.devui import serve
import logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)




# Create Azure OpenAI chat client
chat_client = AzureOpenAIChatClient(
    endpoint="https://models.github.ai/inference",
    deployment_name="openai/gpt-4.1-mini",
    api_key=""
)

# Step 1: Check repository for infrastructure code
repository_checker_agent = chat_client.create_agent(
    name="RepositoryCheckerAgent",
    system_prompt="You are an agent that checks a code repository for existing infrastructure code templates such as Bicep or Terraform. "
                  "Respond with the type of infrastructure code found or 'None' if none is found.",
    tools=[]
)




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

@executor(id="notification_executor")
async def notification_executor(ctx: WorkflowContext[str]) -> None:
    """Send notification about workflow completion.

    Args:
        ctx (WorkflowContext): The workflow context.

    Returns:
        str: A message indicating the workflow has completed.
    """

    result = "Workflow completed successfully."
    await ctx.send_message(result)


def create_workflow() -> WorkflowBuilder:
    workflow = (
        WorkflowBuilder(
            name="VM Snoozing POC DevUI Workflow",
            description="A branching workflow demonstrating VM snoozing POC using different infrastructure code templates.",
        )
        .set_start_executor(check_repository)
        
        .add_edge(check_repository, prepare_infrastructure_prompt, condition=lambda msg: msg != "None")
        .add_edge(prepare_infrastructure_prompt, call_gh_coding_agent)
        .add_executor(
            check_repository
        ).add_executor(
            prepare_infrastructure_prompt
        ).add_executor(
            call_gh_coding_agent    
        ).add_edge(
            check_repository, prepare_infrastructure_prompt
        ).set_start_executor(
            check_repository
        ).build()
    )
    return workflow


def main():
    """Launch the branching workflow in DevUI."""

    logger.info("Starting VM Snoozing POC DevUI...")
    logger.info("Available at: http://localhost:8093")
    logger.info("\nThis workflow demonstrates:")

    serve(entities=[create_workflow()], port=8093, auto_open=True)
    
if __name__ == "__main__":
    asyncio.run(main())