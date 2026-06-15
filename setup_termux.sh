#!/data/data/com.termux/files/usr/bin/bash
# ═══════════════════════════════════════════════════════════════
#  ⛓️ Onchain Bot — Termux Auto Setup
#  Run: bash setup_termux.sh
# ═══════════════════════════════════════════════════════════════

set -e

GREEN='\033[92m'
YELLOW='\033[93m'
CYAN='\033[96m'
RED='\033[91m'
BOLD='\033[1m'
DIM='\033[2m'
END='\033[0m'

banner() {
    echo ""
    echo -e "${CYAN}╔═══════════════════════════════════════════════════╗${END}"
    echo -e "${CYAN}║${BOLD}  ⛓️  Onchain Bot — Termux Setup                  ${END}${CYAN}║${END}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════╝${END}"
    echo ""
}

step() {
    echo -e "  ${CYAN}▸${END} ${BOLD}$1${END}"
}

ok() {
    echo -e "  ${GREEN}✅ $1${END}"
}

warn() {
    echo -e "  ${YELLOW}⚠️  $1${END}"
}

fail() {
    echo -e "  ${RED}❌ $1${END}"
    exit 1
}

banner

# ── Check if running in Termux ──────────────────────────────────
if [ ! -d "/data/data/com.termux" ]; then
    warn "This doesn't look like Termux, but continuing anyway..."
fi

# ── Step 1: Update packages ────────────────────────────────────
step "Updating Termux packages..."
pkg update -y && pkg upgrade -y
ok "Packages updated"

# ── Step 2: Install system dependencies ─────────────────────────
step "Installing system dependencies..."
pkg install -y \
    python \
    git \
    build-essential \
    libffi \
    openssl \
    rust \
    binutils \
    2>/dev/null || true
ok "System dependencies installed"

# ── Step 3: Upgrade pip ─────────────────────────────────────────
step "Upgrading pip..."
pip install --upgrade pip setuptools wheel 2>/dev/null
ok "pip upgraded"

# ── Step 4: Install Python packages ────────────────────────────
step "Installing web3 (this may take a few minutes)..."
echo -e "  ${DIM}Building native extensions for Termux ARM...${END}"

# Set build flags for Termux
export CFLAGS="-Wno-error"
export LDFLAGS="-L/data/data/com.termux/files/usr/lib"
export C_INCLUDE_PATH="/data/data/com.termux/files/usr/include"

pip install web3 2>&1 | tail -5
ok "web3 installed"

# ── Step 5: Verify installation ────────────────────────────────
step "Verifying installation..."
python -c "
from web3 import Web3
from eth_account import Account
print('  web3     :', Web3.__module__)
print('  account  : OK')
print('  All good!')
" || fail "web3 verification failed. Try: pip install web3 --no-cache-dir"
ok "All packages verified"

# ── Step 6: Set permissions ─────────────────────────────────────
step "Setting file permissions..."
chmod +x onchain_bot.py 2>/dev/null || true
ok "Permissions set"

# ── Done ────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════╗${END}"
echo -e "${GREEN}║  ✅ Setup complete! Ready to use.                 ║${END}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════╝${END}"
echo ""
echo -e "  Run the bot:"
echo -e "  ${BOLD}${CYAN}python onchain_bot.py${END}"
echo ""
