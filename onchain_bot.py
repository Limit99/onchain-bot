#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════╗
║              ONCHAIN AUTOMATION BOT v1.9.0                    ║
║  Kirim · Swap · Bridge · Multi-wallet · Tugas Terjadwal       ║
╚═══════════════════════════════════════════════════════════════╝

GitHub: https://github.com/Limit99/onchain-bot

Fitur:
  - Kirim token native (ETH/BNB/MATIC/dll) ke satu atau banyak alamat
  - Swap token via DEX router kompatibel Uniswap V2
  - Bridge token antar chain (dukungan kontrak bridge generik)
  - Dukungan multi-wallet dengan round-robin atau acak
  - Kirim otomatis ke alamat acak
  - Transaksi terjadwal/berulang
  - Mendukung SEMUA chain EVM via RPC kustom (mainnet & testnet)
  - Pilihan nilai preset: 0.1, 0.001, 0.0001 (dalam token native)

Kebutuhan:
  pip install web3

Penggunaan:
  python onchain_bot.py
"""

import json
import os
import sys
import time
import secrets
import threading
import traceback
import urllib.request
import urllib.error
from datetime import datetime
from decimal import Decimal

# For faucet functionality
try:
    import requests
except ImportError:
    requests = None


# ── Import web3 (mendukung v5.x dan v7.x) ──────────────────
_WEB3_ERR = None
try:
    from web3 import Web3
    from eth_account import Account
    # web3 >= 7.x
    try:
        from web3.middleware import ExtraDataToPOAMiddleware
        _POA_MW = ExtraDataToPOAMiddleware
    except ImportError:
        # web3 5.x / 6.x fallback
        try:
            from web3.middleware import geth_poa_middleware
            _POA_MW = geth_poa_middleware
        except ImportError:
            _POA_MW = None
except Exception as e:
    _WEB3_ERR = str(e)
    print(f"\n❌ Gagal import web3: {_WEB3_ERR}")
    print("   Perbaiki:")
    print("   pip install web3\n")
    sys.exit(1)


# ═══════════════════════════════════════════════════════════════
# KONSTANTA
# ═══════════════════════════════════════════════════════════════

VERSION = "2.0.0"

# ── Database Chain ID ───────────────────────────────────────────
# Maps chain_id → (name, symbol, explorer, network_type, rpc_url)
# Semua chain dikenali otomatis dan ter-load saat pertama kali jalan.
KNOWN_CHAINS = {
    # ══════════════════════  MAINNETS  ══════════════════════════
    1:        ("Ethereum",          "ETH",   "https://etherscan.io",                       "mainnet", "https://eth.llamarpc.com"),
    56:       ("BSC",               "BNB",   "https://bscscan.com",                        "mainnet", "https://bsc-dataseed.binance.org"),
    137:      ("Polygon",           "MATIC", "https://polygonscan.com",                    "mainnet", "https://polygon-rpc.com"),
    42161:    ("Arbitrum One",      "ETH",   "https://arbiscan.io",                        "mainnet", "https://arb1.arbitrum.io/rpc"),
    10:       ("Optimism",          "ETH",   "https://optimistic.etherscan.io",            "mainnet", "https://mainnet.optimism.io"),
    43114:    ("Avalanche",         "AVAX",  "https://snowtrace.io",                       "mainnet", "https://api.avax.network/ext/bc/C/rpc"),
    250:      ("Fantom",            "FTM",   "https://ftmscan.com",                        "mainnet", "https://rpc.ftm.tools"),
    8453:     ("Base",              "ETH",   "https://basescan.org",                       "mainnet", "https://mainnet.base.org"),
    324:      ("zkSync Era",        "ETH",   "https://explorer.zksync.io",                 "mainnet", "https://mainnet.era.zksync.io"),
    1101:     ("Polygon zkEVM",     "ETH",   "https://zkevm.polygonscan.com",              "mainnet", "https://zkevm-rpc.com"),
    59144:    ("Linea",             "ETH",   "https://lineascan.build",                    "mainnet", "https://rpc.linea.build"),
    534352:   ("Scroll",            "ETH",   "https://scrollscan.com",                     "mainnet", "https://rpc.scroll.io"),
    5000:     ("Mantle",            "MNT",   "https://mantlescan.xyz",                     "mainnet", "https://rpc.mantle.xyz"),
    169:      ("Manta Pacific",     "ETH",   "https://pacific-explorer.manta.network",     "mainnet", "https://pacific-rpc.manta.network/http"),
    7777777:  ("Zora",              "ETH",   "https://explorer.zora.energy",               "mainnet", "https://rpc.zora.energy"),
    81457:    ("Blast",             "ETH",   "https://blastscan.io",                       "mainnet", "https://rpc.blast.io"),
    204:      ("opBNB",             "BNB",   "https://opbnbscan.com",                      "mainnet", "https://opbnb-mainnet-rpc.bnbchain.org"),
    1284:     ("Moonbeam",          "GLMR",  "https://moonscan.io",                        "mainnet", "https://rpc.api.moonbeam.network"),
    1285:     ("Moonriver",         "MOVR",  "https://moonriver.moonscan.io",              "mainnet", "https://rpc.api.moonriver.moonbeam.network"),
    42220:    ("Celo",              "CELO",  "https://celoscan.io",                        "mainnet", "https://forno.celo.org"),
    100:      ("Gnosis",            "xDAI",  "https://gnosisscan.io",                      "mainnet", "https://rpc.gnosischain.com"),
    25:       ("Cronos",            "CRO",   "https://cronoscan.com",                      "mainnet", "https://evm.cronos.org"),
    1088:     ("Metis",             "METIS", "https://andromeda-explorer.metis.io",         "mainnet", "https://andromeda.metis.io/?owner=1088"),
    34443:    ("Mode",              "ETH",   "https://explorer.mode.network",              "mainnet", "https://mainnet.mode.network"),
    167000:   ("Taiko",             "ETH",   "https://taikoscan.io",                       "mainnet", "https://rpc.taiko.xyz"),
    7560:     ("Cyber",             "ETH",   "https://cyberscan.co",                       "mainnet", "https://cyber.alt.technology"),
    480:      ("World Chain",       "ETH",   "https://worldscan.org",                      "mainnet", "https://worldchain-mainnet.g.alchemy.com/public"),
    2741:     ("Abstract",          "ETH",   "https://abscan.org",                         "mainnet", "https://api.abstrachain.io"),
    57073:    ("Ink",               "ETH",   "https://explorer.inkonchain.com",            "mainnet", "https://rpc-gel.inkonchain.com"),
    130:      ("Unichain",          "ETH",   "https://uniscan.xyz",                        "mainnet", "https://mainnet.unichain.org"),
    146:      ("Sonic",             "S",     "https://sonicscan.org",                      "mainnet", "https://rpc.soniclabs.com"),
    1868:     ("Soneium",           "ETH",   "https://soneium.blockscout.com",             "mainnet", "https://rpc.soneium.org"),
    80094:    ("Berachain",         "BERA",  "https://berascan.com",                       "mainnet", "https://rpc.berachain.com"),
    196:      ("X Layer",           "OKB",   "https://www.okx.com/web3/explorer/xlayer",   "mainnet", "https://rpc.xlayer.tech"),
    1135:     ("Lisk",              "ETH",   "https://blockscout.lisk.com",                "mainnet", "https://rpc.api.lisk.com"),
    252:      ("Fraxtal",           "frxETH","https://fraxscan.com",                       "mainnet", "https://rpc.frax.com"),
    660279:   ("Xai",               "XAI",   "https://explorer.xai-chain.net",             "mainnet", "https://xai-chain.net/rpc"),
    255:      ("Kroma",             "ETH",   "https://kromascan.com",                      "mainnet", "https://api.kroma.network"),
    # ══════════════════════  TESTNETS  ══════════════════════════
    11155111: ("Sepolia",           "ETH",   "https://sepolia.etherscan.io",               "testnet", "https://rpc.sepolia.org"),
    17000:    ("Holesky",           "ETH",   "https://holesky.etherscan.io",               "testnet", "https://ethereum-holesky-rpc.publicnode.com"),
    97:       ("BSC Testnet",       "tBNB",  "https://testnet.bscscan.com",                "testnet", "https://data-seed-prebsc-1-s1.binance.org:8545"),
    80002:    ("Polygon Amoy",      "MATIC", "https://amoy.polygonscan.com",               "testnet", "https://rpc-amoy.polygon.technology"),
    421614:   ("Arbitrum Sepolia",  "ETH",   "https://sepolia.arbiscan.io",                "testnet", "https://sepolia-rollup.arbitrum.io/rpc"),
    11155420: ("Optimism Sepolia",  "ETH",   "https://sepolia-optimism.etherscan.io",      "testnet", "https://sepolia.optimism.io"),
    43113:    ("Avalanche Fuji",    "AVAX",  "https://testnet.snowtrace.io",               "testnet", "https://api.avax-test.network/ext/bc/C/rpc"),
    84532:    ("Base Sepolia",      "ETH",   "https://sepolia.basescan.org",               "testnet", "https://sepolia.base.org"),
    534351:   ("Scroll Sepolia",    "ETH",   "https://sepolia.scrollscan.com",             "testnet", "https://sepolia-rpc.scroll.io"),
    59141:    ("Linea Sepolia",     "ETH",   "https://sepolia.lineascan.build",            "testnet", "https://rpc.sepolia.linea.build"),
    300:      ("zkSync Sepolia",    "ETH",   "https://sepolia-era.zksync.network",         "testnet", "https://sepolia.era.zksync.dev"),
    168587773:("Blast Sepolia",     "ETH",   "https://sepolia.blastscan.io",               "testnet", "https://sepolia.blast.io"),
    80084:    ("Berachain Bartio",  "BERA",  "https://bartio.beratrail.io",                "testnet", "https://bartio.rpc.berachain.com"),
    1301:     ("Unichain Sepolia",  "ETH",   "https://sepolia.uniscan.xyz",                "testnet", "https://sepolia.unichain.org"),
    10200:    ("Gnosis Chiado",     "xDAI",  "https://gnosis-chiado.blockscout.com",       "testnet", "https://rpc.chiadochain.net"),
    5003:     ("Mantle Sepolia",    "MNT",   "https://sepolia.mantlescan.xyz",             "testnet", "https://rpc.sepolia.mantle.xyz"),
    10143:    ("Monad Testnet",     "MON",   "https://testnet.monadexplorer.com",          "testnet", "https://testnet-rpc.monad.xyz"),
}

# ── Deteksi Platform ────────────────────────────────────────────
IS_TERMUX = os.path.isdir("/data/data/com.termux")
IS_ANDROID = IS_TERMUX or os.path.exists("/system/build.prop")

# Gunakan direktori script untuk file config (berjalan di Termux & semua OS)
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(_SCRIPT_DIR, "onchain_config.json")
HISTORY_FILE = os.path.join(_SCRIPT_DIR, "tx_history.json")


# ═══════════════════════════════════════════════════════════════
# WARNA TERMINAL
# ═══════════════════════════════════════════════════════════════

class C:
    """Kode warna ANSI untuk output terminal."""
    R    = "\033[91m"   # Merah
    G    = "\033[92m"   # Hijau
    Y    = "\033[93m"   # Kuning
    B    = "\033[94m"   # Biru
    M    = "\033[95m"   # Magenta
    CY   = "\033[96m"   # Cyan
    W    = "\033[97m"   # Putih
    DIM  = "\033[2m"    # Redup
    BOLD = "\033[1m"    # Tebal
    END  = "\033[0m"    # Reset

    @staticmethod
    def disable():
        """Nonaktifkan warna (untuk environment non-TTY)."""
        for attr in ("R", "G", "Y", "B", "M", "CY", "W", "DIM", "BOLD", "END"):
            setattr(C, attr, "")

# Nonaktifkan warna jika bukan terminal asli
if not sys.stdout.isatty():
    C.disable()

# ── Emoji aman Termux (beberapa terminal tidak render emoji penuh) ──
E_CHECK  = "✅" if not IS_TERMUX else "[OK]"
E_CROSS  = "❌" if not IS_TERMUX else "[ERR]"
E_WARN   = "⚠️ " if not IS_TERMUX else "[!]"
E_INFO   = "ℹ️ " if not IS_TERMUX else "[i]"
E_TX     = "📜" if not IS_TERMUX else "[TX]"


# ═══════════════════════════════════════════════════════════════
# ABI Kontrak (Minimal)
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

# ── ABI Uniswap V3 SwapRouter ────────────────────────────────
ROUTER_V3_ABI = json.loads("""[
    {"inputs":[{"components":[
        {"name":"tokenIn","type":"address"},
        {"name":"tokenOut","type":"address"},
        {"name":"fee","type":"uint24"},
        {"name":"recipient","type":"address"},
        {"name":"deadline","type":"uint256"},
        {"name":"amountIn","type":"uint256"},
        {"name":"amountOutMinimum","type":"uint256"},
        {"name":"sqrtPriceLimitX96","type":"uint160"}
    ],"internalType":"struct ISwapRouter.ExactInputSingleParams",
    "name":"params","type":"tuple"}],
    "name":"exactInputSingle",
    "outputs":[{"name":"amountOut","type":"uint256"}],
    "stateMutability":"payable","type":"function"},

    {"inputs":[{"components":[
        {"name":"path","type":"bytes"},
        {"name":"recipient","type":"address"},
        {"name":"deadline","type":"uint256"},
        {"name":"amountIn","type":"uint256"},
        {"name":"amountOutMinimum","type":"uint256"}
    ],"internalType":"struct ISwapRouter.ExactInputParams",
    "name":"params","type":"tuple"}],
    "name":"exactInput",
    "outputs":[{"name":"amountOut","type":"uint256"}],
    "stateMutability":"payable","type":"function"},

    {"inputs":[
        {"name":"deadline","type":"uint256"},
        {"name":"data","type":"bytes[]"}],
    "name":"multicall",
    "outputs":[{"name":"results","type":"bytes[]"}],
    "stateMutability":"payable","type":"function"},

    {"inputs":[
        {"name":"data","type":"bytes[]"}],
    "name":"multicall",
    "outputs":[{"name":"results","type":"bytes[]"}],
    "stateMutability":"payable","type":"function"},

    {"inputs":[
        {"name":"amountMinimum","type":"uint256"},
        {"name":"recipient","type":"address"}],
    "name":"unwrapWETH9",
    "outputs":[],
    "stateMutability":"payable","type":"function"},

    {"inputs":[],"name":"refundETH",
    "outputs":[],
    "stateMutability":"payable","type":"function"},

    {"inputs":[],"name":"WETH9",
    "outputs":[{"name":"","type":"address"}],
    "stateMutability":"view","type":"function"}
]""")

# Fee tiers Uniswap V3 (dalam basis points × 100)
V3_FEE_TIERS = {
    "1": (100,   "0.01% — stablecoin pairs"),
    "2": (500,   "0.05% — stablecoin/major pairs"),
    "3": (3000,  "0.3%  — most pairs (default)"),
    "4": (10000, "1%    — exotic/volatile pairs"),
}
V3_DEFAULT_FEE = 3000

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

# Nilai preset (dalam token native)
VALUE_PRESETS = {
    "1": "0.1",
    "2": "0.001",
    "3": "0.0001",
}


# ═══════════════════════════════════════════════════════════════
# FUNGSI UTILITAS
# ═══════════════════════════════════════════════════════════════

def clear_screen():
    """Bersihkan layar terminal (berjalan di Termux, Linux, macOS, Windows)."""
    if IS_TERMUX:
        print("\033[H\033[2J", end="", flush=True)
    else:
        os.system("cls" if os.name == "nt" else "clear")


def banner():
    """Tampilkan banner aplikasi."""
    platform_tag = f" {C.G}[Termux]{C.END}" if IS_TERMUX else ""
    print(f"""
{C.CY}╔═══════════════════════════════════════════════════════════════╗
║{C.BOLD}{C.W}              ONCHAIN AUTOMATION BOT v{VERSION}                  {C.END}{C.CY}║
║{C.DIM}  Kirim · Swap · Bridge · Multi-wallet · Terjadwal            {C.END}{C.CY}║
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
    """Cetak hash transaksi dengan link explorer opsional."""
    if explorer:
        url = f"{explorer.rstrip('/')}/tx/{tx_hash}"
        print(f"  {C.G}{E_TX} TX: {url}{C.END}")
    else:
        print(f"  {C.G}{E_TX} TX: {tx_hash}{C.END}")


def prompt(text, default=""):
    """Minta input dari pengguna dengan default opsional."""
    suffix = f" [{default}]" if default else ""
    result = input(f"  {C.Y}▸ {text}{suffix}: {C.END}").strip()
    return result if result else default


def confirm(text):
    """Minta konfirmasi ya/tidak dari pengguna."""
    r = input(f"  {C.Y}▸ {text} (y/n): {C.END}").strip().lower()
    return r in ("y", "yes")


def menu_select(title, options):
    """Tampilkan menu bernomor dan kembalikan pilihan pengguna."""
    print(f"\n  {C.BOLD}{C.CY}{title}{C.END}")
    print(f"  {C.DIM}{'─' * 45}{C.END}")
    for key, label in options:
        print(f"  {C.W}  [{C.CY}{key}{C.W}] {label}{C.END}")
    print(f"  {C.DIM}{'─' * 45}{C.END}")
    return input(f"  {C.Y}▸ Pilih: {C.END}").strip()


# ═══════════════════════════════════════════════════════════════
# DATABASE DEX ROUTER YANG DIKENALI
# chain_name → list of (dex_name, router_address, weth_address)
# ═══════════════════════════════════════════════════════════════
KNOWN_DEX_ROUTERS = {
    # Format: (nama, alamat_router, alamat_weth, tipe)
    # tipe: "v2" = Uniswap V2 compatible, "v3" = Uniswap V3 compatible
    # ── Mainnets ────────────────────────────────────────────────
    "Ethereum": [
        ("uniswap-v2",   "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D", "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", "v2"),
        ("uniswap-v3",   "0xE592427A0AEce92De3Edee1F18E0157C05861564", "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", "v3"),
        ("sushiswap",    "0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F", "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", "v2"),
    ],
    "BSC": [
        ("pancakeswap",  "0x10ED43C718714eb63d5aA57B78B54704E256024E", "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c", "v2"),
        ("uniswap-v3",   "0xB971eF87ede563556b2ED4b1C0b0019111Dd85d2", "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c", "v3"),
    ],
    "Polygon": [
        ("quickswap",    "0xa5E0829CaCEd8fFDD4De3c43696c57F7D7A678ff", "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270", "v2"),
        ("sushiswap",    "0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506", "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270", "v2"),
        ("uniswap-v3",   "0xE592427A0AEce92De3Edee1F18E0157C05861564", "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270", "v3"),
    ],
    "Arbitrum One": [
        ("uniswap-v3",   "0xE592427A0AEce92De3Edee1F18E0157C05861564", "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1", "v3"),
        ("sushiswap",    "0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506", "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1", "v2"),
        ("camelot",      "0xc873fEcbd354f5A56E00E710B90EF4201db2448d", "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1", "v2"),
    ],
    "Optimism": [
        ("uniswap-v3",   "0xE592427A0AEce92De3Edee1F18E0157C05861564", "0x4200000000000000000000000000000000000006", "v3"),
        ("velodrome",    "0xa062aE8A9c5e11aaA026fc2670B0D65cCc8B2858", "0x4200000000000000000000000000000000000006", "v2"),
    ],
    "Avalanche": [
        ("trader-joe",   "0x60aE616a2155Ee3d9A68541Ba4544862310933d4", "0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7", "v2"),
        ("pangolin",     "0xE54Ca86531e17Ef3616d22Ca28b0D458b6C89106", "0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7", "v2"),
    ],
    "Fantom": [
        ("spookyswap",   "0xF491e7B69E4244ad4002BC14e878a34207E38c29", "0x21be370D5312f44cB42ce377BC9b8a0cEF1A4C83", "v2"),
        ("spiritswap",   "0x16327E3FbDaCA3bcF7E38F5Af2599D2DDc33aE52", "0x21be370D5312f44cB42ce377BC9b8a0cEF1A4C83", "v2"),
    ],
    "Base": [
        ("uniswap-v3",   "0x2626664c2603336E57B271c5C0b26F421741e481", "0x4200000000000000000000000000000000000006", "v3"),
        ("aerodrome",    "0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43", "0x4200000000000000000000000000000000000006", "v2"),
        ("sushiswap",    "0x6BDED42c6DA8FBf0d2bA55B2fa120C5e0c8D7891", "0x4200000000000000000000000000000000000006", "v2"),
    ],
    "Linea": [
        ("syncswap",     "0x80e38291e06339d10AAB483C65695D004dBD5C69", "0xe5D7C2a44FfDDf6b295A15c148167daaAf5Cf34f", "v2"),
    ],
    "Scroll": [
        ("syncswap",     "0x80e38291e06339d10AAB483C65695D004dBD5C69", "0x5300000000000000000000000000000000000004", "v2"),
    ],
    "Sonic": [
        ("spookyswap",   "0x12AA6ec7d603DC79Ea6A12a0F2C488E6C4eFC170", "", "v2"),
    ],
    "Mantle": [
        ("agni-finance", "0x319B69888b0d11cEC22caA5034e25FfFBDc88421", "0x78c1b0C915c4FAA5FffA6CAbf0219DA63d7f4cb8", "v3"),
    ],
    # ── Testnets ────────────────────────────────────────────────
    "Sepolia": [
        ("uniswap-v2",   "0xeE567Fe1712Faf6149d80dA1E6934E354124CfE3", "0xfFf9976782d46CC05630D1f6eBAb18b2324d6B14", "v2"),
        ("uniswap-v3",   "0x3bFA4769FB09eefC5a80d6E87c3B9C650f7Ae48E", "0xfFf9976782d46CC05630D1f6eBAb18b2324d6B14", "v3"),
    ],
    "Base Sepolia": [
        ("uniswap-v2",   "0x1689E7B1F10000AE47eBfE339a4f69dECd19F602", "0x4200000000000000000000000000000000000006", "v2"),
    ],
    "Arbitrum Sepolia": [
        ("uniswap-v3",   "0x101F443B4d1b059569D643917553c771E1b9663E", "0x980B62Da83eFf3D4576C647993b0c1b7aaf96816", "v3"),
    ],
    "BSC Testnet": [
        ("pancakeswap",  "0xD99D1c33F9fC3444f8101754aBC46c52416550D1", "0xae13d989daC2f0dEbFf460aC112a837C89BAa7cd", "v2"),
    ],
    "Avalanche Fuji": [
        ("trader-joe",   "0xd7f655E3376cE2D7A2b08fF01Eb3B1023191A901", "0xd00ae08403B9bbb9124bB305C09058E32C39A48c", "v2"),
    ],
    "Monad Testnet": [
        ("zkswap-v2",    "0x3be49777B2Dc6cED93d4BFa0Ad8CA1a0C2114917", "0x760AfE86E5De5fa0Ee542fc7B7B713e1c5425701", "v2"),
        ("bean-swap",    "0xCa810D095e90Daae6e867c19DF3A57F440BDB0D7", "0x760AfE86E5De5fa0Ee542fc7B7B713e1c5425701", "v2"),
    ],
    "monad-testnet": [
        ("zkswap-v2",    "0x3be49777B2Dc6cED93d4BFa0Ad8CA1a0C2114917", "0x760AfE86E5De5fa0Ee542fc7B7B713e1c5425701", "v2"),
        ("bean-swap",    "0xCa810D095e90Daae6e867c19DF3A57F440BDB0D7", "0x760AfE86E5De5fa0Ee542fc7B7B713e1c5425701", "v2"),
    ],
}

# Database token populer per chain
# chain_name → list of (symbol, address, decimals)
KNOWN_TOKENS = {
    "Ethereum": [
        ("USDC",  "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", 6),
        ("USDT",  "0xdAC17F958D2ee523a2206206994597C13D831ec7", 6),
        ("DAI",   "0x6B175474E89094C44Da98b954EedeAC495271d0F", 18),
        ("WETH",  "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", 18),
        ("WBTC",  "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599", 8),
    ],
    "BSC": [
        ("USDT",  "0x55d398326f99059fF775485246999027B3197955", 18),
        ("USDC",  "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d", 18),
        ("BUSD",  "0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56", 18),
        ("WBNB",  "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c", 18),
    ],
    "Polygon": [
        ("USDC",  "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359", 6),
        ("USDT",  "0xc2132D05D31c914a87C6611C10748AEb04B58e8F", 6),
        ("WMATIC","0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270", 18),
    ],
    "Arbitrum One": [
        ("USDC",  "0xaf88d065e77c8cC2239327C5EDb3A432268e5831", 6),
        ("USDT",  "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9", 6),
        ("WETH",  "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1", 18),
    ],
    "Base": [
        ("USDC",  "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", 6),
        ("WETH",  "0x4200000000000000000000000000000000000006", 18),
    ],
    "Optimism": [
        ("USDC",  "0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85", 6),
        ("USDT",  "0x94b008aA00579c1307B0EF2c499aD98a8ce58e58", 6),
        ("WETH",  "0x4200000000000000000000000000000000000006", 18),
    ],
    "Avalanche": [
        ("USDC",  "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E", 6),
        ("USDT",  "0x9702230A8Ea53601f5cD2dc00fDBc13d4dF4A8c7", 6),
        ("WAVAX", "0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7", 18),
    ],
    "Sepolia": [
        ("WETH",  "0xfFf9976782d46CC05630D1f6eBAb18b2324d6B14", 18),
    ],
    "Monad Testnet": [
        ("WMON",  "0x760AfE86E5De5fa0Ee542fc7B7B713e1c5425701", 18),
        ("USDC",  "0xf817257fed379853cDe0fa4F97AB987181B1E5Ea", 6),
        ("USDT",  "0x88b8E2161DEDC77EF4ab7585569D2415a1C1055D", 6),
        ("WETH",  "0xB5a30b0FDc5F801bD3e3Cb7AEe24cE9D30b960C4", 18),
    ],
}


# ═══════════════════════════════════════════════════════════════
# DATABASE BRIDGE ROUTES YANG DIKENALI
# (from_chain, to_chain) → list of (protocol_name, contract, bridge_type)
# bridge_type: "op-l1-deposit", "op-l2-withdraw", "arb-l1-deposit", "generic"
# ═══════════════════════════════════════════════════════════════
KNOWN_BRIDGE_ROUTES = {
    # ═══ MAINNET ═══
    # Ethereum → L2 (OP Stack)
    ("Ethereum", "Base"):              [("Base Official Bridge",       "0x3154Cf16ccdb4C6d922629664174b904d80F2C35", "op-l1-deposit")],
    ("Ethereum", "Optimism"):          [("Optimism Official Bridge",   "0x99C9fc46f92E8a1c0deC1b1747d010903E884bE1", "op-l1-deposit")],
    ("Ethereum", "Mode"):              [("Mode Official Bridge",       "0x735aDBbE72226BD52e818b7181C3a6024F4E5d47", "op-l1-deposit")],
    ("Ethereum", "Zora"):              [("Zora Official Bridge",       "0x3e2Ea9B1921DE8a299622a0d920689AB3B2fb5aF", "op-l1-deposit")],
    ("Ethereum", "Mantle"):            [("Mantle Official Bridge",     "0x95fC37A27a2f68e3A647CDc081F0A89bb47c3012", "op-l1-deposit")],
    # Ethereum → Arbitrum
    ("Ethereum", "Arbitrum One"):      [("Arbitrum Official Bridge",   "0x4Dbd4fc535Ac27206064B68FfCf827b0A60BAB3f", "arb-l1-deposit")],
    # L2 → Ethereum (OP Stack — semua pakai pre-deploy yang sama)
    ("Base", "Ethereum"):              [("Base Official Bridge",       "0x4200000000000000000000000000000000000010", "op-l2-withdraw")],
    ("Optimism", "Ethereum"):          [("Optimism Official Bridge",   "0x4200000000000000000000000000000000000010", "op-l2-withdraw")],
    ("Mode", "Ethereum"):              [("Mode Official Bridge",       "0x4200000000000000000000000000000000000010", "op-l2-withdraw")],
    ("Zora", "Ethereum"):              [("Zora Official Bridge",       "0x4200000000000000000000000000000000000010", "op-l2-withdraw")],
    ("Mantle", "Ethereum"):            [("Mantle Official Bridge",     "0x4200000000000000000000000000000000000010", "op-l2-withdraw")],

    # ═══ TESTNET ═══
    # Sepolia → L2 Testnets (OP Stack)
    ("Sepolia", "Base Sepolia"):       [("Base Official Bridge",       "0xfd0Bf71F60660E2f608ed56e1659C450eB113120", "op-l1-deposit")],
    ("Sepolia", "Optimism Sepolia"):   [("Optimism Official Bridge",   "0xFBb0621E0B23b5478B630BD55a5f21f67730B0F1", "op-l1-deposit")],
    # Sepolia → Arbitrum
    ("Sepolia", "Arbitrum Sepolia"):   [("Arbitrum Official Bridge",   "0xaAe29B0366299461418F5324a79Afc425BE5ae21", "arb-l1-deposit")],
    # L2 Testnets → Sepolia (OP Stack)
    ("Base Sepolia", "Sepolia"):       [("Base Official Bridge",       "0x4200000000000000000000000000000000000010", "op-l2-withdraw")],
    ("Optimism Sepolia", "Sepolia"):   [("Optimism Official Bridge",   "0x4200000000000000000000000000000000000010", "op-l2-withdraw")],
}

# ABI minimal per tipe bridge
BRIDGE_ABIS = {
    "op-l1-deposit": [{"inputs": [
        {"name": "_to", "type": "address"},
        {"name": "_minGasLimit", "type": "uint32"},
        {"name": "_extraData", "type": "bytes"}
    ], "name": "depositETHTo", "outputs": [], "stateMutability": "payable", "type": "function"}],

    "op-l2-withdraw": [{"inputs": [
        {"name": "_to", "type": "address"},
        {"name": "_minGasLimit", "type": "uint32"},
        {"name": "_extraData", "type": "bytes"}
    ], "name": "bridgeETHTo", "outputs": [], "stateMutability": "payable", "type": "function"}],

    "arb-l1-deposit": [{"inputs": [], "name": "depositEth",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "payable", "type": "function"}],
}


def detect_chain(rpc_url):
    """Deteksi otomatis chain ID, nama, simbol, explorer dari URL RPC.
    Return (chain_id, nama, simbol, explorer, tipe_jaringan) atau None jika gagal."""
    try:
        w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 10}))
        if not w3.is_connected():
            return None
        cid = w3.eth.chain_id
        if cid in KNOWN_CHAINS:
            name, symbol, explorer, net_type, _rpc = KNOWN_CHAINS[cid]
            return (cid, name, symbol, explorer, net_type)
        else:
            net = "testnet" if "test" in rpc_url.lower() else "mainnet"
            return (cid, f"chain-{cid}", "ETH", "", net)
    except Exception:
        return None


def short_addr(addr):
    """Persingkat alamat Ethereum untuk ditampilkan."""
    if not addr or len(addr) < 10:
        return addr or "?"
    return f"{addr[:6]}...{addr[-4:]}"


def generate_random_address():
    """Buat alamat Ethereum acak secara kriptografis."""
    private_key = "0x" + secrets.token_hex(32)
    acct = Account.from_key(private_key)
    return acct.address


# ═══════════════════════════════════════════════════════════════
# MANAJER KONFIGURASI
# ═══════════════════════════════════════════════════════════════

class Config:
    """Kelola konfigurasi persisten (chain, wallet, token, dll.)."""

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
            for k, v in self.DEFAULT.items():
                self.data[k] = saved.get(k, v)
            log_ok(f"Konfigurasi dimuat ({self.path})")
        else:
            log_info("Tidak ada konfigurasi — mulai dari awal.")
        # Otomatis tambahkan semua chain yang dikenali
        self._auto_populate_chains()

    def _auto_populate_chains(self):
        """Otomatis muat semua chain dari KNOWN_CHAINS yang belum ada di config."""
        existing_names = set(self.data["chains"].keys())
        existing_ids = {c["chain_id"] for c in self.data["chains"].values()}
        added = 0
        for cid, (name, symbol, explorer, net_type, rpc) in KNOWN_CHAINS.items():
            if name not in existing_names and cid not in existing_ids:
                self.data["chains"][name] = {
                    "rpc": rpc,
                    "chain_id": int(cid),
                    "symbol": symbol.upper(),
                    "explorer": explorer.rstrip("/"),
                    "type": net_type,
                }
                added += 1
        if added > 0:
            self.save()
            log_ok(f"{added} chain baru dimuat otomatis (total: {len(self.data['chains'])} chain)")

    def save(self):
        with open(self.path, "w") as f:
            json.dump(self.data, f, indent=2)

    # ── Chain ───────────────────────────────────────────────────

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

    # ── Wallet ──────────────────────────────────────────────────

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

    # ── DEX Router ──────────────────────────────────────────────

    def add_dex_router(self, chain_name, router_name, router_address, weth_address="", router_type="v2"):
        if chain_name not in self.data["dex_routers"]:
            self.data["dex_routers"][chain_name] = {}
        self.data["dex_routers"][chain_name][router_name] = {
            "address": Web3.to_checksum_address(router_address),
            "weth": Web3.to_checksum_address(weth_address) if weth_address else "",
            "type": router_type,
        }
        self.save()

    def get_dex_routers(self, chain_name):
        return self.data.get("dex_routers", {}).get(chain_name, {})

    # ── Token ───────────────────────────────────────────────────

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

    # ── Kontrak Bridge ──────────────────────────────────────────

    def add_bridge(self, name, chain_from, chain_to, contract_address="", bridge_type="generic"):
        entry = {
            "from_chain": chain_from,
            "to_chain": chain_to,
            "bridge_type": bridge_type,
        }
        if contract_address and contract_address.strip():
            entry["contract"] = Web3.to_checksum_address(contract_address.strip())
        else:
            entry["contract"] = ""
        # Simpan chain_id tujuan otomatis dari chain yang dikenali
        chains = self.data.get("chains", {})
        if chain_to in chains:
            entry["dest_chain_id"] = chains[chain_to]["chain_id"]
        self.data["bridge_contracts"][name] = entry
        self.save()

    def get_bridges(self):
        return self.data.get("bridge_contracts", {})

    def remove_bridge(self, name):
        self.data["bridge_contracts"].pop(name, None)
        self.save()

    # ── Hapus DEX Router ────────────────────────────────────────

    def remove_dex_router(self, chain_name, router_name):
        if chain_name in self.data.get("dex_routers", {}):
            self.data["dex_routers"][chain_name].pop(router_name, None)
            if not self.data["dex_routers"][chain_name]:
                del self.data["dex_routers"][chain_name]
            self.save()

    # ── Hapus Token ─────────────────────────────────────────────

    def remove_token(self, chain_name, symbol):
        if chain_name in self.data.get("tokens", {}):
            self.data["tokens"][chain_name].pop(symbol, None)
            if not self.data["tokens"][chain_name]:
                del self.data["tokens"][chain_name]
            self.save()


# ═══════════════════════════════════════════════════════════════
# MESIN BLOCKCHAIN
# ═══════════════════════════════════════════════════════════════

class BlockchainEngine:
    """Mesin inti untuk semua interaksi on-chain."""

    _fee_cache: dict = {}

    def __init__(self, config: Config):
        self.config = config
        self.w3: Web3 | None = None
        self.current_chain: str | None = None
        self.tx_history: list = []
        self._load_history()
        # Faucet-related state
        self._faucet_last_request = {}

    # ── Riwayat ─────────────────────────────────────────────────

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

    # ── Koneksi ─────────────────────────────────────────────────

    def connect(self, chain_name):
        """Sambungkan ke chain EVM melalui RPC yang dikonfigurasi."""
        chains = self.config.get_chains()
        if chain_name not in chains:
            log_err(f"Chain '{chain_name}' tidak ditemukan di konfigurasi")
            return False

        chain = chains[chain_name]
        try:
            self.w3 = Web3(Web3.HTTPProvider(chain["rpc"], request_kwargs={"timeout": 30}))
            if _POA_MW:
                self.w3.middleware_onion.inject(_POA_MW, layer=0)

            if self.w3.is_connected():
                self.current_chain = chain_name
                block = self.w3.eth.block_number
                log_ok(f"Terhubung ke {chain_name} (Chain ID: {chain['chain_id']}, Blok: #{block:,})")
                return True
            else:
                log_err(f"Tidak bisa terhubung ke RPC {chain_name}: {chain['rpc']}")
                return False
        except Exception as e:
            log_err(f"Error koneksi: {e}")
            return False

    # ── Saldo ───────────────────────────────────────────────────

    def get_balance(self, address):
        """Dapatkan saldo token native dalam ether."""
        bal_wei = self.w3.eth.get_balance(Web3.to_checksum_address(address))
        return self.w3.from_wei(bal_wei, "ether")

    def get_token_balance(self, token_address, wallet_address):
        """Dapatkan saldo token ERC-20."""
        contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(token_address), abi=ERC20_ABI
        )
        raw = contract.functions.balanceOf(Web3.to_checksum_address(wallet_address)).call()
        decimals = contract.functions.decimals().call()
        return Decimal(raw) / Decimal(10 ** decimals)

    # ── Pembangun TX ────────────────────────────────────────────

    def _chain_info(self):
        return self.config.get_chains().get(self.current_chain, {})

    def _build_and_send(self, tx, private_key, wallet_address):
        """Tanda tangani, kirim, dan tunggu receipt transaksi."""
        info = self._chain_info()
        addr = Web3.to_checksum_address(wallet_address)

        # Nonce
        tx["nonce"] = self.w3.eth.get_transaction_count(addr)
        tx["chainId"] = info["chain_id"]

        # Estimasi gas (dengan buffer keamanan 20%)
        if "gas" not in tx:
            try:
                tx["gas"] = int(self.w3.eth.estimate_gas(tx) * 1.2)
            except Exception as e:
                log_warn(f"Estimasi gas gagal ({e}), menggunakan 150.000")
                tx["gas"] = 150_000

        # Harga gas — EIP-1559 adaptif, fallback ke legacy
        try:
            latest = self.w3.eth.get_block("latest")
            base_fee = latest.get("baseFeePerGas")
            if base_fee:
                # Gas adaptif: cek utilisasi blok untuk menentukan multiplier
                gas_used = latest.get("gasUsed", 0)
                gas_limit = latest.get("gasLimit", 1)
                utilization = gas_used / gas_limit if gas_limit else 0

                # Multiplier berdasarkan utilisasi (congestion-aware)
                if utilization > 0.9:
                    # Network sangat sibuk — pakai multiplier agresif
                    base_multiplier = 2.5
                    log_warn("Network congested — menggunakan gas multiplier tinggi (2.5x)")
                elif utilization > 0.7:
                    # Cukup sibuk — multiplier sedang
                    base_multiplier = 2.0
                else:
                    # Normal/sepi — multiplier konservatif (hemat gas)
                    base_multiplier = 1.5

                priority = self.w3.eth.max_priority_fee
                # Batas bawah priority fee: 1 gwei
                priority = max(priority, self.w3.to_wei(1, "gwei"))

                max_fee = int(base_fee * base_multiplier) + priority
                tx["maxFeePerGas"] = max_fee
                tx["maxPriorityFeePerGas"] = priority
                tx.pop("gasPrice", None)

                log_info(f"EIP-1559: baseFee={base_fee/1e9:.2f} gwei, "
                         f"priority={priority/1e9:.2f} gwei, "
                         f"maxFee={max_fee/1e9:.2f} gwei "
                         f"(util={utilization:.0%}, mul={base_multiplier}x)")
            else:
                raise ValueError("tidak ada baseFee")
        except Exception:
            tx["gasPrice"] = self.w3.eth.gas_price
            tx.pop("maxFeePerGas", None)
            tx.pop("maxPriorityFeePerGas", None)
            log_info(f"Legacy gas: {tx['gasPrice']/1e9:.2f} gwei")

        # Hapus key internal sebelum signing
        tx_type = tx.pop("_type", "unknown")

        # Sign + kirim
        signed = self.w3.eth.account.sign_transaction(tx, private_key)
        raw_tx = signed.raw_transaction if hasattr(signed, "raw_transaction") else signed.rawTransaction
        tx_hash = self.w3.eth.send_raw_transaction(raw_tx).hex()

        log_info(f"TX terkirim: {tx_hash}")
        log_info("Menunggu konfirmasi…")

        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
        explorer = info.get("explorer", "")

        if receipt.status == 1:
            log_ok(f"Terkonfirmasi di blok #{receipt.blockNumber:,} (gas terpakai: {receipt.gasUsed:,})")
        else:
            log_err(f"TX gagal (reverted) di blok #{receipt.blockNumber:,}")
        log_tx(tx_hash, explorer)

        # Simpan riwayat
        self._save_history({
            "timestamp": datetime.now().isoformat(),
            "chain": self.current_chain,
            "type": tx_type,
            "from": wallet_address,
            "to": tx.get("to", ""),
            "value": str(tx.get("value", 0)),
            "tx_hash": tx_hash,
            "status": "sukses" if receipt.status == 1 else "gagal",
            "block": receipt.blockNumber,
            "gas_used": receipt.gasUsed,
        })
        return receipt

    # ── Kirim Token Native ──────────────────────────────────────

    def send_native(self, wallet, to_address, amount_ether):
        """Kirim token native ke satu alamat."""
        if not self._ensure_minimum_balance(wallet, amount_ether):
            raise ValueError("Insufficient funds and faucet failed")
        info = self._chain_info()
        amount_wei = self.w3.to_wei(Decimal(str(amount_ether)), "ether")

        log_info(f"Mengirim {amount_ether} {info['symbol']} → {short_addr(to_address)}")
        tx = {
            "from": Web3.to_checksum_address(wallet["address"]),
            "to": Web3.to_checksum_address(to_address),
            "value": amount_wei,
            "_type": "kirim_native",
        }
        return self._build_and_send(tx, wallet["private_key"], wallet["address"])

    def multi_send(self, wallets, addresses, amount_ether, delay_sec=2, wallet_mode="round-robin"):
        """Kirim ke daftar alamat menggunakan satu atau lebih wallet."""
        results = []
        n_wallets = len(wallets)

        for i, addr in enumerate(addresses):
            if wallet_mode == "random":
                wallet = wallets[secrets.randbelow(n_wallets)]
            else:
                wallet = wallets[i % n_wallets]

            log_info(f"[{i+1}/{len(addresses)}] {short_addr(wallet['address'])} → {short_addr(addr)}")
            try:
                receipt = self.send_native(wallet, addr, amount_ether)
                results.append({"to": addr, "status": "sukses", "tx": receipt.transactionHash.hex()})
            except Exception as e:
                log_err(f"Gagal: {e}")
                results.append({"to": addr, "status": "gagal", "error": str(e)})

            if i < len(addresses) - 1 and delay_sec > 0:
                log_info(f"Menunggu {delay_sec} detik…")
                time.sleep(delay_sec)

        return results

    def send_to_random(self, wallets, count, amount_ether, delay_sec=2, wallet_mode="round-robin"):
        """Buat N alamat acak dan kirim ke masing-masing."""
        addresses = [generate_random_address() for _ in range(count)]
        log_info(f"Membuat {count} alamat acak:")
        for i, a in enumerate(addresses, 1):
            print(f"    {C.DIM}{i:>3}. {a}{C.END}")
        print()
        return self.multi_send(wallets, addresses, amount_ether, delay_sec, wallet_mode)

    # ── Swap (V2 & V3) ─────────────────────────────────────────

    def _get_router(self, router_address):
        return self.w3.eth.contract(
            address=Web3.to_checksum_address(router_address), abi=ROUTER_V2_ABI
        )

    def _get_router_v3(self, router_address):
        return self.w3.eth.contract(
            address=Web3.to_checksum_address(router_address), abi=ROUTER_V3_ABI
        )

    def _detect_router_type(self, router_name, router_info):
        """Deteksi tipe router (v2/v3) dari config atau nama."""
        # 1) Dari config (field 'type')
        rtype = router_info.get("type", "")
        if rtype in ("v2", "v3"):
            return rtype
        # 2) Dari nama router
        name_lower = router_name.lower()
        if "v3" in name_lower or "v4" in name_lower:
            return "v3"
        return "v2"

    def _multicall_v3(self, router_v3, deadline, call_data_list, sender):
        """Build multicall TX yang kompatibel dengan SwapRouter & SwapRouter02.
        
        SwapRouter  (original): multicall(bytes[] data)
        SwapRouter02 (newer)  : multicall(uint256 deadline, bytes[] data)
        
        Coba SwapRouter02 dulu (lebih umum), fallback ke original.
        """
        # Coba SwapRouter02 style: multicall(deadline, data[])
        try:
            tx = router_v3.functions.multicall(
                deadline, call_data_list
            ).build_transaction({"from": sender})
            return tx
        except Exception:
            pass

        # Fallback: SwapRouter original: multicall(data[])
        try:
            tx = router_v3.functions.multicall(
                call_data_list
            ).build_transaction({"from": sender})
            return tx
        except Exception as e:
            raise ValueError(
                f"multicall gagal — router tidak mendukung signature yang dikenali.\n"
                f"  Error: {e}"
            )

    def _get_wrapped_native(self, router, router_address=""):
        """
        Deteksi alamat Wrapped Native Token (WETH/WMON/WBNB/dll).

        Strategi:
        1. Ambil dari config (jika user sudah simpan weth saat setup DEX)
        2. Coba panggil router.WETH()
        3. Gagal → informasi error yang jelas
        """
        # 1) Cek config dulu
        if router_address:
            chains = self.config.get_chains() if self.config else {}
            for cname, cinfo in chains.items():
                routers = self.config.data.get("dex_routers", {}).get(cname, {})
                for rname, rinfo in routers.items():
                    if rinfo.get("address", "").lower() == router_address.lower() and rinfo.get("weth"):
                        log_info(f"Wrapped native dari config: {short_addr(rinfo['weth'])}")
                        return Web3.to_checksum_address(rinfo["weth"])

        # 2) Coba WETH() dari router contract (V2)
        try:
            weth = router.functions.WETH().call()
            if weth and weth != "0x" + "0" * 40:
                return weth
        except Exception:
            pass

        # 3) Coba WETH9() dari router contract (V3)
        try:
            router_v3 = self.w3.eth.contract(
                address=router.address, abi=ROUTER_V3_ABI
            )
            weth = router_v3.functions.WETH9().call()
            if weth and weth != "0x" + "0" * 40:
                return weth
        except Exception:
            pass

        raise ValueError(
            "Tidak bisa mendeteksi alamat Wrapped Native Token!\n"
            "  Router ini mungkin tidak punya fungsi WETH()/WETH9().\n"
            "  Solusi: Masuk ke Pengaturan → Tambah DEX Router → isi alamat WETH/WMON manual,\n"
            "  atau hapus router ini dan tambahkan ulang dengan alamat WETH/WMON yang benar."
        )

    def wrap_native(self, wallet, amount_ether):
        """Wrap native token → wrapped token (deposit ke kontrak WETH/WMON)."""
        if not self._ensure_minimum_balance(wallet, amount_ether):
            raise ValueError("Insufficient funds and faucet failed")
        info = self._chain_info()
        amount_wei = self.w3.to_wei(Decimal(str(amount_ether)), "ether")
        addr = Web3.to_checksum_address(wallet["address"])

        # Cari WETH/WMON dari DEX router pertama yang punya
        chains = self.config.get_chains() if self.config else {}
        cn = self.current_chain
        routers = self.config.data.get("dex_routers", {}).get(cn, {})
        weth_addr = None
        for rname, rinfo in routers.items():
            if rinfo.get("weth"):
                weth_addr = rinfo["weth"]
                break
            # Coba dari router contract
            try:
                router = self._get_router(rinfo["address"])
                weth_addr = router.functions.WETH().call()
                break
            except Exception:
                continue

        if not weth_addr:
            raise ValueError(
                "Tidak ditemukan alamat Wrapped Native Token di chain ini.\n"
                "  Tambahkan DEX router dengan alamat WETH/WMON terlebih dahulu."
            )

        WETH_ABI = json.loads('[{"constant":false,"inputs":[],"name":"deposit","outputs":[],"payable":true,"stateMutability":"payable","type":"function"},{"constant":false,"inputs":[{"name":"wad","type":"uint256"}],"name":"withdraw","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"}]')
        weth = self.w3.eth.contract(address=Web3.to_checksum_address(weth_addr), abi=WETH_ABI)

        log_info(f"Wrapping {amount_ether} {info['symbol']} → Wrapped {info['symbol']}")
        tx = weth.functions.deposit().build_transaction({
            "from": addr,
            "value": amount_wei,
        })
        tx["_type"] = "wrap"
        return self._build_and_send(tx, wallet["private_key"], wallet["address"])

    def unwrap_native(self, wallet, amount_ether):
        """Unwrap wrapped token → native token (withdraw dari kontrak WETH/WMON)."""
        if not self._ensure_minimum_balance(wallet, amount_ether):
            raise ValueError("Insufficient funds and faucet failed")
        info = self._chain_info()
        amount_wei = self.w3.to_wei(Decimal(str(amount_ether)), "ether")
        addr = Web3.to_checksum_address(wallet["address"])

        cn = self.current_chain
        routers = self.config.data.get("dex_routers", {}).get(cn, {})
        weth_addr = None
        for rname, rinfo in routers.items():
            if rinfo.get("weth"):
                weth_addr = rinfo["weth"]
                break
            try:
                router = self._get_router(rinfo["address"])
                weth_addr = router.functions.WETH().call()
                break
            except Exception:
                continue

        if not weth_addr:
            raise ValueError("Tidak ditemukan alamat Wrapped Native Token di chain ini.")

        WETH_ABI = json.loads('[{"constant":false,"inputs":[],"name":"deposit","outputs":[],"payable":true,"stateMutability":"payable","type":"function"},{"constant":false,"inputs":[{"name":"wad","type":"uint256"}],"name":"withdraw","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"}]')
        weth = self.w3.eth.contract(address=Web3.to_checksum_address(weth_addr), abi=WETH_ABI)

        log_info(f"Unwrapping {amount_ether} Wrapped {info['symbol']} → {info['symbol']}")
        tx = weth.functions.withdraw(amount_wei).build_transaction({"from": addr})
        tx["_type"] = "unwrap"
        return self._build_and_send(tx, wallet["private_key"], wallet["address"])

    def _approve_if_needed(self, token_address, spender, wallet, amount_raw):
        """Cek allowance ERC-20 dan approve jika kurang."""
        token = self.w3.eth.contract(address=Web3.to_checksum_address(token_address), abi=ERC20_ABI)
        allowance = token.functions.allowance(
            Web3.to_checksum_address(wallet["address"]),
            Web3.to_checksum_address(spender),
        ).call()
        if allowance < amount_raw:
            symbol = token.functions.symbol().call()
            log_info(f"Meng-approve {symbol} untuk router…")
            tx = token.functions.approve(
                Web3.to_checksum_address(spender), 2**256 - 1
            ).build_transaction({"from": Web3.to_checksum_address(wallet["address"])})
            tx["_type"] = "approve"
            self._build_and_send(tx, wallet["private_key"], wallet["address"])

    def swap_native_to_token(self, wallet, router_address, token_address, amount_ether, slippage=5):
        """Swap native → ERC-20 via router kompatibel Uniswap V2."""
        if not self._ensure_minimum_balance(wallet, amount_ether):
            raise ValueError("Insufficient funds and faucet failed")
        info = self._chain_info()
        router = self._get_router(router_address)
        weth = self._get_wrapped_native(router, router_address)

        # Deteksi jika token tujuan = WETH/WMON (wrap, bukan swap)
        if Web3.to_checksum_address(token_address) == Web3.to_checksum_address(weth):
            log_warn("Token tujuan = Wrapped Native Token (WETH/WMON)!")
            log_info("Menggunakan wrap (deposit) langsung — lebih hemat gas")
            return self.wrap_native(wallet, amount_ether)

        amount_in = self.w3.to_wei(Decimal(str(amount_ether)), "ether")
        path = [weth, Web3.to_checksum_address(token_address)]

        try:
            amounts = router.functions.getAmountsOut(amount_in, path).call()
        except Exception as e:
            raise ValueError(
                f"getAmountsOut gagal — kemungkinan tidak ada pair liquidity\n"
                f"  untuk {info['symbol']} ↔ token ini di DEX yang dipilih.\n"
                f"  Pastikan pair sudah ada di DEX tersebut.\n"
                f"  Detail: {e}"
            )

        min_out = int(amounts[-1] * (100 - slippage) / 100)
        deadline = int(time.time()) + 300

        log_info(f"Menukar {amount_ether} {info['symbol']} → token")
        log_info(f"Estimasi: {amounts[-1]} | Min (slippage {slippage}%): {min_out}")

        tx = router.functions.swapExactETHForTokens(
            min_out, path, Web3.to_checksum_address(wallet["address"]), deadline
        ).build_transaction({
            "from": Web3.to_checksum_address(wallet["address"]),
            "value": amount_in,
        })
        tx["_type"] = "swap_native_ke_token"
        return self._build_and_send(tx, wallet["private_key"], wallet["address"])

    def swap_token_to_native(self, wallet, router_address, token_address, amount, slippage=5):
        """Swap ERC-20 → native via router kompatibel Uniswap V2."""
        info = self._chain_info()
        router = self._get_router(router_address)
        weth = self._get_wrapped_native(router, router_address)
        token = self.w3.eth.contract(address=Web3.to_checksum_address(token_address), abi=ERC20_ABI)

        # Deteksi unwrap
        if Web3.to_checksum_address(token_address) == Web3.to_checksum_address(weth):
            log_warn("Token sumber = Wrapped Native Token (WETH/WMON)!")
            log_info("Menggunakan unwrap (withdraw) langsung — lebih hemat gas")
            return self.unwrap_native(wallet, amount)

        decimals = token.functions.decimals().call()
        symbol = token.functions.symbol().call()
        amount_raw = int(Decimal(str(amount)) * Decimal(10 ** decimals))
        path = [Web3.to_checksum_address(token_address), weth]

        self._approve_if_needed(token_address, router_address, wallet, amount_raw)

        try:
            amounts = router.functions.getAmountsOut(amount_raw, path).call()
        except Exception as e:
            raise ValueError(
                f"getAmountsOut gagal — kemungkinan tidak ada pair liquidity\n"
                f"  untuk {symbol} ↔ {info['symbol']} di DEX yang dipilih.\n"
                f"  Detail: {e}"
            )

        min_out = int(amounts[-1] * (100 - slippage) / 100)
        deadline = int(time.time()) + 300

        log_info(f"Menukar {amount} {symbol} → {info['symbol']}")

        tx = router.functions.swapExactTokensForETH(
            amount_raw, min_out, path,
            Web3.to_checksum_address(wallet["address"]), deadline
        ).build_transaction({"from": Web3.to_checksum_address(wallet["address"])})
        tx["_type"] = "swap_token_ke_native"
        return self._build_and_send(tx, wallet["private_key"], wallet["address"])

    def swap_token_to_token(self, wallet, router_address, token_in, token_out, amount, slippage=5):
        """Swap ERC-20 → ERC-20 via router kompatibel Uniswap V2."""
        router = self._get_router(router_address)
        weth = self._get_wrapped_native(router, router_address)
        tok_in = self.w3.eth.contract(address=Web3.to_checksum_address(token_in), abi=ERC20_ABI)

        decimals = tok_in.functions.decimals().call()
        symbol = tok_in.functions.symbol().call()
        amount_raw = int(Decimal(str(amount)) * Decimal(10 ** decimals))
        path = [Web3.to_checksum_address(token_in), weth, Web3.to_checksum_address(token_out)]

        self._approve_if_needed(token_in, router_address, wallet, amount_raw)

        try:
            amounts = router.functions.getAmountsOut(amount_raw, path).call()
        except Exception as e:
            raise ValueError(
                f"getAmountsOut gagal — kemungkinan tidak ada pair liquidity\n"
                f"  di DEX yang dipilih. Coba DEX lain.\n"
                f"  Detail: {e}"
            )

        min_out = int(amounts[-1] * (100 - slippage) / 100)
        deadline = int(time.time()) + 300

        log_info(f"Menukar {amount} {symbol} → token")

        tx = router.functions.swapExactTokensForTokens(
            amount_raw, min_out, path,
            Web3.to_checksum_address(wallet["address"]), deadline
        ).build_transaction({"from": Web3.to_checksum_address(wallet["address"])})
        tx["_type"] = "swap_token_ke_token"
        return self._build_and_send(tx, wallet["private_key"], wallet["address"])

    # ── Auto-Detect Best DEX ─────────────────────────────────────

    def find_best_dex(self, chain, token_in, token_out, amount_in_raw,
                      sender, is_native_in=False, is_native_out=False):
        """Scan semua DEX di chain aktif, bandingkan output, return yang terbaik.

        Args:
            chain: nama chain (key dari config chains)
            token_in: alamat token input (atau WETH address jika native)
            token_out: alamat token output (atau WETH address jika native)
            amount_in_raw: jumlah input dalam wei/raw units
            sender: alamat wallet pengirim
            is_native_in: True jika input native ETH/BNB/dll (bukan ERC-20)
            is_native_out: True jika output native ETH/BNB/dll

        Returns:
            list of dict, sorted by output (terbesar duluan):
            [{"dex_name": str, "router_address": str, "router_type": str,
              "output": int, "fee_tier": int|None, "weth": str}, ...]
        """
        routers = self.config.get_dex_routers(chain) if self.config else {}
        in_cs = Web3.to_checksum_address(token_in)
        out_cs = Web3.to_checksum_address(token_out)
        results = []

        for rname, rinfo in routers.items():
            raddr = rinfo.get("address", "")
            if not raddr:
                continue
            rtype = self._detect_router_type(rname, rinfo)

            try:
                if rtype == "v3":
                    # ── V3: cari fee tier terbaik via exactInputSingle ──
                    router_v3 = self._get_router_v3(raddr)
                    value = amount_in_raw if is_native_in else 0
                    best_fee, best_out = self._find_best_fee_v3(
                        router_v3, in_cs, out_cs, amount_in_raw, sender, value=value
                    )
                    if best_out > 0:
                        results.append({
                            "dex_name": rname,
                            "router_address": raddr,
                            "router_type": "v3",
                            "output": best_out,
                            "fee_tier": best_fee,
                            "weth": rinfo.get("weth", ""),
                        })
                else:
                    # ── V2: quote via getAmountsOut ──
                    router_v2 = self._get_router(raddr)
                    path = [in_cs, out_cs]
                    amounts = router_v2.functions.getAmountsOut(amount_in_raw, path).call()
                    out_amount = amounts[-1]
                    if out_amount > 0:
                        results.append({
                            "dex_name": rname,
                            "router_address": raddr,
                            "router_type": "v2",
                            "output": out_amount,
                            "fee_tier": None,
                            "weth": rinfo.get("weth", ""),
                        })
            except Exception:
                # DEX ini gagal quote — skip (pair mungkin tidak ada)
                continue

        # Sort descending by output
        results.sort(key=lambda x: x["output"], reverse=True)
        return results

    def swap_best_dex(self, wallet, chain, token_address, amount, slippage=5,
                      direction="native_to_token"):
        """Otomatis pilih DEX terbaik dan eksekusi swap.

        Args:
            direction: "native_to_token" | "token_to_native" | "token_to_token"
            token_address: alamat token (untuk native_to_token / token_to_native)
                           atau tuple (token_in, token_out) untuk token_to_token
        """
        info = self._chain_info()
        addr = Web3.to_checksum_address(wallet["address"])
        routers = self.config.get_dex_routers(chain) if self.config else {}

        if not routers:
            raise ValueError(f"Tidak ada DEX router yang dikonfigurasi di {chain}.")

        # Tentukan token_in, token_out, dan amount_raw
        if direction == "native_to_token":
            amount_raw = self.w3.to_wei(Decimal(str(amount)), "ether")
            # Butuh WETH — ambil dari router pertama yang punya
            weth = None
            for _rn, ri in routers.items():
                try:
                    rt = self._detect_router_type(_rn, ri)
                    r = self._get_router(ri["address"]) if rt == "v2" else self._get_router_v3(ri["address"])
                    if rt == "v2":
                        weth = self._get_wrapped_native(r, ri["address"])
                    else:
                        r2 = self._get_router(ri["address"])
                        weth = self._get_wrapped_native(r2, ri["address"])
                    break
                except Exception:
                    continue
            if not weth:
                raise ValueError("Tidak bisa mendeteksi WETH dari router yang ada.")
            token_in = weth
            token_out = token_address
            is_native_in, is_native_out = True, False

        elif direction == "token_to_native":
            token = self.w3.eth.contract(
                address=Web3.to_checksum_address(token_address), abi=ERC20_ABI
            )
            decimals = token.functions.decimals().call()
            amount_raw = int(Decimal(str(amount)) * Decimal(10 ** decimals))
            weth = None
            for _rn, ri in routers.items():
                try:
                    r = self._get_router(ri["address"])
                    weth = self._get_wrapped_native(r, ri["address"])
                    break
                except Exception:
                    continue
            if not weth:
                raise ValueError("Tidak bisa mendeteksi WETH dari router yang ada.")
            token_in = token_address
            token_out = weth
            is_native_in, is_native_out = False, True

        elif direction == "token_to_token":
            if not isinstance(token_address, (list, tuple)) or len(token_address) != 2:
                raise ValueError("Untuk token→token, token_address harus tuple (token_in, token_out)")
            t_in_addr, t_out_addr = token_address
            tok_in = self.w3.eth.contract(
                address=Web3.to_checksum_address(t_in_addr), abi=ERC20_ABI
            )
            decimals = tok_in.functions.decimals().call()
            amount_raw = int(Decimal(str(amount)) * Decimal(10 ** decimals))
            token_in = t_in_addr
            token_out = t_out_addr
            is_native_in, is_native_out = False, False
        else:
            raise ValueError(f"Direction tidak dikenali: {direction}")

        # Scan semua DEX
        log_info(f"🔍 Scanning semua DEX di {chain}…")
        quotes = self.find_best_dex(
            chain, token_in, token_out, amount_raw, addr,
            is_native_in=is_native_in, is_native_out=is_native_out
        )

        if not quotes:
            raise ValueError(
                "Tidak ada DEX yang bisa memproses swap ini.\n"
                "  Pastikan pair sudah ada liquidity di salah satu DEX."
            )

        # Tampilkan perbandingan harga
        log_info(f"📊 Hasil perbandingan {len(quotes)} DEX:")
        for i, q in enumerate(quotes):
            tag = f"[V3 fee={q['fee_tier']}]" if q["router_type"] == "v3" else "[V2]"
            marker = " ← TERBAIK ✅" if i == 0 else ""
            if is_native_out or direction == "native_to_token":
                out_human = self.w3.from_wei(q["output"], "ether")
            else:
                # Untuk token output, perlu tahu decimals
                try:
                    tok_out_c = self.w3.eth.contract(
                        address=Web3.to_checksum_address(token_out), abi=ERC20_ABI
                    )
                    d = tok_out_c.functions.decimals().call()
                    out_human = Decimal(q["output"]) / Decimal(10 ** d)
                except Exception:
                    out_human = q["output"]
            log_info(f"  {i+1}. {q['dex_name']} {tag}: {out_human}{marker}")

        # Eksekusi swap di DEX terbaik
        best = quotes[0]
        log_info(f"⚡ Menggunakan {best['dex_name']} ({best['router_type'].upper()})…")

        if direction == "native_to_token":
            if best["router_type"] == "v3":
                return self.swap_native_to_token_v3(
                    wallet, best["router_address"], token_out, amount, slippage, best["fee_tier"]
                )
            else:
                return self.swap_native_to_token(
                    wallet, best["router_address"], token_out, amount, slippage
                )
        elif direction == "token_to_native":
            if best["router_type"] == "v3":
                return self.swap_token_to_native_v3(
                    wallet, best["router_address"], token_in, amount, slippage, best["fee_tier"]
                )
            else:
                return self.swap_token_to_native(
                    wallet, best["router_address"], token_in, amount, slippage
                )
        elif direction == "token_to_token":
            t_in_addr, t_out_addr = token_address
            if best["router_type"] == "v3":
                return self.swap_token_to_token_v3(
                    wallet, best["router_address"], t_in_addr, t_out_addr, amount, slippage, best["fee_tier"]
                )
            else:
                return self.swap_token_to_token(
                    wallet, best["router_address"], t_in_addr, t_out_addr, amount, slippage
                )

    # ── Swap (Uniswap V3) ─────────────────────────────────────

    def _find_best_fee_v3(self, router_v3, token_in, token_out, amount_in, sender, value=0):
        """Cari fee tier V3 terbaik (output tertinggi).
        
        Args:
            value: msg.value untuk call(). Gunakan amount_in untuk native→token swap
                   agar router bisa wrap ETH→WETH secara internal.
        """
        chain_id = self._chain_info()["chain_id"]
        cache_key = (chain_id, token_in, token_out)
        now = time.time()
        cached = self._fee_cache.get(cache_key)
        if cached and now - cached[1] < 3600:
            best_fee = cached[0]
            # Cache hanya menyimpan best_fee, bukan output.
            # Output bergantung amount_in, jadi kita lakukan satu quote lagi
            # untuk mendapatkan estimasi output yang akurat dengan amount saat ini.
            try:
                out = router_v3.functions.exactInputSingle((
                    Web3.to_checksum_address(token_in),
                    Web3.to_checksum_address(token_out),
                    best_fee,
                    Web3.to_checksum_address(sender),
                    int(time.time()) + 600,
                    amount_in,
                    0,
                    0,
                )).call({"from": sender, "value": value})
            except Exception:
                # Jika cached fee tidak valid lagi, fallback ke full scan
                cached = None
            if cached is not None:
                if out and out > 0:
                    log_info(f"[CACHE HIT] fee={best_fee} key={cache_key}")
                    return best_fee, out
                # Jika quote 0, fallback ke full scan

        best_fee = V3_DEFAULT_FEE
        best_out = 0
        for _key, (fee, _label) in V3_FEE_TIERS.items():
            try:
                out = router_v3.functions.exactInputSingle((
                    Web3.to_checksum_address(token_in),
                    Web3.to_checksum_address(token_out),
                    fee,
                    Web3.to_checksum_address(sender),
                    int(time.time()) + 600,
                    amount_in,
                    0,
                    0,
                )).call({"from": sender, "value": value})
                if out and out > best_out:
                    best_out = out
                    best_fee = fee
            except Exception:
                continue
        self._fee_cache[cache_key] = (best_fee, now)
        log_info(f"[CACHE MISS] fee={best_fee} key={cache_key}")
        return best_fee, best_out

    def swap_native_to_token_v3(self, wallet, router_address, token_address, amount_ether, slippage=5, fee=None):
        """Swap native → ERC-20 via Uniswap V3 SwapRouter (exactInputSingle)."""
        info = self._chain_info()
        router_v3 = self._get_router_v3(router_address)
        router_v2 = self._get_router(router_address)
        weth = self._get_wrapped_native(router_v2, router_address)

        # Deteksi wrap
        if Web3.to_checksum_address(token_address) == Web3.to_checksum_address(weth):
            log_warn("Token tujuan = Wrapped Native Token!")
            log_info("Menggunakan wrap (deposit) langsung — lebih hemat gas")
            return self.wrap_native(wallet, amount_ether)

        amount_in = self.w3.to_wei(Decimal(str(amount_ether)), "ether")
        addr = Web3.to_checksum_address(wallet["address"])
        token_cs = Web3.to_checksum_address(token_address)
        weth_cs = Web3.to_checksum_address(weth)

        # Auto-detect fee tier terbaik jika tidak dispesifikasi
        if fee is None:
            log_info("Mencari fee tier V3 terbaik…")
            # value=amount_in agar router bisa wrap ETH→WETH untuk quote
            fee, est_out = self._find_best_fee_v3(router_v3, weth_cs, token_cs, amount_in, addr, value=amount_in)
            if est_out == 0:
                raise ValueError(
                    "Tidak bisa menemukan pool V3 untuk pair ini.\n"
                    "  Pastikan ada liquidity di Uniswap V3 untuk pair ini."
                )
            fee_label = next((l for _k, (f, l) in V3_FEE_TIERS.items() if f == fee), f"{fee/10000}%")
            log_info(f"Fee tier terbaik: {fee} ({fee_label}), estimasi output: {est_out}")
        else:
            # Quote dengan fee yang dispesifikasi
            try:
                est_out = router_v3.functions.exactInputSingle((
                    weth_cs, token_cs, fee, addr,
                    int(time.time()) + 600, amount_in, 0, 0,
                )).call({"from": addr, "value": amount_in})
            except Exception as e:
                raise ValueError(f"Quote V3 gagal — pool mungkin tidak ada untuk fee {fee}: {e}")

        min_out = int(est_out * (100 - slippage) / 100)
        deadline = int(time.time()) + 300

        log_info(f"[V3] Menukar {amount_ether} {info['symbol']} → token (fee={fee})")
        log_info(f"Estimasi: {est_out} | Min (slippage {slippage}%): {min_out}")

        tx = router_v3.functions.exactInputSingle((
            weth_cs, token_cs, fee, addr, deadline, amount_in, min_out, 0,
        )).build_transaction({
            "from": addr,
            "value": amount_in,
        })
        tx["_type"] = "swap_v3_native_ke_token"
        return self._build_and_send(tx, wallet["private_key"], wallet["address"])

    def swap_token_to_native_v3(self, wallet, router_address, token_address, amount, slippage=5, fee=None):
        """Swap ERC-20 → native via Uniswap V3 (exactInputSingle + unwrapWETH9 via multicall)."""
        info = self._chain_info()
        router_v3 = self._get_router_v3(router_address)
        router_v2 = self._get_router(router_address)
        weth = self._get_wrapped_native(router_v2, router_address)
        token = self.w3.eth.contract(address=Web3.to_checksum_address(token_address), abi=ERC20_ABI)

        # Deteksi unwrap
        if Web3.to_checksum_address(token_address) == Web3.to_checksum_address(weth):
            log_warn("Token sumber = Wrapped Native Token!")
            log_info("Menggunakan unwrap (withdraw) langsung — lebih hemat gas")
            return self.unwrap_native(wallet, amount)

        decimals = token.functions.decimals().call()
        symbol = token.functions.symbol().call()
        amount_raw = int(Decimal(str(amount)) * Decimal(10 ** decimals))
        addr = Web3.to_checksum_address(wallet["address"])
        token_cs = Web3.to_checksum_address(token_address)
        weth_cs = Web3.to_checksum_address(weth)
        router_addr_cs = Web3.to_checksum_address(router_address)

        self._approve_if_needed(token_address, router_address, wallet, amount_raw)

        # Auto-detect fee tier
        if fee is None:
            log_info("Mencari fee tier V3 terbaik…")
            fee, est_out = self._find_best_fee_v3(router_v3, token_cs, weth_cs, amount_raw, addr)
            if est_out == 0:
                raise ValueError("Tidak bisa menemukan pool V3 untuk pair ini.")
            fee_label = next((l for _k, (f, l) in V3_FEE_TIERS.items() if f == fee), f"{fee/10000}%")
            log_info(f"Fee tier terbaik: {fee} ({fee_label}), estimasi output: {est_out}")
        else:
            try:
                est_out = router_v3.functions.exactInputSingle((
                    token_cs, weth_cs, fee, router_addr_cs,
                    int(time.time()) + 600, amount_raw, 0, 0,
                )).call({"from": addr})
            except Exception as e:
                raise ValueError(
                    f"Quote V3 gagal (Token→Native) fee={fee}"
                    f": {e}"
                )

        min_out = int(est_out * (100 - slippage) / 100)
        deadline = int(time.time()) + 300

        log_info(f"[V3] Menukar {amount} {symbol} → {info['symbol']} (fee={fee})")
        log_info(f"Estimasi: {self.w3.from_wei(est_out, 'ether')} {info['symbol']} | Min: {self.w3.from_wei(min_out, 'ether')}")

        # Multicall: exactInputSingle (recipient=router) + unwrapWETH9 (kirim ke user) + refundETH (bersih sisa WETH/ETH di router)
        swap_data = router_v3.functions.exactInputSingle((
            token_cs, weth_cs, fee, router_addr_cs, deadline, amount_raw, min_out, 0,
        ))._encode_transaction_data()

        unwrap_data = router_v3.functions.unwrapWETH9(
            min_out, addr
        )._encode_transaction_data()

        cleanup_data = router_v3.functions.refundETH()._encode_transaction_data()

        # Encode via multicall (auto-detect SwapRouter vs SwapRouter02)
        tx = self._multicall_v3(router_v3, deadline, [swap_data, unwrap_data, cleanup_data], addr)
        tx["_type"] = "swap_v3_token_ke_native"
        return self._build_and_send(tx, wallet["private_key"], wallet["address"])

    def swap_token_to_token_v3(self, wallet, router_address, token_in, token_out, amount, slippage=5, fee=None):
        """Swap ERC-20 → ERC-20 via Uniswap V3 (exactInputSingle)."""
        router_v3 = self._get_router_v3(router_address)
        tok_in = self.w3.eth.contract(address=Web3.to_checksum_address(token_in), abi=ERC20_ABI)

        decimals = tok_in.functions.decimals().call()
        symbol = tok_in.functions.symbol().call()
        amount_raw = int(Decimal(str(amount)) * Decimal(10 ** decimals))
        addr = Web3.to_checksum_address(wallet["address"])
        in_cs = Web3.to_checksum_address(token_in)
        out_cs = Web3.to_checksum_address(token_out)

        self._approve_if_needed(token_in, router_address, wallet, amount_raw)

        # Auto-detect fee tier
        if fee is None:
            log_info("Mencari fee tier V3 terbaik…")
            fee, est_out = self._find_best_fee_v3(router_v3, in_cs, out_cs, amount_raw, addr)
            if est_out == 0:
                # Coba lewat WETH (multi-hop)
                log_info("Direct pair tidak ditemukan, mencoba rute via WETH…")
                raise ValueError(
                    "Tidak bisa menemukan pool V3 untuk pair langsung ini.\n"
                    "  Coba swap via native token (misal: token A → native → token B)."
                )
            fee_label = next((l for _k, (f, l) in V3_FEE_TIERS.items() if f == fee), f"{fee/10000}%")
            log_info(f"Fee tier terbaik: {fee} ({fee_label}), estimasi output: {est_out}")
        else:
            try:
                est_out = router_v3.functions.exactInputSingle((
                    in_cs, out_cs, fee, addr,
                    int(time.time()) + 600, amount_raw, 0, 0,
                )).call({"from": addr})
            except Exception as e:
                raise ValueError(
                    f"Quote V3 gagal (Token→Token) fee={fee}"
                    f": {e}"
                )

        min_out = int(est_out * (100 - slippage) / 100)
        deadline = int(time.time()) + 300

        log_info(f"[V3] Menukar {amount} {symbol} → token (fee={fee})")
        log_info(f"Estimasi: {est_out} | Min (slippage {slippage}%): {min_out}")

        tx = router_v3.functions.exactInputSingle((
            in_cs, out_cs, fee, addr, deadline, amount_raw, min_out, 0,
        )).build_transaction({"from": addr})
        tx["_type"] = "swap_v3_token_ke_token"
        return self._build_and_send(tx, wallet["private_key"], wallet["address"])

    # ── Bridge (Generik) ────────────────────────────────────────

    def bridge_native(self, wallet, bridge_contract, dest_chain_id, amount_ether, bridge_type="generic"):
        """
        Bridge token native via kontrak bridge.

        Mendukung beberapa tipe bridge:
        - op-l1-deposit  : OP Stack L1 → L2 (depositETHTo)
        - op-l2-withdraw : OP Stack L2 → L1 (bridgeETHTo)
        - arb-l1-deposit : Arbitrum L1 → L2 (depositEth)
        - generic        : Calldata generik bridge(uint256, address)
        """
        info = self._chain_info()
        amount_wei = self.w3.to_wei(Decimal(str(amount_ether)), "ether")
        addr = Web3.to_checksum_address(wallet["address"])
        contract_addr = Web3.to_checksum_address(bridge_contract)

        log_info(f"Bridging {amount_ether} {info['symbol']} → chain {dest_chain_id} [{bridge_type}]")

        if bridge_type in BRIDGE_ABIS:
            abi = BRIDGE_ABIS[bridge_type]
            contract = self.w3.eth.contract(address=contract_addr, abi=abi)

            if bridge_type == "op-l1-deposit":
                func = contract.functions.depositETHTo(addr, 200_000, b"")
            elif bridge_type == "op-l2-withdraw":
                func = contract.functions.bridgeETHTo(addr, 200_000, b"")
            elif bridge_type == "arb-l1-deposit":
                func = contract.functions.depositEth()
            else:
                func = None

            if func:
                tx = func.build_transaction({
                    "from": addr,
                    "value": amount_wei,
                })
                tx["_type"] = "bridge"
                return self._build_and_send(tx, wallet["private_key"], wallet["address"])

        # Fallback: generic bridge(uint256, address)
        log_warn("Menggunakan ABI generik — mungkin tidak kompatibel dengan semua bridge")
        selector = Web3.keccak(text="bridge(uint256,address)")[:4]
        data = (
            selector
            + int(dest_chain_id).to_bytes(32, "big")
            + bytes.fromhex(wallet["address"][2:].zfill(64))
        )

        tx = {
            "from": addr,
            "to": contract_addr,
            "value": amount_wei,
            "data": "0x" + data.hex(),
            "_type": "bridge",
        }
        return self._build_and_send(tx, wallet["private_key"], wallet["address"])

    def _request_faucet(self, chain_name: str, address: str) -> bool:
        """Attempt to get funds from a faucet for the given address on the given chain.
        
        REALITA 2025: Semua faucet public testnet butuh captcha/login/API key.
        Fungsi ini akan:
        1. Coba berbagai faucet API (kemungkinan besar gagal karena captcha)
        2. Generate manual claim links untuk user
        3. Return False jika semua gagal (caller harus handle gracefully)
        """
        # Faucet configurations + manual claim links
        FAUCETS = {
            "Sepolia": {
                "manual_links": [
                    "https://cloud.google.com/application/web3/faucet/ethereum/sepolia",
                    "https://www.alchemy.com/faucets/ethereum-sepolia",
                    "https://faucets.chain.link/sepolia",
                    "https://faucet.quicknode.com/ethereum/sepolia",
                ],
                "api_endpoints": [
                    # Tidak ada API publik yang work tanpa captcha di 2025
                ]
            },
            "Base Sepolia": {
                "manual_links": [
                    "https://www.coinbase.com/developer-platform/products/faucet",
                    "https://www.alchemy.com/faucets/base-sepolia",
                    "https://faucet.quicknode.com/base/sepolia",
                ],
                "api_endpoints": []
            },
            "Polygon Amoy": {
                "manual_links": [
                    "https://faucet.polygon.technology/",
                    "https://www.alchemy.com/faucets/polygon-amoy",
                ],
                "api_endpoints": []
            },
            "Arbitrum Sepolia": {
                "manual_links": [
                    "https://www.alchemy.com/faucets/arbitrum-sepolia",
                    "https://faucet.quicknode.com/arbitrum/sepolia",
                ],
                "api_endpoints": []
            },
            "Optimism Sepolia": {
                "manual_links": [
                    "https://www.alchemy.com/faucets/optimism-sepolia",
                    "https://faucet.quicknode.com/optimism/sepolia",
                ],
                "api_endpoints": []
            },
        }
        
        if chain_name not in FAUCETS:
            log_warn(f"No faucet configured for {chain_name}")
            return False
        
        faucet_config = FAUCETS[chain_name]
        api_endpoints = faucet_config.get("api_endpoints", [])
        manual_links = faucet_config.get("manual_links", [])
        
        # Rate limiting: wait at least 60 seconds between requests per address/chain
        now = time.time()
        last = self._faucet_last_request.get((chain_name, address), 0)
        if now - last < 60:
            wait = int(60 - (now - last))
            log_info(f"Faucet rate limiting: menunggu {wait} detik sebelum request ulang")
            time.sleep(wait)
        
        # Try API endpoints first
        for endpoint in api_endpoints:
            endpoint_name = endpoint.get("name", "Unknown")
            url = endpoint["url"]
            method = endpoint.get("method", "GET").upper()
            headers = endpoint.get("headers", {})
            data_func = endpoint.get("data")
            data = data_func(address) if data_func else None
            
            log_info(f"Trying {endpoint_name} faucet for {chain_name}...")
            
            try:
                if requests is not None:
                    if method == "POST":
                        resp = requests.post(url, json=data, headers=headers, timeout=30)
                    else:
                        resp = requests.get(url, params=data, headers=headers, timeout=30)
                    
                    # Success - verify it's actually JSON response, not HTML
                    if resp.status_code in (200, 201, 202):
                        # Check if response is JSON (not HTML page)
                        if 'application/json' in resp.headers.get('Content-Type', ''):
                            log_ok(f"✅ Faucet request successful via {endpoint_name} for {address} on {chain_name}")
                            self._faucet_last_request[(chain_name, address)] = time.time()
                            return True
                        else:
                            log_warn(f"⚠️  {endpoint_name} returned HTML (captcha/login required)")
                            continue
                    
                    # Captcha/Cloudflare detected
                    elif resp.status_code in (403, 405):
                        log_warn(f"⚠️  {endpoint_name} blocked (captcha/cloudflare): {resp.status_code}")
                        continue
                    
                    # Other error
                    else:
                        log_err(f"❌ {endpoint_name} failed: {resp.status_code}")
                        continue
                
                else:
                    # Fallback to urllib
                    import urllib.request
                    import urllib.error
                    
                    data_encoded = None
                    if data is not None and method == "POST":
                        data_encoded = json.dumps(data).encode("utf-8")
                    elif data is not None and method == "GET":
                        log_warn("GET with data not supported in fallback")
                        continue
                    
                    req = urllib.request.Request(url, data=data_encoded, headers=headers, method=method)
                    try:
                        with urllib.request.urlopen(req, timeout=30) as resp:
                            if 200 <= resp.status < 300:
                                content_type = resp.headers.get('Content-Type', '')
                                if 'application/json' in content_type:
                                    log_ok(f"✅ Faucet request successful via {endpoint_name} for {address} on {chain_name}")
                                    self._faucet_last_request[(chain_name, address)] = time.time()
                                    return True
                                else:
                                    log_warn(f"⚠️  {endpoint_name} returned HTML (captcha/login required)")
                                    continue
                    except urllib.error.HTTPError as e:
                        log_err(f"❌ {endpoint_name} failed: {e.code}")
                        continue
                    except Exception as e:
                        log_err(f"❌ {endpoint_name} error: {e}")
                        continue
            
            except Exception as e:
                log_err(f"❌ {endpoint_name} exception: {e}")
                continue
        
        # No API endpoints or all failed - show manual claim links
        if manual_links:
            log_warn(f"⚠️  Auto-faucet tidak tersedia untuk {chain_name} (captcha/login required)")
            log_info(f"💡 Manual claim untuk address {address}:")
            for i, link in enumerate(manual_links, 1):
                log_info(f"   {i}. {link}")
        
        return False

    def _ensure_minimum_balance(self, wallet, required_amount):
        """Ensure wallet has minimum balance before transaction.
        
        Args:
            wallet: Dict with 'address' key
            required_amount: Amount needed for transaction (in ether)
        
        Returns:
            True if balance sufficient or faucet succeeded, False otherwise
        """
        from decimal import Decimal
        
        address = wallet["address"]
        min_balance = Decimal("0.001")  # Minimum balance threshold
        
        # Check current balance
        try:
            balance_wei = self.w3.eth.get_balance(address)
            balance_eth = Decimal(str(self.w3.from_wei(balance_wei, "ether")))
        except Exception as e:
            log_err(f"Failed to check balance: {e}")
            return False
        
        # Check if balance is sufficient
        if balance_eth >= min_balance:
            return True
        
        # Balance insufficient - try faucet
        log_warn(f"⚠️  Balance rendah: {balance_eth} ETH (min: {min_balance} ETH)")
        
        # Only try faucet on testnet
        chain_info = self._chain_info()
        if not chain_info.get("testnet", False):
            log_warn("⚠️  Bukan testnet, skip auto-faucet")
            return False
        
        chain_name = chain_info.get("name", self.chain_name)
        log_info(f"🔄 Mencoba auto-faucet untuk {chain_name}...")
        
        # Try faucet up to 3 times
        for attempt in range(1, 4):
            log_info(f"Attempt {attempt}/3...")
            if self._request_faucet(chain_name, address):
                # Wait a bit for transaction to propagate
                time.sleep(5)
                # Re-check balance
                try:
                    new_balance_wei = self.w3.eth.get_balance(address)
                    new_balance_eth = Decimal(str(self.w3.from_wei(new_balance_wei, "ether")))
                    log_ok(f"✅ Balance after faucet: {new_balance_eth} ETH")
                    if new_balance_eth >= min_balance:
                        return True
                except Exception as e:
                    log_err(f"Failed to re-check balance: {e}")
        
        # All attempts failed
        log_err(f"❌ Auto-faucet gagal. Balance tetap: {balance_eth} ETH")
        return False

