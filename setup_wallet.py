import os
from bip_utils import Bip39MnemonicGenerator, Bip39SeedGenerator, Bip44, Bip44Coins

WALLET_DIR = '.wallet'
WALLET_FILE = os.path.join(WALLET_DIR, 'wallet.seed')
NETWORK = os.getenv('BTC_NETWORK', 'testnet')

def main():
    print(f'--- Setup Portafoglio Bitcoin ({NETWORK}) ---')

    if os.path.exists(WALLET_FILE):
        print(f'⚠️  Un seed di portafoglio esiste già in "{WALLET_FILE}".')
        print('Cancella manualmente il file .wallet/wallet.seed per crearne uno nuovo.')
        # Carica e mostra le info esistenti
        with open(WALLET_FILE, 'rb') as f:
            seed_bytes = f.read()
        print('\n--- INFORMAZIONI PORTAFOGLIO ESISTENTE ---')
    else:
        if not os.path.exists(WALLET_DIR):
            os.makedirs(WALLET_DIR)

        print('\nGenerazione di un nuovo portafoglio...')
        mnemonic = Bip39MnemonicGenerator().FromWordsNumber(12)
        # Per ora, la password del seed è vuota. L\'utente la imposterà nel .env
        seed_bytes = Bip39SeedGenerator(mnemonic).Generate("")

        with open(WALLET_FILE, 'wb') as f:
            f.write(seed_bytes)

        print(f'✅ Seed del portafoglio salvato in "{WALLET_FILE}"')
        print('\n--- 💾 INFORMAZIONI CRITICHE - SALVARE IN UN POSTO SICURO ---')
        print(f'\n📄 Seed Phrase (Mnemonic):')
        print(f'   {mnemonic}')

    coin_type = Bip44Coins.BITCOIN_TESTNET if NETWORK == 'testnet' else Bip44Coins.BITCOIN
    bip44_mst = Bip44.FromSeed(seed_bytes, coin_type)
    bip44_acc = bip44_mst.Purpose().Coin().Account(0)
    xpub = bip44_acc.PublicKey().ToExtended()

    print(f'\n🔑 Chiave Pubblica Estesa (XPUB):')
    print(f'   {xpub}')

    print('\n--- 🚀 AZIONE RICHIESTA ---')
    print('1. Salva la SEED PHRASE in un luogo sicuro e offline.')
    print(f'2. Crea o modifica il file .env nella cartella escrow-gigs-bot sul server.')
    print(f'3. Aggiungi queste righe al file .env:')
    print(f'   BTC_NETWORK={NETWORK}')
    print(f'   BTC_XPUB="{xpub}"')
    print(f'   BTC_WALLET_SEED_PASSPHRASE="LA_TUA_PASSWORD_SEGRETA"')
    print(f'   # Assicurati di impostare anche le altre variabili come TELEGRAM_TOKEN, etc.')

    print('\nSetup completato.')

if __name__ == '__main__':
    main()
