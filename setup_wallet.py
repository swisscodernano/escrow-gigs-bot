import os
import getpass
from bip_utils import Bip39MnemonicGenerator, Bip39SeedGenerator, Bip44, Bip44Coins, Bip44Changes

WALLET_DIR = '.wallet'
WALLET_FILE = os.path.join(WALLET_DIR, 'wallet.seed')
NETWORK = os.getenv('BTC_NETWORK', 'testnet')

def main():
    print(f'--- Setup Portafoglio Bitcoin ({NETWORK}) ---')

    if os.path.exists(WALLET_FILE):
        print(f'⚠️  Un seed di portafoglio esiste già in "{WALLET_FILE}".')
        action = input('Vuoi cancellarlo e crearne uno nuovo? (sì/no): ').lower()
        if action in ['sì', 'si', 'yes', 'y']:
            os.remove(WALLET_FILE)
            print('Vecchio file del seed cancellato.')
        else:
            print('Setup annullato.')
            return

    if not os.path.exists(WALLET_DIR):
        os.makedirs(WALLET_DIR)

    password = getpass.getpass('Inserisci una password robusta per criptare il seed (opzionale, premi invio per saltare): ')
    
    print('\nGenerazione del seed in corso...')
    mnemonic = Bip39MnemonicGenerator().Generate()
    seed_bytes = Bip39SeedGenerator(mnemonic).Generate(password)

    with open(WALLET_FILE, 'wb') as f:
        f.write(seed_bytes)
    
    print(f'✅ Seed del portafoglio salvato e criptato in "{WALLET_FILE}"')

    coin_type = Bip44Coins.BITCOIN_TESTNET if NETWORK == 'testnet' else Bip44Coins.BITCOIN
    bip44_mst = Bip44.FromSeed(seed_bytes, coin_type)
    bip44_acc = bip44_mst.Purpose().Coin().Account(0)
    xpub = bip44_acc.PublicKey().ToExtended()

    print('\n--- 💾 INFORMAZIONI CRITICHE - SALVARE IN UN POSTO SICURO ---')
    print(f'\n📄 Seed Phrase (Mnemonic):')
    print(f'   {mnemonic}')
    
    print(f'\n🔑 Chiave Pubblica Estesa (XPUB) per il .env:')
    print(f'   {xpub}')
    
    print('\n--- ISTRUZIONI ---')
    print('1. Salva la SEED PHRASE in un luogo sicuro e offline. È l\'unico modo per recuperare i fondi.')
    print(f'2. Aggiungi le seguenti righe al tuo file .env:')
    print(f'   BTC_NETWORK={NETWORK}')
    print(f'   BTC_XPUB="{xpub}"')
    print(f'   # Lascia vuota la password se non l\'hai impostata')
    print(f'   BTC_WALLET_SEED_PASSPHRASE="{password}"')

    print('\nSetup completato.')

if __name__ == '__main__':
    main()