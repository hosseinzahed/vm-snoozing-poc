
from agent_framework import ChatAgent
from agent_framework.azure import AzureOpenAIChatClient
from azure.identity.aio import DefaultAzureCredential

chat_client = AzureOpenAIChatClient(
    credential=DefaultAzureCredential()    
)


