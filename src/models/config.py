"""
Configuration models for the VM Snoozing workflow.
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class GitHubConfig:
    """GitHub repository configuration."""
    repo_owner: str
    repo_name: str
    base_branch: str
    token: str
    
    @classmethod
    def from_env(cls) -> 'GitHubConfig':
        """Load GitHub config from environment variables."""
        return cls(
            repo_owner=os.getenv('GITHUB_REPO_OWNER', ''),
            repo_name=os.getenv('GITHUB_REPO_NAME', ''),
            base_branch=os.getenv('GITHUB_BASE_BRANCH', 'main'),
            token=os.getenv('GITHUB_TOKEN', '')
        )


@dataclass
class NotificationConfig:
    """External notification system configuration."""
    webhook_url: str
    api_key: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> 'NotificationConfig':
        """Load notification config from environment variables."""
        return cls(
            webhook_url=os.getenv('NOTIFICATION_WEBHOOK_URL', ''),
            api_key=os.getenv('NOTIFICATION_API_KEY')
        )


@dataclass
class WorkflowConfig:
    """Main workflow configuration."""
    github_config: GitHubConfig
    notification_config: NotificationConfig
    target_subscription_id: str
    timezone: str
    start_time: str
    stop_time: str
    schedule_days: str
    
    @classmethod
    def from_env(cls) -> 'WorkflowConfig':
        """Load workflow config from environment variables."""
        return cls(
            github_config=GitHubConfig.from_env(),
            notification_config=NotificationConfig.from_env(),
            target_subscription_id=os.getenv('AZURE_SUBSCRIPTION_ID', ''),
            timezone=os.getenv('TIMEZONE', 'Europe/Copenhagen'),
            start_time=os.getenv('VM_START_TIME', '07:30'),
            stop_time=os.getenv('VM_STOP_TIME', '18:30'),
            schedule_days=os.getenv('SCHEDULE_DAYS', 'Mon-Fri')
        )
