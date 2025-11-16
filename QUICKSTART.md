# Quick Start Guide

## 5-Minute Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.template .env
```

Edit `.env` with your values:
- `GITHUB_REPO_OWNER`: Your GitHub organization or username
- `GITHUB_REPO_NAME`: Your repository name
- `GITHUB_TOKEN`: Generate at https://github.com/settings/tokens
- `AZURE_SUBSCRIPTION_ID`: Your Azure subscription ID
- Other settings as needed

### 3. Test Locally

```bash
python example_run.py
```

### 4. Expected Output

The workflow will:
1. ✅ Inspect your repository
2. ✅ Detect IaC type (Bicep or Terraform)
3. ✅ Create a new branch
4. ✅ Generate Automation Account code
5. ✅ Create a Pull Request
6. ✅ Send notifications

### 5. Review the PR

Check your GitHub repository for a new PR with:
- Azure Automation Account IaC code
- PowerShell runbooks for VM start/stop
- Schedule configurations
- Validation results

### 6. Merge & Deploy

When you merge the PR, GitHub Actions will:
- ✅ Validate the IaC code
- ✅ Run security scans
- ✅ Deploy to Azure (if main branch)
- ✅ Upload runbooks
- ✅ Configure schedules

## Verify Deployment

```bash
# Check Automation Account
az automation account list --query "[?tags.managedBy=='vm-snoozing-agent']"

# Check runbooks
az automation runbook list \
  --automation-account-name <name> \
  --resource-group <rg>

# Test stop runbook
az automation runbook start \
  --automation-account-name <name> \
  --resource-group <rg> \
  --name "Stop-TargetedVMs"
```

## Troubleshooting

### Issue: "No IaC files detected"
- Ensure your repo has `.bicep` or `.tf` files
- Check that files are in `infra/` directory

### Issue: "Authentication failed"
- Verify GitHub token has correct permissions
- Check Azure credentials are set correctly

### Issue: "VM not found"
- Verify VMs have correct tags (`snooze=true`, `environment=nonprod`)
- Check VM is in the target subscription

## Next Steps

1. **Tag your VMs**: Add `snooze=true` and `environment=nonprod` tags
2. **Customize schedules**: Edit times in `.env`
3. **Add monitoring**: Configure Log Analytics
4. **Set up alerts**: Create Azure Monitor alerts for failures

## Need Help?

- 📖 See [README.md](README.md) for full documentation
- 📝 Check [spec/problem_statement.md](spec/problem_statement.md) for details
- 🐛 Open an issue on GitHub
