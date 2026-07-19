import logging

import os

# Configure logging
from api.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

class OllamaModelNotFoundError(Exception):
    """Custom exception for when Ollama model is not found"""
    pass

def check_ollama_model_exists(model_name: str, ollama_host: str = None) -> bool:
    """
    Check if an Ollama model exists before attempting to use it.
    
    Args:
        model_name: Name of the model to check
        ollama_host: Ollama host URL, defaults to localhost:11434
        
    Returns:
        bool: True if model exists, False otherwise
    """
    import ollama
    import httpx
    if ollama_host is None:
        ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    try:
        # Remove /api prefix if present and add it back
        if ollama_host.endswith('/api'):
            ollama_host = ollama_host[:-4]
        ret: ollama.ListResponse = ollama.Client(host=ollama_host, timeout=5).list()
        is_available = any(model_name == model.model for model in ret.models)
        if is_available:
            logger.info("Ollama model '%s' is available", model_name)
        else:
            logger.warning(
                "Ollama model '%s' is not available. Available models: %s. ",
                model_name,
                str([model.model for model in ret.models]))
        return is_available
    except (httpx.ConnectTimeout, ConnectionError) as e:
        logger.warning(f"Could not connect to Ollama to check models: {e}")
        return False
    except Exception as e:
        logger.warning(f"Error checking Ollama model availability: {e}")
        return False
