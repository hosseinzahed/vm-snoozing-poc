import os
from glob import glob


class PromptsService:
    def __init__(self):
        self.PROMPTS_DIR = os.path.join((os.path.dirname(__file__)), 'prompts')

    def load_code_generator_prompt(self, cloud_provider: str, iac_type: str,
                                   repository_url: str) -> str:
        """Load Azure prompt template and fill in the repository URL.

        Args:
            cloud_provider (str): The cloud provider (e.g., "azure" or "aws").
            iac_type (str): The infrastructure as code type (e.g., "terraform" or "bicep").
            repository_url (str): The URL of the repository to analyze.
        Returns:
            str: The filled prompt template.
        """
        # Load the prompt template from a file
        file_name = ""

        if cloud_provider == "azure" and iac_type == "terraform":
            file_name = "azure_tf.prompty"
        elif cloud_provider == "azure" and iac_type == "bicep":
            file_name = "azure_bicep.prompty"
        elif cloud_provider == "aws" and iac_type == "terraform":
            file_name = "aws_tf.prompty"
        else:
            raise ValueError(
                f"Unsupported combination of cloud_provider '{cloud_provider}' and iac_type '{iac_type}'")

        with open(os.path.join(self.PROMPTS_DIR, file_name), "r") as file:
            prompt_template = file.read()
        # Fill in the repository URL
        prompt = prompt_template.format(
            repository_url=repository_url
        )

        return prompt


prompts_service = PromptsService()
