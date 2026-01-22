#!/usr/bin/env python3
import signal
import os
import sys
import subprocess
import readline
from abc import ABC, abstractmethod

def exit_handler(sig, frame):
    print()
    raise InterruptedError()

signal.signal(signal.SIGINT, exit_handler)

script_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(script_dir, ".env")
config_path = os.path.join(script_dir, ".provider")

# =============================================================================
# Provider Abstraction
# =============================================================================

class Provider(ABC):
    name: str
    key_env_var: str
    key_url: str

    @abstractmethod
    def generate(self, prompt: str) -> str:
        pass


class GeminiProvider(Provider):
    name = "gemini"
    key_env_var = "GEMINI_API_KEY"
    key_url = "https://aistudio.google.com/apikey"

    def __init__(self):
        from google import genai
        self.client = genai.Client(api_key=os.getenv(self.key_env_var))

    def generate(self, prompt: str) -> str:
        response = self.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return response.text.strip()


class OpenAIProvider(Provider):
    name = "openai"
    key_env_var = "OPENAI_API_KEY"
    key_url = "https://platform.openai.com/api-keys"

    def __init__(self):
        from openai import OpenAI
        self.client = OpenAI(api_key=os.getenv(self.key_env_var))

    def generate(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=256
        )
        return response.choices[0].message.content.strip()


class ClaudeProvider(Provider):
    name = "claude"
    key_env_var = "ANTHROPIC_API_KEY"
    key_url = "https://console.anthropic.com/settings/keys"

    def __init__(self):
        from anthropic import Anthropic
        self.client = Anthropic(api_key=os.getenv(self.key_env_var))

    def generate(self, prompt: str) -> str:
        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text.strip()


class OpenRouterProvider(Provider):
    """OpenRouter - unified API. Access Claude, GPT, and 200+ models."""
    name = "openrouter"
    key_env_var = "OPENROUTER_API_KEY"
    key_url = "https://openrouter.ai/keys"

    def __init__(self):
        from openai import OpenAI
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv(self.key_env_var)
        )

    def generate(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model="anthropic/claude-sonnet-4",  # Can also use openai/gpt-4o-mini, etc.
            messages=[{"role": "user", "content": prompt}],
            max_tokens=256
        )
        return response.choices[0].message.content.strip()

PROVIDERS = {
    "gemini": GeminiProvider,
    "openai": OpenAIProvider,
    "claude": ClaudeProvider,
    "openrouter": OpenRouterProvider,
}

# =============================================================================
# Configuration
# =============================================================================

def load_env():
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key] = value

def save_env_key(key_name: str, value: str):
    """Save or update a key in the .env file."""
    env_vars = {}
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env_vars[k] = v
    env_vars[key_name] = value
    with open(env_path, "w") as f:
        for k, v in env_vars.items():
            f.write(f"{k}={v}\n")
    os.environ[key_name] = value

def get_current_provider_name() -> str:
    if os.path.exists(config_path):
        with open(config_path) as f:
            return f.read().strip()
    return "gemini"

def set_current_provider(name: str):
    with open(config_path, "w") as f:
        f.write(name)

def setup_api_key(provider_class):
    print(f"\n\033[36mGet your API key at: {provider_class.key_url}\033[0m\n")
    api_key = input(f"\033[33mEnter your {provider_class.name.title()} API key:\033[0m ").strip()
    if not api_key:
        print("No API key provided.")
        return False
    save_env_key(provider_class.key_env_var, api_key)
    print("\033[32m✓ API key saved!\033[0m\n")
    return True

def show_help():
    print("\033[36m!api\033[0m       - Change API key for current provider")
    print("\033[36m!provider\033[0m  - Switch AI provider (gemini/openai/claude/openrouter)")
    print("\033[36m!uninstall\033[0m - Remove nlsh")
    print("\033[36m!help\033[0m      - Show this help")
    print("\033[36m!cmd\033[0m       - Run cmd directly")
    print()

def show_providers():
    current = get_current_provider_name()
    print("\033[36mAvailable providers:\033[0m")
    for name in PROVIDERS:
        marker = " \033[32m(active)\033[0m" if name == current else ""
        has_key = "✓" if os.getenv(PROVIDERS[name].key_env_var) else "✗"
        print(f"  {name} [{has_key}]{marker}")
    print()

# =============================================================================
# Provider Initialization
# =============================================================================

def init_provider(name: str) -> Provider:
    if name not in PROVIDERS:
        print(f"\033[31mUnknown provider: {name}\033[0m")
        sys.exit(1)

    provider_class = PROVIDERS[name]

    if not os.getenv(provider_class.key_env_var):
        print(f"\033[33mNo API key found for {name}\033[0m")
        if not setup_api_key(provider_class):
            sys.exit(1)

    try:
        return provider_class()
    except Exception as e:
        print(f"\033[31mFailed to initialize {name}: {e}\033[0m")
        sys.exit(1)

# =============================================================================
# Command History
# =============================================================================

command_history = []
MAX_HISTORY = 10
MAX_CONTEXT_CHARS = 4000

def get_context_size() -> int:
    return sum(len(e["command"]) + len(e["output"]) for e in command_history)

def add_to_history(command: str, output: str = ""):
    command_history.append({
        "command": command,
        "output": output[:500] if output else ""
    })
    while len(command_history) > MAX_HISTORY:
        command_history.pop(0)
    while get_context_size() > MAX_CONTEXT_CHARS and len(command_history) > 1:
        command_history.pop(0)

def format_history() -> str:
    if not command_history:
        return "No previous commands."

    lines = []
    for i, entry in enumerate(command_history[-5:], 1):
        lines.append(f"{i}. $ {entry['command']}")
        if entry['output']:
            output_lines = entry['output'].strip().split('\n')[:2]
            for line in output_lines:
                lines.append(f"   {line}")
    return "\n".join(lines)

# =============================================================================
# Command Generation
# =============================================================================

def get_command(provider: Provider, user_input: str, cwd: str) -> str:
    history_context = format_history()
    prompt = f"""You are a shell command translator. Convert the user's request into a shell command for macOS/zsh.
Current directory: {cwd}

Recent command history:
{history_context}

Rules:
- Output ONLY the command, nothing else
- No explanations, no markdown, no backticks
- If unclear, make a reasonable assumption
- Prefer simple, common commands
- Use the command history for context (e.g., "do that again", "delete the file I just created")

User request: {user_input}"""

    return provider.generate(prompt)

def is_natural_language(text: str) -> bool:
    if text.startswith("!"):
        return False
    shell_commands = ["ls", "pwd", "clear", "exit", "quit", "whoami", "date", "cal",
                      "top", "htop", "history", "which", "man", "touch", "head", "tail",
                      "grep", "find", "sort", "wc", "diff", "tar", "zip", "unzip"]
    shell_starters = ["cd ", "ls ", "echo ", "cat ", "mkdir ", "rm ", "cp ", "mv ",
                      "git ", "npm ", "node ", "npx ", "python", "pip ", "brew ", "curl ",
                      "wget ", "chmod ", "chown ", "sudo ", "vi ", "vim ", "nano ", "code ",
                      "open ", "export ", "source ", "docker ", "kubectl ", "aws ", "gcloud ",
                      "./", "/", "~", "$", ">", ">>", "|", "&&"]
    if text in shell_commands:
        return False
    return not any(text.startswith(s) for s in shell_starters)

# =============================================================================
# Main Loop
# =============================================================================

def main():
    # Require interactive terminal
    if not sys.stdin.isatty():
        print("nlsh requires an interactive terminal. Run it directly in your shell.")
        sys.exit(1)

    load_env()

    provider_name = get_current_provider_name()
    provider = init_provider(provider_name)

    first_run = not any(os.getenv(p.key_env_var) for p in PROVIDERS.values())
    if first_run:
        print("\033[1mnlsh\033[0m - talk to your terminal\n")
        show_help()

    while True:
        try:
            cwd = os.getcwd()
            prompt = f"\033[32m{os.path.basename(cwd)}\033[0m > "
            user_input = input(prompt).strip()

            if not user_input:
                continue

            # cd handling
            if user_input.startswith("cd "):
                path = os.path.expanduser(user_input[3:].strip())
                try:
                    os.chdir(path)
                except Exception as e:
                    print(f"cd: {e}")
                continue
            elif user_input == "cd":
                os.chdir(os.path.expanduser("~"))
                continue

            # !api - change API key
            if user_input == "!api":
                setup_api_key(PROVIDERS[provider_name])
                provider = init_provider(provider_name)
                continue

            # !provider - switch providers
            if user_input == "!provider":
                show_providers()
                choice = input("\033[33mEnter provider name:\033[0m ").strip().lower()
                if choice in PROVIDERS:
                    provider_name = choice
                    set_current_provider(provider_name)
                    provider = init_provider(provider_name)
                    print(f"\033[32m✓ Switched to {provider_name}\033[0m\n")
                elif choice:
                    print(f"\033[31mUnknown provider: {choice}\033[0m")
                continue

            # !uninstall
            if user_input == "!uninstall":
                confirm = input("\033[33mRemove nlsh? [y/N]\033[0m ")
                if confirm.lower() == "y":
                    import shutil
                    install_dir = os.path.expanduser("~/.nlsh")
                    bin_path = os.path.expanduser("~/.local/bin/nlsh")
                    if os.path.exists(install_dir):
                        shutil.rmtree(install_dir)
                    if os.path.exists(bin_path):
                        os.remove(bin_path)
                    print("\033[32m✓ nlsh uninstalled\033[0m")
                    sys.exit(0)
                continue

            # !help
            if user_input == "!help":
                show_help()
                continue

            # !cmd - direct command
            if user_input.startswith("!"):
                cmd = user_input[1:]
                if not cmd:
                    continue
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                print(result.stdout, end="")
                if result.stderr:
                    print(result.stderr, end="")
                add_to_history(cmd, result.stdout + result.stderr)
                continue

            # Regular shell commands
            if not is_natural_language(user_input):
                result = subprocess.run(user_input, shell=True, capture_output=True, text=True)
                print(result.stdout, end="")
                if result.stderr:
                    print(result.stderr, end="")
                add_to_history(user_input, result.stdout + result.stderr)
                continue

            # Natural language -> command
            command = get_command(provider, user_input, cwd)
            confirm = input(f"\033[33m→ {command}\033[0m [Enter] ")

            if confirm == "":
                if command.startswith("cd "):
                    path = os.path.expanduser(command[3:].strip())
                    try:
                        os.chdir(path)
                    except Exception as e:
                        print(f"cd: {e}")
                else:
                    result = subprocess.run(command, shell=True, capture_output=True, text=True)
                    print(result.stdout, end="")
                    if result.stderr:
                        print(result.stderr, end="")
                    add_to_history(command, result.stdout + result.stderr)

        except (EOFError, InterruptedError, KeyboardInterrupt):
            continue
        except Exception as e:
            err = str(e)
            if "429" in err or "quota" in err.lower() or "rate" in err.lower():
                print("\033[31mrate limit hit - wait a moment and try again\033[0m")
            elif "InterruptedError" not in err and "KeyboardInterrupt" not in err:
                print(f"\033[31merror: {err[:100]}\033[0m")

if __name__ == "__main__":
    main()
