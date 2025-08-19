def format_dispute_summary(order_id: int, buyer_claim: str, seller_claim: str) -> str:
    return (
        f"# Dispute Summary for Order {order_id}\n"
        f"**Buyer says:** {buyer_claim}\n"
        f"**Seller says:** {seller_claim}\n"
        "Suggested next steps: request evidence (screenshots, file hashes), check delivery logs."
    )
