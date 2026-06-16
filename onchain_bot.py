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
from datetime import datetime
from decimal import Decimal

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

VERSION = "1.9.0"

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
    41455:    ("Monad Testnet",     "MON",   "https://testnet.monadexplorer.com",          "testnet", "https://testnet-rpc.monad.xyz"),
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
    # ── Mainnets ────────────────────────────────────────────────
    "Ethereum": [
        ("uniswap-v2",   "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D", "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"),
        ("uniswap-v3",   "0xE592427A0AEce92De3Edee1F18E0157C05861564", "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"),
        ("sushiswap",    "0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F", "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"),
    ],
    "BSC": [
        ("pancakeswap",  "0x10ED43C718714eb63d5aA57B78B54704E256024E", "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c"),
        ("uniswap-v3",   "0xB971eF87ede563556b2ED4b1C0b0019111Dd85d2", "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c"),
    ],
    "Polygon": [
        ("quickswap",    "0xa5E0829CaCEd8fFDD4De3c43696c57F7D7A678ff", "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270"),
        ("sushiswap",    "0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506", "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270"),
        ("uniswap-v3",   "0xE592427A0AEce92De3Edee1F18E0157C05861564", "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270"),
    ],
    "Arbitrum One": [
        ("uniswap-v3",   "0xE592427A0AEce92De3Edee1F18E0157C05861564", "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1"),
        ("sushiswap",    "0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506", "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1"),
        ("camelot",      "0xc873fEcbd354f5A56E00E710B90EF4201db2448d", "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1"),
    ],
    "Optimism": [
        ("uniswap-v3",   "0xE592427A0AEce92De3Edee1F18E0157C05861564", "0x4200000000000000000000000000000000000006"),
        ("velodrome",    "0xa062aE8A9c5e11aaA026fc2670B0D65cCc8B2858", "0x4200000000000000000000000000000000000006"),
    ],
    "Avalanche": [
        ("trader-joe",   "0x60aE616a2155Ee3d9A68541Ba4544862310933d4", "0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7"),
        ("pangolin",     "0xE54Ca86531e17Ef3616d22Ca28b0D458b6C89106", "0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7"),
    ],
    "Fantom": [
        ("spookyswap",   "0xF491e7B69E4244ad4002BC14e878a34207E38c29", "0x21be370D5312f44cB42ce377BC9b8a0cEF1A4C83"),
        ("spiritswap",   "0x16327E3FbDaCA3bcF7E38F5Af2599D2DDc33aE52", "0x21be370D5312f44cB42ce377BC9b8a0cEF1A4C83"),
    ],
    "Base": [
        ("uniswap-v3",   "0x2626664c2603336E57B271c5C0b26F421741e481", "0x4200000000000000000000000000000000000006"),
        ("aerodrome",    "0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43", "0x4200000000000000000000000000000000000006"),
        ("sushiswap",    "0x6BDED42c6DA8FBf0d2bA55B2fa120C5e0c8D7891", "0x4200000000000000000000000000000000000006"),
    ],
    "Linea": [
        ("syncswap",     "0x80e38291e06339d10AAB483C65695D004dBD5C69", "0xe5D7C2a44FfDDf6b295A15c148167daaAf5Cf34f"),
    ],
    "Scroll": [
        ("syncswap",     "0x80e38291e06339d10AAB483C65695D004dBD5C69", "0x5300000000000000000000000000000000000004"),
    ],
    "Sonic": [
        ("spookyswap",   "0x12AA6ec7d603DC79Ea6A12a0F2C488E6C4eFC170", ""),
    ],
    "Mantle": [
        ("agni-finance", "0x319B69888b0d11cEC22caA5034e25FfFBDc88421", "0x78c1b0C915c4FAA5FffA6CAbf0219DA63d7f4cb8"),
    ],
    # ── Testnets ────────────────────────────────────────────────
    "Sepolia": [
        ("uniswap-v2",   "0xeE567Fe1712Faf6149d80dA1E6934E354124CfE3", "0xfFf9976782d46CC05630D1f6eBAb18b2324d6B14"),
        ("uniswap-v3",   "0x3bFA4769FB09eefC5a80d6E87c3B9C650f7Ae48E", "0xfFf9976782d46CC05630D1f6eBAb18b2324d6B14"),
    ],
    "Base Sepolia": [
        ("uniswap-v2",   "0x1689E7B1F10000AE47eBfE339a4f69dECd19F602", "0x4200000000000000000000000000000000000006"),
    ],
    "Arbitrum Sepolia": [
        ("uniswap-v3",   "0x101F443B4d1b059569D643917553c771E1b9663E", "0x980B62Da83eFf3D4576C647993b0c1V7aaf96816"),
    ],
    "BSC Testnet": [
        ("pancakeswap",  "0xD99D1c33F9fC3444f8101754aBC46c52416550D1", "0xae13d989daC2f0dEbFf460aC112a837C89BAa7cd"),
    ],
    "Avalanche Fuji": [
        ("trader-joe",   "0xd7f655E3376cE2D7A2b08fF01Eb3B1023191A901", "0xd00ae08403B9bbb9124bB305C09058E32C39A48c"),
    ],
    "Monad Testnet": [
        ("zkswap-v2",    "0x3be49777B2Dc6cED93d4BFa0Ad8CA1a0C2114917", "0x760AfE86E5De5fa0Ee542fc7B7B713e1c5425701"),
        ("bean-swap",    "0xCa810D095e90Daae6e867c19DF3A57F440BDB0D7", "0x760AfE86E5De5fa0Ee542fc7B7B713e1c5425701"),
    ],
    "monad-testnet": [
        ("zkswap-v2",    "0x3be49777B2Dc6cED93d4BFa0Ad8CA1a0C2114917", "0x760AfE86E5De5fa0Ee542fc7B7B713e1c5425701"),
        ("bean-swap",    "0xCa810D095e90Daae6e867c19DF3A57F440BDB0D7", "0x760AfE86E5De5fa0Ee542fc7B7B713e1c5425701"),
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

    def __init__(self, config: Config):
        self.config = config
        self.w3: Web3 | None = None
        self.current_chain: str | None = None
        self.tx_history: list = []
        self._load_history()

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

        # Harga gas — coba EIP-1559 dulu, fallback ke legacy
        try:
            base_fee = self.w3.eth.get_block("latest").get("baseFeePerGas")
            if base_fee:
                priority = self.w3.eth.max_priority_fee
                tx["maxFeePerGas"] = base_fee * 2 + priority
                tx["maxPriorityFeePerGas"] = priority
                tx.pop("gasPrice", None)
            else:
                raise ValueError("tidak ada baseFee")
        except Exception:
            tx["gasPrice"] = self.w3.eth.gas_price
            tx.pop("maxFeePerGas", None)
            tx.pop("maxPriorityFeePerGas", None)

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

    # ── Swap (Kompatibel Uniswap V2) ───────────────────────────

    def _get_router(self, router_address):
        return self.w3.eth.contract(
            address=Web3.to_checksum_address(router_address), abi=ROUTER_V2_ABI
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

        # 2) Coba WETH() dari router contract
        try:
            weth = router.functions.WETH().call()
            if weth and weth != "0x" + "0" * 40:
                return weth
        except Exception:
            pass

        raise ValueError(
            "Tidak bisa mendeteksi alamat Wrapped Native Token!\n"
            "  Router ini mungkin tidak punya fungsi WETH().\n"
            "  Solusi: Masuk ke Pengaturan → Tambah DEX Router → isi alamat WETH/WMON manual,\n"
            "  atau hapus router ini dan tambahkan ulang dengan alamat WETH/WMON yang benar."
        )

    def wrap_native(self, wallet, amount_ether):
        """Wrap native token → wrapped token (deposit ke kontrak WETH/WMON)."""
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


# ═══════════════════════════════════════════════════════════════
# PENJADWAL TUGAS
# ═══════════════════════════════════════════════════════════════

class Scheduler:
    """Penjadwal tugas latar belakang untuk transaksi berulang.

    Saat berjalan, output disimpan ke buffer agar tidak mengganggu
    menu interaktif. Pengguna bisa lihat log via 'Lihat Log Jadwal'.
    """

    def __init__(self):
        self.tasks: list[dict] = []
        self._running = False
        self._thread: threading.Thread | None = None
        self._log: list[str] = []
        self._log_lock = threading.Lock()
        self._total_runs = 0
        self._total_ok = 0
        self._total_err = 0

    def add(self, name, func, interval_sec, *args, **kwargs):
        self.tasks.append({
            "name": name,
            "func": func,
            "interval": interval_sec,
            "args": args,
            "kwargs": kwargs,
            "next_run": time.time(),
            "active": True,
            "runs": 0,
            "errors": 0,
        })
        log_ok(f"Dijadwalkan: '{name}' setiap {interval_sec} detik")

    def remove(self, index):
        if 0 <= index < len(self.tasks):
            t = self.tasks.pop(index)
            log_ok(f"Dihapus: '{t['name']}'")

    @property
    def is_running(self):
        return self._running

    def status_line(self):
        """Status satu baris untuk ditampilkan di menu utama."""
        if not self._running:
            return None
        active = sum(1 for t in self.tasks if t["active"])
        next_t = ""
        soonest = None
        now = time.time()
        for t in self.tasks:
            if t["active"]:
                remaining = max(0, t["next_run"] - now)
                if soonest is None or remaining < soonest:
                    soonest = remaining
                    next_t = t["name"]
        if soonest is not None:
            m, s = divmod(int(soonest), 60)
            h, m = divmod(m, 60)
            if h > 0:
                eta = f"{h}j{m:02d}m"
            elif m > 0:
                eta = f"{m}m{s:02d}d"
            else:
                eta = f"{s}d"
            return f"⏰ Jadwal: {C.G}BERJALAN{C.END} — {active} tugas — selanjutnya '{next_t}' dalam {eta} — ✅{self._total_ok} ❌{self._total_err}"
        return f"⏰ Jadwal: {C.G}BERJALAN{C.END} — {active} tugas"

    def start(self):
        if not self.tasks:
            log_warn("Tidak ada tugas untuk dijalankan")
            return
        if self._running:
            log_warn("Penjadwal sudah berjalan")
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        log_ok("Penjadwal dimulai di latar belakang")
        log_info("Kamu bisa kembali ke Menu Utama dan tetap pakai bot!")
        log_info("Output jadwal tersimpan — lihat via 'Lihat Log Jadwal'")

    def stop(self):
        self._running = False
        log_ok("Penjadwal dihentikan")

    def show(self):
        if not self.tasks:
            log_info("Tidak ada tugas terjadwal")
            return
        now = time.time()
        print(f"\n  {C.BOLD}Tugas Terjadwal:{C.END}")
        if self._running:
            print(f"  {C.G}● BERJALAN{C.END}  (eksekusi: {self._total_runs} | berhasil: {self._total_ok} | gagal: {self._total_err})")
        for i, t in enumerate(self.tasks):
            st = f"{C.G}aktif{C.END}" if t["active"] else f"{C.R}dijeda{C.END}"
            remaining = max(0, t["next_run"] - now) if self._running else 0
            m, s = divmod(int(remaining), 60)
            h, m = divmod(m, 60)
            if self._running and t["active"]:
                if h > 0:
                    eta = f" — berikutnya {h}j{m:02d}m{s:02d}d"
                else:
                    eta = f" — berikutnya {m}m{s:02d}d"
            else:
                eta = ""
            print(f"    {i+1}. {t['name']} — setiap {t['interval']}d — {st} — jalan: {t['runs']}x{eta}")

    def show_log(self, n=30):
        """Tampilkan N entri terakhir log penjadwal."""
        with self._log_lock:
            entries = list(self._log[-n:])
        if not entries:
            log_info("Log penjadwal kosong")
            return
        print(f"\n  {C.BOLD}📋 Log Penjadwal ({len(entries)} entri terakhir):{C.END}")
        print(f"  {C.DIM}{'─' * 55}{C.END}")
        for line in entries:
            print(f"  {line}")
        print(f"  {C.DIM}{'─' * 55}{C.END}")

    def _bg_log(self, msg, color=C.CY):
        """Simpan ke buffer alih-alih print (untuk thread latar belakang)."""
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"{C.DIM}[{ts}]{C.END} {color}{msg}{C.END}"
        with self._log_lock:
            self._log.append(line)
            if len(self._log) > 200:
                self._log = self._log[-200:]

    def _loop(self):
        """Loop latar belakang — semua output ke buffer, bukan stdout."""
        while self._running:
            now = time.time()
            for t in self.tasks:
                if t["active"] and now >= t["next_run"]:
                    self._bg_log(f"▶ Menjalankan: {t['name']}")
                    self._total_runs += 1
                    try:
                        import io
                        old_stdout = sys.stdout
                        capture = io.StringIO()
                        sys.stdout = capture
                        try:
                            t["func"](*t["args"], **t["kwargs"])
                        finally:
                            sys.stdout = old_stdout
                        output = capture.getvalue().strip()
                        if output:
                            for line in output.split("\n")[-10:]:
                                self._bg_log(f"  {line.strip()}", C.DIM)
                        t["runs"] += 1
                        self._total_ok += 1
                        self._bg_log(f"✅ Selesai: {t['name']} (jalan ke-{t['runs']})", C.G)
                    except Exception as e:
                        sys.stdout = old_stdout if 'old_stdout' in dir() else sys.__stdout__
                        t["errors"] += 1
                        self._total_err += 1
                        self._bg_log(f"❌ Gagal: {t['name']}: {e}", C.R)
                    t["next_run"] = now + t["interval"]
            time.sleep(1)


# ═══════════════════════════════════════════════════════════════
# CLI INTERAKTIF
# ═══════════════════════════════════════════════════════════════

class CLI:
    """Antarmuka baris perintah interaktif."""

    def __init__(self):
        self.config = Config()
        self.engine = BlockchainEngine(self.config)
        self.scheduler = Scheduler()

    # ── Loop Utama ──────────────────────────────────────────────

    def run(self):
        clear_screen()
        banner()

        while True:
            if self.scheduler.is_running:
                print(f"\n  {self.scheduler.status_line()}")
            choice = menu_select("MENU UTAMA", [
                ("1", "⚙️  Pengaturan & Konfigurasi"),
                ("2", "💸 Kirim Token Native"),
                ("3", "📤 Multi-Kirim (Batch)"),
                ("4", "🎲 Kirim ke Alamat Acak"),
                ("5", "🔄 Swap Token (DEX)"),
                ("6", "🌉 Bridge Token"),
                ("7", "⏰ Tugas Terjadwal"),
                ("8", "💰 Cek Saldo"),
                ("9", "📜 Riwayat Transaksi"),
                ("0", "🚪 Keluar"),
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
                    log_info("Sampai jumpa! 👋")
                    break
                elif choice in actions:
                    actions[choice]()
            except KeyboardInterrupt:
                print()
                log_warn("Terganggu — kembali ke menu")
            except Exception as e:
                log_err(f"Error: {e}")
                if os.environ.get("DEBUG"):
                    traceback.print_exc()

    # ── Pemilih Umum ────────────────────────────────────────────

    def _pick_chain_name(self, label="Pilih Chain", filter_type=None):
        """Tampilkan daftar chain bernomor dan kembalikan nama chain yang dipilih (tanpa koneksi)."""
        chains = self.config.get_chains()
        if filter_type:
            chains = {n: c for n, c in chains.items() if c.get("type") == filter_type}
        if not chains:
            log_warn("Tidak ada chain tersedia.")
            return None

        # Urutkan: mainnet dulu, lalu testnet, lalu alphabetical
        sorted_chains = sorted(chains.items(), key=lambda x: (0 if x[1].get("type") == "mainnet" else 1, x[0].lower()))

        keyword = prompt(f"{label} — ketik kata kunci untuk filter (atau Enter untuk lihat semua)", "")
        if keyword:
            sorted_chains = [(n, c) for n, c in sorted_chains
                             if keyword.lower() in n.lower() or keyword.lower() in c["symbol"].lower()]
            if not sorted_chains:
                log_err(f"Tidak ditemukan chain dengan kata kunci '{keyword}'")
                return None

        print(f"\n  {C.BOLD}{label}:{C.END}")
        for i, (name, c) in enumerate(sorted_chains, 1):
            tag = f"{C.G}mainnet{C.END}" if c.get("type") == "mainnet" else f"{C.Y}testnet{C.END}"
            print(f"    {C.BOLD}{i:3}.{C.END} {C.CY}{name}{C.END} ({c['symbol']}) — {tag}")
        print()

        try:
            idx = int(prompt("Ketik nomor")) - 1
            if 0 <= idx < len(sorted_chains):
                return sorted_chains[idx][0]
            else:
                log_err("Nomor tidak valid")
                return None
        except ValueError:
            log_err("Masukkan angka yang valid")
            return None

    def _select_chain(self):
        chains = self.config.get_chains()
        if not chains:
            log_warn("Belum ada chain! Masuk ke Pengaturan → Tambah Chain dulu.")
            return None

        choice = menu_select("Pilih Chain", [
            ("1", "🌐 Lihat Mainnet"),
            ("2", "🧪 Lihat Testnet"),
            ("3", "📋 Lihat Semua"),
            ("4", "🔍 Cari Chain"),
        ])

        if choice == "1":
            self._print_chains(filter_type="mainnet")
        elif choice == "2":
            self._print_chains(filter_type="testnet")
        elif choice == "3":
            self._print_chains()
        elif choice == "4":
            keyword = prompt("Kata kunci (nama/simbol)").lower()
            matches = {n: c for n, c in chains.items()
                       if keyword in n.lower() or keyword in c["symbol"].lower()}
            if not matches:
                log_err(f"Tidak ditemukan chain dengan kata kunci '{keyword}'")
                return None
            self._print_chains(custom=matches)
        else:
            self._print_chains()

        name = prompt("Ketik nama chain")
        if name not in chains:
            # Coba cari case-insensitive
            for cn in chains:
                if cn.lower() == name.lower():
                    name = cn
                    break
            else:
                log_err(f"Chain '{name}' tidak ditemukan")
                return None
        if not self.engine.connect(name):
            return None
        return name

    def _select_wallet(self, allow_multi=False):
        wallets = self.config.get_wallets()
        if not wallets:
            log_warn("Belum ada wallet! Masuk ke Pengaturan → Tambah Wallet dulu.")
            return None
        self._print_wallets()
        if allow_multi:
            choice = prompt("Pilih wallet (nomor, 'all', atau 'random')")
            if choice.lower() == "all":
                return wallets, "round-robin"
            elif choice.lower() == "random":
                return wallets, "random"
            idx = int(choice) - 1
            return [wallets[idx]], "single"
        else:
            idx = int(prompt("Pilih nomor wallet")) - 1
            return wallets[idx]

    def _select_amount(self):
        choice = menu_select("Jumlah (token native)", [
            ("1", "0.1"),
            ("2", "0.001"),
            ("3", "0.0001"),
            ("4", "Kustom"),
        ])
        if choice in VALUE_PRESETS:
            return VALUE_PRESETS[choice]
        elif choice == "4":
            return prompt("Masukkan jumlah")
        return None

    # ── Printer ─────────────────────────────────────────────────

    def _print_chains(self, filter_type=None, custom=None):
        chains = custom if custom else self.config.get_chains()
        if filter_type:
            chains = {n: c for n, c in chains.items() if c.get("type") == filter_type}

        mainnets = {n: c for n, c in chains.items() if c.get("type") == "mainnet"}
        testnets = {n: c for n, c in chains.items() if c.get("type") == "testnet"}

        def _print_group(label, group):
            if not group:
                return
            print(f"\n  {C.BOLD}{label} ({len(group)}):{C.END}")
            for name, c in sorted(group.items()):
                print(f"    • {C.CY}{name}{C.END} ({c['symbol']}) — ID {c['chain_id']}")

        if mainnets:
            _print_group("🌐 Mainnet", mainnets)
        if testnets:
            _print_group("🧪 Testnet", testnets)
        print()

    def _print_wallets(self):
        wallets = self.config.get_wallets()
        print(f"\n  {C.BOLD}Daftar Wallet:{C.END}")
        for i, w in enumerate(wallets, 1):
            print(f"    {i}. {C.CY}{w['name']}{C.END} — {short_addr(w['address'])}")

    # ── Menu Pengaturan ─────────────────────────────────────────

    def _menu_setup(self):
        while True:
            choice = menu_select("⚙️  PENGATURAN", [
                ("1", "Tambah Chain (RPC)"),
                ("2", "Tambah Wallet"),
                ("3", "Tambah DEX Router"),
                ("4", "Tambah Token"),
                ("5", "Tambah Kontrak Bridge"),
                ("6", "Lihat Semua Konfigurasi"),
                ("7", "🗑 Hapus Konfigurasi"),
                ("0", "← Kembali"),
            ])
            if choice == "0":
                break

            elif choice == "1":
                sub = menu_select("Tambah Chain", [
                    ("1", "🔍 Masukkan RPC (auto-deteksi)"),
                    ("2", "✏️  Masukkan manual (chain kustom)"),
                    ("3", "🔄 Ganti RPC chain yang sudah ada"),
                ])
                if sub == "1":
                    rpc = prompt("URL RPC")
                    if not rpc:
                        continue
                    log_info("Mendeteksi chain...")
                    detected = detect_chain(rpc)
                    if detected:
                        cid, d_name, d_symbol, d_explorer, d_net = detected
                        log_ok(f"Terdeteksi: {d_name} (Chain ID: {cid}, {d_symbol}, {d_net})")
                        name     = prompt("Nama chain", d_name)
                        chain_id = prompt("Chain ID", str(cid))
                        symbol   = prompt("Simbol native", d_symbol)
                        explorer = prompt("URL Explorer", d_explorer)
                        net_type = prompt("Tipe (mainnet/testnet)", d_net)
                    else:
                        log_warn("Tidak bisa deteksi otomatis. Masukkan manual:")
                        name     = prompt("Nama chain (misal: ethereum, bsc-testnet)")
                        chain_id = prompt("Chain ID (misal: 1, 56, 421614)")
                        symbol   = prompt("Simbol native (misal: ETH, BNB)")
                        explorer = prompt("URL Explorer (opsional)", "")
                        net_type = prompt("Tipe (mainnet/testnet)", "mainnet")
                    self.config.add_chain(name, rpc, chain_id, symbol, explorer, net_type)
                    log_ok(f"Chain '{name}' berhasil ditambahkan!")
                elif sub == "2":
                    name     = prompt("Nama chain")
                    rpc      = prompt("URL RPC")
                    chain_id = prompt("Chain ID")
                    symbol   = prompt("Simbol native")
                    explorer = prompt("URL Explorer (opsional)", "")
                    net_type = prompt("Tipe (mainnet/testnet)", "mainnet")
                    self.config.add_chain(name, rpc, chain_id, symbol, explorer, net_type)
                    log_ok(f"Chain '{name}' berhasil ditambahkan!")
                elif sub == "3":
                    self._print_chains()
                    name = prompt("Nama chain yang mau diganti RPC-nya")
                    chains = self.config.get_chains()
                    matched = None
                    for cn in chains:
                        if cn.lower() == name.lower():
                            matched = cn
                            break
                    if not matched:
                        log_err(f"Chain '{name}' tidak ditemukan")
                        continue
                    old_rpc = chains[matched].get("rpc", "?")
                    log_info(f"RPC saat ini: {old_rpc}")
                    new_rpc = prompt("RPC baru")
                    if new_rpc:
                        c = chains[matched]
                        self.config.add_chain(matched, new_rpc, c["chain_id"], c["symbol"], c.get("explorer",""), c.get("type","mainnet"))
                        log_ok(f"RPC untuk '{matched}' berhasil diganti!")

            elif choice == "2":
                label   = prompt("Label wallet (misal: utama, hot1)")
                address = prompt("Alamat (0x…)")
                pk      = prompt("Private key")
                try:
                    self.config.add_wallet(label, address, pk)
                    log_ok(f"Wallet '{label}' berhasil ditambahkan!")
                except Exception as e:
                    log_err(f"Wallet tidak valid: {e}")

            elif choice == "3":
                if not self.config.get_chains():
                    log_warn("Tambah chain dulu!"); continue
                log_info("Pilih chain untuk DEX Router:")
                chain = self._pick_chain_name("Chain")
                if not chain:
                    continue
                # Cek apakah ada DEX yang dikenali untuk chain ini
                known = KNOWN_DEX_ROUTERS.get(chain, [])
                if known:
                    print(f"\n  {C.BOLD}DEX yang dikenali untuk {C.CY}{chain}{C.END}{C.BOLD}:{C.END}")
                    for i, (dname, daddr, dweth) in enumerate(known, 1):
                        print(f"    {C.BOLD}{i}.{C.END} {C.CY}{dname}{C.END} — {short_addr(daddr)}")
                    print(f"    {C.BOLD}{len(known)+1}.{C.END} {C.Y}✏️  Masukkan manual{C.END}")
                    print()
                    try:
                        pick = int(prompt("Pilih nomor")) - 1
                        if 0 <= pick < len(known):
                            dname, daddr, dweth = known[pick]
                            self.config.add_dex_router(chain, dname, daddr, dweth)
                            log_ok(f"DEX '{dname}' ditambahkan di {chain}! (otomatis)")
                            continue
                    except ValueError:
                        pass
                # Manual input
                name  = prompt("Nama DEX (misal: uniswap-v2, pancakeswap)")
                addr  = prompt("Alamat kontrak router")
                if not addr:
                    log_err("Alamat kontrak router wajib diisi!"); continue
                weth  = prompt("Alamat WETH (opsional, kosongkan untuk auto)", "")
                self.config.add_dex_router(chain, name, addr, weth)
                log_ok(f"DEX '{name}' ditambahkan di {chain}!")

            elif choice == "4":
                if not self.config.get_chains():
                    log_warn("Tambah chain dulu!"); continue
                log_info("Pilih chain untuk Token:")
                chain = self._pick_chain_name("Chain")
                if not chain:
                    continue
                # Cek apakah ada token yang dikenali untuk chain ini
                known_t = KNOWN_TOKENS.get(chain, [])
                if known_t:
                    print(f"\n  {C.BOLD}Token yang dikenali untuk {C.CY}{chain}{C.END}{C.BOLD}:{C.END}")
                    for i, (tsym, taddr, tdec) in enumerate(known_t, 1):
                        print(f"    {C.BOLD}{i}.{C.END} {C.CY}{tsym}{C.END} — {short_addr(taddr)} ({tdec}d)")
                    print(f"    {C.BOLD}{len(known_t)+1}.{C.END} {C.Y}✏️  Masukkan manual{C.END}")
                    print()
                    try:
                        pick = int(prompt("Pilih nomor")) - 1
                        if 0 <= pick < len(known_t):
                            tsym, taddr, tdec = known_t[pick]
                            self.config.add_token(chain, tsym, taddr, tdec)
                            log_ok(f"Token '{tsym}' ditambahkan di {chain}! (otomatis)")
                            continue
                    except ValueError:
                        pass
                # Manual input
                sym   = prompt("Simbol token (misal: USDC)")
                addr  = prompt("Alamat kontrak token")
                if not addr:
                    log_err("Alamat kontrak token wajib diisi!"); continue
                dec   = prompt("Desimal", "18")
                self.config.add_token(chain, sym, addr, dec)
                log_ok(f"Token '{sym}' ditambahkan di {chain}!")

            elif choice == "5":
                self._setup_bridge()

            elif choice == "6":
                self._print_full_config()

            elif choice == "7":
                self._menu_delete()

    def _print_full_config(self):
        print(f"\n  {'═' * 55}")
        self._print_chains()
        self._print_wallets()
        routers = self.config.data.get("dex_routers", {})
        if routers:
            print(f"\n  {C.BOLD}DEX Router:{C.END}")
            for ch, dexes in routers.items():
                for nm, info in dexes.items():
                    print(f"    • {C.CY}{ch}/{nm}{C.END} — {short_addr(info['address'])}")
        tokens = self.config.data.get("tokens", {})
        if tokens:
            print(f"\n  {C.BOLD}Token:{C.END}")
            for ch, toks in tokens.items():
                for sym, info in toks.items():
                    print(f"    • {C.CY}{ch}/{sym}{C.END} — {short_addr(info['address'])} ({info['decimals']}d)")
        bridges = self.config.get_bridges()
        if bridges:
            print(f"\n  {C.BOLD}Bridge:{C.END}")
            for nm, info in bridges.items():
                contract_str = short_addr(info['contract']) if info.get('contract') else "(belum ada kontrak)"
                print(f"    • {C.CY}{nm}{C.END} — {info['from_chain']} → {info['to_chain']} — {contract_str}")
        print(f"  {'═' * 55}")

    # ── Setup Bridge (auto-detect + manual) ──────────────────────

    def _setup_bridge(self):
        """Setup bridge baru — otomatis deteksi rute yang dikenali, atau manual."""
        log_info("Pilih chain asal:")
        cfrom = self._pick_chain_name("Chain Asal")
        if not cfrom:
            return
        log_info("Pilih chain tujuan:")
        cto = self._pick_chain_name("Chain Tujuan")
        if not cto:
            return

        route_key = (cfrom, cto)
        known = KNOWN_BRIDGE_ROUTES.get(route_key, [])

        if known:
            print(f"\n  {C.BOLD}Bridge yang dikenali untuk {C.CY}{cfrom} → {cto}{C.END}{C.BOLD}:{C.END}")
            for i, (pname, paddr, ptype) in enumerate(known, 1):
                type_label = {
                    "op-l1-deposit": "OP Stack (L1→L2)",
                    "op-l2-withdraw": "OP Stack (L2→L1)",
                    "arb-l1-deposit": "Arbitrum (L1→L2)",
                }.get(ptype, ptype)
                print(f"    {C.BOLD}{i}.{C.END} {C.CY}{pname}{C.END}")
                print(f"       Kontrak: {short_addr(paddr)} | Tipe: {type_label}")
            print(f"    {C.BOLD}{len(known)+1}.{C.END} {C.Y}✏️  Setup manual{C.END}")
            print()

            try:
                pick = int(prompt("Pilih nomor")) - 1
                if 0 <= pick < len(known):
                    pname, paddr, ptype = known[pick]
                    bname = f"{cfrom.lower()}-{cto.lower()}".replace(" ", "-")
                    self.config.add_bridge(bname, cfrom, cto, paddr, ptype)
                    log_ok(f"Bridge '{bname}' ditambahkan! ({cfrom} → {cto})")
                    log_ok(f"Kontrak & ABI otomatis: {pname} [{ptype}]")
                    return
            except ValueError:
                pass

        # Manual setup
        if not known:
            log_info(f"Tidak ada bridge yang dikenali untuk {cfrom} → {cto}")
        name = prompt("Nama bridge (misal: stargate, hop, custom)")
        addr = prompt("Alamat kontrak bridge (kosongkan jika belum tahu)", "")
        self.config.add_bridge(name, cfrom, cto, addr, "generic")
        log_ok(f"Bridge '{name}' berhasil ditambahkan! ({cfrom} → {cto})")
        if not addr:
            log_warn("Kontrak belum diisi — nanti diminta saat eksekusi bridge")

    # ── Hapus Konfigurasi ────────────────────────────────────────

    def _menu_delete(self):
        while True:
            choice = menu_select("🗑 HAPUS KONFIGURASI", [
                ("1", "Hapus Chain"),
                ("2", "Hapus Wallet"),
                ("3", "Hapus Bridge"),
                ("4", "Hapus DEX Router"),
                ("5", "Hapus Token"),
                ("0", "← Kembali"),
            ])
            if choice == "0":
                break

            elif choice == "1":
                chains = self.config.get_chains()
                if not chains:
                    log_warn("Tidak ada chain."); continue
                self._print_chains()
                n = prompt("Nama chain yang dihapus")
                # Case-insensitive
                for cn in chains:
                    if cn.lower() == n.lower():
                        n = cn; break
                if n not in chains:
                    log_err(f"Chain '{n}' tidak ditemukan"); continue
                if confirm(f"Yakin hapus chain '{n}'?"):
                    self.config.remove_chain(n)
                    log_ok(f"Chain '{n}' berhasil dihapus!")

            elif choice == "2":
                wallets = self.config.get_wallets()
                if not wallets:
                    log_warn("Tidak ada wallet."); continue
                self._print_wallets()
                try:
                    idx = int(prompt("Nomor wallet yang dihapus")) - 1
                    if 0 <= idx < len(wallets):
                        wname = wallets[idx]['name']
                        if confirm(f"Yakin hapus wallet '{wname}'?"):
                            self.config.remove_wallet(idx)
                            log_ok(f"Wallet '{wname}' berhasil dihapus!")
                    else:
                        log_err("Nomor tidak valid")
                except ValueError:
                    log_err("Masukkan angka")

            elif choice == "3":
                bridges = self.config.get_bridges()
                if not bridges:
                    log_warn("Tidak ada bridge."); continue
                b_list = list(bridges.items())
                print(f"\n  {C.BOLD}Daftar Bridge:{C.END}")
                for i, (nm, info) in enumerate(b_list, 1):
                    contract_str = short_addr(info['contract']) if info.get('contract') else "(tanpa kontrak)"
                    print(f"    {i}. {C.CY}{nm}{C.END} — {info['from_chain']} → {info['to_chain']} — {contract_str}")
                print()
                try:
                    idx = int(prompt("Nomor bridge yang dihapus")) - 1
                    if 0 <= idx < len(b_list):
                        bname = b_list[idx][0]
                        if confirm(f"Yakin hapus bridge '{bname}'?"):
                            self.config.remove_bridge(bname)
                            log_ok(f"Bridge '{bname}' berhasil dihapus!")
                    else:
                        log_err("Nomor tidak valid")
                except ValueError:
                    log_err("Masukkan angka")

            elif choice == "4":
                routers = self.config.data.get("dex_routers", {})
                if not routers:
                    log_warn("Tidak ada DEX router."); continue
                r_list = []
                print(f"\n  {C.BOLD}DEX Router:{C.END}")
                num = 1
                for ch, dexes in routers.items():
                    for nm, info in dexes.items():
                        r_list.append((ch, nm))
                        print(f"    {num}. {C.CY}{ch}/{nm}{C.END} — {short_addr(info['address'])}")
                        num += 1
                print()
                try:
                    idx = int(prompt("Nomor DEX router yang dihapus")) - 1
                    if 0 <= idx < len(r_list):
                        ch, nm = r_list[idx]
                        if confirm(f"Yakin hapus DEX router '{ch}/{nm}'?"):
                            self.config.remove_dex_router(ch, nm)
                            log_ok(f"DEX router '{ch}/{nm}' berhasil dihapus!")
                    else:
                        log_err("Nomor tidak valid")
                except ValueError:
                    log_err("Masukkan angka")

            elif choice == "5":
                tokens = self.config.data.get("tokens", {})
                if not tokens:
                    log_warn("Tidak ada token."); continue
                t_list = []
                print(f"\n  {C.BOLD}Token:{C.END}")
                num = 1
                for ch, toks in tokens.items():
                    for sym, info in toks.items():
                        t_list.append((ch, sym))
                        print(f"    {num}. {C.CY}{ch}/{sym}{C.END} — {short_addr(info['address'])} ({info['decimals']}d)")
                        num += 1
                print()
                try:
                    idx = int(prompt("Nomor token yang dihapus")) - 1
                    if 0 <= idx < len(t_list):
                        ch, sym = t_list[idx]
                        if confirm(f"Yakin hapus token '{ch}/{sym}'?"):
                            self.config.remove_token(ch, sym)
                            log_ok(f"Token '{ch}/{sym}' berhasil dihapus!")
                    else:
                        log_err("Nomor tidak valid")
                except ValueError:
                    log_err("Masukkan angka")

    # ── Kirim ───────────────────────────────────────────────────

    def _menu_send(self):
        chain = self._select_chain()
        if not chain: return
        wallet = self._select_wallet()
        if not wallet: return
        to = prompt("Alamat penerima (0x…)")
        amount = self._select_amount()
        if not amount: return

        info = self.config.get_chains()[chain]
        print(f"\n  {C.BOLD}Pratinjau Transaksi:{C.END}")
        print(f"    Chain  : {C.CY}{chain}{C.END}")
        print(f"    Dari   : {short_addr(wallet['address'])}")
        print(f"    Ke     : {short_addr(to)}")
        print(f"    Nilai  : {C.G}{amount} {info['symbol']}{C.END}")
        if confirm("Konfirmasi & kirim?"):
            self.engine.send_native(wallet, to, amount)

    # ── Multi-Kirim ─────────────────────────────────────────────

    def _menu_multi_send(self):
        chain = self._select_chain()
        if not chain: return
        result = self._select_wallet(allow_multi=True)
        if not result: return
        wallets, mode = result

        print(f"\n  {C.BOLD}Masukkan alamat penerima (baris kosong untuk selesai):{C.END}")
        addresses = []
        while True:
            a = prompt(f"#{len(addresses)+1}")
            if not a: break
            addresses.append(a)
        if not addresses:
            log_warn("Tidak ada alamat yang dimasukkan"); return

        amount = self._select_amount()
        if not amount: return
        delay = int(prompt("Jeda antar TX (detik)", "3"))

        info = self.config.get_chains()[chain]
        total = Decimal(amount) * len(addresses)
        print(f"\n  {C.BOLD}Ringkasan Batch:{C.END}")
        print(f"    Chain      : {C.CY}{chain}{C.END}")
        print(f"    Wallet     : {len(wallets)} ({mode})")
        print(f"    Penerima   : {len(addresses)}")
        print(f"    Per-kirim  : {C.G}{amount} {info['symbol']}{C.END}")
        print(f"    Total      : {C.G}{total} {info['symbol']}{C.END}")
        print(f"    Jeda       : {delay} detik antar TX")

        if confirm("Jalankan batch kirim?"):
            results = self.engine.multi_send(wallets, addresses, amount, delay, mode)
            ok = sum(1 for r in results if r["status"] == "sukses")
            log_ok(f"Selesai: {ok}/{len(results)} berhasil")

    # ── Kirim Acak ──────────────────────────────────────────────

    def _menu_send_random(self):
        chain = self._select_chain()
        if not chain: return
        result = self._select_wallet(allow_multi=True)
        if not result: return
        wallets, mode = result

        count  = int(prompt("Jumlah alamat acak", "5"))
        amount = self._select_amount()
        if not amount: return
        delay  = int(prompt("Jeda antar TX (detik)", "3"))

        info = self.config.get_chains()[chain]
        total = Decimal(amount) * count
        print(f"\n  {C.BOLD}Ringkasan Kirim Acak:{C.END}")
        print(f"    Chain      : {C.CY}{chain}{C.END}")
        print(f"    Wallet     : {len(wallets)} ({mode})")
        print(f"    Jumlah     : {count} alamat")
        print(f"    Per-kirim  : {C.G}{amount} {info['symbol']}{C.END}")
        print(f"    Total      : {C.G}{total} {info['symbol']}{C.END}")

        if confirm("Jalankan kirim acak?"):
            results = self.engine.send_to_random(wallets, count, amount, delay, mode)
            ok = sum(1 for r in results if r["status"] == "sukses")
            log_ok(f"Selesai: {ok}/{len(results)} berhasil")

    # ── Swap ────────────────────────────────────────────────────

    def _menu_swap(self):
        chain = self._select_chain()
        if not chain: return
        routers = self.config.get_dex_routers(chain)
        if not routers:
            log_warn(f"Belum ada DEX router di {chain}. Tambahkan di Pengaturan."); return
        wallet = self._select_wallet()
        if not wallet: return

        r_list = list(routers.items())
        print(f"\n  {C.BOLD}DEX Router:{C.END}")
        for i, (n, info) in enumerate(r_list, 1):
            print(f"    {i}. {C.CY}{n}{C.END} — {short_addr(info['address'])}")
        ri = int(prompt("Pilih router")) - 1
        _, rinfo = r_list[ri]

        stype = menu_select("Arah Swap", [
            ("1", "Native → Token"),
            ("2", "Token → Native"),
            ("3", "Token → Token"),
            ("4", "🔄 Wrap (Native → Wrapped)"),
            ("5", "🔄 Unwrap (Wrapped → Native)"),
            ("0", "← Kembali"),
        ])
        if stype == "0": return

        if stype in ("4", "5"):
            amount = self._select_amount()
            if not amount: return
            try:
                if stype == "4":
                    if confirm(f"Wrap {amount} native?"):
                        self.engine.wrap_native(wallet, amount)
                else:
                    if confirm(f"Unwrap {amount} wrapped native?"):
                        self.engine.unwrap_native(wallet, amount)
            except Exception as e:
                log_err(str(e))
            return

        slippage = float(prompt("Slippage %", "5"))
        tokens = self.config.get_tokens(chain)

        def pick_token(label="token"):
            if tokens:
                t_list = list(tokens.items())
                print(f"\n  {C.BOLD}Token:{C.END}")
                for i, (s, inf) in enumerate(t_list, 1):
                    print(f"    {i}. {C.CY}{s}{C.END} — {short_addr(inf['address'])}")
                print(f"    {len(t_list)+1}. Masukkan alamat manual")
                c = int(prompt(f"Pilih {label}")) - 1
                if c < len(t_list):
                    return t_list[c][1]["address"]
            return prompt(f"Alamat {label}")

        if stype == "1":
            token = pick_token("token yang dibeli")
            amount = self._select_amount()
            if not amount: return
            if confirm(f"Swap {amount} native → token?"):
                self.engine.swap_native_to_token(wallet, rinfo["address"], token, amount, slippage)

        elif stype == "2":
            token = pick_token("token yang dijual")
            amount = prompt("Jumlah yang dijual")
            if confirm(f"Swap {amount} token → native?"):
                self.engine.swap_token_to_native(wallet, rinfo["address"], token, amount, slippage)

        elif stype == "3":
            t_in  = pick_token("token yang dijual")
            t_out = pick_token("token yang dibeli")
            amount = prompt("Jumlah yang dijual")
            if confirm(f"Swap {amount} token → token?"):
                self.engine.swap_token_to_token(wallet, rinfo["address"], t_in, t_out, amount, slippage)

    # ── Bridge ──────────────────────────────────────────────────

    def _menu_bridge(self):
        bridges = self.config.get_bridges()
        if not bridges:
            log_warn("Belum ada bridge. Mau setup bridge sekarang?")
            if confirm("Setup bridge baru?"):
                self._setup_bridge()
                bridges = self.config.get_bridges()
            if not bridges:
                return

        b_list = list(bridges.items())
        print(f"\n  {C.BOLD}Daftar Bridge:{C.END}")
        chains = self.config.get_chains()
        for i, (n, info) in enumerate(b_list, 1):
            src = info['from_chain']
            dst = info['to_chain']
            src_sym = chains.get(src, {}).get("symbol", "?")
            dst_sym = chains.get(dst, {}).get("symbol", "?")
            btype = info.get("bridge_type", "generic")
            status = f"{C.G}✓ {btype}{C.END}" if info.get("contract") else f"{C.Y}tanpa kontrak{C.END}"
            print(f"    {i}. {C.CY}{n}{C.END} — {src} ({src_sym}) → {dst} ({dst_sym}) [{status}]")
        print()

        try:
            bi = int(prompt("Pilih bridge (nomor)")) - 1
            if bi < 0 or bi >= len(b_list):
                log_err("Nomor tidak valid"); return
        except ValueError:
            log_err("Masukkan angka"); return

        bname, binfo = b_list[bi]
        bridge_type = binfo.get("bridge_type", "generic")

        # Cek apakah kontrak bridge ada
        contract = binfo.get("contract", "")
        if not contract:
            log_warn(f"Bridge '{bname}' belum punya alamat kontrak!")
            contract = prompt("Masukkan alamat kontrak bridge untuk melanjutkan", "")
            if not contract:
                log_err("Tidak bisa bridge tanpa alamat kontrak."); return
            binfo["contract"] = Web3.to_checksum_address(contract.strip())
            self.config.data["bridge_contracts"][bname] = binfo
            self.config.save()
            log_ok("Alamat kontrak disimpan!")

        if not self.engine.connect(binfo["from_chain"]):
            return
        wallet = self._select_wallet()
        if not wallet: return
        amount = self._select_amount()
        if not amount: return

        # Ambil chain ID tujuan otomatis
        dest = chains.get(binfo["to_chain"], {})
        dest_id = binfo.get("dest_chain_id") or dest.get("chain_id")
        if not dest_id:
            dest_id = prompt("Chain ID tujuan (tidak terdeteksi otomatis)")

        src_sym = chains.get(binfo["from_chain"], {}).get("symbol", "?")
        type_label = {
            "op-l1-deposit": "OP Stack (L1→L2) — depositETHTo",
            "op-l2-withdraw": "OP Stack (L2→L1) — bridgeETHTo",
            "arb-l1-deposit": "Arbitrum (L1→L2) — depositEth",
            "generic": "Generik — bridge(uint256,address)",
        }.get(bridge_type, bridge_type)

        print(f"\n  {C.BOLD}Pratinjau Bridge:{C.END}")
        print(f"    Bridge      : {C.CY}{bname}{C.END}")
        print(f"    Rute        : {binfo['from_chain']} → {binfo['to_chain']}")
        print(f"    Chain ID    : {dest_id}")
        print(f"    Jumlah      : {C.G}{amount} {src_sym}{C.END}")
        print(f"    Kontrak     : {binfo['contract']}")
        print(f"    Tipe ABI    : {C.CY}{type_label}{C.END}")

        if bridge_type == "generic":
            log_warn("ABI generik — mungkin tidak kompatibel dengan semua bridge")

        if confirm("Jalankan bridge?"):
            self.engine.bridge_native(wallet, binfo["contract"], dest_id, amount, bridge_type)

    # ── Penjadwal ───────────────────────────────────────────────

    def _menu_scheduler(self):
        while True:
            self.scheduler.show()
            sched_label = "⏹ Hentikan Penjadwal" if self.scheduler.is_running else "▶ Mulai Penjadwal"
            choice = menu_select("⏰ PENJADWAL", [
                ("1", "Jadwalkan Kirim Berulang"),
                ("2", "Jadwalkan Swap Berulang"),
                ("3", sched_label),
                ("4", "📋 Lihat Log Penjadwal"),
                ("5", "Hapus Tugas"),
                ("0", "← Kembali"),
            ])
            if choice == "0": break

            elif choice == "1":
                chain = self._select_chain()
                if not chain: continue
                result = self._select_wallet(allow_multi=True)
                if not result: continue
                wallets, mode = result

                target = menu_select("Kirim ke", [
                    ("1", "Alamat tertentu"),
                    ("2", "Alamat acak setiap jalan"),
                ])
                if target == "1":
                    addrs = []
                    while True:
                        a = prompt(f"Alamat #{len(addrs)+1} (kosongkan untuk selesai)")
                        if not a: break
                        addrs.append(a)
                    if not addrs: continue
                else:
                    addrs = None
                    n_random = int(prompt("Jumlah alamat acak per jalan", "3"))

                amount   = self._select_amount()
                if not amount: continue
                interval = int(prompt("Interval (detik)", "3600"))
                name     = prompt("Nama tugas", f"kirim-{chain}")

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
                    log_warn(f"Belum ada DEX di {chain}"); continue
                wallet = self._select_wallet()
                if not wallet: continue

                r_list = list(routers.items())
                for i, (n, info) in enumerate(r_list, 1):
                    print(f"    {i}. {n}")
                ri = int(prompt("Pilih router")) - 1
                rinfo = r_list[ri][1]

                token    = prompt("Alamat token yang dibeli")
                amount   = self._select_amount()
                if not amount: continue
                slippage = float(prompt("Slippage %", "5"))
                interval = int(prompt("Interval (detik)", "3600"))
                name     = prompt("Nama tugas", f"swap-{chain}")

                self.scheduler.add(name,
                    lambda w=wallet, r=rinfo["address"], t=token, a=amount, s=slippage:
                        self.engine.swap_native_to_token(w, r, t, a, s),
                    interval)

            elif choice == "3":
                if self.scheduler.is_running:
                    self.scheduler.stop()
                else:
                    self.scheduler.start()

            elif choice == "4":
                self.scheduler.show_log()

            elif choice == "5":
                self.scheduler.show()
                idx = int(prompt("Tugas # yang dihapus")) - 1
                self.scheduler.remove(idx)

    # ── Saldo ───────────────────────────────────────────────────

    def _menu_balances(self):
        chain = self._select_chain()
        if not chain: return
        wallets = self.config.get_wallets()
        if not wallets:
            log_warn("Belum ada wallet!"); return

        info   = self.config.get_chains()[chain]
        tokens = self.config.get_tokens(chain)

        print(f"\n  {'═' * 55}")
        print(f"  {C.BOLD}Saldo di {C.CY}{chain}{C.END}")
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

    # ── Riwayat ─────────────────────────────────────────────────

    def _menu_history(self):
        h = self.engine.tx_history
        if not h:
            log_info("Belum ada transaksi"); return

        n = min(20, len(h))
        print(f"\n  {C.BOLD}{n} Transaksi Terakhir:{C.END}")
        print(f"  {'─' * 72}")
        for tx in h[-n:]:
            st = f"{C.G}✓{C.END}" if tx.get("status") == "sukses" else f"{C.R}✗{C.END}"
            ts = tx.get("timestamp", "")[:19]
            print(f"  {st} {C.DIM}{ts}{C.END} [{C.CY}{tx.get('chain','?')}{C.END}] "
                  f"{tx.get('type','?')}  {short_addr(tx.get('from',''))} → {short_addr(tx.get('to',''))}")
            print(f"    {C.DIM}TX: {tx.get('tx_hash','?')}{C.END}")
        print(f"  {'─' * 72}")


# ═══════════════════════════════════════════════════════════════
# TITIK MASUK
# ═══════════════════════════════════════════════════════════════

def main():
    print(f"""
{C.Y}{'━' * 55}
  ⚠️  PERINGATAN KEAMANAN
{'━' * 55}{C.END}
  Private key akan disimpan di {C.BOLD}{CONFIG_FILE}{C.END}
  di mesin lokal kamu.

  • JANGAN bagikan file konfigurasi ke siapapun.
  • JANGAN jalankan tool ini di mesin yang tidak terpercaya.
  • Gunakan hot wallet khusus dengan jumlah kecil.
  • Disarankan untuk testnet / operasi nilai kecil.
{C.Y}{'━' * 55}{C.END}
""")
    input(f"  {C.DIM}Tekan Enter untuk lanjut…{C.END}")

    CLI().run()


if __name__ == "__main__":
    main()
