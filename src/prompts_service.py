import os
from glob import glob

class PromptsService:
    def __init__(self):
        self.PROMPTS_DIR = os.path.join((os.path.dirname(__file__)), 'prompts')
    
    def load_azure_prompt(self, iac_type: str, repository_url: str) -> str:
        """Load Azure prompt template and fill in the repository URL.

        Args:
            repository_url (str): The URL of the repository to analyze.
        Returns:
            str: The filled prompt template.
        """
        # Load the prompt template from a file
        file_name = ""
        
        if iac_type.lower() == "terraform":
            file_name = "azure_tf.prompty"
        elif iac_type.lower() == "bicep":
            file_name = "azure_bicep.prompty"        
        else:
            raise ValueError("Unsupported")
        
        with open(os.path.join(self.PROMPTS_DIR, file_name), "r") as file:
            prompt_template = file.read()
        # Fill in the repository URL
        prompt = prompt_template.format(repository_url=repository_url)
        return prompt

prompts_service = PromptsService()