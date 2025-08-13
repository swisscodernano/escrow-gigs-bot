from celery import Celery
from app.config import settings
from db import SessionLocal
from models import Order

celery_app = Celery(
    "tasks",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

@celery_app.task
def process_withdrawal(order_id: int):
    """
    Task asincrono per processare un prelievo.
    TODO: Implementare la logica on-chain effettiva.
    """
    db = SessionLocal()
    order = db.query(Order).get(order_id)
    if not order or order.status != "RELEASED":
        print(f"[WORKER] Ordine {order_id} non valido o non pronto per il prelievo.")
        db.close()
        return

    print(f"[WORKER] Avvio prelievo per ordine #{order_id}...")
    # --- QUI VA LA LOGICA ON-CHAIN ---
    # 1. Carica il wallet usando la seed phrase (passata come variabile d'ambiente sicura)
    # 2. Determina l'indirizzo di destinazione del venditore (da aggiungere al modello User)
    # 3. Calcola l'importo finale (al netto della fee)
    # 4. Crea, firma e trasmetti la transazione Bitcoin/TRON
    # 5. Attendi la conferma della transazione
    # ------------------------------------
    
    # Per ora, simuliamo il successo
    order.status = "COMPLETED"
    db.commit()
    print(f"[WORKER] Prelievo per ordine #{order_id} completato con successo (simulato).")
    db.close()
