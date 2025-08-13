
import os
import getpass
from bitcoinlib.wallets import HDWallet, wallet_delete
from bitcoinlib.mnemonic import Mnemonic

WALLET_NAME = 'escrow_wallet'
WALLET_DIR = '.wallet'
WALLET_PATH = os.path.join(WALLET_DIR, f'{WALLET_NAME}.db')
NETWORK = os.getenv('BTC_NETWORK', 'testnet')

def main():
    print(f'--- Setup Portafoglio Bitcoin ({NETWORK}) ---')

    if os.path.exists(WALLET_PATH):
        print(f'⚠️  Un portafoglio esiste già in "{WALLET_PATH}".')
        action = input('Vuoi cancellarlo e crearne uno nuovo? (sì/no): ').lower()
        if action == 'sì' or action == 'si':
            wallet_delete(WALLET_NAME, db_uri=f'sqlite:///{WALLET_PATH}')
            print('Vecchio portafoglio cancellato.')
        else:
            print('Setup annullato.')
            return

    if not os.path.exists(WALLET_DIR):
        os.makedirs(WALLET_DIR)

    password = getpass.getpass('Inserisci una password robusta per il portafoglio: ')
    password_confirm = getpass.getpass('Conferma password: ')

    if password != password_confirm:
        print('❌ Le password non coincidono.')
        return

    print('\nGenerazione del portafoglio in corso...')
    mnemonic = Mnemonic('english')
    seed_phrase = mnemonic.generate()
    
    wallet = HDWallet.create(
        WALLET_NAME,
        keys=seed_phrase,
        network=NETWORK,
        scheme='bip84',
        db_uri=f'sqlite:///{WALLET_PATH}'
    )
    wallet.encrypt(password)
    print(f'✅ Portafoglio "{WALLET_NAME}" creato con successo in "{WALLET_PATH}"')

    account = wallet.new_account('Escrow Account')
    xpub = account.xpub
    
    print('\n--- 💾 INFORMAZIONI CRITICHE - SALVARE IN UN POSTO SICURO ---')
    print(f'\n📄 Seed Phrase (Mnemonic):')
    print(f'   {seed_phrase}')
    
    print(f'\n🔑 Chiave Pubblica Estesa (XPUB) per il .env:')
    print(f'   {xpub}')
    
    print('\n--- ISTRUZIONI ---')
    print('1. Salva la SEED PHRASE in un luogo sicuro e offline. È l\'unico modo per recuperare i fondi.')
    print(f'2. Aggiungi le seguenti righe al tuo file .env:')
    print(f'   BTC_NETWORK={NETWORK}')
    print(f'   BTC_XPUB="{xpub}"')
    print(f'   BTC_WALLET_PASSPHRASE="{password}"')
    print(f'   BTC_WALLET_PATH="{WALLET_PATH}"')
    print('\nSetup completato.')

if __name__ == '__main__':
    main()
