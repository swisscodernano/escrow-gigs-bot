#!/usr/bin/env python3
import os, sys
from getpass import getpass
from bip_utils import (
    Bip39SeedGenerator, Bip39MnemonicValidator, Bip39Languages,
    Bip44, Bip44Coins, Bip44Changes
)

# TRON / Trust Wallet: m/44'/195'/0'/0/index
BASE_DERIV = "m/44'/195'/0'/0"
expect = os.getenv("EXPECT_ADDR", "").strip().upper()
scan = int(os.getenv("SCAN", "0"))      # 0 = usa solo ADDR_INDEX
idx  = int(os.getenv("ADDR_INDEX", "0"))

def read_mnemonic():
    if os.getenv("MNEMONIC"):
        return os.getenv("MNEMONIC").strip()
    if len(sys.argv) >= 2 and os.path.isfile(sys.argv[1]):
        return open(sys.argv[1], "r", encoding="utf-8").read().strip()
    print("Inserisci le 12/24 parole (non verranno salvate):")
    return getpass("> ").strip()

mnemo = read_mnemonic()

# Valida (specificando la lingua nel costruttore)
Bip39MnemonicValidator(Bip39Languages.ENGLISH).Validate(mnemo)
seed = Bip39SeedGenerator(mnemo).Generate()

def derive_at(i: int):
    acc = (Bip44.FromSeed(seed, Bip44Coins.TRON)
              .Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(i))
    return {
        "index": i,
        "path": f"{BASE_DERIV}/{i}",
        "address": acc.PublicKey().ToAddress(),          # es. TRxxxx
        "priv_hex": acc.PrivateKey().Raw().ToHex(),      # per TRON_USDT_PRIV (senza 0x)
    }

if scan and scan > 0:
    print(f"==> Scansione indici 0..{scan-1} (path base {BASE_DERIV})")
    for i in range(scan):
        r = derive_at(i)
        line = f"[{i:02d}] {r['address']}  {r['path']}"
        if expect and r["address"].upper() == expect:
            print(line, "<- MATCH")
            print("Private Key (HEX):", r["priv_hex"])
            sys.exit(0)
        print(line)
    if expect:
        print("\nNessun match trovato. Aumenta SCAN e riprova.")
else:
    r = derive_at(idx)
    print("==> Derivazione:", r["path"])
    print("TRON Address:", r["address"])
    print("Private Key (HEX):", r["priv_hex"])
