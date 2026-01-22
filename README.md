# nlsh - Natural Language Shell

Talk to your terminal in plain English.

> **Requirements**: macOS or Linux (Windows not currently supported)

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/junaid-mahmood/nlsh/main/install.sh | bash
```

## Uninstall

```bash
curl -fsSL https://raw.githubusercontent.com/junaid-mahmood/nlsh/main/uninstall.sh | bash
```

## Usage

```bash
nlsh
```

Type naturally:
- `list all python files` → `find . -name "*.py"`
- `git commit with message fixed bug` → `git commit -m "fixed bug"`

Commands:
- `!provider` - Switch AI provider (gemini/openai/claude)
- `!api` - Change API key for current provider
- `!help` - Show help
- `!cmd` - Run cmd directly
- `Ctrl+D` - Exit

## Supported Providers

| Provider | Model | API Key |
|----------|-------|---------|
| Gemini (default) | gemini-2.5-flash | [Get key](https://aistudio.google.com/apikey) |
| OpenAI | gpt-4o-mini | [Get key](https://platform.openai.com/api-keys) |
| Claude | claude-sonnet-4 | [Get key](https://console.anthropic.com/settings/keys) |
| OpenRouter | claude/gpt/200+ models | [Get key](https://openrouter.ai/keys) |

Switch providers with `!provider` command.
