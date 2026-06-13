import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from api.models.user import Base


class AiRunCost(Base):
    __tablename__ = "ai_run_costs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    thread_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("coach_threads.id"),
        nullable=True,
        index=True,
    )
    feature: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(40), nullable=False)
    source_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    cost_status: Mapped[str] = mapped_column(String(20), nullable=False, default="captured")
    langsmith_project: Mapped[str | None] = mapped_column(String(200), nullable=True)
    langsmith_trace_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    langsmith_root_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    run_name: Mapped[str] = mapped_column(String(80), nullable=False)
    total_cost_usd: Mapped[float | None] = mapped_column(Numeric(12, 6), nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_web_searches: Mapped[int | None] = mapped_column(Integer, nullable=True)
    model_breakdown: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    source_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("source_type", "source_id", name="uq_ai_run_costs_source_ref"),
    )
