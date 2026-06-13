import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from api.models.user import Base


class WeeklyRecapRun(Base):
    __tablename__ = "weekly_recap_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    week_anchor_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    trigger_source: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")
    context_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    recap_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    proposal_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("coach_proposals.id"), nullable=True
    )
    recap_event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("coach_events.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    follow_up_question: Mapped[str | None] = mapped_column(Text, nullable=True)
    athlete_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (UniqueConstraint("user_id", "week_anchor_utc", name="uq_weekly_recap_runs_user_week_anchor"),)
