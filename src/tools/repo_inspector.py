"""
Repository inspector tool to detect infrastructure type (Terraform vs Bicep).
"""

import os
import logging
from typing import Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class RepoInspector:
    """Inspects repository to detect infrastructure type and patterns."""
    
    def __init__(self, github_config):
        """
        Initialize the repo inspector.
        
        Args:
            github_config: GitHub configuration
        """
        self.github_config = github_config
        
    async def inspect_repository(self, repo_path: Optional[str] = None) -> Dict:
        """
        Inspect repository to detect infrastructure type.
        
        Args:
            repo_path: Optional local path to repository. If None, uses current directory.
            
        Returns:
            Dict containing:
                - infra_type: 'terraform', 'bicep', or None
                - confidence: float between 0 and 1
                - patterns_found: dict of detected patterns
                - suggested_paths: suggested paths for new files
        """
        if repo_path is None:
            repo_path = os.getcwd()
        
        logger.info(f"Inspecting repository at: {repo_path}")
        
        # Search for IaC patterns
        terraform_patterns = self._detect_terraform(repo_path)
        bicep_patterns = self._detect_bicep(repo_path)
        
        # Determine infrastructure type based on patterns
        terraform_score = self._calculate_confidence(terraform_patterns)
        bicep_score = self._calculate_confidence(bicep_patterns)
        
        logger.info(f"Terraform confidence: {terraform_score}, Bicep confidence: {bicep_score}")
        
        if terraform_score > bicep_score and terraform_score > 0:
            infra_type = 'terraform'
            confidence = terraform_score
            patterns = terraform_patterns
        elif bicep_score > terraform_score and bicep_score > 0:
            infra_type = 'bicep'
            confidence = bicep_score
            patterns = bicep_patterns
        else:
            # Default to Bicep if no clear pattern
            logger.warning("No clear infrastructure pattern detected, defaulting to Bicep")
            infra_type = 'bicep'
            confidence = 0.5
            patterns = bicep_patterns
        
        # Determine suggested paths for new files
        suggested_paths = self._suggest_file_paths(repo_path, infra_type, patterns)
        
        return {
            'infra_type': infra_type,
            'confidence': confidence,
            'patterns_found': patterns,
            'suggested_paths': suggested_paths,
            'repo_path': repo_path
        }
    
    def _detect_terraform(self, repo_path: str) -> Dict:
        """Detect Terraform patterns in repository."""
        patterns = {
            'tf_files': [],
            'tfvars_files': [],
            'terraform_dirs': [],
            'provider_configs': [],
            'state_files': []
        }
        
        for root, dirs, files in os.walk(repo_path):
            # Skip hidden directories and common exclusions
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', 'venv', '__pycache__']]
            
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, repo_path)
                
                if file.endswith('.tf'):
                    patterns['tf_files'].append(rel_path)
                    if 'provider' in file.lower():
                        patterns['provider_configs'].append(rel_path)
                elif file.endswith('.tfvars'):
                    patterns['tfvars_files'].append(rel_path)
                elif file == 'terraform.tfstate' or file.endswith('.tfstate'):
                    patterns['state_files'].append(rel_path)
            
            # Check for terraform directories
            if 'terraform' in os.path.basename(root).lower():
                patterns['terraform_dirs'].append(os.path.relpath(root, repo_path))
        
        return patterns
    
    def _detect_bicep(self, repo_path: str) -> Dict:
        """Detect Bicep patterns in repository."""
        patterns = {
            'bicep_files': [],
            'bicepparam_files': [],
            'bicep_dirs': [],
            'main_bicep': []
        }
        
        for root, dirs, files in os.walk(repo_path):
            # Skip hidden directories and common exclusions
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', 'venv', '__pycache__']]
            
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, repo_path)
                
                if file.endswith('.bicep'):
                    patterns['bicep_files'].append(rel_path)
                    if file in ['main.bicep', 'azuredeploy.bicep']:
                        patterns['main_bicep'].append(rel_path)
                elif file.endswith('.bicepparam'):
                    patterns['bicepparam_files'].append(rel_path)
            
            # Check for bicep/infra directories
            if any(keyword in os.path.basename(root).lower() for keyword in ['bicep', 'infra', 'infrastructure']):
                patterns['bicep_dirs'].append(os.path.relpath(root, repo_path))
        
        return patterns
    
    def _calculate_confidence(self, patterns: Dict) -> float:
        """Calculate confidence score based on detected patterns."""
        score = 0.0
        
        # Weight different pattern types
        for key, items in patterns.items():
            if not items:
                continue
            
            if key in ['tf_files', 'bicep_files']:
                # Main files are strong indicators
                score += min(len(items) * 0.2, 0.6)
            elif key in ['provider_configs', 'main_bicep']:
                # Configuration files are strong indicators
                score += min(len(items) * 0.3, 0.3)
            elif key in ['terraform_dirs', 'bicep_dirs']:
                # Directory structure is moderate indicator
                score += min(len(items) * 0.1, 0.2)
            else:
                # Other files are weak indicators
                score += min(len(items) * 0.05, 0.1)
        
        return min(score, 1.0)
    
    def _suggest_file_paths(self, repo_path: str, infra_type: str, patterns: Dict) -> Dict:
        """Suggest paths for new infrastructure files."""
        suggestions = {
            'iac_dir': '',
            'automation_dir': '',
            'runbooks_dir': ''
        }
        
        if infra_type == 'terraform':
            # Look for existing terraform directories
            if patterns.get('terraform_dirs'):
                base_dir = patterns['terraform_dirs'][0]
            elif patterns.get('tf_files'):
                # Use directory of first .tf file
                base_dir = os.path.dirname(patterns['tf_files'][0])
            else:
                # Default to terraform/ or infra/terraform/
                base_dir = 'infra/terraform' if os.path.exists(os.path.join(repo_path, 'infra')) else 'terraform'
            
            suggestions['iac_dir'] = base_dir
            suggestions['automation_dir'] = os.path.join(base_dir, 'automation')
            suggestions['runbooks_dir'] = os.path.join(base_dir, 'automation', 'runbooks')
            
        elif infra_type == 'bicep':
            # Look for existing bicep directories
            if patterns.get('bicep_dirs'):
                base_dir = patterns['bicep_dirs'][0]
            elif patterns.get('bicep_files'):
                # Use directory of first .bicep file
                base_dir = os.path.dirname(patterns['bicep_files'][0])
            else:
                # Default to bicep/ or infra/bicep/
                base_dir = 'infra/bicep' if os.path.exists(os.path.join(repo_path, 'infra')) else 'bicep'
            
            suggestions['iac_dir'] = base_dir
            suggestions['automation_dir'] = os.path.join(base_dir, 'automation')
            suggestions['runbooks_dir'] = os.path.join(base_dir, 'automation', 'runbooks')
        
        return suggestions
