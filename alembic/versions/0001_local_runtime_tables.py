"""local runtime tables

Revision ID: 0001_local_runtime_tables
Revises:
Create Date: 2026-08-15
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0001_local_runtime_tables"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "runs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("game", sa.String(length=32), nullable=True),
        sa.Column("profile", sa.String(length=128), nullable=True),
        sa.Column("objective", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_runs_status", "runs", ["status"])

    op.create_table(
        "events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_events_event_type", "events", ["event_type"])
    op.create_index("ix_events_created_at", "events", ["created_at"])

    op.create_table(
        "macro_attempts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("run_id", sa.String(length=36), nullable=True),
        sa.Column("macro_name", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("expected_result", sa.Text(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_macro_attempts_run_id", "macro_attempts", ["run_id"])
    op.create_index("ix_macro_attempts_macro_name", "macro_attempts", ["macro_name"])
    op.create_index("ix_macro_attempts_status", "macro_attempts", ["status"])
    op.create_index("ix_macro_attempts_created_at", "macro_attempts", ["created_at"])

    op.create_table(
        "macro_feedback",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("macro_run_id", sa.String(length=36), nullable=False),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_macro_feedback_macro_run_id", "macro_feedback", ["macro_run_id"])
    op.create_index("ix_macro_feedback_outcome", "macro_feedback", ["outcome"])
    op.create_index("ix_macro_feedback_created_at", "macro_feedback", ["created_at"])

    op.create_table(
        "artifacts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("artifact_type", sa.String(length=64), nullable=False),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_artifacts_artifact_type", "artifacts", ["artifact_type"])
    op.create_index("ix_artifacts_created_at", "artifacts", ["created_at"])

    op.create_table(
        "model_calls",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("purpose", sa.String(length=128), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("cached_input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("estimated_cost_usd", sa.Float(), nullable=True),
        sa.Column("accepted", sa.Boolean(), nullable=False),
        sa.Column("required_retry", sa.Boolean(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_model_calls_provider", "model_calls", ["provider"])
    op.create_index("ix_model_calls_model", "model_calls", ["model"])
    op.create_index("ix_model_calls_purpose", "model_calls", ["purpose"])
    op.create_index("ix_model_calls_created_at", "model_calls", ["created_at"])


def downgrade() -> None:
    op.drop_table("model_calls")
    op.drop_table("artifacts")
    op.drop_table("macro_feedback")
    op.drop_table("macro_attempts")
    op.drop_table("events")
    op.drop_table("runs")
