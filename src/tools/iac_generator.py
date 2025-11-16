"""
IaC generator tool to create Terraform or Bicep code for Azure Automation Account.
"""

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class IaCGenerator:
    """Generates Infrastructure as Code for Azure Automation Account and runbooks."""
    
    def __init__(self):
        """Initialize the IaC generator."""
        pass
    
    async def generate_automation_account(
        self,
        infra_type: str,
        subscription_id: str,
        vm_selector: Dict,
        timezone: str,
        start_time: str,
        stop_time: str,
        repo_context: Dict
    ) -> List[Dict]:
        """
        Generate IaC code for Azure Automation Account with VM start/stop runbooks.
        
        Args:
            infra_type: 'terraform' or 'bicep'
            subscription_id: Azure subscription ID
            vm_selector: VM selection criteria
            timezone: Timezone for schedules
            start_time: VM start time (HH:MM)
            stop_time: VM stop time (HH:MM)
            repo_context: Repository context from inspector
            
        Returns:
            List of file dictionaries with 'path' and 'content'
        """
        logger.info(f"Generating {infra_type} code for subscription {subscription_id}")
        
        suggested_paths = repo_context.get('suggested_paths', {})
        
        if infra_type == 'terraform':
            return await self._generate_terraform(
                subscription_id, vm_selector, timezone, start_time, stop_time, suggested_paths
            )
        elif infra_type == 'bicep':
            return await self._generate_bicep(
                subscription_id, vm_selector, timezone, start_time, stop_time, suggested_paths
            )
        else:
            raise ValueError(f"Unsupported infrastructure type: {infra_type}")
    
    async def _generate_terraform(
        self,
        subscription_id: str,
        vm_selector: Dict,
        timezone: str,
        start_time: str,
        stop_time: str,
        suggested_paths: Dict
    ) -> List[Dict]:
        """Generate Terraform files."""
        from templates.terraform_templates import (
            generate_main_tf,
            generate_variables_tf,
            generate_outputs_tf,
            generate_stop_runbook,
            generate_start_runbook
        )
        
        automation_dir = suggested_paths.get('automation_dir', 'infra/terraform/automation')
        runbooks_dir = suggested_paths.get('runbooks_dir', 'infra/terraform/automation/runbooks')
        
        tag_selector = vm_selector.get('tag_selector', {})
        
        files = [
            {
                'path': f'{automation_dir}/main.tf',
                'content': generate_main_tf(subscription_id, timezone, start_time, stop_time)
            },
            {
                'path': f'{automation_dir}/variables.tf',
                'content': generate_variables_tf()
            },
            {
                'path': f'{automation_dir}/outputs.tf',
                'content': generate_outputs_tf()
            },
            {
                'path': f'{runbooks_dir}/Stop-TargetedVMs.ps1',
                'content': generate_stop_runbook(tag_selector)
            },
            {
                'path': f'{runbooks_dir}/Start-TargetedVMs.ps1',
                'content': generate_start_runbook(tag_selector)
            }
        ]
        
        return files
    
    async def _generate_bicep(
        self,
        subscription_id: str,
        vm_selector: Dict,
        timezone: str,
        start_time: str,
        stop_time: str,
        suggested_paths: Dict
    ) -> List[Dict]:
        """Generate Bicep files."""
        from templates.bicep_templates import (
            generate_main_bicep,
            generate_parameters_bicepparam,
            generate_stop_runbook,
            generate_start_runbook
        )
        
        automation_dir = suggested_paths.get('automation_dir', 'infra/bicep/automation')
        runbooks_dir = suggested_paths.get('runbooks_dir', 'infra/bicep/automation/runbooks')
        
        tag_selector = vm_selector.get('tag_selector', {})
        
        files = [
            {
                'path': f'{automation_dir}/main.bicep',
                'content': generate_main_bicep(subscription_id, timezone, start_time, stop_time)
            },
            {
                'path': f'{automation_dir}/main.bicepparam',
                'content': generate_parameters_bicepparam(subscription_id)
            },
            {
                'path': f'{runbooks_dir}/Stop-TargetedVMs.ps1',
                'content': generate_stop_runbook(tag_selector)
            },
            {
                'path': f'{runbooks_dir}/Start-TargetedVMs.ps1',
                'content': generate_start_runbook(tag_selector)
            }
        ]
        
        return files
