from .claude import ClaudeProvider
from .codex import CodexProvider


PROVIDERS = {
    ClaudeProvider.name: ClaudeProvider,
    CodexProvider.name: CodexProvider,
}