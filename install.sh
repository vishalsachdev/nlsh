set -e

INSTALL_DIR="$HOME/.nlsh"
REPO_URL="https://github.com/junaid-mahmood/nlsh.git"

echo "Installing nlsh..."

if ! command -v python3 &> /dev/null; then
    echo "Python 3 is required. Please install it first."
    exit 1
fi

if [ -d "$INSTALL_DIR" ]; then
    echo "Updating existing installation..."
    cd "$INSTALL_DIR"
    git pull --quiet
else
    echo "Downloading nlsh..."
    git clone --quiet "$REPO_URL" "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"

echo "Setting up Python environment..."
python3 -m venv venv
source venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

echo "Creating nlsh command..."
mkdir -p "$HOME/.local/bin"
cat > "$HOME/.local/bin/nlsh" << 'EOF'
#!/bin/bash
source "$HOME/.nlsh/venv/bin/activate"
python "$HOME/.nlsh/nlsh.py" "$@"
EOF
chmod +x "$HOME/.local/bin/nlsh"

# Add to PATH automatically if needed
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    SHELL_RC=""
    if [ -f "$HOME/.zshrc" ]; then
        SHELL_RC="$HOME/.zshrc"
    elif [ -f "$HOME/.bashrc" ]; then
        SHELL_RC="$HOME/.bashrc"
    elif [ -f "$HOME/.bash_profile" ]; then
        SHELL_RC="$HOME/.bash_profile"
    fi
    
    if [ -n "$SHELL_RC" ]; then
        if ! grep -q '.local/bin' "$SHELL_RC" 2>/dev/null; then
            echo '' >> "$SHELL_RC"
            echo '# nlsh' >> "$SHELL_RC"
            echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$SHELL_RC"
            echo "Added to PATH in $SHELL_RC"
        fi
    fi
fi

echo ""
echo "nlsh installed! Open a new terminal and run 'nlsh' to start."
echo ""
