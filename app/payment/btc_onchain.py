from bip_utils import (
    Bip39MnemonicGenerator,
    Bip39SeedGenerator,
    Bip44,
    Bip44Coins,
    Bip44Changes,
)

def new_deposit_address(order_id: int):
    # Generate a 12-word mnemonic
    mnemonic = Bip39MnemonicGenerator().FromWordsNumber(12)

    # Generate the seed from the mnemonic
    seed_bytes = Bip39SeedGenerator(mnemonic).Generate()

    # Create a BIP44 wallet for Bitcoin
    bip44_mst_ctx = Bip44.FromSeed(seed_bytes, Bip44Coins.BITCOIN)

    # Derive the first account
    bip44_acc_ctx = bip44_mst_ctx.Purpose().Coin().Account(0)

    # Derive the external chain
    bip44_chg_ctx = bip44_acc_ctx.Change(Bip44Changes.CHAIN_EXT)

    # Derive the address for the order
    bip44_addr_ctx = bip44_chg_ctx.AddressIndex(order_id)

    # Return the address
    return bip44_addr_ctx.PublicKey().ToAddress()