#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════╗
║              ONCHAIN AUTOMATION BOT v1.0                      ║
║  Auto Send · Swap · Bridge · Multi-wallet · Scheduled Tasks   ║
╚═══════════════════════════════════════════════════════════════╝

GitHub: https://github.com/Limit99/onchain-bot

Features:
  - Send native tokens (ETH/BNB/MATIC/etc) to single or multiple addresses
  - Swap tokens via Uniswap V2 compatible DEX routers
  - Bridge tokens across chains (generic bridge contract support)
  - Multi-wallet support with round-robin or random selection
  - Auto-send to random generated addresses
  - Scheduled/recurring transactions
  - Support ANY EVM chain via custom RPC (mainnet & testnet)
  - Preset value options: 0.1, 0.001, 0.0001 (in native token)

Requirements:
  pip install web3

Usage:
  python onchain_bot.py
"""

import json
import os
import sys
import time
import secrets
import threading
import traceback
from datetime import datetime
from decimal import Decimal

try:
    from web3 import Web3
    from web3.middleware import ExtraDataToPOAMiddleware
    from eth_account import Account
except ImportError:
    print("\n❌ web3 not installed. Run:\n   pip install web3\n")
    sys.exit(1)


# ═══════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════

VERSION = "1.1.0"

# ── Platform Detection ──────────────────────────────────────────
IS_TERMUX = os.path.isdir("/data/data/com.termux")
IS_ANDROID = IS_TERMUX or os.path.exists("/system/build.prop")

# Use script directory for config files (works on Termux & everywhere)
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(_SCRIPT_DIR, "onchain_config.json")
HISTORY_FILE = os.path.join(_SCRIPT_DIR, "tx_history.json")


# ═══════════════════════════════════════════════════════════════
# TERMINAL COLORS
# ═══════════════════════════════════════════════════════════════

class C:
    """ANSI color codes for terminal output."""
    R    = "\033[91m"   # Red
    G    = "\033[92m"   # Green
    Y    = "\033[93m"   # Yellow
    B    = "\033[94m"   # Blue
    M    = "\033[95m"   # Magenta
    CY   = "\033[96m"   # Cyan
    W    = "\033[97m"   # White
    DIM  = "\033[2m"    # Dim
    BOLD = "\033[1m"    # Bold
    END  = "\033[0m"    # Reset

    @staticmethod
    def disable():
        """Disable colors (for non-TTY environments)."""
        for attr in ("R", "G", "Y", "B", "M", "CY", "W", "DIM", "BOLD", "END"):
            setattr(C, attr, "")

# Disable colors if not a real terminal
if not sys.stdout.isatty():
    C.disable()

# ── Termux-safe emoji (some terminals may not render full emoji) ──
E_CHECK  = "✅" if not IS_TERMUX else "[OK]"
E_CROSS  = "❌" if not IS_TERMUX else "[ERR]"
E_WARN   = "⚠️ " if not IS_TERMUX else "[!]"
E_INFO   = "ℹ️ " if not IS_TERMUX else "[i]"
E_TX     = "📜" if not IS_TERMUX else "[TX]"


# ═══════════════════════════════════════════════════════════════
# CONTRACT ABIs (Minimal)
# ═══════════════════════════════════════════════════════════════

ROUTER_V2_ABI = json.loads("""[
    {"inputs":[{"internalType":"uint256","name":"amountOutMin","type":"uint256"},
    {"internalType":"address[]","name":"path","type":"address[]"},
    {"internalType":"address","name":"to","type":"address"},
    {"internalType":"uint256","name":"deadline","type":"uint256"}],
    "name":"swapExactETHForTokens",
    "outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],
    "stateMutability":"payable","type":"function"},

    {"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},
    {"internalType":"uint256","name":"amountOutMin","type":"uint256"},
    {"internalType":"address[]","name":"path","type":"address[]"},
    {"internalType":"address","name":"to","type":"address"},
    {"internalType":"uint256","name":"deadline","type":"uint256"}],
    "name":"swapExactTokensForETH",
    "outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],
    "stateMutability":"nonpayable","type":"function"},

    {"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},
    {"internalType":"uint256","name":"amountOutMin","type":"uint256"},
    {"internalType":"address[]","name":"path","type":"address[]"},
    {"internalType":"address","name":"to","type":"address"},
    {"internalType":"uint256","name":"deadline","type":"uint256"}],
    "name":"swapExactTokensForTokens",
    "outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],
    "stateMutability":"nonpayable","type":"function"},

    {"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},
    {"internalType":"address[]","name":"path","type":"address[]"}],
    "name":"getAmountsOut",
    "outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],
    "stateMutability":"view","type":"function"},

    {"inputs":[],"name":"WETH",
    "outputs":[{"internalType":"address","name":"","type":"address"}],
    "stateMutability":"view","type":"function"}
]""")

ERC20_ABI = json.loads("""[
    {"inputs":[{"name":"spender","type":"address"},{"name":"amount","type":"uint256"}],
    "name":"approve","outputs":[{"name":"","type":"bool"}],
    "stateMutability":"nonpayable","type":"function"},

    {"inputs":[{"name":"account","type":"address"}],
    "name":"balanceOf","outputs":[{"name":"","type":"uint256"}],
    "stateMutability":"view","type":"function"},

    {"inputs":[{"name":"owner","type":"address"},{"name":"spender","type":"address"}],
    "name":"allowance","outputs":[{"name":"","type":"uint256"}],
    "stateMutability":"view","type":"function"},

    {"inputs":[],"name":"decimals",
    "outputs":[{"name":"","type":"uint8"}],
    "stateMutability":"view","type":"function"},

    {"inputs":[],"name":"symbol",
    "outputs":[{"name":"","type":"string"}],
    "stateMutability":"view","type":"function"},

    {"inputs":[{"name":"to","type":"address"},{"name":"amount","type":"uint256"}],
    "name":"transfer","outputs":[{"name":"","type":"bool"}],
    "stateMutability":"nonpayable","type":"function"}
]""")

# Preset amounts (in native token)
VALUE_PRESETS = {
    "1": "0.1",
    "2": "0.001",
    "3": "0.0001",
}


# ═══════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def clear_screen():
    """Clear terminal screen (works on Termux, Linux, macOS, Windows)."""
    if IS_TERMUX:
        # Termux: use ANSI escape or clear
        print("\033[H\033[2J", end="", flush=True)
    else:
        os.system("cls" if os.name == "nt" else "clear")


def banner():
    """Print application banner."""
    platform_tag = f" {C.G}[Termux]{C.END}" if IS_TERMUX else ""
    print(f"""
{C.CY}╔═══════════════════════════════════════════════════════════════╗
║{C.BOLD}{C.W}              ONCHAIN AUTOMATION BOT v{VERSION}                  {C.END}{C.CY}║
║{C.DIM}  Auto Send · Swap · Bridge · Multi-wallet · Scheduler        {C.END}{C.CY}║
╚═══════════════════════════════════════════════════════════════╝{C.END}{platform_tag}
""")


def log(msg, color=C.W):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"  {C.DIM}[{ts}]{C.END} {color}{msg}{C.END}")


def log_ok(msg):    log(f"{E_CHECK} {msg}", C.G)
def log_err(msg):   log(f"{E_CROSS} {msg}", C.R)
def log_warn(msg):  log(f"{E_WARN} {msg}", C.Y)
def log_info(msg):  log(f"{E_INFO} {msg}", C.CY)


def log_tx(tx_hash, explorer=""):
    """Print transaction hash with optional explorer link."""
    if explorer:
        url = f"{explorer.rstrip('/')}/tx/{tx_hash}"
        print(f"  {C.G}{E_TX} TX: {url}{C.END}")
    else:
        print(f"  {C.G}{E_TX} TX: {tx_hash}{C.END}")


def prompt(text, default=""):
    """Prompt user for input with optional default."""
    suffix = f" [{default}]" if default else ""
    result = input(f"  {C.Y}▸ {text}{suffix}: {C.END}").strip()
    return result if result else default


def confirm(text):
    """Ask user for yes/no confirmation."""
    r = input(f"  {C.Y}▸ {text} (y/n): {C.END}").strip().lower()
    return r in ("y", "yes")


def menu_select(title, options):
    """Display a numbered menu and return the user's choice."""
    print(f"\n  {C.BOLD}{C.CY}{title}{C.END}")
    print(f"  {C.DIM}{'─' * 45}{C.END}")
    for key, label in options:
        print(f"  {C.W}  [{C.CY}{key}{C.W}] {label}{C.END}")
    print(f"  {C.DIM}{'─' * 45}{C.END}")
    return input(f"  {C.Y}▸ Choose: {C.END}").strip()


def short_addr(addr):
    """Shorten an Ethereum address for display."""
    if not addr or len(addr) < 10:
        return addr or "?"
    return f"{addr[:6]}...{addr[-4:]}"


def generate_random_address():
    """Generate a cryptographically random Ethereum address."""
    private_key = "0x" + secrets.token_hex(32)
    acct = Account.from_key(private_key)
    return acct.address


# ═══════════════════════════════════════════════════════════════
# CONFIGURATION MANAGER
# ═══════════════════════════════════════════════════════════════

class Config:
    """Manages persistent configuration (chains, wallets, tokens, etc.)."""

    DEFAULT = {
        "chains": {},
        "wallets": [],
        "tokens": {},
        "dex_routers": {},
        "bridge_contracts": {},
    }

    def __init__(self, path=CONFIG_FILE):
        self.path = path
        self.data = dict(self.DEFAULT)
        self.load()

    def load(self):
        if os.path.exists(self.path):
            with open(self.path, "r") as f:
                saved = json.load(f)
            # Merge with defaults so new keys are always present
            for k, v in self.DEFAULT.items():
                self.data[k] = saved.get(k, v)
            log_ok(f"Config loaded ({self.path})")
        else:
            log_info("No config found — starting fresh.")

    def save(self):
        with open(self.path, "w") as f:
            json.dump(self.data, f, indent=2)

    # ── Chains ──────────────────────────────────────────────────

    def add_chain(self, name, rpc_url, chain_id, symbol, explorer="", network_type="mainnet"):
        self.data["chains"][name] = {
            "rpc": rpc_url,
            "chain_id": int(chain_id),
            "symbol": symbol.upper(),
            "explorer": explorer.rstrip("/"),
            "type": network_type,
        }
        self.save()

    def get_chains(self):
        return self.data.get("chains", {})

    def remove_chain(self, name):
        self.data["chains"].pop(name, None)
        self.save()

    # ── Wallets ─────────────────────────────────────────────────

    def add_wallet(self, name, address, private_key):
        self.data["wallets"].append({
            "name": name,
            "address": Web3.to_checksum_address(address),
            "private_key": private_key,
        })
        self.save()

    def get_wallets(self):
        return self.data.get("wallets", [])

    def remove_wallet(self, index):
        if 0 <= index < len(self.data["wallets"]):
            self.data["wallets"].pop(index)
            self.save()

    # ── DEX Routers ─────────────────────────────────────────────

    def add_dex_router(self, chain_name, router_name, router_address, weth_address=""):
        if chain_name not in self.data["dex_routers"]:
            self.data["dex_routers"][chain_name] = {}
        self.data["dex_routers"][chain_name][router_name] = {
            "address": Web3.to_checksum_address(router_address),
            "weth": Web3.to_checksum_address(weth_address) if weth_address else "",
        }
        self.save()

    def get_dex_routers(self, chain_name):
        return self.data.get("dex_routers", {}).get(chain_name, {})

    # ── Tokens ──────────────────────────────────────────────────

    def add_token(self, chain_name, symbol, address, decimals=18):
        if chain_name not in self.data["tokens"]:
            self.data["tokens"][chain_name] = {}
        self.data["tokens"][chain_name][symbol.upper()] = {
            "address": Web3.to_checksum_address(address),
            "decimals": int(decimals),
        }
        self.save()

    def get_tokens(self, chain_name):
        return self.data.get("tokens", {}).get(chain_name, {})

    # ── Bridge Contracts ────────────────────────────────────────

    def add_bridge(self, name, chain_from, chain_to, contract_address):
        self.data["bridge_contracts"][name] = {
            "from_chain": chain_from,
            "to_chain": chain_to,
            "contract": Web3.to_checksum_address(contract_address),
        }
        self.save()

    def get_bridges(self):
        return self.data.get("bridge_contracts", {})


# ═══════════════════════════════════════════════════════════════
# BLOCKCHAIN ENGINE
# ═══════════════════════════════════════════════════════════════

class BlockchainEngine:
    """Core engine for all on-chain interactions."""

    def __init__(self, config: Config):
        self.config = config
        self.w3: Web3 | None = None
        self.current_chain: str | None = None
        self.tx_history: list = []
        self._load_history()

    # ── History ─────────────────────────────────────────────────

    def _load_history(self):
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r") as f:
                    self.tx_history = json.load(f)
            except json.JSONDecodeError:
                self.tx_history = []

    def _save_history(self, tx_data):
        self.tx_history.append(tx_data)
        with open(HISTORY_FILE, "w") as f:
            json.dump(self.tx_history, f, indent=2)

    # ── Connection ──────────────────────────────────────────────

    def connect(self, chain_name):
        """Connect to an EVM chain via its configured RPC."""
        chains = self.config.get_chains()
        if chain_name not in chains:
            log_err(f"Chain '{chain_name}' not found in config")
            return False

        chain = chains[chain_name]
        try:
            self.w3 = Web3(Web3.HTTPProvider(chain["rpc"], request_kwargs={"timeout": 30}))
            # POA middleware for BSC, Polygon, Avalanche, etc.
            self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

            if self.w3.is_connected():
                self.current_chain = chain_name
                block = self.w3.eth.block_number
                log_ok(f"Connected to {chain_name} (Chain ID: {chain['chain_id']}, Block: #{block:,})")
                return True
            else:
                log_err(f"Cannot connect to {chain_name} RPC: {chain['rpc']}")
                return False
        except Exception as e:
            log_err(f"Connection error: {e}")
            return False

    # ── Balances ────────────────────────────────────────────────

    def get_balance(self, address):
        """Get native token balance in ether."""
        bal_wei = self.w3.eth.get_balance(Web3.to_checksum_address(address))
        return self.w3.from_wei(bal_wei, "ether")

    def get_token_balance(self, token_address, wallet_address):
        """Get ERC-20 token balance."""
        contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(token_address), abi=ERC20_ABI
        )
        raw = contract.functions.balanceOf(Web3.to_checksum_address(wallet_address)).call()
        decimals = contract.functions.decimals().call()
        return Decimal(raw) / Decimal(10 ** decimals)

    # ── TX Builder ──────────────────────────────────────────────

    def _chain_info(self):
        return self.config.get_chains().get(self.current_chain, {})

    def _build_and_send(self, tx, private_key, wallet_address):
        """Sign, broadcast, and wait for a transaction receipt."""
        info = self._chain_info()
        addr = Web3.to_checksum_address(wallet_address)

        # Nonce
        tx["nonce"] = self.w3.eth.get_transaction_count(addr)
        tx["chainId"] = info["chain_id"]

        # Gas estimate (with 20 % safety buffer)
        if "gas" not in tx:
            try:
                tx["gas"] = int(self.w3.eth.estimate_gas(tx) * 1.2)
            except Exception as e:
                log_warn(f"Gas estimation failed ({e}), using 150 000")
                tx["gas"] = 150_000

        # Gas pricing — try EIP-1559 first, fall back to legacy
        try:
            base_fee = self.w3.eth.get_block("latest").get("baseFeePerGas")
            if base_fee:
                priority = self.w3.eth.max_priority_fee
                tx["maxFeePerGas"] = base_fee * 2 + priority
                tx["maxPriorityFeePerGas"] = priority
                tx.pop("gasPrice", None)
            else:
                raise ValueError("no baseFee")
        except Exception:
            tx["gasPrice"] = self.w3.eth.gas_price
            tx.pop("maxFeePerGas", None)
            tx.pop("maxPriorityFeePerGas", None)

        # Remove internal keys before signing
        tx_type = tx.pop("_type", "unknown")

        # Sign + send
        signed = self.w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction).hex()

        log_info(f"TX sent: {tx_hash}")
        log_info("Waiting for confirmation…")

        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
        explorer = info.get("explorer", "")

        if receipt.status == 1:
            log_ok(f"Confirmed in block #{receipt.blockNumber:,} (gas used: {receipt.gasUsed:,})")
        else:
            log_err(f"TX reverted in block #{receipt.blockNumber:,}")
        log_tx(tx_hash, explorer)

        # Record
        self._save_history({
            "timestamp": datetime.now().isoformat(),
            "chain": self.current_chain,
            "type": tx_type,
            "from": wallet_address,
            "to": tx.get("to", ""),
            "value": str(tx.get("value", 0)),
            "tx_hash": tx_hash,
            "status": "success" if receipt.status == 1 else "failed",
            "block": receipt.blockNumber,
            "gas_used": receipt.gasUsed,
        })
        return receipt

    # ── Send Native Token ───────────────────────────────────────

    def send_native(self, wallet, to_address, amount_ether):
        """Send native token to a single address."""
        info = self._chain_info()
        amount_wei = self.w3.to_wei(Decimal(str(amount_ether)), "ether")

        log_info(f"Sending {amount_ether} {info['symbol']} → {short_addr(to_address)}")
        tx = {
            "from": Web3.to_checksum_address(wallet["address"]),
            "to": Web3.to_checksum_address(to_address),
            "value": amount_wei,
            "_type": "send_native",
        }
        return self._build_and_send(tx, wallet["private_key"], wallet["address"])

    def multi_send(self, wallets, addresses, amount_ether, delay_sec=2, wallet_mode="round-robin"):
        """Send to a list of addresses using one or more wallets."""
        results = []
        n_wallets = len(wallets)

        for i, addr in enumerate(addresses):
            # Select wallet
            if wallet_mode == "random":
                wallet = wallets[secrets.randbelow(n_wallets)]
            else:  # round-robin or single
                wallet = wallets[i % n_wallets]

            log_info(f"[{i+1}/{len(addresses)}] {short_addr(wallet['address'])} → {short_addr(addr)}")
            try:
                receipt = self.send_native(wallet, addr, amount_ether)
                results.append({"to": addr, "status": "success", "tx": receipt.transactionHash.hex()})
            except Exception as e:
                log_err(f"Failed: {e}")
                results.append({"to": addr, "status": "failed", "error": str(e)})

            if i < len(addresses) - 1 and delay_sec > 0:
                log_info(f"Waiting {delay_sec}s…")
                time.sleep(delay_sec)

        return results

    def send_to_random(self, wallets, count, amount_ether, delay_sec=2, wallet_mode="round-robin"):
        """Generate N random addresses and send to each."""
        addresses = [generate_random_address() for _ in range(count)]
        log_info(f"Generated {count} random addresses:")
        for i, a in enumerate(addresses, 1):
            print(f"    {C.DIM}{i:>3}. {a}{C.END}")
        print()
        return self.multi_send(wallets, addresses, amount_ether, delay_sec, wallet_mode)

    # ── Swap (Uniswap V2 Compatible) ───────────────────────────

    def _get_router(self, router_address):
        return self.w3.eth.contract(
            address=Web3.to_checksum_address(router_address), abi=ROUTER_V2_ABI
        )

    def _approve_if_needed(self, token_address, spender, wallet, amount_raw):
        """Check ERC-20 allowance and approve if insufficient."""
        token = self.w3.eth.contract(address=Web3.to_checksum_address(token_address), abi=ERC20_ABI)
        allowance = token.functions.allowance(
            Web3.to_checksum_address(wallet["address"]),
            Web3.to_checksum_address(spender),
        ).call()
        if allowance < amount_raw:
            symbol = token.functions.symbol().call()
            log_info(f"Approving {symbol} for router…")
            tx = token.functions.approve(
                Web3.to_checksum_address(spender), 2**256 - 1
            ).build_transaction({"from": Web3.to_checksum_address(wallet["address"])})
            tx["_type"] = "approve"
            self._build_and_send(tx, wallet["private_key"], wallet["address"])

    def swap_native_to_token(self, wallet, router_address, token_address, amount_ether, slippage=5):
        """Swap native → ERC-20 via a Uniswap V2-compatible router."""
        info = self._chain_info()
        router = self._get_router(router_address)
        weth = router.functions.WETH().call()
        amount_in = self.w3.to_wei(Decimal(str(amount_ether)), "ether")
        path = [weth, Web3.to_checksum_address(token_address)]

        amounts = router.functions.getAmountsOut(amount_in, path).call()
        min_out = int(amounts[-1] * (100 - slippage) / 100)
        deadline = int(time.time()) + 300

        log_info(f"Swapping {amount_ether} {info['symbol']} → token")
        log_info(f"Expected: {amounts[-1]} | Min (slippage {slippage}%): {min_out}")

        tx = router.functions.swapExactETHForTokens(
            min_out, path, Web3.to_checksum_address(wallet["address"]), deadline
        ).build_transaction({
            "from": Web3.to_checksum_address(wallet["address"]),
            "value": amount_in,
        })
        tx["_type"] = "swap_native_to_token"
        return self._build_and_send(tx, wallet["private_key"], wallet["address"])

    def swap_token_to_native(self, wallet, router_address, token_address, amount, slippage=5):
        """Swap ERC-20 → native via a Uniswap V2-compatible router."""
        info = self._chain_info()
        router = self._get_router(router_address)
        token = self.w3.eth.contract(address=Web3.to_checksum_address(token_address), abi=ERC20_ABI)

        decimals = token.functions.decimals().call()
        symbol = token.functions.symbol().call()
        amount_raw = int(Decimal(str(amount)) * Decimal(10 ** decimals))
        weth = router.functions.WETH().call()
        path = [Web3.to_checksum_address(token_address), weth]

        self._approve_if_needed(token_address, router_address, wallet, amount_raw)

        amounts = router.functions.getAmountsOut(amount_raw, path).call()
        min_out = int(amounts[-1] * (100 - slippage) / 100)
        deadline = int(time.time()) + 300

        log_info(f"Swapping {amount} {symbol} → {info['symbol']}")

        tx = router.functions.swapExactTokensForETH(
            amount_raw, min_out, path,
            Web3.to_checksum_address(wallet["address"]), deadline
        ).build_transaction({"from": Web3.to_checksum_address(wallet["address"])})
        tx["_type"] = "swap_token_to_native"
        return self._build_and_send(tx, wallet["private_key"], wallet["address"])

    def swap_token_to_token(self, wallet, router_address, token_in, token_out, amount, slippage=5):
        """Swap ERC-20 → ERC-20 via a Uniswap V2-compatible router."""
        router = self._get_router(router_address)
        tok_in = self.w3.eth.contract(address=Web3.to_checksum_address(token_in), abi=ERC20_ABI)

        decimals = tok_in.functions.decimals().call()
        symbol = tok_in.functions.symbol().call()
        amount_raw = int(Decimal(str(amount)) * Decimal(10 ** decimals))
        weth = router.functions.WETH().call()
        path = [Web3.to_checksum_address(token_in), weth, Web3.to_checksum_address(token_out)]

        self._approve_if_needed(token_in, router_address, wallet, amount_raw)

        amounts = router.functions.getAmountsOut(amount_raw, path).call()
        min_out = int(amounts[-1] * (100 - slippage) / 100)
        deadline = int(time.time()) + 300

        log_info(f"Swapping {amount} {symbol} → token")

        tx = router.functions.swapExactTokensForTokens(
            amount_raw, min_out, path,
            Web3.to_checksum_address(wallet["address"]), deadline
        ).build_transaction({"from": Web3.to_checksum_address(wallet["address"])})
        tx["_type"] = "swap_token_to_token"
        return self._build_and_send(tx, wallet["private_key"], wallet["address"])

    # ── Bridge (Generic) ────────────────────────────────────────

    def bridge_native(self, wallet, bridge_contract, dest_chain_id, amount_ether):
        """
        Bridge native token via a generic bridge contract.

        ⚠️  Bridge ABIs vary widely. This implementation sends native value
        with a generic `bridge(uint256, address)` calldata. You may need to
        adjust the calldata encoding for your specific bridge protocol
        (Stargate, Hop, Across, LayerZero, etc.).
        """
        info = self._chain_info()
        amount_wei = self.w3.to_wei(Decimal(str(amount_ether)), "ether")

        # Generic calldata: bridge(destChainId, recipient)
        selector = Web3.keccak(text="bridge(uint256,address)")[:4]
        data = (
            selector
            + int(dest_chain_id).to_bytes(32, "big")
            + bytes.fromhex(wallet["address"][2:].zfill(64))
        )

        log_info(f"Bridging {amount_ether} {info['symbol']} → chain {dest_chain_id}")

        tx = {
            "from": Web3.to_checksum_address(wallet["address"]),
            "to": Web3.to_checksum_address(bridge_contract),
            "value": amount_wei,
            "data": "0x" + data.hex(),
            "_type": "bridge",
        }
        return self._build_and_send(tx, wallet["private_key"], wallet["address"])


# ═══════════════════════════════════════════════════════════════
# TASK SCHEDULER
# ═══════════════════════════════════════════════════════════════

class Scheduler:
    """Background task scheduler for recurring transactions."""

    def __init__(self):
        self.tasks: list[dict] = []
        self._running = False
        self._thread: threading.Thread | None = None

    def add(self, name, func, interval_sec, *args, **kwargs):
        self.tasks.append({
            "name": name,
            "func": func,
            "interval": interval_sec,
            "args": args,
            "kwargs": kwargs,
            "next_run": time.time(),
            "active": True,
        })
        log_ok(f"Scheduled: '{name}' every {interval_sec}s")

    def remove(self, index):
        if 0 <= index < len(self.tasks):
            t = self.tasks.pop(index)
            log_ok(f"Removed: '{t['name']}'")

    def start(self):
        if not self.tasks:
            log_warn("No tasks to run")
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        log_ok("Scheduler started in background")

    def stop(self):
        self._running = False
        log_ok("Scheduler stopped")

    def show(self):
        if not self.tasks:
            log_info("No scheduled tasks")
            return
        print(f"\n  {C.BOLD}Scheduled Tasks:{C.END}")
        for i, t in enumerate(self.tasks):
            st = f"{C.G}active{C.END}" if t["active"] else f"{C.R}paused{C.END}"
            print(f"    {i+1}. {t['name']} — every {t['interval']}s — {st}")

    def _loop(self):
        while self._running:
            now = time.time()
            for t in self.tasks:
                if t["active"] and now >= t["next_run"]:
                    log_info(f"[Scheduler] Running: {t['name']}")
                    try:
                        t["func"](*t["args"], **t["kwargs"])
                    except Exception as e:
                        log_err(f"[Scheduler] '{t['name']}' failed: {e}")
                    t["next_run"] = now + t["interval"]
            time.sleep(1)


# ═══════════════════════════════════════════════════════════════
# INTERACTIVE CLI
# ═══════════════════════════════════════════════════════════════

class CLI:
    """Interactive command-line interface."""

    def __init__(self):
        self.config = Config()
        self.engine = BlockchainEngine(self.config)
        self.scheduler = Scheduler()

    # ── Main Loop ───────────────────────────────────────────────

    def run(self):
        clear_screen()
        banner()

        while True:
            choice = menu_select("MAIN MENU", [
                ("1", "⚙️  Setup & Configuration"),
                ("2", "💸 Send Native Token"),
                ("3", "📤 Multi-Send (Batch)"),
                ("4", "🎲 Send to Random Addresses"),
                ("5", "🔄 Swap Tokens (DEX)"),
                ("6", "🌉 Bridge Tokens"),
                ("7", "⏰ Scheduled Tasks"),
                ("8", "💰 Check Balances"),
                ("9", "📜 Transaction History"),
                ("0", "🚪 Exit"),
            ])

            try:
                actions = {
                    "1": self._menu_setup,
                    "2": self._menu_send,
                    "3": self._menu_multi_send,
                    "4": self._menu_send_random,
                    "5": self._menu_swap,
                    "6": self._menu_bridge,
                    "7": self._menu_scheduler,
                    "8": self._menu_balances,
                    "9": self._menu_history,
                }
                if choice == "0":
                    self.scheduler.stop()
                    log_info("Goodbye! 👋")
                    break
                elif choice in actions:
                    actions[choice]()
            except KeyboardInterrupt:
                print()
                log_warn("Interrupted — returning to menu")
            except Exception as e:
                log_err(f"Error: {e}")
                if os.environ.get("DEBUG"):
                    traceback.print_exc()

    # ── Shared Selectors ────────────────────────────────────────

    def _select_chain(self):
        chains = self.config.get_chains()
        if not chains:
            log_warn("No chains configured! Go to Setup → Add Chain first.")
            return None
        self._print_chains()
        name = prompt("Select chain")
        if name not in chains:
            log_err(f"Chain '{name}' not found")
            return None
        if not self.engine.connect(name):
            return None
        return name

    def _select_wallet(self, allow_multi=False):
        wallets = self.config.get_wallets()
        if not wallets:
            log_warn("No wallets configured! Go to Setup → Add Wallet first.")
            return None
        self._print_wallets()
        if allow_multi:
            choice = prompt("Select wallet (number, 'all', or 'random')")
            if choice.lower() == "all":
                return wallets, "round-robin"
            elif choice.lower() == "random":
                return wallets, "random"
            idx = int(choice) - 1
            return [wallets[idx]], "single"
        else:
            idx = int(prompt("Select wallet number")) - 1
            return wallets[idx]

    def _select_amount(self):
        choice = menu_select("Amount (native token)", [
            ("1", "0.1"),
            ("2", "0.001"),
            ("3", "0.0001"),
            ("4", "Custom"),
        ])
        if choice in VALUE_PRESETS:
            return VALUE_PRESETS[choice]
        elif choice == "4":
            return prompt("Enter amount")
        return None

    # ── Printers ────────────────────────────────────────────────

    def _print_chains(self):
        chains = self.config.get_chains()
        print(f"\n  {C.BOLD}Chains:{C.END}")
        for name, c in chains.items():
            net = f"{C.G}mainnet{C.END}" if c["type"] == "mainnet" else f"{C.Y}testnet{C.END}"
            print(f"    • {C.CY}{name}{C.END} ({c['symbol']}) — ID {c['chain_id']} — {net}")

    def _print_wallets(self):
        wallets = self.config.get_wallets()
        print(f"\n  {C.BOLD}Wallets:{C.END}")
        for i, w in enumerate(wallets, 1):
            print(f"    {i}. {C.CY}{w['name']}{C.END} — {short_addr(w['address'])}")

    # ── Setup Menu ──────────────────────────────────────────────

    def _menu_setup(self):
        while True:
            choice = menu_select("⚙️  SETUP", [
                ("1", "Add Chain (RPC)"),
                ("2", "Add Wallet"),
                ("3", "Add DEX Router"),
                ("4", "Add Token"),
                ("5", "Add Bridge Contract"),
                ("6", "View All Config"),
                ("7", "Remove Chain"),
                ("8", "Remove Wallet"),
                ("0", "← Back"),
            ])
            if choice == "0":
                break

            elif choice == "1":
                name       = prompt("Chain name (e.g. ethereum, bsc-testnet)")
                rpc        = prompt("RPC URL")
                chain_id   = prompt("Chain ID (e.g. 1, 56, 421614)")
                symbol     = prompt("Native symbol (e.g. ETH, BNB)")
                explorer   = prompt("Explorer URL (optional)", "")
                net_type   = prompt("Type (mainnet/testnet)", "mainnet")
                self.config.add_chain(name, rpc, chain_id, symbol, explorer, net_type)
                log_ok(f"Chain '{name}' added!")

            elif choice == "2":
                label   = prompt("Wallet label (e.g. main, hot1)")
                address = prompt("Address (0x…)")
                pk      = prompt("Private key")
                try:
                    self.config.add_wallet(label, address, pk)
                    log_ok(f"Wallet '{label}' added!")
                except Exception as e:
                    log_err(f"Invalid wallet: {e}")

            elif choice == "3":
                if not self.config.get_chains():
                    log_warn("Add a chain first!"); continue
                self._print_chains()
                chain = prompt("Chain name")
                name  = prompt("DEX name (e.g. uniswap-v2, pancakeswap)")
                addr  = prompt("Router contract address")
                weth  = prompt("WETH address (optional, auto-detect if empty)", "")
                self.config.add_dex_router(chain, name, addr, weth)
                log_ok(f"DEX '{name}' added on {chain}!")

            elif choice == "4":
                if not self.config.get_chains():
                    log_warn("Add a chain first!"); continue
                self._print_chains()
                chain = prompt("Chain name")
                sym   = prompt("Token symbol (e.g. USDC)")
                addr  = prompt("Token contract address")
                dec   = prompt("Decimals", "18")
                self.config.add_token(chain, sym, addr, dec)
                log_ok(f"Token '{sym}' added on {chain}!")

            elif choice == "5":
                name   = prompt("Bridge name (e.g. stargate, hop)")
                cfrom  = prompt("Source chain")
                cto    = prompt("Destination chain")
                addr   = prompt("Bridge contract address")
                self.config.add_bridge(name, cfrom, cto, addr)
                log_ok(f"Bridge '{name}' added!")

            elif choice == "6":
                self._print_full_config()

            elif choice == "7":
                self._print_chains()
                n = prompt("Chain name to remove")
                self.config.remove_chain(n)
                log_ok(f"'{n}' removed!")

            elif choice == "8":
                self._print_wallets()
                idx = int(prompt("Wallet # to remove")) - 1
                self.config.remove_wallet(idx)
                log_ok("Wallet removed!")

    def _print_full_config(self):
        print(f"\n  {'═' * 55}")
        self._print_chains()
        self._print_wallets()
        routers = self.config.data.get("dex_routers", {})
        if routers:
            print(f"\n  {C.BOLD}DEX Routers:{C.END}")
            for ch, dexes in routers.items():
                for nm, info in dexes.items():
                    print(f"    • {C.CY}{ch}/{nm}{C.END} — {short_addr(info['address'])}")
        tokens = self.config.data.get("tokens", {})
        if tokens:
            print(f"\n  {C.BOLD}Tokens:{C.END}")
            for ch, toks in tokens.items():
                for sym, info in toks.items():
                    print(f"    • {C.CY}{ch}/{sym}{C.END} — {short_addr(info['address'])} ({info['decimals']}d)")
        bridges = self.config.get_bridges()
        if bridges:
            print(f"\n  {C.BOLD}Bridges:{C.END}")
            for nm, info in bridges.items():
                print(f"    • {C.CY}{nm}{C.END} — {info['from_chain']} → {info['to_chain']}")
        print(f"  {'═' * 55}")

    # ── Send ────────────────────────────────────────────────────

    def _menu_send(self):
        chain = self._select_chain()
        if not chain: return
        wallet = self._select_wallet()
        if not wallet: return
        to = prompt("Recipient address (0x…)")
        amount = self._select_amount()
        if not amount: return

        info = self.config.get_chains()[chain]
        print(f"\n  {C.BOLD}Transaction Preview:{C.END}")
        print(f"    Chain : {C.CY}{chain}{C.END}")
        print(f"    From  : {short_addr(wallet['address'])}")
        print(f"    To    : {short_addr(to)}")
        print(f"    Value : {C.G}{amount} {info['symbol']}{C.END}")
        if confirm("Confirm & send?"):
            self.engine.send_native(wallet, to, amount)

    # ── Multi-Send ──────────────────────────────────────────────

    def _menu_multi_send(self):
        chain = self._select_chain()
        if not chain: return
        result = self._select_wallet(allow_multi=True)
        if not result: return
        wallets, mode = result

        print(f"\n  {C.BOLD}Enter recipient addresses (blank line to finish):{C.END}")
        addresses = []
        while True:
            a = prompt(f"#{len(addresses)+1}")
            if not a: break
            addresses.append(a)
        if not addresses:
            log_warn("No addresses entered"); return

        amount = self._select_amount()
        if not amount: return
        delay = int(prompt("Delay between TXs (sec)", "3"))

        info = self.config.get_chains()[chain]
        total = Decimal(amount) * len(addresses)
        print(f"\n  {C.BOLD}Batch Summary:{C.END}")
        print(f"    Chain      : {C.CY}{chain}{C.END}")
        print(f"    Wallets    : {len(wallets)} ({mode})")
        print(f"    Recipients : {len(addresses)}")
        print(f"    Each       : {C.G}{amount} {info['symbol']}{C.END}")
        print(f"    Total      : {C.G}{total} {info['symbol']}{C.END}")
        print(f"    Delay      : {delay}s between TXs")

        if confirm("Execute batch send?"):
            results = self.engine.multi_send(wallets, addresses, amount, delay, mode)
            ok = sum(1 for r in results if r["status"] == "success")
            log_ok(f"Done: {ok}/{len(results)} succeeded")

    # ── Random Send ─────────────────────────────────────────────

    def _menu_send_random(self):
        chain = self._select_chain()
        if not chain: return
        result = self._select_wallet(allow_multi=True)
        if not result: return
        wallets, mode = result

        count  = int(prompt("Number of random addresses", "5"))
        amount = self._select_amount()
        if not amount: return
        delay  = int(prompt("Delay between TXs (sec)", "3"))

        info = self.config.get_chains()[chain]
        total = Decimal(amount) * count
        print(f"\n  {C.BOLD}Random Send Summary:{C.END}")
        print(f"    Chain      : {C.CY}{chain}{C.END}")
        print(f"    Wallets    : {len(wallets)} ({mode})")
        print(f"    Count      : {count}")
        print(f"    Each       : {C.G}{amount} {info['symbol']}{C.END}")
        print(f"    Total      : {C.G}{total} {info['symbol']}{C.END}")

        if confirm("Execute random send?"):
            results = self.engine.send_to_random(wallets, count, amount, delay, mode)
            ok = sum(1 for r in results if r["status"] == "success")
            log_ok(f"Done: {ok}/{len(results)} succeeded")

    # ── Swap ────────────────────────────────────────────────────

    def _menu_swap(self):
        chain = self._select_chain()
        if not chain: return
        routers = self.config.get_dex_routers(chain)
        if not routers:
            log_warn(f"No DEX router on {chain}. Add one in Setup."); return
        wallet = self._select_wallet()
        if not wallet: return

        # Pick router
        r_list = list(routers.items())
        print(f"\n  {C.BOLD}DEX Routers:{C.END}")
        for i, (n, info) in enumerate(r_list, 1):
            print(f"    {i}. {C.CY}{n}{C.END} — {short_addr(info['address'])}")
        ri = int(prompt("Select router")) - 1
        _, rinfo = r_list[ri]

        stype = menu_select("Swap Direction", [
            ("1", "Native → Token"),
            ("2", "Token → Native"),
            ("3", "Token → Token"),
            ("0", "← Back"),
        ])
        if stype == "0": return

        slippage = float(prompt("Slippage %", "5"))
        tokens = self.config.get_tokens(chain)

        def pick_token(label="token"):
            if tokens:
                t_list = list(tokens.items())
                print(f"\n  {C.BOLD}Tokens:{C.END}")
                for i, (s, inf) in enumerate(t_list, 1):
                    print(f"    {i}. {C.CY}{s}{C.END} — {short_addr(inf['address'])}")
                print(f"    {len(t_list)+1}. Enter address manually")
                c = int(prompt(f"Select {label}")) - 1
                if c < len(t_list):
                    return t_list[c][1]["address"]
            return prompt(f"{label} address")

        if stype == "1":
            token = pick_token("token to buy")
            amount = self._select_amount()
            if not amount: return
            if confirm(f"Swap {amount} native → token?"):
                self.engine.swap_native_to_token(wallet, rinfo["address"], token, amount, slippage)

        elif stype == "2":
            token = pick_token("token to sell")
            amount = prompt("Amount to sell")
            if confirm(f"Swap {amount} token → native?"):
                self.engine.swap_token_to_native(wallet, rinfo["address"], token, amount, slippage)

        elif stype == "3":
            t_in  = pick_token("token to sell")
            t_out = pick_token("token to buy")
            amount = prompt("Amount to sell")
            if confirm(f"Swap {amount} token → token?"):
                self.engine.swap_token_to_token(wallet, rinfo["address"], t_in, t_out, amount, slippage)

    # ── Bridge ──────────────────────────────────────────────────

    def _menu_bridge(self):
        bridges = self.config.get_bridges()
        if not bridges:
            log_warn("No bridges configured. Add one in Setup."); return

        b_list = list(bridges.items())
        print(f"\n  {C.BOLD}Bridges:{C.END}")
        for i, (n, info) in enumerate(b_list, 1):
            print(f"    {i}. {C.CY}{n}{C.END} — {info['from_chain']} → {info['to_chain']}")
        bi = int(prompt("Select bridge")) - 1
        bname, binfo = b_list[bi]

        if not self.engine.connect(binfo["from_chain"]):
            return
        wallet = self._select_wallet()
        if not wallet: return
        amount = self._select_amount()
        if not amount: return

        dest = self.config.get_chains().get(binfo["to_chain"], {})
        dest_id = dest.get("chain_id") or prompt("Destination chain ID")

        print(f"\n  {C.BOLD}Bridge Preview:{C.END}")
        print(f"    Bridge : {C.CY}{bname}{C.END}")
        print(f"    Route  : {binfo['from_chain']} → {binfo['to_chain']}")
        print(f"    Amount : {C.G}{amount}{C.END}")
        log_warn("Bridge ABIs vary! Make sure the contract matches the generic interface.")

        if confirm("Execute bridge?"):
            self.engine.bridge_native(wallet, binfo["contract"], dest_id, amount)

    # ── Scheduler ───────────────────────────────────────────────

    def _menu_scheduler(self):
        while True:
            self.scheduler.show()
            choice = menu_select("⏰ SCHEDULER", [
                ("1", "Schedule Recurring Send"),
                ("2", "Schedule Recurring Swap"),
                ("3", "▶ Start Scheduler"),
                ("4", "⏹ Stop Scheduler"),
                ("5", "Remove Task"),
                ("0", "← Back"),
            ])
            if choice == "0": break

            elif choice == "1":
                chain = self._select_chain()
                if not chain: continue
                result = self._select_wallet(allow_multi=True)
                if not result: continue
                wallets, mode = result

                target = menu_select("Send to", [
                    ("1", "Specific address(es)"),
                    ("2", "Random addresses each run"),
                ])
                if target == "1":
                    addrs = []
                    while True:
                        a = prompt(f"Address #{len(addrs)+1} (blank to finish)")
                        if not a: break
                        addrs.append(a)
                    if not addrs: continue
                else:
                    addrs = None
                    n_random = int(prompt("Random addresses per run", "3"))

                amount   = self._select_amount()
                if not amount: continue
                interval = int(prompt("Interval (seconds)", "3600"))
                name     = prompt("Task name", f"send-{chain}")

                if addrs:
                    self.scheduler.add(name,
                        lambda w=wallets, a=addrs, am=amount, m=mode:
                            self.engine.multi_send(w, a, am, 2, m),
                        interval)
                else:
                    self.scheduler.add(name,
                        lambda w=wallets, c=n_random, am=amount, m=mode:
                            self.engine.send_to_random(w, c, am, 2, m),
                        interval)

            elif choice == "2":
                chain = self._select_chain()
                if not chain: continue
                routers = self.config.get_dex_routers(chain)
                if not routers:
                    log_warn(f"No DEX on {chain}"); continue
                wallet = self._select_wallet()
                if not wallet: continue

                r_list = list(routers.items())
                for i, (n, info) in enumerate(r_list, 1):
                    print(f"    {i}. {n}")
                ri = int(prompt("Select router")) - 1
                rinfo = r_list[ri][1]

                token    = prompt("Token address to buy")
                amount   = self._select_amount()
                if not amount: continue
                slippage = float(prompt("Slippage %", "5"))
                interval = int(prompt("Interval (seconds)", "3600"))
                name     = prompt("Task name", f"swap-{chain}")

                self.scheduler.add(name,
                    lambda w=wallet, r=rinfo["address"], t=token, a=amount, s=slippage:
                        self.engine.swap_native_to_token(w, r, t, a, s),
                    interval)

            elif choice == "3":
                self.scheduler.start()

            elif choice == "4":
                self.scheduler.stop()

            elif choice == "5":
                self.scheduler.show()
                idx = int(prompt("Task # to remove")) - 1
                self.scheduler.remove(idx)

    # ── Balances ────────────────────────────────────────────────

    def _menu_balances(self):
        chain = self._select_chain()
        if not chain: return
        wallets = self.config.get_wallets()
        if not wallets:
            log_warn("No wallets configured!"); return

        info   = self.config.get_chains()[chain]
        tokens = self.config.get_tokens(chain)

        print(f"\n  {'═' * 55}")
        print(f"  {C.BOLD}Balances on {C.CY}{chain}{C.END}")
        print(f"  {'═' * 55}")

        for w in wallets:
            bal = self.engine.get_balance(w["address"])
            print(f"\n  {C.BOLD}{w['name']}{C.END} ({short_addr(w['address'])})")
            print(f"    {info['symbol']:>8}: {C.G}{bal:.8f}{C.END}")
            for sym, tok in tokens.items():
                try:
                    tb = self.engine.get_token_balance(tok["address"], w["address"])
                    print(f"    {sym:>8}: {C.G}{tb:.6f}{C.END}")
                except Exception:
                    print(f"    {sym:>8}: {C.R}error{C.END}")

        print(f"\n  {'═' * 55}")

    # ── History ─────────────────────────────────────────────────

    def _menu_history(self):
        h = self.engine.tx_history
        if not h:
            log_info("No transactions yet"); return

        n = min(20, len(h))
        print(f"\n  {C.BOLD}Last {n} Transactions:{C.END}")
        print(f"  {'─' * 72}")
        for tx in h[-n:]:
            st = f"{C.G}✓{C.END}" if tx.get("status") == "success" else f"{C.R}✗{C.END}"
            ts = tx.get("timestamp", "")[:19]
            print(f"  {st} {C.DIM}{ts}{C.END} [{C.CY}{tx.get('chain','?')}{C.END}] "
                  f"{tx.get('type','?')}  {short_addr(tx.get('from',''))} → {short_addr(tx.get('to',''))}")
            print(f"    {C.DIM}TX: {tx.get('tx_hash','?')}{C.END}")
        print(f"  {'─' * 72}")


# ═══════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════

def main():
    print(f"""
{C.Y}{'━' * 55}
  ⚠️  SECURITY NOTICE
{'━' * 55}{C.END}
  Private keys will be stored in {C.BOLD}{CONFIG_FILE}{C.END}
  on your local machine.

  • Do NOT share your config file with anyone.
  • Do NOT run this tool on untrusted machines.
  • Use a dedicated hot wallet with small amounts.
  • Recommended for testnet / small-value operations.
{C.Y}{'━' * 55}{C.END}
""")
    input(f"  {C.DIM}Press Enter to continue…{C.END}")

    CLI().run()


if __name__ == "__main__":
    main()
