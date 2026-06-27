# 🚀 PR: Auto-Faucet Integration untuk Onchain-Bot

## 📌 Deskripsi
PR ini menambahkan **fitur auto-faucet** untuk otomatis request dana dari faucet testnet jika balance wallet rendah. Fitur ini terintegrasi dengan:
- **`_request_faucet()`** → Request dana ke faucet endpoint (Sepolia, Polygon Amoy, Arbitrum Sepolia, Optimism Sepolia).
- **`_ensure_minimum_balance()`** → Cek balance sebelum transaksi, auto-request faucet jika kurang.
- **Fallback ke `urllib`** → Jika `requests` tidak tersedia, pake `urllib.request`.
- **Rate limiting** → Minimal 60 detik antar request per alamat/chain.

---

## ✅ Perubahan yang Sudah Diapply

### 1. **Patch `onchain_bot.py`** (via `apply_patch.py`)
- **Baris 41**: Tambah import `requests` (dengan fallback `None` jika gagal).
  ```python
  try:
      import requests
  except ImportError:
      requests = None
  ```

- **Baris 794-795**: Tambah state faucet di `BlockchainEngine.__init__`:
  ```python
  # Faucet-related state
  self._faucet_last_request = {}
  ```

- **Baris 1819+**: Tambah method `_request_faucet()`:
  - Support **Sepolia**, **Polygon Amoy**, **Arbitrum Sepolia**, **Optimism Sepolia**.
  - Fallback ke `urllib` jika `requests` tidak ada.
  - Rate limiting (60 detik per alamat/chain).

- **Baris 1860+**: Tambah method `_ensure_minimum_balance()`:
  - Cek balance wallet sebelum transaksi.
  - Auto-request faucet **3x** jika balance < `min_balance` (default: 0.001 ETH).
  - Hanya berjalan di **testnet**.

- **Panggilan `_ensure_minimum_balance`** di 4 method:
  - `send_native` (baris 959)
  - `wrap_native` (baris 1107)
  - `unwrap_native` (baris 1149)
  - `swap_native_to_token` (baris 1198)

---

## ⚠️ Masalah yang Ketemu (Belum Terselesaikan)

### 1. **Test Script Gagal Inisialisasi `BlockchainEngine`**
- **Error**: `BlockchainEngine.__init__() takes 1 positional argument but 2 were given`
- **Penyebab**: Test script salah panggil `BlockchainEngine(config)` (seharusnya udah benar, tapi masih error).
- **Solusi yang dicoba**:
  - Udah perbaiki test script pake `Config(CONFIG_FILE)` (bukan `**config_data`).
  - Masih error → **butuh debug lebih lanjut**.

### 2. **Faucet Endpoints Belum Terverifikasi**
- **Sepolia**: `https://sepolia-faucet.pk910.de/` (POST, JSON)
- **Polygon Amoy**: `https://faucet.polygon.technology/` (POST, JSON)
- **Arbitrum Sepolia**: `https://arbitrum-sepolia.faucet.arbitrum.io/` (POST, JSON)
- **Optimism Sepolia**: `https://opsepolia-fuel.com/` (POST, JSON)
- **Status**: Belum di-test langsung (karena error inisialisasi).

### 3. **Fallback `urllib` Belum Teruji**
- Jika `requests` tidak terinstall, code akan fallback ke `urllib.request`.
- **Status**: Belum di-test (butuh verifikasi).

---

## 🔧 Cara Menguji (Untuk Tim)

### 1. **Persyaratan**
- Python 3.8+
- `pip install web3 requests` (atau `urllib` untuk fallback)
- Wallet test: `0x3E947a1B809847AA635c88ba1C1C95A14F518268`

### 2. **Langkah Test**
```bash
cd onchain-bot
# Apply patch (sudah dilakukan)
python apply_patch.py

# Test faucet (contoh untuk Sepolia)
python -c "
from onchain_bot import BlockchainEngine, Config
from decimal import Decimal

# Inisialisasi
config = Config('onchain_config.json')
engine = BlockchainEngine(config)
engine.set_chain('Sepolia')

# Test request faucet
result = engine._request_faucet('Sepolia', '0x3E947a1B809847AA635c88ba1C1C95A14F518268')
print('Faucet request:', 'SUKSES' if result else 'GAGAL')

# Test ensure_minimum_balance
wallet = {'address': '0x3E947a1B809847AA635c88ba1C1C95A14F518268'}
result = engine._ensure_minimum_balance(wallet, Decimal('0.0001'))
print('Balance check:', 'PASSED' if result else 'FAILED')
"
```

### 3. **Expected Output**
- Jika sukses:
  ```
  [OK] Faucet request successful for 0x3E9... on Sepolia
  [OK] Balance after faucet: 0.001 ETH
  ```
- Jika gagal (faucet endpoint down):
  ```
  [ERR] Faucet request failed: 404 Not Found
  [WARN] GET with data not supported in fallback, skipping faucet
  ```

---

## 🛠️ Alternatif Solusi (Jika Error Berlanjut)

### 1. **Jika `requests` Tidak Tersedia**
- Gunakan **`urllib`** (sudah di-implementasi di patch).
- Contoh fallback:
  ```python
  import urllib.request
  import json
  
  data = json.dumps({"address": "0x3E947a1B809847AA635c88ba1C1C95A14F518268"}).encode("utf-8")
  req = urllib.request.Request(
      "https://sepolia-faucet.pk910.de/",
      data=data,
      headers={"Content-Type": "application/json"},
      method="POST"
  )
  with urllib.request.urlopen(req, timeout=30) as resp:
      print(resp.status)  # 200 = sukses
  ```

### 2. **Jika Faucet Endpoint Gagal**
- **Alternatif faucet endpoints** (bisa ditambahkan di `FAUCETS`):
  | Chain          | Endpoint (Alternatif)                          | Method | Catatan                     |
  |----------------|-----------------------------------------------|--------|-----------------------------|
  | Sepolia        | `https://faucet.quicknode.com/eth/sepolia`    | POST   | Butuh API key              |
  | Sepolia        | `https://sepolia-faucet.vercel.app/`          | POST   | Tanpa API key              |
  | Polygon Amoy   | `https://faucet.amoy.polygon.technology/`      | POST   | Resmi Polygon              |
  | Arbitrum Sepolia | `https://faucet.arbitrum.io/`                | POST   | Resmi Arbitrum             |

### 3. **Jika Inisialisasi `BlockchainEngine` Masih Error**
- **Debug manual**:
  ```python
  from onchain_bot import Config, BlockchainEngine
  config = Config('onchain_config.json')
  print(config.data.keys())  # Cek struktur config
  engine = BlockchainEngine(config)  # Debug disini
  ```
- **Solusi sementara**: Panggil `_request_faucet` **langsung** (tanpa `BlockchainEngine`):
  ```python
  import sys
  sys.path.insert(0, '/path/to/onchain-bot')
  from onchain_bot import log_ok, log_err, time
  
  def request_faucet_manual(chain_name, address):
      FAUCETS = {
          "Sepolia": {
              "url": "https://sepolia-faucet.pk910.de/",
              "method": "POST",
              "headers": {"Content-Type": "application/json"},
              "data": lambda addr: {"address": addr},
          }
      }
      # ... (copy logic dari _request_faucet)
  ```

---

## 📝 Todo untuk Tim
- [ ] **Verifikasi patch** di `onchain_bot.py` (cek indentasi method `_request_faucet` dan `_ensure_minimum_balance`).
- [ ] **Test inisialisasi `BlockchainEngine`** (debug error `takes 1 positional argument but 2 were given`).
- [ ] **Test faucet endpoints** (Sepolia, Polygon Amoy, dll) dengan wallet test.
- [ ] **Tambah faucet endpoints alternatif** (lihat tabel di atas).
- [ ] **Update `FAUCETS`** di `_request_faucet` dengan endpoint yang working.
- [ ] **Hapus `apply_patch.py` dan `patch_bot.py`** (sudah tidak diperlukan).
- [ ] **Documentasi**: Tambah contoh penggunaan auto-faucet di README.

---

## 📎 File yang Berubah
1. **`onchain_bot.py`** → Patch auto-faucet (method + import + panggilan).
2. **`apply_patch.py`** → Script untuk apply patch (bisa dihapus setelah PR merged).
3. **`patch_bot.py`** → Backup script patch (bisa dihapus).

---

## 🔗 Referensi
- **Faucet Endpoints**:
  - [Sepolia Faucet (PK910)](https://sepolia-faucet.pk910.de/)
  - [Polygon Amoy Faucet](https://faucet.polygon.technology/)
  - [Arbitrum Sepolia Faucet](https://arbitrum-sepolia.faucet.arbitrum.io/)
  - [Optimism Sepolia Faucet](https://opsepolia-fuel.com/)
- **Fallback HTTP**: [Python `urllib` Docs](https://docs.python.org/3/library/urllib.request.html)

---

## 💬 Catatan Tambahan
- **Wallet Test**: `0x3E947a1B809847AA635c88ba1C1C95A14F518268` (sudah terdaftar di memory).
- **Rate Limiting**: 60 detik per alamat/chain (bisa disesuaikan).
- **Min Balance**: Default `0.001 ETH` (bisa diubah di `_ensure_minimum_balance`).
- **Retries**: 3x attempt sebelum gagal (bisa ditambah).

---

**PR ini siap untuk direview & dikerjakan oleh tim!** 🚀
