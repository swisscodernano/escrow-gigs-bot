from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db_core import Base


class Feedback(Base):
    __tablename__ = "feedbacks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("orders.id"), index=True
    )
    reviewer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), index=True
    )
    reviewee_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), index=True
    )
    review_type: Mapped[str] = mapped_column(
        String(16), default="buyer_review"
    )  # buyer_review or seller_review
    score: Mapped[int] = mapped_column(Integer)  # Score from 1 to 5
    comment: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    order = relationship("Order")
    reviewer = relationship("User", foreign_keys=[reviewer_id])
    reviewee = relationship("User", foreign_keys=[reviewee_id])

    __table_args__ = (
        UniqueConstraint("order_id", "reviewer_id", name="_order_reviewer_uc"),
    )
