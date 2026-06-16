<p align="center">
  <img src="https://img.shields.io/badge/python-3.10+-blue?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/web3.py-7.x-orange?logo=ethereum&logoColor=white" alt="Web3">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
  <img src="https://img.shields.io/badge/EVM-Semua_Chain-blueviolet" alt="EVM">
  <img src="https://img.shields.io/badge/Termux-Android-brightgreen?logo=android&logoColor=white" alt="Termux">
</p>

<h1 align="center">⛓️ Onchain Automation Bot</h1>

<p align="center">
  <b>Otomatisasi transaksi on-chain di SEMUA chain EVM</b><br>
  Kirim · Swap · Bridge · Multi-wallet · Penjadwal
</p>

---

## ✨ Fitur

| Fitur | Deskripsi |
|---|---|
| 💸 **Kirim** | Kirim token native (ETH, BNB, MATIC, dll.) ke alamat manapun |
| 📤 **Multi-Kirim** | Kirim batch ke banyak alamat sekaligus |
| 🎲 **Kirim Acak** | Buat alamat acak otomatis dan kirim ke masing-masing |
| 🔄 **Swap** | Tukar token via DEX kompatibel Uniswap V2 |
| 🌉 **Bridge** | Bridge token antar chain (dukungan bridge generik) |
| 👛 **Multi-Wallet** | Kelola banyak wallet dengan round-robin atau acak |
| ⏰ **Penjadwal** | Atur tugas kirim/swap berulang yang jalan otomatis |
| 🌐 **Semua Chain EVM** | Berjalan di SEMUA chain EVM — cukup tambahkan URL RPC |
| 🧪 **Siap Testnet** | Dukungan penuh untuk testnet (Sepolia, BSC Testnet, dll.) |
| 📜 **Riwayat TX** | Semua transaksi tercatat lokal untuk pelacakan |
| 🔍 **Auto-Deteksi Chain** | Cukup masukkan RPC, chain ID/nama/simbol terdeteksi otomatis |
| 📦 **55 Chain Terpasang** | 37 mainnet + 18 testnet sudah ter-load otomatis dengan RPC default |

## 📋 Kebutuhan

- Python 3.10 atau lebih tinggi
- Library `web3`
- Berjalan di: **Linux**, **macOS**, **Windows**, **Android (Termux)**

## 🚀 Mulai Cepat

### 1. Clone repository

```bash
git clone https://github.com/Limit99/onchain-bot.git
cd onchain-bot
```

### 2. Install dependensi

```bash
pip install -r requirements.txt
```

### 3. Jalankan bot

```bash
python onchain_bot.py
```

### 4. Pengaturan pertama kali

Saat pertama kali jalan, *55 chain EVM sudah ter-load otomatis* (lengkap dengan RPC default). Kamu cukup:

1. **Tambah Wallet** — Masukkan alamat wallet dan private key
2. **Pilih Chain** — Pilih dari 37 mainnet atau 18 testnet yang sudah tersedia
3. **Mulai bertransaksi!**

> 💡 Tidak perlu setup chain manual! Semua chain populer sudah siap pakai.

## 📖 Panduan Penggunaan

### ⚙️ Pengaturan & Konfigurasi

Sebelum menggunakan fitur apapun, kamu perlu menambahkan minimal satu wallet. *Chain tidak perlu di-setup* — 55 chain sudah otomatis tersedia!

#### Chain yang Sudah Ter-load (55 chain)

**🌐 Mainnet (37):** Ethereum, BSC, Polygon, Arbitrum One, Optimism, Avalanche, Fantom, Base, zkSync Era, Polygon zkEVM, Linea, Scroll, Mantle, Manta Pacific, Zora, Blast, opBNB, Moonbeam, Moonriver, Celo, Gnosis, Cronos, Metis, Mode, Taiko, Cyber, World Chain, Abstract, Ink, Unichain, Sonic, Soneium, Berachain, X Layer, Lisk, Fraxtal, Xai, Kroma

**🧪 Testnet (18):** Sepolia, Holesky, BSC Testnet, Polygon Amoy, Arbitrum Sepolia, Optimism Sepolia, Avalanche Fuji, Base Sepolia, Scroll Sepolia, Linea Sepolia, zkSync Sepolia, Blast Sepolia, Berachain Bartio, Unichain Sepolia, Gnosis Chiado, Mantle Sepolia, Monad Testnet

> Semua chain di atas sudah punya RPC publik default. Tinggal pilih dan pakai!

#### Menambahkan Chain Kustom

Kalau chain yang kamu butuhkan belum ada, kamu bisa tambah manual:

```
Pilih: 1 (Tambah Chain)
  ▸ Pilih: 1 (Masukkan RPC - auto-deteksi)
  ▸ URL RPC: https://rpc-custom-chain.example.com
  [OK] Terdeteksi: CustomChain (Chain ID: 99999, CUSTOM, mainnet)
```

Atau ganti RPC chain yang sudah ada:

```
Pilih: 1 (Tambah Chain)
  ▸ Pilih: 3 (Ganti RPC chain yang sudah ada)
  ▸ Nama chain: Ethereum
  [i] RPC saat ini: https://eth.llamarpc.com
  ▸ RPC baru: https://rpc-custom-kamu.example.com
```

#### Menambahkan Wallet

```
Pilih: 2 (Tambah Wallet)
  ▸ Label wallet: utama
  ▸ Alamat (0x…): 0xAlamatKamu...
  ▸ Private key: PrivateKeyKamu...
```

### 💸 Kirim Token Native

Kirim token native (ETH/BNB/MATIC/dll.) ke satu alamat.

Pilih dari jumlah preset:
- `0.1` — Jumlah standar
- `0.001` — Jumlah kecil
- `0.0001` — Jumlah mikro
- `Kustom` — Masukkan jumlah bebas

### 📤 Multi-Kirim (Batch)

Kirim token ke banyak alamat dalam satu batch:

1. Pilih chain dan wallet
2. Masukkan alamat penerima satu per satu
3. Pilih jumlah per transaksi
4. Atur jeda antar transaksi
5. Konfirmasi dan jalankan

**Mode wallet:**
- **Single** — Gunakan satu wallet untuk semua transaksi
- **All (Round-Robin)** — Putar giliran antar wallet
- **Random** — Pilih wallet acak untuk setiap TX

### 🎲 Kirim ke Alamat Acak

Bot membuat alamat Ethereum acak secara kriptografis dan mengirim token ke masing-masing:

1. Pilih chain dan wallet
2. Pilih berapa alamat acak yang dibuat
3. Pilih jumlah
4. Jalankan

> Cocok untuk aktivitas testnet / farming interaksi.

### 🔄 Swap Token (DEX)

Tukar token via DEX router kompatibel Uniswap V2:

**Tipe swap yang didukung:**
- Native → Token (misal: ETH → USDC)
- Token → Native (misal: USDC → ETH)
- Token → Token (misal: USDC → WETH)

**Perlu setup:** Tambah DEX router di Pengaturan dulu.

```
Pilih: 3 (Tambah DEX Router)
  ▸ Nama chain: ethereum
  ▸ Nama DEX: uniswap-v2
  ▸ Alamat router: 0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D
```

### 🌉 Bridge Token

Bridge token native ke chain lain:

1. Konfigurasi kontrak bridge di Pengaturan
2. Pilih bridge
3. Pilih jumlah
4. Jalankan

> ⚠️ ABI kontrak bridge sangat bervariasi antar protokol. Implementasi default menggunakan interface generik `bridge(uint256, address)`. Kamu mungkin perlu menyesuaikan encoding calldata untuk bridge spesifik kamu.

### ⏰ Tugas Terjadwal

Atur transaksi berulang yang jalan otomatis:

- **Kirim Berulang** — Kirim otomatis pada interval tetap
- **Swap Berulang** — Swap otomatis pada interval tetap
- Mendukung alamat acak per eksekusi
- Jalan di latar belakang (tidak mengganggu menu)
- Status live di Menu Utama
- Log tersimpan, bisa dilihat kapan saja

```
  ▸ Interval (detik): 3600    # Setiap 1 jam
  ▸ Nama tugas: kirim-harian
```

Setelah penjadwal dimulai, kamu bisa kembali ke Menu Utama dan tetap menggunakan bot untuk hal lain. Tugas akan tetap berjalan di latar belakang.

### 💰 Cek Saldo

Lihat saldo token native dan ERC-20 untuk semua wallet yang dikonfigurasi di chain manapun.

### 📜 Riwayat Transaksi

Lihat 20 transaksi terakhir dengan status, chain, tipe, alamat, dan hash TX.

## 🔧 DEX Router Populer

| DEX | Chain | Alamat Router |
|---|---|---|
| Uniswap V2 | Ethereum | `0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D` |
| PancakeSwap V2 | BSC | `0x10ED43C718714eb63d5aA57B78B54704E256024E` |
| SushiSwap | Multi-chain | `0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F` |
| QuickSwap | Polygon | `0xa5E0829CaCEd8fFDD4De3c43696c57F7D7A678ff` |
| TraderJoe | Avalanche | `0x60aE616a2155Ee3d9A68541Ba4544862310933d4` |
| SpookySwap | Fantom | `0xF491e7B69E4244ad4002BC14e878a34207E38c29` |

## 📱 Setup Termux (Android)

Onchain Bot mendukung penuh [Termux](https://termux.dev/) di Android. Bot otomatis mendeteksi Termux dan menyesuaikan tampilannya untuk terminal mobile.

### Metode 1: Setup Otomatis (Disarankan)

Satu perintah untuk install semuanya:

```bash
# 1. Install git dulu (jika belum ada)
pkg install git

# 2. Clone repo
git clone https://github.com/Limit99/onchain-bot.git
cd onchain-bot

# 3. Jalankan script setup otomatis
bash setup_termux.sh

# 4. Selesai! Jalankan bot
python onchain_bot.py
```

Script `setup_termux.sh` akan:
- Update paket Termux
- Install Python, build tools, libffi, openssl, rust (dibutuhkan untuk compile web3)
- Install web3 dengan flag build yang benar untuk ARM
- Verifikasi semuanya berjalan

### Metode 2: Setup Manual

Jika kamu ingin install manual:

```bash
# Update paket
pkg update && pkg upgrade

# Install paket sistem yang dibutuhkan
pkg install python git build-essential libffi openssl rust binutils

# Clone repo
git clone https://github.com/Limit99/onchain-bot.git
cd onchain-bot

# Upgrade pip
pip install --upgrade pip setuptools wheel

# Set flag build untuk arsitektur ARM Termux
export CFLAGS="-Wno-error"
export LDFLAGS="-L/data/data/com.termux/files/usr/lib"
export C_INCLUDE_PATH="/data/data/com.termux/files/usr/include"

# Install web3
pip install web3

# Jalankan bot
python onchain_bot.py
```

### Tips & Troubleshooting Termux

<details>
<summary><b>💡 Tips untuk pengalaman terbaik</b></summary>

- **Gunakan mode landscape** — Menu terlihat lebih baik dalam orientasi landscape
- **Perbesar font** — Cubit untuk zoom jika teks terlalu kecil
- **Jaga sesi tetap aktif** — Jalankan `termux-wake-lock` untuk mencegah Termux tidur saat tugas terjadwal berjalan lama
- **Notifikasi** — Install `termux-api` + aplikasi `Termux:API` untuk dapat notifikasi:
  ```bash
  pkg install termux-api
  ```
- **Jalan di latar belakang** — Gunakan `tmux` atau `nohup` untuk tugas terjadwal:
  ```bash
  pkg install tmux
  tmux new -s bot
  python onchain_bot.py
  # Tekan Ctrl+B lalu D untuk detach
  # Untuk kembali: tmux attach -t bot
  ```

</details>

<details>
<summary><b>🔧 Masalah umum</b></summary>

| Masalah | Solusi |
|---|---|
| `ModuleNotFoundError: No module named 'pkg_resources'` | Jalankan: `pip install --force-reinstall setuptools` |
| `maturin failed` / `Failed to determine Android API level` | Jalankan: `export ANDROID_API_LEVEL=$(getprop ro.build.version.sdk)` lalu ulangi `pip install web3` |
| Error build `pydantic-core` | Set API level dulu: `export ANDROID_API_LEVEL=$(getprop ro.build.version.sdk)` lalu `pip install pydantic-core web3` |
| `pip install web3` gagal dengan error build | Pastikan sudah install: `pkg install build-essential libffi openssl rust binutils` |
| `error: can't find Rust compiler` | Jalankan: `pkg install rust` dan coba lagi |
| `ModuleNotFoundError: No module named 'web3'` | Jalankan: `pip install setuptools web3` |
| Script lambat saat mulai | Import pertama web3 butuh beberapa detik di HP — ini normal |
| Emoji tidak tampil dengan benar | Bot otomatis deteksi Termux dan pakai fallback teks `[OK]`, `[ERR]`, dll. |
| Termux mati di background | Gunakan `termux-wake-lock` atau jalankan di dalam sesi `tmux` |
| Permission denied | Jalankan: `chmod +x onchain_bot.py` |
| Butuh akses storage | Jalankan: `termux-setup-storage` untuk akses storage eksternal |

</details>

<details>
<summary><b>📏 Kebutuhan minimum Termux</b></summary>

- **Termux** v0.118+ (dari [F-Droid](https://f-droid.org/en/packages/com.termux/) — versi Google Play sudah usang)
- **Android** 7.0+
- **Storage** ~500MB (Python + dependensi web3)
- **RAM** 2GB+ disarankan

</details>

## 📁 Struktur File

```
onchain-bot/
├── onchain_bot.py          # Script utama bot
├── setup_termux.sh         # Setup Termux satu klik
├── requirements.txt        # Dependensi Python
├── config.example.json     # Contoh konfigurasi
├── README.md               # File ini
├── LICENSE                  # Lisensi MIT
└── .gitignore              # Aturan git ignore
```

## ⚠️ Keamanan

> **PENTING:** Tool ini menyimpan private key dalam file JSON lokal (`onchain_config.json`).

- 🔒 **Jangan pernah** bagikan file `onchain_config.json` kamu
- 🔒 **Jangan pernah** jalankan ini di mesin yang tidak terpercaya atau bersama
- 🔒 **Jangan pernah** commit file config dengan private key asli
- ✅ Gunakan **hot wallet khusus** dengan jumlah kecil
- ✅ **Test di testnet dulu** sebelum menggunakan mainnet
- ✅ Pastikan `onchain_config.json` ada di `.gitignore`

## 🤝 Kontribusi

Kontribusi sangat diterima! Silakan:

1. Fork repository
2. Buat branch fitur (`git checkout -b fitur/fitur-keren`)
3. Commit perubahan (`git commit -m 'Tambah fitur keren'`)
4. Push ke branch (`git push origin fitur/fitur-keren`)
5. Buka Pull Request

## 📄 Lisensi

Proyek ini dilisensikan di bawah Lisensi MIT — lihat file [LICENSE](LICENSE) untuk detailnya.

## ⭐ Beri Bintang Repo Ini

Jika kamu merasa tool ini berguna, beri ⭐ di GitHub!

---

<p align="center">
  Dibuat dengan ❤️ oleh <a href="https://github.com/Limit99">Limit99</a>
</p>
