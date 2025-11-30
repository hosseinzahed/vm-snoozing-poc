import asyncio
from typing_extensions import Never
from agent_framework import WorkflowBuilder, WorkflowContext, WorkflowOutputEvent, executor
from agent_framework.devui import serve
import logging
from dotenv import load_dotenv
from github_mcp_client import call_github_mcp
from dataclasses import dataclass
from prompts_service import prompts_service
from typing import cast
import json


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


@dataclass
class CreateBranchOutput:
    branch_name: str
    iac_type: str
    cloud_provider: str


@dataclass
class CodeGeneratorOutput:
    status: str  # "success", "partial_success", or "failed"
    repository_url: str
    branch_name: str
    issue_url: str
    errors: list[str]
    warnings: list[str]


@dataclass
class PullRequestOutput:
    repository_url: str
    issue_url: str
    branch_name: str
    pull_request_url: str
    pull_request_status: str
    pull_request_description: str


@executor(id="check_repository")
async def check_repository(input: CheckRepositoryInput, ctx: WorkflowContext[CheckRepositoryOutput]) -> None:
    """Step 1: Check repository for infrastructure code.

    Args:
        ctx (WorkflowContext): The workflow context.    
    Returns:
        str: The type of infrastructure code found ('bicep', 'terraform', or 'none').
    """

    # Prepare prompt to check repository files
    prompt = (f"""              
            Search through repository files in {input.repository_url} repository.
            If any .bicep file is present return 'bicep' and 'azure'.
            If any .tf file is present, check the terraform provider for aws or azure and return 'terraform' and 'azure' or 'terraform' and 'aws' accordingly.
            If none of these files are present, return 'none' and 'none'.
            The output structure must be two just words separated by a comma: '<iac_type>,<cloud_provider>'.
            No further explanations are needed.
        """)

    # Store repository URL in shared state for later use
    await ctx.set_shared_state("repository_url", input.repository_url)

    # Call GitHub MCP to analyze the repository
    print("Checking repository:", input.repository_url)
    result = await call_github_mcp(prompt)
    iac_type, cloud_provider = str(result).split(",")
    print("Infrastructure type found:", iac_type)
    print("Cloud provider:", cloud_provider)

    # Prepare output dataclass
    output = CheckRepositoryOutput(
        iac_type=iac_type.strip(),
        cloud_provider=cloud_provider.strip()
    )

    # Send output to the next executor
    await ctx.send_message(output)


@executor(id="create_branch")
async def create_branch(input: CheckRepositoryOutput, ctx: WorkflowContext[CreateBranchOutput]) -> None:
    """Step 2: Create a new branch in the repository.
    Args:
        ctx (WorkflowContext): The workflow context.
    Returns:
        output (CreateBranchOutput) with branch name.
    """
    # Get repository URL from shared state
    repository_url = await ctx.get_shared_state("repository_url")

    # Prepare prompt to create a new branch
    prompt = (f"""
            Follow these steps carefully:
            1. Create a new branch in the repository: {repository_url}
            2. Name the branch using the format: vm-snoozing-automation-<random_number>
            3. Return only the branch name—no additional text or explanation.
        """)

    # Call GitHub MCP to create the branch
    new_branch_name = await call_github_mcp(prompt)
    print("New branch name:", new_branch_name)

    # Prepare output dataclass
    output = CreateBranchOutput(
        branch_name=str(new_branch_name).strip(),
        iac_type=input.iac_type,
        cloud_provider=input.cloud_provider
    )

    # Send output to the next executor
    await ctx.send_message(output)


@executor(id="code_generator")
async def code_generator(input: CheckRepositoryOutput, ctx: WorkflowContext[CodeGeneratorOutput]) -> None:
    """Step 3: Generate infrastructure code in the new branch.
    Args:
        input (CheckRepositoryOutput): The input data containing IaC type and cloud provider.
        ctx (WorkflowContext): The workflow context.
    Returns:
        output (CodeGeneratorOutput) with code generation status and details.
    """

    # Get repository URL from shared state
    repository_url = await ctx.get_shared_state("repository_url")

    # Prepare prompt to create a new branch
    prompt = prompts_service.load_code_generator_prompt(
        cloud_provider=input.cloud_provider,
        iac_type=input.iac_type,
        repository_url=repository_url
    )

    # Call GitHub MCP to generate the code
    result = await call_github_mcp(prompt)
    print("Code generation result:", result)

    # Parse the JSON response from the MCP
    result_data = json.loads(str(result))

    # Prepare output dataclass
    output = CodeGeneratorOutput(
        status=result_data.get("status", "failed"),
        repository_url=result_data.get("repository_url", repository_url),
        branch_name=result_data.get("branch_name", ""),
        issue_url=result_data.get("issue_url", ""),
        errors=result_data.get("errors", []),
        warnings=result_data.get("warnings", [])
    )

    # Send output to the next executor
    await ctx.send_message(output)


@executor(id="associate_issue_to_pr")
async def associate_issue_to_pr(input: CodeGeneratorOutput, ctx: WorkflowContext[PullRequestOutput, str]) -> None:
    """ Step 4: Associate issue to pull request.

    Args:
        input (CodeGeneratorOutput): The input data containing code generation results.
        ctx (WorkflowContext): The workflow context.

    Returns:
        PullRequestOutput: A message indicating the workflow has skipped.
    """

    # Prepare prompt to associate issue to pull request
    prompt = (f"""
        Which pull request is associated with the issue {input.issue_url}?
        Provide the pull request URL, status, and description in the following JSON format:
        {{
            "repository_url": "{input.repository_url}",
            "issue_url": "{input.issue_url}",
            "branch_name": "{input.branch_name}",
            "pull_request_url": "<pull_request_url>",
            "pull_request_status": "<pull_request_status>",
            "pull_request_description": "<pull_request_description>"
        }}
        Only return the JSON object without any additional text.
    """)

    # Call GitHub MCP to associate issue to pull request
    result_data = {}
    print("Associating issue to pull request...")

    # Retry until a valid pull request URL is found
    while True:

        # Call GitHub MCP
        result = await call_github_mcp(prompt)

        try:
            # Parse the JSON response from the MCP
            result_data = json.loads(str(result))

            # Check if pull_request_url is present
            if (result_data.get("pull_request_url", "") != ""):
                print("Pull request associated successfully.")
                break

            # If pull_request_url is empty, retry
            print("Pull request URL is empty, retrying...")
            # delay before retrying
            await asyncio.sleep(5)

        except json.JSONDecodeError:
            print("Failed to parse JSON, retrying...")

    # Prepare output dataclass
    output = PullRequestOutput(
        repository_url=result_data.get("repository_url", ""),
        issue_url=result_data.get("issue_url", ""),
        branch_name=result_data.get("branch_name", ""),
        pull_request_url=result_data.get("pull_request_url", ""),
        pull_request_status=result_data.get("pull_request_status", ""),
        pull_request_description=result_data.get(
            "pull_request_description", "")
    )

    # Send output to the next executor
    await ctx.send_message(output)


@executor(id="notify")
async def notify(input: PullRequestOutput, ctx: WorkflowContext[Never, str]) -> None:
    """Send notification about workflow completion.

    Args:
        input (PullRequestOutput): The input data containing pull request details.
        ctx (WorkflowContext): The workflow context.

    Returns:
        str: A message indicating the workflow has completed.
    """

    # Prepare notification message

    output = (f"Workflow completed successfully!\n"
              f"Repository URL: {input.repository_url}\n"
              f"Issue URL: {input.issue_url}\n"
              f"Branch Name: {input.branch_name}\n"
              f"Pull Request URL: {input.pull_request_url}\n"
              f"Pull Request Status: {input.pull_request_status}\n"
              f"Pull Request Description: {input.pull_request_description}\n"
              )
    print(output)

    # Log the notification message
    await ctx.yield_output(output)


@executor(id="skip")
async def skip(input: CheckRepositoryOutput, ctx: WorkflowContext[Never, str]) -> None:
    """Skip the workflow.

    Args:
        input (CheckRepositoryOutput): The input data containing IaC type and cloud provider.
        ctx (WorkflowContext): The workflow context.

    Returns:
        str: A message indicating the workflow has skipped.
    """

    # Prepare skip message
    result = f"Workflow skipped. Infrastructure type: {input.iac_type}, Cloud provider: {input.cloud_provider}"
    print(result)

    # Log the skip message
    await ctx.yield_output(result)


def create_workflow() -> WorkflowBuilder:
    workflow = (
        WorkflowBuilder(
            name="VM Snoozing POC DevUI Workflow",
            description="A branching workflow demonstrating VM snoozing POC using different infrastructure code templates.",
        )
        .add_edge(check_repository, skip,
                  condition=lambda output:
                      cast(CheckRepositoryOutput, output).iac_type == "none"
                  )
        .add_edge(check_repository, code_generator)
        .add_edge(code_generator, associate_issue_to_pr)
        .add_edge(associate_issue_to_pr, notify)
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
    serve(entities=[workflow],
          port=8093,
          auto_open=True,
          mode="developer"
          )


if __name__ == "__main__":
    asyncio.run(main())
