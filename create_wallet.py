
from bitcoinlib.wallets import HDWallet

wallet = HDWallet.create('escrow_wallet')
print(f"Mnemonic: {wallet.mnemonic}")
print(f"Master Key: {wallet.master_key_hex}")
