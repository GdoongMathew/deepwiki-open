"""Unify Adalflow compatible clients to here.
Any patches and additional clients could be applied or imported in this module.
"""

from .google_embedder import GoogleEmbedderClient
from .bedrock import BedrockClient
from .dashscope import DashscopeClient
from .ollama import OllamaClient
from .litellm import LiteLLMClient
from .openrouter import OpenRouterClient
from adalflow.components.model_client import (
    AzureAIClient,
    OpenAIClient,
    GoogleGenAIClient,
)

__all__ = [
    "AzureAIClient",
    "BedrockClient",
    "DashscopeClient",
    "GoogleEmbedderClient",
    "GoogleGenAIClient",
    "LiteLLMClient",
    "OllamaClient",
    "OpenAIClient",
    "OpenRouterClient",
]