import logging
from abc import abstractmethod, ABC

from typing import TYPE_CHECKING

from collections.abc import AsyncIterator

from adalflow.core.types import ModelType
from api.config import (
    OPENROUTER_API_KEY,
    OPENAI_API_KEY,
    AWS_ACCESS_KEY_ID,
    AWS_SECRET_ACCESS_KEY,
)

if TYPE_CHECKING:
    from ollama import ChatResponse
    from openai.types.chat import ChatCompletionChunk
    from openai import AsyncStream

MODEL_CFG = dict[str, str | int | float]

# Configure logging
from api.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


class ChatStreamer(ABC):
    _registry: dict[str, type["ChatStreamer"]] = {}
    provider: str

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        if provider := getattr(cls, "provider", None):
            ChatStreamer._registry[provider] = cls

    @classmethod
    def create(cls, *, provider: str, model: str | None = None, model_config: MODEL_CFG) -> "ChatStreamer":
        model = model or model_config.get("model")
        logger.info("Using %s with model: %s", provider, model)
        registered = ChatStreamer._registry.get(provider, None)
        if registered:
            return registered(model=model, model_config=model_config)
        raise RuntimeError(f"Provider {provider} not registered")

    @abstractmethod
    def respond_stream(self, prompt: str) -> AsyncIterator[str]:
        raise NotImplementedError(f"{type(self).__name__} does not implement `respond_stream`")


class OllamaChatStreamer(ChatStreamer):
    provider = "ollama"

    def __init__(self, *, model: str, model_config: MODEL_CFG):
        from adalflow.components.model_client.ollama_client import OllamaClient

        self.client = OllamaClient()
        self.model_kwargs = {
            "model": model,
            "stream": True,
            "options": {
                "temperature": model_config["temperature"],
                "top_p": model_config["top_p"],
                "num_ctx": model_config["num_ctx"]
            }
        }

        logger.debug(f"Prompting Ollama with kwargs: {self.model_kwargs}")

    async def respond_stream(self, prompt: str) -> AsyncIterator[str]:
        api_kwargs = self.client.convert_inputs_to_api_kwargs(
            input=prompt + " /no_think",    # todo I think this could be added into model kwargs?
            model_kwargs=self.model_kwargs,
            model_type=ModelType.LLM,
        )

        response: "AsyncIterator[ChatResponse]" = await self.client.acall(
            api_kwargs=api_kwargs,
            model_type=ModelType.LLM,
        )

        async for chunk in response:
            if not hasattr(chunk, "message"):
                raise RuntimeError(
                    "`message` field not found in response. Wrong ollama-python version probably.",
                )
            text = chunk.message.content
            if text:
                text = text.replace('<think>', '').replace('</think>', '')
                yield text


class OpenRouterChatStreamer(ChatStreamer):
    provider = "openrouter"

    def __init__(self, *, model: str, model_config: MODEL_CFG):
        if not OPENROUTER_API_KEY:
            logger.warning("OPENROUTER_API_KEY not configured, but continuing with request")
            # We'll let the OpenRouterClient handle this and return a friendly error message
        from api.openrouter_client import OpenRouterClient

        self.client = OpenRouterClient()
        self.model_kwargs = {
            "model": model,
            "stream": True,
            "temperature": model_config["temperature"]
        }
        if "top_k" in model_config:
            self.model_kwargs["top_k"] = model_config["top_k"]

    async def respond_stream(self, prompt: str) -> AsyncIterator[str]:
        api_kwargs = self.client.convert_inputs_to_api_kwargs(
            input=prompt,
            model_kwargs=self.model_kwargs,
            model_type=ModelType.LLM,
        )
        async for chunk in await self.client.acall(
                api_kwargs=api_kwargs,
                model_type=ModelType.LLM,
        ):
            yield chunk


class OpenAIChatStreamer(ChatStreamer):
    provider = "openai"

    def __init__(self, *, model: str, model_config: MODEL_CFG):
        if not OPENAI_API_KEY:
            logger.warning("OPENAI_API_KEY not configured, but continuing with request")
            # We'll let the OpenAIClient handle this and return an error message
        from api.openai_client import OpenAIClient

        self.client = OpenAIClient()
        self.model_kwargs = {
            "model": model,
            "stream": True,
            "temperature": model_config["temperature"]
        }
        # Only add top_p if it exists in the model config
        if "top_p" in model_config:
            self.model_kwargs["top_p"] = model_config["top_p"]

    async def respond_stream(self, prompt: str) -> AsyncIterator[str]:
        api_kwargs = self.client.convert_inputs_to_api_kwargs(
            input=prompt,
            model_kwargs=self.model_kwargs,
            model_type=ModelType.LLM
        )
        response: "AsyncStream[ChatCompletionChunk]" = await self.client.acall(
            api_kwargs=api_kwargs,
            model_type=ModelType.LLM,
        )

        async for chunk in response:
            if (
                    chunk.choices and
                    chunk.choices[0].delta is not None and
                    chunk.choices[0].delta.content is not None
            ):
                yield chunk.choices[0].delta.content


class AzureChatStreamer(ChatStreamer):
    provider = "azure"

    def __init__(self, *, model: str, model_config: MODEL_CFG):
        from api.azureai_client import AzureAIClient

        self.client = AzureAIClient()
        self.model_kwargs = {
            "model": model,
            "stream": True,
            "temperature": model_config["temperature"],
            "top_p": model_config["top_p"]
        }

    async def respond_stream(self, prompt: str) -> AsyncIterator[str]:
        api_kwargs = self.client.convert_inputs_to_api_kwargs(
            input=prompt,
            model_kwargs=self.model_kwargs,
            model_type=ModelType.LLM
        )
        response: "AsyncStream[ChatCompletionChunk]" = await self.client.acall(
            api_kwargs=api_kwargs,
            model_type=ModelType.LLM,
        )

        async for chunk in response:
            if (
                    chunk.choices and
                    chunk.choices[0].delta is not None and
                    chunk.choices[0].delta.content is not None
            ):
                yield chunk.choices[0].delta.content


class BedrockChatStreamer(ChatStreamer):
    provider = "bedrock"

    def __init__(self, *, model: str, model_config: MODEL_CFG):
        if not AWS_ACCESS_KEY_ID or not AWS_SECRET_ACCESS_KEY:
            logger.warning("AWS_ACCESS_KEY_ID or AWS_SECRET_ACCESS_KEY not configured, but continuing with request")
            # We'll let the BedrockClient handle this and return an error message
        from api.bedrock_client import BedrockClient

        self.client = BedrockClient()
        self.model_kwargs = {
            "model": model,
            "temperature": model_config["temperature"],
            "top_p": model_config["top_p"]
        }

    async def respond_stream(self, prompt: str) -> AsyncIterator[str]:
        api_kwargs = self.client.convert_inputs_to_api_kwargs(
            input=prompt,
            model_kwargs=self.model_kwargs,
            model_type=ModelType.LLM,
        )
        response = await self.client.acall(
            api_kwargs=api_kwargs,
            model_type=ModelType.LLM,
        )
        if not isinstance(response, str):
            response = str(response)
        yield response


class DashScopeChatStreamer(ChatStreamer):
    provider = "dashscope"

    def __init__(self, *, model: str, model_config: MODEL_CFG):
        from api.dashscope_client import DashscopeClient

        self.client = DashscopeClient()
        self.model_kwargs = {
            "model": model,
            "stream": True,
            "temperature": model_config["temperature"],
            "top_p": model_config["top_p"],
        }

    async def respond_stream(self, prompt: str) -> AsyncIterator[str]:
        api_kwargs = self.client.convert_inputs_to_api_kwargs(
            input=prompt,
            model_kwargs=self.model_kwargs,
            model_type=ModelType.LLM,
        )
        response = await self.client.acall(
            api_kwargs=api_kwargs,
            model_type=ModelType.LLM,
        )
        async for text in response:
            if text:
                yield text


class GoogleGenerativeChatStreamer(ChatStreamer):
    provider = "google"

    def __init__(self, *, model: str, model_config: MODEL_CFG):
        import google.generativeai as genai
        from google.generativeai.types import GenerationConfig

        self.client = genai.GenerativeModel(
            model_name=model,
            generation_config=GenerationConfig(
                temperature=model_config["temperature"],
                top_p=model_config["top_p"],
                top_k=model_config["top_k"],
            )
        )

    async def respond_stream(self, prompt: str) -> AsyncIterator[str]:
        response = await self.client.generate_content_async(prompt, stream=True)
        async for chunk in response:
            if hasattr(chunk, "text"):
                yield chunk.text
