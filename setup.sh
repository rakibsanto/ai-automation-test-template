#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# AI Automation Test Agent — One-command setup
# Works on macOS and Linux. Run: bash setup.sh
# ─────────────────────────────────────────────────────────────────────────────

set -e

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✅ $*${NC}"; }
warn() { echo -e "${YELLOW}⚠️  $*${NC}"; }
err()  { echo -e "${RED}❌ $*${NC}"; }
info() { echo -e "   $*"; }

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  AI Test Automation — Setup"    
echo "═══════════════════════════════════════════════════════════════"
echo ""

# ── 1. Python 3.10+ ───────────────────────────────────────────────────────────
echo "── 1. Checking Python..."
PY=""
for cmd in python3.12 python3.11 python3.10 python3 python; do
    if command -v "$cmd" &>/dev/null; then
        ver=$("$cmd" --version 2>&1 | grep -oP '\d+\.\d+' | head -1)
        major=$(echo "$ver" | cut -d. -f1)
        minor=$(echo "$ver" | cut -d. -f2)
        if [ "$major" -ge 3 ] && [ "$minor" -ge 10 ]; then
            PY="$cmd"
            ok "Python $ver ($cmd)"
            break
        fi
    fi
done
if [ -z "$PY" ]; then
    err "Python 3.10+ required. Install from https://python.org"
    exit 1
fi

# ── 2. pip dependencies ───────────────────────────────────────────────────────
echo ""
echo "── 2. Installing Python dependencies..."
if [ -f requirements.txt ]; then
    $PY -m pip install -r requirements.txt --quiet
    ok "Dependencies installed"
else
    $PY -m pip install playwright pytest pytest-playwright pytest-json-report \
        pytest-timeout ollama --quiet
    ok "Core dependencies installed"
fi

# ── 3. Playwright browsers ────────────────────────────────────────────────────
echo ""
echo "── 3. Installing Playwright browsers..."
$PY -m playwright install chromium
ok "Chromium browser installed"

# ── 4. Ollama ─────────────────────────────────────────────────────────────────
echo ""
echo "── 4. Installing Ollama (local AI — no API keys needed)..."
if command -v ollama &>/dev/null; then
    ok "Ollama already installed ($(ollama --version 2>/dev/null || echo 'version unknown'))"
else
    if [[ "$OSTYPE" == "darwin"* ]]; then
        if command -v brew &>/dev/null; then
            brew install ollama
            ok "Ollama installed via Homebrew"
        else
            warn "Homebrew not found. Downloading Ollama installer..."
            curl -fsSL https://ollama.ai/install.sh | sh
            ok "Ollama installed"
        fi
    else
        curl -fsSL https://ollama.ai/install.sh | sh
        ok "Ollama installed"
    fi
fi

# ── 5. Start Ollama service ───────────────────────────────────────────────────
echo ""
echo "── 5. Starting Ollama service..."
if ! pgrep -x ollama &>/dev/null; then
    ollama serve &>/dev/null &
    OLLAMA_PID=$!
    echo "   Waiting for Ollama to start..."
    for i in $(seq 1 20); do
        if curl -s http://localhost:11434/api/tags &>/dev/null; then
            ok "Ollama service running (PID $OLLAMA_PID)"
            break
        fi
        sleep 1
    done
else
    ok "Ollama service already running"
fi

# ── 6. Pull AI models ─────────────────────────────────────────────────────────
echo ""
echo "── 6. Pulling AI models (this may take a few minutes)..."
echo ""

pull_model() {
    local model=$1
    local size=$2
    local label=$3
    echo -n "   Pulling $label ($size)... "
    if ollama pull "$model" &>/dev/null 2>&1; then
        ok "$label ready"
    else
        warn "$label unavailable (optional — other models will be tried)"
    fi
}

# Always pull the primary CI model (small and fast)
pull_model "qwen2.5-coder:1.5b" "986 MB" "qwen2.5-coder:1.5b (primary)"

# Ask about larger models
echo ""
echo "   Optional: pull more models for better test quality?"
read -r -p "   Pull qwen2.5-coder:7b (best quality, 4.7 GB)? [y/N]: " PULL_LARGE
if [[ "$PULL_LARGE" =~ ^[Yy]$ ]]; then
    pull_model "qwen2.5-coder:7b" "4.7 GB" "qwen2.5-coder:7b (best)"
fi

read -r -p "   Pull llama3.2:1b (fast backup, 1.3 GB)? [y/N]: " PULL_LLAMA
if [[ "$PULL_LLAMA" =~ ^[Yy]$ ]]; then
    pull_model "llama3.2:1b" "1.3 GB" "llama3.2:1b (backup)"
fi

read -r -p "   Pull phi3.5 (Microsoft, 2.2 GB)? [y/N]: " PULL_PHI
if [[ "$PULL_PHI" =~ ^[Yy]$ ]]; then
    pull_model "phi3.5" "2.2 GB" "phi3.5 (backup)"
fi

echo ""
echo "   Available models:"
ollama list

# ── 7. Create directories ─────────────────────────────────────────────────────
echo ""
echo "── 7. Creating required directories..."
mkdir -p specs tests reports reports/screenshots reports/evidence payloads
ok "Directories ready"

# ── 8. Verify all modules ─────────────────────────────────────────────────────
echo ""
echo "── 8. Verifying all modules..."
PYTHONPATH="$(pwd)" $PY -c "
import sys
errors = []
modules = [
    ('ai_engine.spec_parser',   'parse'),
    ('ai_engine.spec_compiler', 'compile_spec'),
    ('ai_engine.test_generator','generate_all'),
    ('ai_engine.test_validator','validate_code'),
    ('ai_engine.evidence',      'enrich_bug'),
    ('ai_engine.bug_builder',   'build_from_json_report'),
    ('ai_engine.gap_checker',   'detect_gaps'),
    ('ai_engine.memory',        'load'),
    ('ai_engine.reporter',      'generate_report'),
    ('ai_engine.agent',         'template_tests'),
]
for mod, fn in modules:
    try:
        m = __import__(mod, fromlist=[fn])
        getattr(m, fn)
        print(f'  ✅ {mod}')
    except Exception as e:
        errors.append(f'{mod}: {e}')
        print(f'  ❌ {mod}: {e}')

try:
    from payloads import XSS, SQLI, BOUNDARY
    print(f'  ✅ payloads  XSS:{len(XSS)} SQLi:{len(SQLI)} Boundary:{len(BOUNDARY)}')
except Exception as e:
    errors.append(f'payloads: {e}')
    print(f'  ❌ payloads: {e}')

if errors:
    print(f'\n❌ {len(errors)} module(s) failed')
    sys.exit(1)
else:
    print(f'\n✅ All modules verified')
"

# ── 9. Configuration ──────────────────────────────────────────────────────────
echo ""
echo "── 9. Configuration..."
echo ""
read -r -p "   Target URL (default: https://beta-stg.fagun.ai): " INPUT_URL
BASE_URL="${INPUT_URL:-https://beta-stg.fagun.ai}"
echo "   BASE_URL=$BASE_URL"
echo ""

# Write .env for convenience
if [ ! -f .env ]; then
    cat > .env << EOF
BASE_URL=${BASE_URL}
AI_MODEL=qwen2.5-coder:1.5b
TEST_PASSWORD=Test@1234!
EOF
    ok ".env file created"
    warn "Edit .env to set your TEST_PASSWORD before running"
else
    ok ".env already exists"
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  Setup Complete!"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "  To run the AI test agent:"
echo "    export BASE_URL=${BASE_URL}"
echo "    export TEST_PASSWORD=your_password"
echo "    python ai_engine/agent.py"
echo ""
echo "  To adapt to your own project:"
echo "    1. Copy specs/TEMPLATE.md to specs/your-page.md"
echo "    2. Fill in your page's URL, selectors, flows, validations"
echo "    3. Run: python ai_engine/agent.py"
echo ""
echo "  Available AI models (more = better quality):"
ollama list 2>/dev/null | head -10
echo ""
