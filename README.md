<p align="center">
  <img src="https://img.shields.io/badge/python-3.10+-blue?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/web3.py-7.x-orange?logo=ethereum&logoColor=white" alt="Web3">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
  <img src="https://img.shields.io/badge/EVM-All_Chains-blueviolet" alt="EVM">
  <img src="https://img.shields.io/badge/Termux-Android-brightgreen?logo=android&logoColor=white" alt="Termux">
</p>

<h1 align="center">⛓️ Onchain Automation Bot</h1>

<p align="center">
  <b>Automate on-chain transactions across ANY EVM chain</b><br>
  Send · Swap · Bridge · Multi-wallet · Scheduler
</p>

---

## ✨ Features

| Feature | Description |
|---|---|
| 💸 **Send** | Send native tokens (ETH, BNB, MATIC, etc.) to any address |
| 📤 **Multi-Send** | Batch send to multiple addresses in one go |
| 🎲 **Random Send** | Auto-generate random addresses and send to them |
| 🔄 **Swap** | Swap tokens via any Uniswap V2-compatible DEX |
| 🌉 **Bridge** | Bridge tokens across chains (generic bridge support) |
| 👛 **Multi-Wallet** | Manage multiple wallets with round-robin or random selection |
| ⏰ **Scheduler** | Set up recurring send/swap tasks that run automatically |
| 🌐 **Any EVM Chain** | Works with ANY EVM chain — just add the RPC URL |
| 🧪 **Testnet Ready** | Full support for testnets (Sepolia, BSC Testnet, etc.) |
| 📜 **TX History** | All transactions logged locally for tracking |

## 📋 Requirements

- Python 3.10 or higher
- `web3` library
- Works on: **Linux**, **macOS**, **Windows**, **Android (Termux)**

## 🚀 Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/Limit99/onchain-bot.git
cd onchain-bot
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the bot

```bash
python onchain_bot.py
```

### 4. First-time setup

When you run the bot for the first time, you'll need to configure:

1. **Add a Chain** — Enter the RPC URL, Chain ID, and native token symbol
2. **Add a Wallet** — Enter your wallet address and private key
3. **Start transacting!**

## 📖 Usage Guide

### ⚙️ Setup & Configuration

Before using any feature, you need to add at least one chain and one wallet.

#### Adding a Chain

```
Select: 1 (Add Chain)
  ▸ Chain name: sepolia
  ▸ RPC URL: https://rpc.sepolia.org
  ▸ Chain ID: 11155111
  ▸ Native symbol: ETH
  ▸ Explorer URL: https://sepolia.etherscan.io
  ▸ Type: testnet
```

#### Adding a Wallet

```
Select: 2 (Add Wallet)
  ▸ Wallet label: main
  ▸ Address: 0xYourAddress...
  ▸ Private key: YourPrivateKey...
```

### 💸 Send Native Token

Send native tokens (ETH/BNB/MATIC/etc.) to a single address.

Choose from preset amounts:
- `0.1` — Standard amount
- `0.001` — Small amount
- `0.0001` — Micro amount
- `Custom` — Enter any amount

### 📤 Multi-Send (Batch)

Send tokens to multiple addresses in one batch:

1. Select chain and wallet(s)
2. Enter recipient addresses one by one
3. Choose amount per transaction
4. Set delay between transactions
5. Confirm and execute

**Wallet modes:**
- **Single** — Use one wallet for all transactions
- **All (Round-Robin)** — Cycle through wallets
- **Random** — Pick a random wallet for each TX

### 🎲 Send to Random Addresses

The bot generates cryptographically random Ethereum addresses and sends tokens to each:

1. Select chain and wallet(s)
2. Choose how many random addresses to generate
3. Select amount
4. Execute

> Great for testnet activity / interaction farming.

### 🔄 Swap Tokens (DEX)

Swap tokens via any Uniswap V2-compatible DEX router:

**Supported swap types:**
- Native → Token (e.g., ETH → USDC)
- Token → Native (e.g., USDC → ETH)
- Token → Token (e.g., USDC → WETH)

**Setup required:** Add a DEX router in Setup first.

```
Select: 3 (Add DEX Router)
  ▸ Chain name: ethereum
  ▸ DEX name: uniswap-v2
  ▸ Router address: 0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D
```

### 🌉 Bridge Tokens

Bridge native tokens to another chain:

1. Configure bridge contract in Setup
2. Select the bridge
3. Choose amount
4. Execute

> ⚠️ Bridge contract ABIs vary significantly between protocols. The default implementation uses a generic `bridge(uint256, address)` interface. You may need to modify the calldata encoding for your specific bridge.

### ⏰ Scheduled Tasks

Set up recurring transactions that execute automatically:

- **Recurring Send** — Auto-send at fixed intervals
- **Recurring Swap** — Auto-swap at fixed intervals
- Supports random addresses per run
- Background execution (non-blocking)

```
  ▸ Interval (seconds): 3600    # Every 1 hour
  ▸ Task name: hourly-send
```

### 💰 Check Balances

View native token and ERC-20 token balances for all configured wallets on any chain.

### 📜 Transaction History

View the last 20 transactions with status, chain, type, addresses, and TX hashes.

## 🔧 Popular Chain Configs

Here are some commonly used chain configurations:

### Mainnets

| Chain | RPC URL | Chain ID | Symbol |
|---|---|---|---|
| Ethereum | `https://eth.llamarpc.com` | 1 | ETH |
| BSC | `https://bsc-dataseed.binance.org` | 56 | BNB |
| Polygon | `https://polygon-rpc.com` | 137 | MATIC |
| Arbitrum | `https://arb1.arbitrum.io/rpc` | 42161 | ETH |
| Optimism | `https://mainnet.optimism.io` | 10 | ETH |
| Avalanche | `https://api.avax.network/ext/bc/C/rpc` | 43114 | AVAX |
| Base | `https://mainnet.base.org` | 8453 | ETH |
| Fantom | `https://rpc.ftm.tools` | 250 | FTM |

### Testnets

| Chain | RPC URL | Chain ID | Symbol |
|---|---|---|---|
| Sepolia | `https://rpc.sepolia.org` | 11155111 | ETH |
| BSC Testnet | `https://data-seed-prebsc-1-s1.binance.org:8545` | 97 | tBNB |
| Mumbai | `https://rpc-mumbai.maticvigil.com` | 80001 | MATIC |
| Arbitrum Sepolia | `https://sepolia-rollup.arbitrum.io/rpc` | 421614 | ETH |
| Base Sepolia | `https://sepolia.base.org` | 84532 | ETH |

### Popular DEX Routers

| DEX | Chain | Router Address |
|---|---|---|
| Uniswap V2 | Ethereum | `0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D` |
| PancakeSwap V2 | BSC | `0x10ED43C718714eb63d5aA57B78B54704E256024E` |
| SushiSwap | Multi-chain | `0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F` |
| QuickSwap | Polygon | `0xa5E0829CaCEd8fFDD4De3c43696c57F7D7A678ff` |
| TraderJoe | Avalanche | `0x60aE616a2155Ee3d9A68541Ba4544862310933d4` |
| SpookySwap | Fantom | `0xF491e7B69E4244ad4002BC14e878a34207E38c29` |

## 📱 Termux (Android) Setup

Onchain Bot fully supports [Termux](https://termux.dev/) on Android. The bot auto-detects Termux and adapts its display for the mobile terminal.

### Method 1: Auto Setup (Recommended)

One command installs everything:

```bash
# 1. Install git first (if you don't have it)
pkg install git

# 2. Clone the repo
git clone https://github.com/Limit99/onchain-bot.git
cd onchain-bot

# 3. Run the auto setup script
bash setup_termux.sh

# 4. Done! Run the bot
python onchain_bot.py
```

The `setup_termux.sh` script will:
- Update Termux packages
- Install Python, build tools, libffi, openssl, rust (needed to compile web3)
- Install web3 with the correct build flags for ARM
- Verify everything works

### Method 2: Manual Setup

If you prefer to install manually:

```bash
# Update packages
pkg update && pkg upgrade

# Install required system packages
pkg install python git build-essential libffi openssl rust binutils

# Clone the repo
git clone https://github.com/Limit99/onchain-bot.git
cd onchain-bot

# Upgrade pip
pip install --upgrade pip setuptools wheel

# Set build flags for Termux ARM architecture
export CFLAGS="-Wno-error"
export LDFLAGS="-L/data/data/com.termux/files/usr/lib"
export C_INCLUDE_PATH="/data/data/com.termux/files/usr/include"

# Install web3
pip install web3

# Run the bot
python onchain_bot.py
```

### Termux Tips & Troubleshooting

<details>
<summary><b>💡 Tips for best experience</b></summary>

- **Use landscape mode** — The menu looks best in landscape orientation
- **Increase font size** — Pinch to zoom if text is too small
- **Keep session alive** — Run `termux-wake-lock` to prevent Termux from sleeping during long scheduled tasks
- **Notification** — Install `termux-api` + `Termux:API` app to get notifications:
  ```bash
  pkg install termux-api
  ```
- **Run in background** — Use `tmux` or `nohup` for scheduled tasks:
  ```bash
  pkg install tmux
  tmux new -s bot
  python onchain_bot.py
  # Press Ctrl+B then D to detach
  # Reattach: tmux attach -t bot
  ```

</details>

<details>
<summary><b>🔧 Common issues</b></summary>

| Problem | Solution |
|---|---|
| `ModuleNotFoundError: No module named 'pkg_resources'` | Run: `pip install --force-reinstall setuptools` |
| `maturin failed` / `Failed to determine Android API level` | Run: `export ANDROID_API_LEVEL=$(getprop ro.build.version.sdk)` then retry `pip install web3` |
| `pydantic-core` build error | Set API level first: `export ANDROID_API_LEVEL=$(getprop ro.build.version.sdk)` then `pip install pydantic-core web3` |
| `pip install web3` fails with build errors | Make sure you have: `pkg install build-essential libffi openssl rust binutils` |
| `error: can't find Rust compiler` | Run: `pkg install rust` and retry |
| `ModuleNotFoundError: No module named 'web3'` | Run: `pip install setuptools web3` |
| Script is slow to start | First import of web3 takes a few seconds on mobile — this is normal |
| Emoji not showing correctly | The bot auto-detects Termux and uses text fallbacks `[OK]`, `[ERR]`, etc. |
| Termux killed in background | Use `termux-wake-lock` or run inside `tmux` session |
| Permission denied | Run: `chmod +x onchain_bot.py` |
| Storage access needed | Run: `termux-setup-storage` for external storage access |

</details>

<details>
<summary><b>📏 Minimum Termux requirements</b></summary>

- **Termux** v0.118+ (from [F-Droid](https://f-droid.org/en/packages/com.termux/) — Google Play version is outdated)
- **Android** 7.0+
- **Storage** ~500MB (Python + web3 dependencies)
- **RAM** 2GB+ recommended

</details>

## 📁 File Structure

```
onchain-bot/
├── onchain_bot.py          # Main bot script
├── setup_termux.sh         # One-click Termux setup
├── requirements.txt        # Python dependencies
├── config.example.json     # Example configuration
├── README.md               # This file
├── LICENSE                  # MIT License
└── .gitignore              # Git ignore rules
```

## ⚠️ Security

> **IMPORTANT:** This tool stores private keys in a local JSON file (`onchain_config.json`).

- 🔒 **Never** share your `onchain_config.json` file
- 🔒 **Never** run this on untrusted or shared machines
- 🔒 **Never** commit config files with real private keys
- ✅ Use a **dedicated hot wallet** with small amounts
- ✅ **Test on testnets first** before using mainnet
- ✅ Keep your `onchain_config.json` in `.gitignore`

## 🤝 Contributing

Contributions are welcome! Feel free to:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

## ⭐ Star This Repo

If you find this tool useful, give it a ⭐ on GitHub!

---

<p align="center">
  Built with ❤️ by <a href="https://github.com/Limit99">Limit99</a>
</p>
