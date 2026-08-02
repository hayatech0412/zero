#!/usr/bin/env bash
set -e

# === Configuration ===
PYTHON_VERSION="3.11.9"
VENV_NAME="zero-env"

# Determine project root (dir of this script)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 1. Ensure OpenAI key exists
if [ ! -f .env ]; then
  echo "ERROR: .env file not found. Please create it with OPENAI_API_KEY=<key>" >&2
  exit 1
fi

# Export env vars from .env
export $(grep -v '^#' .env | xargs)

# 2. Check if pyenv is installed
if command -v pyenv >/dev/null 2>&1; then
  echo "[INFO] Using pyenv to manage Python $PYTHON_VERSION"
  eval "$(pyenv init --path)"
  eval "$(pyenv init -)"
  eval "$(pyenv virtualenv-init -)"

  # Install python if missing
  if ! pyenv versions --bare | grep -q "^${PYTHON_VERSION}$"; then
    echo "[INFO] Installing Python $PYTHON_VERSION via pyenv (this may take a while)"
    pyenv install "$PYTHON_VERSION"
  fi

  # Create virtualenv if missing
  if ! pyenv virtualenvs --bare | grep -q "^${VENV_NAME}$"; then
    echo "[INFO] Creating virtualenv $VENV_NAME"
    pyenv virtualenv -f "$PYTHON_VERSION" "$VENV_NAME"
  fi

  pyenv activate "$VENV_NAME"
else
  echo "[WARN] pyenv not found. Falling back to system python (>=3.10 required)"
  if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: python3 not found. Install Python 3.10+ or pyenv." >&2
    exit 1
  fi
  PY_VERSION_NUM=$(python3 -c 'import sys; print("{}.{}".format(sys.version_info.major, sys.version_info.minor))')
  case "$PY_VERSION_NUM" in
    3.1[0-9]|3.[2-9]) ;;
    *) echo "ERROR: Python >=3.10 required but $PY_VERSION_NUM found." >&2; exit 1 ;;
  esac

  python3 -m venv .venv
  source .venv/bin/activate
fi

# 3. Upgrade pip & install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Run the FastAPI server
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload 