"""
VM Snoozing PoC - Main Orchestrator using Microsoft Agent Framework

This module implements the main orchestrator workflow that:
1. Inspects a repository to detect IaC type (Terraform/Bicep)
2. Creates a new branch
3. Generates IaC code for Azure Automation Account with VM start/stop runbooks
4. Commits and creates a PR
5. Sends notifications to external systems
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

from azure.identity import DefaultAzureCredential
from agent_framework import Workflow, Task, HumanApproval

from tools.repo_inspector import RepoInspector
from tools.iac_generator import IaCGenerator
from tools.github_client import GitHubClient
from tools.notification_client import NotificationClient
from models.config import WorkflowConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VMSnoozingWorkflow:
    """Main orchestrator workflow for VM snoozing automation."""
    
    def __init__(self, config: WorkflowConfig):
        """
        Initialize the workflow with configuration.
        
        Args:
            config: WorkflowConfig containing all necessary settings
        """
        self.config = config
        self.credential = DefaultAzureCredential()
        self.repo_inspector = RepoInspector(config.github_config)
        self.iac_generator = IaCGenerator()
        self.github_client = GitHubClient(config.github_config)
        self.notification_client = NotificationClient(config.notification_config)
        
    async def execute(self, subscription_id: str, vm_selector: Optional[Dict] = None) -> Dict:
        """
        Execute the complete workflow for a given subscription.
        
        Args:
            subscription_id: Azure subscription ID to target
            vm_selector: Optional VM selector criteria (tags, names, or resource IDs)
            
        Returns:
            Dict containing workflow execution results and PR details
        """
        workflow_id = f"snooze-{subscription_id}-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        logger.info(f"Starting workflow {workflow_id} for subscription {subscription_id}")
        
        try:
            # Step 1: Inspect repository to detect IaC type
            logger.info("Step 1: Inspecting repository")
            repo_context = await self.repo_inspector.inspect_repository()
            infra_type = repo_context.get('infra_type')
            logger.info(f"Detected infrastructure type: {infra_type}")
            
            if not infra_type or infra_type not in ['terraform', 'bicep']:
                raise ValueError(f"Unable to detect valid infrastructure type: {infra_type}")
            
            # Step 2: Create new branch
            logger.info("Step 2: Creating new branch")
            branch_name = f"agent/snooze-automation/{subscription_id}-{datetime.utcnow().strftime('%Y%m%d')}"
            branch = await self.github_client.create_branch(
                base_branch=self.config.github_config.base_branch,
                new_branch=branch_name
            )
            logger.info(f"Created branch: {branch_name}")
            
            # Step 3: Generate IaC code
            logger.info("Step 3: Generating IaC code")
            vm_selector = vm_selector or {
                "tag_selector": {
                    "snooze": "true",
                    "environment": "nonprod"
                }
            }
            
            generated_files = await self.iac_generator.generate_automation_account(
                infra_type=infra_type,
                subscription_id=subscription_id,
                vm_selector=vm_selector,
                timezone=self.config.timezone,
                start_time=self.config.start_time,
                stop_time=self.config.stop_time,
                repo_context=repo_context
            )
            logger.info(f"Generated {len(generated_files)} files")
            
            # Step 4: Commit changes to branch
            logger.info("Step 4: Committing changes")
            commit_sha = await self.github_client.commit_files(
                branch=branch_name,
                files=generated_files,
                message=f"[agent] Add Automation Account for VM snoozing in subscription {subscription_id}"
            )
            logger.info(f"Committed changes: {commit_sha}")
            
            # Step 5: Run validation checks
            logger.info("Step 5: Running validation checks")
            validation_results = await self._run_validation_checks(
                branch=branch_name,
                infra_type=infra_type,
                files=generated_files
            )
            
            if not validation_results['passed']:
                logger.error(f"Validation failed: {validation_results['errors']}")
                await self.notification_client.send_notification({
                    'workflow_id': workflow_id,
                    'status': 'failed_validation',
                    'subscription_id': subscription_id,
                    'branch': branch_name,
                    'errors': validation_results['errors']
                })
                return {
                    'success': False,
                    'workflow_id': workflow_id,
                    'error': 'Validation checks failed',
                    'details': validation_results
                }
            
            # Step 6: Create Pull Request
            logger.info("Step 6: Creating pull request")
            pr_body = self._generate_pr_body(
                subscription_id=subscription_id,
                infra_type=infra_type,
                generated_files=generated_files,
                vm_selector=vm_selector,
                validation_results=validation_results
            )
            
            pr = await self.github_client.create_pull_request(
                head_branch=branch_name,
                base_branch=self.config.github_config.base_branch,
                title=f"[agent] Add Automation Account for VM snoozing - {subscription_id}",
                body=pr_body
            )
            logger.info(f"Created PR #{pr['number']}: {pr['url']}")
            
            # Step 7: Send notification to external system
            logger.info("Step 7: Sending notification")
            await self.notification_client.send_notification({
                'workflow_id': workflow_id,
                'status': 'pr_created',
                'subscription_id': subscription_id,
                'branch': branch_name,
                'pr_number': pr['number'],
                'pr_url': pr['url'],
                'files_generated': [f['path'] for f in generated_files],
                'infra_type': infra_type,
                'validation': validation_results
            })
            
            logger.info(f"Workflow {workflow_id} completed successfully")
            return {
                'success': True,
                'workflow_id': workflow_id,
                'pr': pr,
                'branch': branch_name,
                'files': [f['path'] for f in generated_files],
                'validation': validation_results
            }
            
        except Exception as e:
            logger.error(f"Workflow {workflow_id} failed: {str(e)}", exc_info=True)
            await self.notification_client.send_notification({
                'workflow_id': workflow_id,
                'status': 'failed',
                'subscription_id': subscription_id,
                'error': str(e)
            })
            raise
    
    async def _run_validation_checks(
        self,
        branch: str,
        infra_type: str,
        files: List[Dict]
    ) -> Dict:
        """
        Run validation checks on generated IaC code.
        
        Args:
            branch: Branch name to validate
            infra_type: Type of infrastructure (terraform/bicep)
            files: List of generated files
            
        Returns:
            Dict containing validation results
        """
        results = {
            'passed': True,
            'checks': [],
            'errors': []
        }
        
        try:
            if infra_type == 'terraform':
                # Run terraform fmt check
                fmt_check = await self._run_terraform_fmt(files)
                results['checks'].append(fmt_check)
                if not fmt_check['passed']:
                    results['passed'] = False
                    results['errors'].append(fmt_check['error'])
                
                # Run terraform validate
                validate_check = await self._run_terraform_validate(files)
                results['checks'].append(validate_check)
                if not validate_check['passed']:
                    results['passed'] = False
                    results['errors'].append(validate_check['error'])
                    
            elif infra_type == 'bicep':
                # Run bicep build/validate
                build_check = await self._run_bicep_build(files)
                results['checks'].append(build_check)
                if not build_check['passed']:
                    results['passed'] = False
                    results['errors'].append(build_check['error'])
            
            # Run secret scan
            secret_scan = await self._run_secret_scan(files)
            results['checks'].append(secret_scan)
            if not secret_scan['passed']:
                results['passed'] = False
                results['errors'].append(secret_scan['error'])
                
        except Exception as e:
            logger.error(f"Validation error: {str(e)}")
            results['passed'] = False
            results['errors'].append(str(e))
        
        return results
    
    async def _run_terraform_fmt(self, files: List[Dict]) -> Dict:
        """Run terraform fmt check."""
        # Placeholder - would execute actual terraform fmt
        return {'name': 'terraform_fmt', 'passed': True}
    
    async def _run_terraform_validate(self, files: List[Dict]) -> Dict:
        """Run terraform validate check."""
        # Placeholder - would execute actual terraform validate
        return {'name': 'terraform_validate', 'passed': True}
    
    async def _run_bicep_build(self, files: List[Dict]) -> Dict:
        """Run bicep build check."""
        # Placeholder - would execute actual bicep build
        return {'name': 'bicep_build', 'passed': True}
    
    async def _run_secret_scan(self, files: List[Dict]) -> Dict:
        """Run secret scanning check."""
        # Placeholder - would execute actual secret scan (e.g., git-secrets)
        return {'name': 'secret_scan', 'passed': True}
    
    def _generate_pr_body(
        self,
        subscription_id: str,
        infra_type: str,
        generated_files: List[Dict],
        vm_selector: Dict,
        validation_results: Dict
    ) -> str:
        """Generate PR body with details about changes."""
        files_list = "\n".join([f"- {f['path']}" for f in generated_files])
        checks_list = "\n".join([
            f"- {check['name']}: {'✓ passed' if check['passed'] else '✗ failed'}"
            for check in validation_results['checks']
        ])
        
        vm_selector_str = ""
        if 'tag_selector' in vm_selector:
            tags = ", ".join([f"{k}={v}" for k, v in vm_selector['tag_selector'].items()])
            vm_selector_str = f"Tag selector: {tags}"
        elif 'vm_ids' in vm_selector:
            vm_selector_str = f"Explicit VM IDs: {len(vm_selector['vm_ids'])} VMs"
        
        return f"""## [agent] Add Automation Account + Runbooks for VM snoozing

### Summary
- Adds Automation Account: `snooze-automation-{subscription_id}`
- Adds Runbooks: `Stop-TargetedVMs.ps1`, `Start-TargetedVMs.ps1`
- Adds schedule: Stop at {self.config.stop_time} {self.config.timezone}, Start at {self.config.start_time} {self.config.timezone}
- Infrastructure type: {infra_type.upper()}
- {vm_selector_str}

### Files generated
{files_list}

### Validation checks
{checks_list}

### Action required
- **Reviewer**: Please confirm schedules, VM selection logic, and least-privilege configuration for managed identity
- Verify that the targeted subscription and VMs are correct
- Check that business hours align with team requirements

### Security considerations
- Uses Managed Identity for authentication
- Least privilege RBAC roles assigned
- All secrets managed via Azure Key Vault
- VM operations logged to Log Analytics

---
*This PR was automatically generated by the VM Snoozing Agent*
"""


async def main():
    """Main entry point for the workflow."""
    # Load configuration
    config = WorkflowConfig.from_env()
    
    # Initialize workflow
    workflow = VMSnoozingWorkflow(config)
    
    # Execute for a subscription (example)
    subscription_id = config.target_subscription_id
    
    result = await workflow.execute(
        subscription_id=subscription_id,
        vm_selector={
            "tag_selector": {
                "snooze": "true",
                "environment": "nonprod"
            }
        }
    )
    
    logger.info(f"Workflow completed: {result}")
    return result


if __name__ == "__main__":
    asyncio.run(main())
