"""Persist typed coverage, FTS documents, embedding chunks and index jobs."""

from alembic import op
import sqlalchemy as sa


revision = "ad81c0a8e56a"
down_revision = "7a98092553cd"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "profile_coverages",
        sa.Column("profile_id", sa.String(length=64), nullable=False),
        sa.Column("scope_key", sa.String(length=170), nullable=False),
        sa.Column("department_id", sa.String(length=80), nullable=True),
        sa.Column("locality_id", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("(department_id IS NULL) != (locality_id IS NULL)", name="ck_profile_coverage_one_scope"),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["locality_id"], ["localities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["profile_id"], ["profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("profile_id", "scope_key"),
    )
    op.create_index("ix_profile_coverages_locality", "profile_coverages", ["locality_id"])
    op.create_index("ix_profile_coverages_department", "profile_coverages", ["department_id"])

    op.create_table(
        "profile_search_documents",
        sa.Column("profile_id", sa.String(length=64), nullable=False),
        sa.Column("source_hash", sa.String(length=64), nullable=False),
        sa.Column("search_text", sa.Text(), nullable=False),
        sa.Column("profession", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("short_description", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("tags", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["profile_id"], ["profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("profile_id"),
    )

    op.create_table(
        "profile_search_chunks",
        sa.Column("chunk_id", sa.String(length=64), nullable=False),
        sa.Column("profile_id", sa.String(length=64), nullable=False),
        sa.Column("source_hash", sa.String(length=64), nullable=False),
        sa.Column("source_field", sa.String(length=32), nullable=False),
        sa.Column("literal_text", sa.Text(), nullable=False),
        sa.Column("start_char", sa.Integer(), nullable=False),
        sa.Column("end_char", sa.Integer(), nullable=False),
        sa.Column("encoder_model", sa.String(length=160), nullable=False),
        sa.Column("encoder_revision", sa.String(length=64), nullable=False),
        sa.Column("vector_dimension", sa.Integer(), nullable=False),
        sa.Column("vector_dtype", sa.String(length=24), nullable=False),
        sa.Column("vector_bytes", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["profile_id"], ["profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("chunk_id"),
    )
    op.create_index("ix_profile_search_chunks_profile_revision", "profile_search_chunks", ["profile_id", "source_hash"])
    op.create_index("ix_profile_search_chunks_encoder", "profile_search_chunks", ["encoder_model", "encoder_revision"])

    op.create_table(
        "profile_search_index_jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("profile_id", sa.String(length=64), nullable=False),
        sa.Column("source_hash", sa.String(length=64), nullable=False),
        sa.Column("encoder_model", sa.String(length=160), nullable=False),
        sa.Column("encoder_revision", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("last_error", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("status IN ('pending', 'running', 'succeeded', 'failed', 'superseded')", name="ck_profile_index_job_status"),
        sa.ForeignKeyConstraint(["profile_id"], ["profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("profile_id", "source_hash", "encoder_model", "encoder_revision", name="uq_profile_index_revision"),
    )
    op.create_index("ix_profile_index_jobs_queue", "profile_search_index_jobs", ["status", "next_attempt_at", "created_at"])

    op.create_table(
        "advanced_search_rate_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("account_id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_advanced_search_rate_account_time", "advanced_search_rate_events", ["account_id", "created_at"])

    if op.get_bind().dialect.name == "sqlite":
        op.execute(
            "CREATE VIRTUAL TABLE profile_search_fts USING fts5("
            "profile_id UNINDEXED, source_hash UNINDEXED, profession, category, "
            "short_description, description, tags, "
            "tokenize='unicode61 remove_diacritics 2')"
        )


def downgrade():
    if op.get_bind().dialect.name == "sqlite":
        op.execute("DROP TABLE IF EXISTS profile_search_fts")
    op.drop_index("ix_advanced_search_rate_account_time", table_name="advanced_search_rate_events")
    op.drop_table("advanced_search_rate_events")
    op.drop_index("ix_profile_index_jobs_queue", table_name="profile_search_index_jobs")
    op.drop_table("profile_search_index_jobs")
    op.drop_index("ix_profile_search_chunks_encoder", table_name="profile_search_chunks")
    op.drop_index("ix_profile_search_chunks_profile_revision", table_name="profile_search_chunks")
    op.drop_table("profile_search_chunks")
    op.drop_table("profile_search_documents")
    op.drop_index("ix_profile_coverages_department", table_name="profile_coverages")
    op.drop_index("ix_profile_coverages_locality", table_name="profile_coverages")
    op.drop_table("profile_coverages")
