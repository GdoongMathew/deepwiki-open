from typing import Optional, List, Literal
from urllib.parse import unquote

from pydantic import BaseModel, Field, field_validator

# Models for the API
class ChatMessage(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str

class ChatCompletionRequest(BaseModel):
    """
    Model for requesting a chat completion.
    """
    repo_url: str = Field(..., description="URL of the repository to query")
    messages: List[ChatMessage] = Field(..., description="List of chat messages")
    filePath: Optional[str] = Field(None, description="Optional path to a file in the repository to include in the prompt")
    token: Optional[str] = Field(None, description="Personal access token for private repositories")
    type: Optional[Literal["github", "gitlab", "bitbucket"]] = Field(
        "github",
        description="Type of repository (e.g., 'github', 'gitlab', 'bitbucket')",
    )

    # model parameters
    provider: str = Field("google", description="Model provider (google, openai, openrouter, ollama, bedrock, azure, dashscope)")
    model: Optional[str] = Field(None, description="Model name for the specified provider")

    language: Optional[str] = Field("en", description="Language for content generation (e.g., 'en', 'ja', 'zh', 'es', 'kr', 'vi')")
    excluded_dirs: List[str] = Field(
        default_factory=list,
        description="List or newline-separated string of directories to exclude from processing",
    )
    excluded_files: List[str] = Field(
        default_factory=list,
        description="List or newline-separated string of file patterns to exclude from processing",
    )
    included_dirs: List[str] = Field(
        default_factory=list,
        description="List or newline-separated string of directories to include exclusively",
    )
    included_files: List[str] = Field(
        default_factory=list,
        description="List or newline-separated string of file patterns to include exclusively",
    )

    @field_validator(
        "excluded_dirs",
        "excluded_files",
        "included_dirs",
        "included_files",
        mode="before",
    )
    @classmethod
    def validate_path(cls, value: list[str] | str) -> list[str]:
        if isinstance(value, str):
            value = [unquote(path) for path in value.strip().split("\n") if path]
        return value
