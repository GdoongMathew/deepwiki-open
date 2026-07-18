import pytest
from api.chat import (
    ChatStreamer,
    OllamaChatStreamer,
    OpenRouterChatStreamer,
    OpenAIChatStreamer,
    AzureChatStreamer,
    BedrockChatStreamer,
    DashScopeChatStreamer,
    GoogleGenerativeChatStreamer,
)

@pytest.mark.parametrize("provider, expected", [
    ("ollama", OllamaChatStreamer),
    ("openrouter", OpenRouterChatStreamer),
    ("openai", OpenAIChatStreamer),
    ("azure", AzureChatStreamer),
    ("bedrock", BedrockChatStreamer),
    ("dashscope", DashScopeChatStreamer),
    ("google", GoogleGenerativeChatStreamer),
])
def test_every_provider_is_registered(provider, expected):
    assert ChatStreamer._registry[provider] is expected

@pytest.mark.parametrize("provider, expected", [
    ("ollama", OllamaChatStreamer),
    ("openrouter", OpenRouterChatStreamer),
    ("openai", OpenAIChatStreamer),
    ("azure", AzureChatStreamer),
    ("bedrock", BedrockChatStreamer),
    ("dashscope", DashScopeChatStreamer),
    ("google", GoogleGenerativeChatStreamer),
])
def test_create_returns_correct_subclass(monkeypatch, provider, expected):
    monkeypatch.setattr(expected, "__init__", lambda self, **kw: None)
    s = ChatStreamer.create(provider=provider, model="m", model_config={"model": "m"})
    assert isinstance(s, expected)

def test_create_unknown_provider_raises():
    with pytest.raises(RuntimeError, match="not registered"):
        ChatStreamer.create(provider="nope", model=None, model_config={})
