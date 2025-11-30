# VM Snoozing POC

An automated workflow system for implementing VM snoozing automation in Azure and AWS cloud environments using Infrastructure as Code (IaC). This POC leverages GitHub Coding Agent and Microsoft Agent Framework to automatically detect repository infrastructure type and generate appropriate automation code.

## Overview

This project demonstrates an agentic workflow that:
1. Analyzes a GitHub repository to detect Infrastructure as Code type (Bicep or Terraform)
2. Identifies the cloud provider (Azure or AWS)
3. Creates a GitHub issue with implementation requirements
4. Uses GitHub Coding Agent to automatically generate infrastructure code
5. Creates a pull request with the changes
6. Tracks the workflow through to completion

## Architecture

The workflow consists of multiple executor nodes:

```
check_repository → code_generator → associate_issue_to_pr → notify
                ↓
               skip (if no IaC found)
```

### Key Components

- **main.py**: Orchestrates the workflow using Microsoft Agent Framework
- **github_mcp_client.py**: Communicates with GitHub MCP Server for GitHub operations
- **prompts_service.py**: Manages prompt templates for different IaC/cloud combinations
- **Prompt Templates**: Pre-configured instructions for code generation
  - `azure_tf.prompty`: Terraform for Azure
  - `azure_bicep.prompty`: Bicep for Azure
  - `azure_tf-full.prompty`: Full Terraform template reference (Not optimal for GitHub Coding Agent)

## Features

- **Automatic IaC Detection**: Identifies Bicep (.bicep) or Terraform (.tf) files
- **Cloud Provider Detection**: Determines Azure or AWS from Terraform provider configuration
- **GitHub Coding Agent Integration**: Leverages GitHub's AI agent to implement changes
- **Multi-Step Workflow**: Issue creation → Code generation → PR creation → Notification
- **DevUI Interface**: Visual workflow monitoring on http://localhost:8093
- **Error Handling**: Comprehensive retry logic and status tracking

## Prerequisites

### Required Software
- Python 3.9+
- PowerShell (for VM management scripts)
- Git

### Required Services & Access
- **Azure Subscription** with appropriate permissions
- **GitHub Personal Access Token (PAT)** with:
  - `repo` (full repository access)
  - `workflow` (if modifying GitHub Actions)
- **Azure AI Services** endpoint (for Agent Framework)
- **GitHub Coding Agent** enabled for target repositories

### Environment Variables
Create a `.env` file in the project root:

```env
# GitHub Configuration
GITHUB_TOKEN=ghp_your_github_personal_access_token

# Azure AI Configuration (for Agent Framework)
AZURE_AI_PROJECT_CONNECTION_STRING=your_azure_ai_connection_string
# OR
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/
AZURE_OPENAI_API_KEY=your_api_key
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4.1-mini
```

## Installation

1. **Clone the repository**:
   ```powershell
   git clone https://github.com/hosseinzahed/vm-snoozing-poc.git
   cd vm-snoozing-poc
   ```

2. **Install dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```

3. **Configure environment variables**:
   - Copy `.env.example` to `.env` (if provided)
   - Fill in your credentials and endpoints

4. **Verify Azure authentication**:
   ```powershell
   az login
   ```

## How to Run

### Start the Workflow DevUI

```powershell
cd src
python main.py
```

This will:
- Launch the workflow DevUI at http://localhost:8093
- Automatically open in your default browser
- Display the workflow graph and execution status

### Execute a Workflow

1. Open http://localhost:8093 in your browser
2. Input the target repository URL (e.g., `https://github.com/username/repo-name`)
3. Click **Start Workflow**
4. Monitor the progress through each executor node
5. Review the output including:
   - Issue URL
   - Pull Request URL
   - Branch name
   - Status messages

### Test with Sample Repository

Use this sample Azure Terraform repository for testing:
```
https://github.com/hosseinzahed/sample-azure-tf-repo
```

## Workflow Stages

### 1. Check Repository
- Searches for `.bicep` or `.tf` files
- Identifies cloud provider from Terraform provider block
- Returns IaC type and cloud provider
- Skips workflow if no infrastructure code found

### 2. Code Generator
- Loads appropriate prompt template
- Creates GitHub issue with requirements
- Assigns issue to GitHub Coding Agent
- Waits for code generation completion
- Returns status, branch name, and issue URL

### 3. Associate Issue to PR
- Polls for PR associated with the issue
- Retrieves PR status and description
- Retries every 5 seconds until PR is found
- Returns complete PR information

### 4. Notify
- Outputs workflow completion summary
- Displays all relevant URLs and status
- Logs final results

## Prompt Templates

### Azure Terraform (`azure_tf.prompty`)
Generates Terraform configuration with:
- Resource group (`rg-vm-snoozing-automation`)
- Automation Account with Managed Identity
- PowerShell runbook with modern Az modules
- Role assignment (Virtual Machine Contributor)
- Optional schedules for start/stop automation

### Azure Bicep (`azure_bicep.prompty`)
Generates Bicep configuration with equivalent resources using ARM template syntax.

### Guidelines in Prompts
- **DO NOT modify existing code** - only append new resources
- Preserve existing provider and variable configurations
- Follow naming convention: `-vm-snoozing-automation` suffix
- Include comprehensive error handling
- Use Managed Identity (no credentials in code)

## Infrastructure Generated

The workflow creates Azure resources for VM snoozing automation:

### Resources
- **Resource Group**: `rg-vm-snoozing-automation` (Sweden Central)
- **Automation Account**: `aa-vm-snoozing-automation`
- **Runbook**: `Stop-Start-AzureVM` (PowerShell)
- **Role Assignment**: Virtual Machine Contributor at subscription scope

### Runbook Features
- Managed Identity authentication
- Tag-based VM filtering (default: `AutoSnooze = true`)
- Resource group filtering
- VM name list filtering
- Power state validation
- Start/Stop operations
- Comprehensive logging

### Optional Schedules
- **Stop Schedule**: Weekdays at 6 PM (W. Europe Standard Time)
- **Start Schedule**: Weekdays at 8 AM (W. Europe Standard Time)

## Potential Issues & Troubleshooting

### GitHub Coding Agent Issues

**Issue**: GitHub Coding Agent not responding or creating PR
- **Solution**: Verify GitHub Coding Agent is enabled for the repository
  - Go to repository Settings → Code security → GitHub Advanced Security
  - Enable GitHub Copilot and Coding Agent features

**Issue**: Coding Agent firewall blocking
- **Solution**: Ensure your organization has whitelisted GitHub Coding Agent IPs
- **Contact**: Your GitHub organization administrator

### Authentication Issues

**Issue**: `DefaultAzureCredential` authentication failure
- **Solution**: Check credential chain order ([Azure Identity Documentation](https://learn.microsoft.com/en-us/azure/developer/python/sdk/authentication/credential-chains?tabs=dac#defaultazurecredential-overview))
- **Try**: `az login` to establish local credentials
- **Verify**: Environment variables are correctly set

**Issue**: GitHub token permissions insufficient
- **Solution**: Regenerate PAT with required scopes:
  - `repo` (full control of private repositories)
  - `workflow` (update GitHub Action workflows)
  - `admin:org` (if working with organization repositories)

### Workflow Issues

**Issue**: Repository IaC type detection fails
- **Solution**: Verify repository contains `.tf` or `.bicep` files
- **Check**: Files are in root or infrastructure directory
- **Terraform**: Ensure provider block is properly configured

**Issue**: PR association timeout
- **Solution**: Check if Coding Agent has started working on the issue
- **Verify**: Issue is assigned to Coding Agent
- **Wait**: Initial processing can take 30-60 seconds

**Issue**: Code generation fails
- **Solution**: Review issue description and error messages
- **Check**: Repository has appropriate permissions
- **Verify**: Branch creation succeeded

### Azure Resource Issues

**Issue**: Managed Identity lacks permissions
- **Solution**: Manually grant "Virtual Machine Contributor" role
  ```powershell
  az role assignment create `
    --assignee <managed-identity-principal-id> `
    --role "Virtual Machine Contributor" `
    --scope /subscriptions/<subscription-id>
  ```

**Issue**: Runbook fails to execute
- **Solution**: Check Automation Account modules
- **Verify**: Az.Accounts and Az.Compute modules are imported
- **Update**: Modules to latest versions if needed

### Development Issues

**Issue**: DevUI not launching
- **Solution**: Check if port 8093 is available
- **Alternative**: Change port in `main.py` serve() call
- **Firewall**: Allow local connections to port 8093

**Issue**: Module import errors
- **Solution**: Reinstall dependencies
  ```powershell
  pip install -r requirements.txt --upgrade
  ```

## API & Integration Details

### GitHub MCP Server
- **Endpoint**: `https://api.githubcopilot.com/mcp`
- **Authentication**: Bearer token (GitHub PAT)
- **Protocol**: HTTP-based Model Context Protocol

### Azure AI Agent Client
- **Model**: `gpt-4.1-mini` (configurable)
- **Authentication**: DefaultAzureCredential
- **Framework**: Microsoft Agent Framework (agent-framework package)

## Project Structure

```
vm-snoozing-poc/
├── src/
│   ├── main.py                    # Main workflow orchestration
│   ├── github_mcp_client.py       # GitHub MCP integration
│   ├── prompts_service.py         # Prompt template manager
│   ├── tools.py                   # GitHub MCP helper functions
│   ├── prompts/
│   │   ├── azure_bicep.prompty    # Bicep template
│   │   ├── azure_tf.prompty       # Terraform template
│   │   └── azure_tf-full.prompty  # Full Terraform reference
│   └── ps_scripts/
│       └── stop_start_vm.ps1      # Legacy PowerShell script
├── requirements.txt               # Python dependencies
├── README.md                      # This file
└── .env                          # Environment variables (not committed)
```

## Contributing

When adding new prompt templates:
1. Place `.prompty` files in `src/prompts/`
2. Update `prompts_service.py` to handle the new combination
3. Follow the existing naming convention: `<cloud>_<iac>.prompty`
4. Include comprehensive implementation guidelines in prompts

## References

- [Azure Identity Credential Chains](https://learn.microsoft.com/en-us/azure/developer/python/sdk/authentication/credential-chains?tabs=dac#defaultazurecredential-overview)
- [GitHub Coding Agent Documentation](https://docs.github.com/en/copilot/using-github-copilot/using-copilot-coding-agent)
- [Microsoft Agent Framework](https://github.com/microsoft/agent-framework)
- [Azure Automation Account Documentation](https://learn.microsoft.com/en-us/azure/automation/)

## Sample Repository

Test with this sample Azure Terraform repository:
[https://github.com/hosseinzahed/sample-azure-tf-repo](https://github.com/hosseinzahed/sample-azure-tf-repo)

## License

This is a sample repository for demonstration purposes.

## Support

For issues and questions:
- Create an issue in this repository
- Check the troubleshooting section above
- Review Azure and GitHub documentation links
