# VM Snoozing PoC

An agentic solution using Microsoft Agent Framework to automatically manage VM start/stop schedules for non-production Azure subscriptions.

## Overview

This solution automates the process of creating Azure Automation Accounts with runbooks that manage VM power states based on business hours. It leverages:

- **Microsoft Agent Framework** for orchestration workflows
- **GitHub MCP** for repository operations and PR creation
- **Azure Automation Account** for scheduled VM operations
- **Infrastructure as Code** (Bicep or Terraform) for resource provisioning

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  VM Snoozing Orchestrator                    │
│                (Microsoft Agent Framework)                    │
└──────────────┬───────────────────────────────┬──────────────┘
               │                                 │
               ▼                                 ▼
    ┌──────────────────┐              ┌─────────────────────┐
    │  Repo Inspector  │              │   IaC Generator     │
    │   (Detect Type)  │              │  (Bicep/Terraform)  │
    └──────────────────┘              └─────────────────────┘
               │                                 │
               ▼                                 ▼
    ┌──────────────────┐              ┌─────────────────────┐
    │  GitHub Client   │              │ Notification Client │
    │ (Branch/PR/MCP)  │              │  (External System)  │
    └──────────────────┘              └─────────────────────┘
               │
               ▼
    ┌──────────────────────────────────────────────────────┐
    │            GitHub Actions CI/CD Pipeline              │
    │  (Validation, Security Scan, Deployment via OIDC)    │
    └──────────────────────────────────────────────────────┘
               │
               ▼
    ┌──────────────────────────────────────────────────────┐
    │         Azure Automation Account + Runbooks          │
    │    (Stop/Start VMs based on tags & schedules)        │
    └──────────────────────────────────────────────────────┘
```

## Features

### 🤖 Automated Workflow
- Detects infrastructure type (Terraform/Bicep) in existing repositories
- Creates feature branches automatically
- Generates IaC code for Azure Automation Account
- Creates Pull Requests with detailed change summaries
- Sends notifications to external systems

### 🔒 Security & Compliance
- Uses Azure Managed Identity for authentication
- OIDC-based GitHub Actions authentication
- Least-privilege RBAC roles
- Security scanning (Checkov, TruffleHog)
- Secret management via Azure Key Vault

### 📊 VM Targeting Options
- **Tag-based**: Select VMs by tags (e.g., `snooze=true`, `environment=nonprod`)
- **Explicit IDs**: Specify VM resource IDs directly
- **Name patterns**: Use naming conventions to target VMs

### ⏰ Flexible Scheduling
- Configurable business hours
- Timezone-aware schedules
- Day-of-week selection (e.g., Mon-Fri)
- Separate start and stop times

## Project Structure

```
vm-snoozing-poc/
├── src/
│   ├── main.py                    # Main orchestrator workflow
│   ├── models/
│   │   ├── __init__.py
│   │   └── config.py              # Configuration models
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── repo_inspector.py      # IaC type detection
│   │   ├── iac_generator.py       # Code generation
│   │   ├── github_client.py       # GitHub operations
│   │   └── notification_client.py # External notifications
│   └── templates/
│       ├── __init__.py
│       ├── bicep_templates.py     # Bicep code generators
│       └── terraform_templates.py # Terraform code generators
├── .github/
│   └── workflows/
│       └── iac-ci.yml             # CI/CD pipeline
├── spec/
│   └── problem_statement.md       # Detailed requirements
├── requirements.txt               # Python dependencies
├── .env.template                  # Environment variables template
└── README.md                      # This file
```

## Setup Instructions

### Prerequisites

1. **Python 3.9+** installed
2. **Azure subscription** with permissions to create resources
3. **GitHub repository** with Actions enabled
4. **GitHub Personal Access Token** with repo permissions
5. **Azure Service Principal** or Managed Identity

### Step 1: Clone Repository

```bash
git clone https://github.com/your-org/vm-snoozing-poc.git
cd vm-snoozing-poc
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Configure Environment

```bash
# Copy template and fill in your values
cp .env.template .env
# Edit .env with your configuration
```

### Step 4: Configure Azure OIDC for GitHub Actions

1. Create an Azure AD Application:
```bash
az ad app create --display-name "VM-Snoozing-GitHub-Actions"
```

2. Create a Service Principal:
```bash
az ad sp create --id <app-id>
```

3. Configure federated credentials for GitHub Actions:
```bash
az ad app federated-credential create \
  --id <app-id> \
  --parameters '{
    "name": "github-actions",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:your-org/your-repo:ref:refs/heads/main",
    "audiences": ["api://AzureADTokenExchange"]
  }'
```

4. Assign permissions to the Service Principal:
```bash
az role assignment create \
  --assignee <service-principal-id> \
  --role "Contributor" \
  --scope /subscriptions/<subscription-id>
```

### Step 5: Configure GitHub Secrets

Add the following secrets to your GitHub repository:

- `AZURE_CLIENT_ID`: Application (client) ID
- `AZURE_TENANT_ID`: Directory (tenant) ID
- `AZURE_SUBSCRIPTION_ID`: Subscription ID
- `AZURE_RESOURCE_GROUP`: Resource group name
- `GITHUB_TOKEN`: GitHub Personal Access Token

### Step 6: Run the Workflow

```bash
# Run the orchestrator
python src/main.py
```

Or trigger via Python:

```python
import asyncio
from src.main import main

asyncio.run(main())
```

## Usage Examples

### Example 1: Tag-Based VM Selection

```python
from src.main import VMSnoozingWorkflow
from src.models.config import WorkflowConfig

config = WorkflowConfig.from_env()
workflow = VMSnoozingWorkflow(config)

result = await workflow.execute(
    subscription_id="00000000-0000-0000-0000-000000000000",
    vm_selector={
        "tag_selector": {
            "snooze": "true",
            "environment": "nonprod"
        }
    }
)
```

### Example 2: Explicit VM IDs

```python
result = await workflow.execute(
    subscription_id="00000000-0000-0000-0000-000000000000",
    vm_selector={
        "vm_ids": [
            "/subscriptions/.../resourceGroups/rg-app/providers/Microsoft.Compute/virtualMachines/vm-app-01",
            "/subscriptions/.../resourceGroups/rg-app/providers/Microsoft.Compute/virtualMachines/vm-app-02"
        ]
    }
)
```

## Generated Pull Request Example

When the workflow runs, it creates a PR with:

```markdown
## [agent] Add Automation Account + Runbooks for VM snoozing

### Summary
- Adds Automation Account: `snooze-automation-abc12345`
- Adds Runbooks: `Stop-TargetedVMs.ps1`, `Start-TargetedVMs.ps1`
- Adds schedule: Stop at 18:30 Europe/Copenhagen, Start at 07:30 Europe/Copenhagen
- Infrastructure type: BICEP
- Tag selector: snooze=true, environment=nonprod

### Files generated
- infra/bicep/automation/main.bicep
- infra/bicep/automation/main.bicepparam
- infra/bicep/automation/runbooks/Stop-TargetedVMs.ps1
- infra/bicep/automation/runbooks/Start-TargetedVMs.ps1

### Validation checks
- bicep_build: ✓ passed
- secret_scan: ✓ passed

### Action required
- **Reviewer**: Please confirm schedules, VM selection logic, and least-privilege configuration
```

## CI/CD Pipeline

The GitHub Actions workflow (`iac-ci.yml`) automatically:

1. **Detects** infrastructure type (Bicep/Terraform)
2. **Validates** IaC code (format, syntax, lint)
3. **Scans** for security issues and secrets
4. **Deploys** to Azure (on merge to main)
5. **Uploads** runbooks to Automation Account
6. **Comments** on PRs with validation results

## Monitoring & Operations

### View Runbook Execution Logs

```bash
az automation job list \
  --automation-account-name <account-name> \
  --resource-group <resource-group>

az automation job show-output \
  --automation-account-name <account-name> \
  --resource-group <resource-group> \
  --name <job-id>
```

### Test Runbook Manually

```bash
az automation runbook start \
  --automation-account-name <account-name> \
  --resource-group <resource-group> \
  --name "Stop-TargetedVMs"
```

### View VM Power States

```bash
az vm list \
  --query "[?tags.snooze=='true'].{Name:name, PowerState:powerState}" \
  --output table
```

## Troubleshooting

### Issue: Workflow fails to detect IaC type

**Solution**: Ensure your repository contains either `.bicep` or `.tf` files in the expected locations.

### Issue: GitHub Actions deployment fails

**Solution**: Verify OIDC federated credentials and service principal permissions.

### Issue: Runbooks don't execute

**Solution**: Check that:
1. Automation Account has System-Assigned Managed Identity enabled
2. Managed Identity has required RBAC roles
3. Schedules are properly configured with correct timezone

## Best Practices

1. **Start small**: Test with a single non-prod subscription first
2. **Use tags**: Tag-based selection is more scalable than explicit IDs
3. **Human approval**: Enable PR review requirements for production
4. **Monitor logs**: Use Log Analytics for runbook execution tracking
5. **Test runbooks**: Manually test before scheduling
6. **Document exceptions**: Maintain a list of VMs that should never be stopped

## Security Considerations

- All agent commits use a bot identity
- Human review required for merges
- Secrets stored in Azure Key Vault
- Pre-commit scanning for secrets
- Azure Policy guardrails
- Least-privilege service principals

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License

## Support

For issues and questions, please open a GitHub issue.

---

**Built with Microsoft Agent Framework** 🤖
