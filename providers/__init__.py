from .claude import ClaudeProvider
from .codex import CodexProvider
from .opencode import OpenCodeProvider


PROVIDERS = {
    ClaudeProvider.name: ClaudeProvider,
    CodexProvider.name: CodexProvider,
    OpenCodeProvider.name: OpenCodeProvider,
}