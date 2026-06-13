"""initial local-first schema

Revision ID: 001_initial_local_first
Revises:
Create Date: 2026-06-13 11:05:02.402223

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "001_initial_local_first"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "local_usage_plan_overrides",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("plan_key", sa.String(length=100), nullable=True),
        sa.Column("plan_name", sa.String(length=255), nullable=True),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("local_owner_key", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("credits", sa.Integer(), nullable=False),
        sa.Column("memory_summary", sa.Text(), nullable=True),
        sa.Column("athlete_model", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index(op.f("ix_users_local_owner_key"), "users", ["local_owner_key"], unique=True)
    op.create_table(
        "analysis_jobs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("progress_steps", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("cost_usd", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_analysis_jobs_user_id"), "analysis_jobs", ["user_id"], unique=False)
    op.create_table(
        "athlete_profiles",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("profile", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_athlete_profiles_user_id"), "athlete_profiles", ["user_id"], unique=True)
    op.create_table(
        "coach_conversations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_coach_conversations_user_id"),
    )
    op.create_index(op.f("ix_coach_conversations_user_id"), "coach_conversations", ["user_id"], unique=False)
    op.create_table(
        "coach_interaction_quotas",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("week_anchor_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("interactions_used", sa.Integer(), nullable=False),
        sa.Column("interactions_limit", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "week_anchor_utc", name="uq_coach_interaction_quotas_user_week_anchor"),
    )
    op.create_index(op.f("ix_coach_interaction_quotas_user_id"), "coach_interaction_quotas", ["user_id"], unique=False)
    op.create_table(
        "coach_turn_requests",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=120), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("response_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "idempotency_key", name="uq_coach_turn_requests_user_key"),
    )
    op.create_index(op.f("ix_coach_turn_requests_user_id"), "coach_turn_requests", ["user_id"], unique=False)
    op.create_table(
        "competitions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("date", sa.Date(), nullable=True),
        sa.Column("date_text", sa.String(length=120), nullable=True),
        sa.Column("race_type", sa.String(length=100), nullable=True),
        sa.Column("priority", sa.String(length=10), nullable=True),
        sa.Column("target_time", sa.String(length=50), nullable=True),
        sa.Column("notes", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_competitions_user_id"), "competitions", ["user_id"], unique=False)
    op.create_table(
        "integration_connections",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("first_connected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_connected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_disconnected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_disconnect_reason", sa.String(length=64), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("user_id", "provider"),
    )
    op.create_table(
        "local_usage_counters",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("feature_key", sa.String(length=100), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used", sa.Integer(), nullable=False),
        sa.Column("limit_value", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "feature_key", "window_start", "window_end", name="uq_local_usage_counters_user_feature_window"
        ),
    )
    op.create_index(op.f("ix_local_usage_counters_user_id"), "local_usage_counters", ["user_id"], unique=False)
    op.create_table(
        "local_usage_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("feature_key", sa.String(length=100), nullable=False),
        sa.Column("source_type", sa.String(length=100), nullable=False),
        sa.Column("source_id", sa.String(length=255), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("consumed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("feature_key", "source_type", "source_id", name="uq_local_usage_events_feature_source"),
    )
    op.create_index(op.f("ix_local_usage_events_user_id"), "local_usage_events", ["user_id"], unique=False)
    op.create_table(
        "oauth_sessions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("state", sa.String(length=255), nullable=False),
        sa.Column("code_verifier", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "state", name="uq_oauth_sessions_provider_state"),
    )
    op.create_index(op.f("ix_oauth_sessions_expires_at"), "oauth_sessions", ["expires_at"], unique=False)
    op.create_index(op.f("ix_oauth_sessions_provider"), "oauth_sessions", ["provider"], unique=False)
    op.create_index(op.f("ix_oauth_sessions_user_id"), "oauth_sessions", ["user_id"], unique=False)
    op.create_table(
        "strava_credentials",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("encrypted_access_token", sa.LargeBinary(), nullable=False),
        sa.Column("encrypted_refresh_token", sa.LargeBinary(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scope", sa.String(length=1024), nullable=False),
        sa.Column("strava_athlete_id", sa.BigInteger(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_index(
        op.f("ix_strava_credentials_strava_athlete_id"), "strava_credentials", ["strava_athlete_id"], unique=False
    )
    op.create_table(
        "whoop_credentials",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("encrypted_access_token", sa.LargeBinary(), nullable=False),
        sa.Column("encrypted_refresh_token", sa.LargeBinary(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scope", sa.String(length=1024), nullable=False),
        sa.Column("whoop_user_id", sa.BigInteger(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_table(
        "active_analyses",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("analysis_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("expert_context", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source_job_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_job_id"],
            ["analysis_jobs.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_active_analyses_user_id"),
    )
    op.create_index(op.f("ix_active_analyses_user_id"), "active_analyses", ["user_id"], unique=True)
    op.create_table(
        "active_season_plans",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("plan_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source_job_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_job_id"],
            ["analysis_jobs.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_active_season_plans_user_id"),
    )
    op.create_index(op.f("ix_active_season_plans_user_id"), "active_season_plans", ["user_id"], unique=True)
    op.create_table(
        "active_weekly_plans",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("plan_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source_job_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_job_id"],
            ["analysis_jobs.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_active_weekly_plans_user_id"),
    )
    op.create_index(op.f("ix_active_weekly_plans_user_id"), "active_weekly_plans", ["user_id"], unique=True)
    op.create_table(
        "coach_messages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("conversation_id", sa.UUID(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["coach_conversations.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_coach_messages_conversation_id"), "coach_messages", ["conversation_id"], unique=False)
    op.create_table(
        "coach_threads",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=True),
        sa.Column("latest_seq", sa.Integer(), nullable=False),
        sa.Column("last_full_run_job_id", sa.UUID(), nullable=True),
        sa.Column("last_full_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["last_full_run_job_id"],
            ["analysis_jobs.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_coach_threads_user_id"), "coach_threads", ["user_id"], unique=False)
    op.create_table(
        "ai_run_costs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("thread_id", sa.UUID(), nullable=True),
        sa.Column("feature", sa.String(length=40), nullable=False),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("source_id", sa.String(length=120), nullable=True),
        sa.Column("cost_status", sa.String(length=20), nullable=False),
        sa.Column("langsmith_project", sa.String(length=200), nullable=True),
        sa.Column("langsmith_trace_id", sa.String(length=36), nullable=True),
        sa.Column("langsmith_root_run_id", sa.String(length=36), nullable=True),
        sa.Column("run_name", sa.String(length=80), nullable=False),
        sa.Column("total_cost_usd", sa.Numeric(precision=12, scale=6), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("total_input_tokens", sa.Integer(), nullable=True),
        sa.Column("total_output_tokens", sa.Integer(), nullable=True),
        sa.Column("total_web_searches", sa.Integer(), nullable=True),
        sa.Column("model_breakdown", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("source_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["thread_id"],
            ["coach_threads.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_type", "source_id", name="uq_ai_run_costs_source_ref"),
    )
    op.create_index(op.f("ix_ai_run_costs_feature"), "ai_run_costs", ["feature"], unique=False)
    op.create_index(
        op.f("ix_ai_run_costs_langsmith_root_run_id"), "ai_run_costs", ["langsmith_root_run_id"], unique=False
    )
    op.create_index(op.f("ix_ai_run_costs_langsmith_trace_id"), "ai_run_costs", ["langsmith_trace_id"], unique=False)
    op.create_index(op.f("ix_ai_run_costs_thread_id"), "ai_run_costs", ["thread_id"], unique=False)
    op.create_index(op.f("ix_ai_run_costs_user_id"), "ai_run_costs", ["user_id"], unique=False)
    op.create_table(
        "coach_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("thread_id", sa.UUID(), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("actor", sa.String(length=20), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["thread_id"],
            ["coach_threads.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("thread_id", "seq", name="uq_coach_events_thread_seq"),
    )
    op.create_index(op.f("ix_coach_events_thread_id"), "coach_events", ["thread_id"], unique=False)
    op.create_table(
        "coach_proposals",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("thread_id", sa.UUID(), nullable=True),
        sa.Column("source_event_seq", sa.Integer(), nullable=True),
        sa.Column("weekly_plan_version", sa.Integer(), nullable=False),
        sa.Column("assistant_message", sa.String(), nullable=False),
        sa.Column("ops", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("origin", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("rejection_reason", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["thread_id"],
            ["coach_threads.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_coach_proposals_thread_id"), "coach_proposals", ["thread_id"], unique=False)
    op.create_index(op.f("ix_coach_proposals_user_id"), "coach_proposals", ["user_id"], unique=False)
    op.create_table(
        "coach_turn_runs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("thread_id", sa.UUID(), nullable=False),
        sa.Column("turn_seq_anchor", sa.Integer(), nullable=False),
        sa.Column("user_message_event_id", sa.UUID(), nullable=False),
        sa.Column("response_event_id", sa.UUID(), nullable=True),
        sa.Column("langsmith_project", sa.String(length=200), nullable=True),
        sa.Column("langsmith_trace_id", sa.String(length=36), nullable=True),
        sa.Column("langsmith_root_run_id", sa.String(length=36), nullable=True),
        sa.Column("run_name", sa.String(length=80), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["response_event_id"],
            ["coach_events.id"],
        ),
        sa.ForeignKeyConstraint(
            ["thread_id"],
            ["coach_threads.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_message_event_id"],
            ["coach_events.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_message_event_id", name="uq_coach_turn_runs_user_message_event_id"),
    )
    op.create_index(
        op.f("ix_coach_turn_runs_langsmith_trace_id"), "coach_turn_runs", ["langsmith_trace_id"], unique=False
    )
    op.create_index(op.f("ix_coach_turn_runs_thread_id"), "coach_turn_runs", ["thread_id"], unique=False)
    op.create_index(op.f("ix_coach_turn_runs_user_id"), "coach_turn_runs", ["user_id"], unique=False)
    op.create_table(
        "daily_update_runs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=False),
        sa.Column("trigger_source", sa.String(length=20), nullable=False),
        sa.Column("context_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("update_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("proposal_id", sa.UUID(), nullable=True),
        sa.Column("update_event_id", sa.UUID(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["proposal_id"],
            ["coach_proposals.id"],
        ),
        sa.ForeignKeyConstraint(
            ["update_event_id"],
            ["coach_events.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "target_date", name="uq_daily_update_runs_user_target_date"),
    )
    op.create_index(op.f("ix_daily_update_runs_user_id"), "daily_update_runs", ["user_id"], unique=False)
    op.create_table(
        "weekly_recap_runs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("week_anchor_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("trigger_source", sa.String(length=20), nullable=False),
        sa.Column("context_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("recap_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("proposal_id", sa.UUID(), nullable=True),
        sa.Column("recap_event_id", sa.UUID(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("follow_up_question", sa.Text(), nullable=True),
        sa.Column("athlete_response", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["proposal_id"],
            ["coach_proposals.id"],
        ),
        sa.ForeignKeyConstraint(
            ["recap_event_id"],
            ["coach_events.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "week_anchor_utc", name="uq_weekly_recap_runs_user_week_anchor"),
    )
    op.create_index(op.f("ix_weekly_recap_runs_user_id"), "weekly_recap_runs", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_weekly_recap_runs_user_id"), table_name="weekly_recap_runs")
    op.drop_table("weekly_recap_runs")
    op.drop_index(op.f("ix_daily_update_runs_user_id"), table_name="daily_update_runs")
    op.drop_table("daily_update_runs")
    op.drop_index(op.f("ix_coach_turn_runs_user_id"), table_name="coach_turn_runs")
    op.drop_index(op.f("ix_coach_turn_runs_thread_id"), table_name="coach_turn_runs")
    op.drop_index(op.f("ix_coach_turn_runs_langsmith_trace_id"), table_name="coach_turn_runs")
    op.drop_table("coach_turn_runs")
    op.drop_index(op.f("ix_coach_proposals_user_id"), table_name="coach_proposals")
    op.drop_index(op.f("ix_coach_proposals_thread_id"), table_name="coach_proposals")
    op.drop_table("coach_proposals")
    op.drop_index(op.f("ix_coach_events_thread_id"), table_name="coach_events")
    op.drop_table("coach_events")
    op.drop_index(op.f("ix_ai_run_costs_user_id"), table_name="ai_run_costs")
    op.drop_index(op.f("ix_ai_run_costs_thread_id"), table_name="ai_run_costs")
    op.drop_index(op.f("ix_ai_run_costs_langsmith_trace_id"), table_name="ai_run_costs")
    op.drop_index(op.f("ix_ai_run_costs_langsmith_root_run_id"), table_name="ai_run_costs")
    op.drop_index(op.f("ix_ai_run_costs_feature"), table_name="ai_run_costs")
    op.drop_table("ai_run_costs")
    op.drop_index(op.f("ix_coach_threads_user_id"), table_name="coach_threads")
    op.drop_table("coach_threads")
    op.drop_index(op.f("ix_coach_messages_conversation_id"), table_name="coach_messages")
    op.drop_table("coach_messages")
    op.drop_index(op.f("ix_active_weekly_plans_user_id"), table_name="active_weekly_plans")
    op.drop_table("active_weekly_plans")
    op.drop_index(op.f("ix_active_season_plans_user_id"), table_name="active_season_plans")
    op.drop_table("active_season_plans")
    op.drop_index(op.f("ix_active_analyses_user_id"), table_name="active_analyses")
    op.drop_table("active_analyses")
    op.drop_table("whoop_credentials")
    op.drop_index(op.f("ix_strava_credentials_strava_athlete_id"), table_name="strava_credentials")
    op.drop_table("strava_credentials")
    op.drop_index(op.f("ix_oauth_sessions_user_id"), table_name="oauth_sessions")
    op.drop_index(op.f("ix_oauth_sessions_provider"), table_name="oauth_sessions")
    op.drop_index(op.f("ix_oauth_sessions_expires_at"), table_name="oauth_sessions")
    op.drop_table("oauth_sessions")
    op.drop_index(op.f("ix_local_usage_events_user_id"), table_name="local_usage_events")
    op.drop_table("local_usage_events")
    op.drop_index(op.f("ix_local_usage_counters_user_id"), table_name="local_usage_counters")
    op.drop_table("local_usage_counters")
    op.drop_table("integration_connections")
    op.drop_index(op.f("ix_competitions_user_id"), table_name="competitions")
    op.drop_table("competitions")
    op.drop_index(op.f("ix_coach_turn_requests_user_id"), table_name="coach_turn_requests")
    op.drop_table("coach_turn_requests")
    op.drop_index(op.f("ix_coach_interaction_quotas_user_id"), table_name="coach_interaction_quotas")
    op.drop_table("coach_interaction_quotas")
    op.drop_index(op.f("ix_coach_conversations_user_id"), table_name="coach_conversations")
    op.drop_table("coach_conversations")
    op.drop_index(op.f("ix_athlete_profiles_user_id"), table_name="athlete_profiles")
    op.drop_table("athlete_profiles")
    op.drop_index(op.f("ix_analysis_jobs_user_id"), table_name="analysis_jobs")
    op.drop_table("analysis_jobs")
    op.drop_index(op.f("ix_users_local_owner_key"), table_name="users")
    op.drop_table("users")
    op.drop_table("local_usage_plan_overrides")
