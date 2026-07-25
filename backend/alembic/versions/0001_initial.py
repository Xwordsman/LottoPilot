"""Initial schema for LottoPilot.

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-24
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("display_name", sa.String(length=100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "user_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
    )
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])
    op.create_index("ix_user_sessions_token_hash", "user_sessions", ["token_hash"], unique=True)

    op.create_table(
        "app_settings",
        sa.Column("key", sa.String(length=100), primary_key=True, nullable=False),
        sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("job_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("progress_current", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("progress_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("resource_type", sa.String(length=50), nullable=True),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("payload_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("cancel_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_jobs_job_type", "jobs", ["job_type"])
    op.create_index("ix_jobs_status", "jobs", ["status"])

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("resource_type", sa.String(length=50), nullable=False),
        sa.Column("resource_id", sa.String(length=64), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_audit_logs_request_id", "audit_logs", ["request_id"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])

    op.create_table(
        "draws",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("lottery_type", sa.String(length=8), nullable=False),
        sa.Column("issue", sa.String(length=20), nullable=False),
        sa.Column("draw_date", sa.Date(), nullable=False),
        sa.Column("primary_numbers", postgresql.ARRAY(sa.SmallInteger()), nullable=False),
        sa.Column("secondary_numbers", postgresql.ARRAY(sa.SmallInteger()), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("source_checksum", sa.String(length=64), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("lottery_type", "issue", name="uq_draws_lottery_issue"),
    )
    op.create_index("ix_draws_lottery_type", "draws", ["lottery_type"])
    op.create_index("ix_draws_draw_date", "draws", ["draw_date"])

    op.create_table(
        "ingestion_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("source_name", sa.String(length=50), nullable=False),
        sa.Column("lottery_type", sa.String(length=8), nullable=False),
        sa.Column("mode", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pages_processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_seen", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("inserted_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skipped_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cursor", sa.String(length=100), nullable=True),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.UniqueConstraint("job_id", name="uq_ingestion_runs_job_id"),
    )
    op.create_index("ix_ingestion_runs_lottery_type", "ingestion_runs", ["lottery_type"])

    op.create_table(
        "ingestion_errors",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ingestion_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_item_key", sa.String(length=100), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_ingestion_errors_run_id", "ingestion_errors", ["run_id"])

    op.create_table(
        "strategy_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("version", sa.String(length=40), nullable=False),
        sa.Column("lottery_type", sa.String(length=8), nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("name", "version", "lottery_type", name="uq_strategy_name_ver_lottery"),
    )
    op.create_index("ix_strategy_profiles_lottery_type", "strategy_profiles", ["lottery_type"])

    op.create_table(
        "ai_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("base_url", sa.String(length=500), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("api_key_encrypted", sa.Text(), nullable=False),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("max_tokens", sa.Integer(), nullable=False, server_default="1024"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("extra", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("name", name="uq_ai_configs_name"),
    )

    op.create_table(
        "prize_rule_sets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("lottery_type", sa.String(length=8), nullable=False),
        sa.Column("version", sa.String(length=40), nullable=False),
        sa.Column("effective_from_issue", sa.String(length=20), nullable=True),
        sa.Column("effective_to_issue", sa.String(length=20), nullable=True),
        sa.Column("rules", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("lottery_type", "version", name="uq_prize_rule_lottery_version"),
    )
    op.create_index("ix_prize_rule_sets_lottery_type", "prize_rule_sets", ["lottery_type"])

    op.create_table(
        "recommendation_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("lottery_type", sa.String(length=8), nullable=False),
        sa.Column("target_issue", sa.String(length=20), nullable=True),
        sa.Column("strategy_profile_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("strategy_profiles.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("data_cutoff_issue", sa.String(length=20), nullable=True),
        sa.Column("data_snapshot_hash", sa.String(length=64), nullable=True),
        sa.Column("seed", sa.BigInteger(), nullable=True),
        sa.Column("candidate_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ai_config_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ai_configs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("ai_status", sa.String(length=20), nullable=False),
        sa.Column("ai_provider", sa.String(length=50), nullable=True),
        sa.Column("ai_model", sa.String(length=100), nullable=True),
        sa.Column("ai_prompt_version", sa.String(length=40), nullable=True),
        sa.Column("ai_response_hash", sa.String(length=64), nullable=True),
        sa.Column("ai_metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("job_id", name="uq_recommendation_runs_job_id"),
    )
    op.create_index("ix_recommendation_runs_lottery_type", "recommendation_runs", ["lottery_type"])
    op.create_index("ix_recommendation_runs_status", "recommendation_runs", ["status"])

    op.create_table(
        "recommendation_tickets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("recommendation_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rank", sa.SmallInteger(), nullable=False),
        sa.Column("primary_numbers", postgresql.ARRAY(sa.SmallInteger()), nullable=False),
        sa.Column("secondary_numbers", postgresql.ARRAY(sa.SmallInteger()), nullable=False),
        sa.Column("statistical_score", sa.Numeric(12, 6), nullable=False),
        sa.Column("ai_score", sa.Numeric(12, 6), nullable=True),
        sa.Column("final_score", sa.Numeric(12, 6), nullable=False),
        sa.Column("feature_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("run_id", "rank", name="uq_recommendation_ticket_rank"),
    )
    op.create_index("ix_recommendation_tickets_run_id", "recommendation_tickets", ["run_id"])

    op.create_table(
        "recommendation_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("recommendation_tickets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("draw_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("draws.id", ondelete="CASCADE"), nullable=False),
        sa.Column("primary_hits", sa.SmallInteger(), nullable=False),
        sa.Column("secondary_hits", sa.SmallInteger(), nullable=False),
        sa.Column("prize_level", sa.String(length=40), nullable=True),
        sa.Column("prize_rule_set_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("prize_rule_sets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("ticket_id", "draw_id", name="uq_recommendation_result_ticket_draw"),
    )

    op.create_table(
        "backtest_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("lottery_type", sa.String(length=8), nullable=False),
        sa.Column("strategy_profile_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("strategy_profiles.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("start_issue", sa.String(length=20), nullable=False),
        sa.Column("end_issue", sa.String(length=20), nullable=False),
        sa.Column("seed", sa.BigInteger(), nullable=True),
        sa.Column("baseline_trials", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("job_id", name="uq_backtest_runs_job_id"),
    )
    op.create_index("ix_backtest_runs_lottery_type", "backtest_runs", ["lottery_type"])
    op.create_index("ix_backtest_runs_status", "backtest_runs", ["status"])

    op.create_table(
        "backtest_issue_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("backtest_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("backtest_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_draw_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("draws.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("training_cutoff_draw_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("draws.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("tickets", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("hit_metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("baseline_metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("runtime_ms", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_backtest_issue_results_backtest_run_id", "backtest_issue_results", ["backtest_run_id"])


def downgrade() -> None:
    op.drop_table("backtest_issue_results")
    op.drop_table("backtest_runs")
    op.drop_table("recommendation_results")
    op.drop_table("recommendation_tickets")
    op.drop_table("recommendation_runs")
    op.drop_table("prize_rule_sets")
    op.drop_table("ai_configs")
    op.drop_table("strategy_profiles")
    op.drop_table("ingestion_errors")
    op.drop_table("ingestion_runs")
    op.drop_table("draws")
    op.drop_table("audit_logs")
    op.drop_table("jobs")
    op.drop_table("app_settings")
    op.drop_table("user_sessions")
    op.drop_table("users")
