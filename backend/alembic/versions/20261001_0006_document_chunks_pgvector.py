"""document search: pgvector extension, document_chunks table, document index state

Vector column: vector(768), gemini-embedding-2 with outputDimensionality=768 (verified against the
API). Distance: cosine. Index: HNSW with vector_cosine_ops (works on an empty table, good recall,
no re-training as documents are added, unlike IVFFlat).

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-01 09:00:00
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DIMENSIONS = 768


def upgrade() -> None:
    # Deliberately not wrapped: without pgvector the migration must fail, not half-apply.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    index_status = sa.Enum("pending", "indexing", "indexed", "failed", "unsupported", name="documentindexstatus",
                           native_enum=False, create_constraint=True, length=32)
    op.add_column("documents", sa.Column("index_status", index_status, server_default="pending", nullable=False))
    op.add_column("documents", sa.Column("index_error", sa.Text(), nullable=True))
    op.add_column("documents", sa.Column("index_attempts", sa.Integer(), server_default="0", nullable=False))
    op.add_column("documents", sa.Column("index_started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("documents", sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("documents", sa.Column("chunk_count", sa.Integer(), server_default="0", nullable=False))
    op.add_column("documents", sa.Column("embedding_model", sa.String(length=100), nullable=True))

    op.create_table(
        "document_chunks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("character_count", sa.Integer(), nullable=False),
        sa.Column("embedding", Vector(DIMENSIONS), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], name=op.f("fk_document_chunks_document_id_documents"),
                                ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_document_chunks_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_document_chunks")),
        sa.UniqueConstraint("document_id", "chunk_index", name="uq_document_chunks_document_id_chunk_index"),
    )
    op.create_index(op.f("ix_document_chunks_user_id"), "document_chunks", ["user_id"], unique=False)
    op.create_index(op.f("ix_document_chunks_document_id"), "document_chunks", ["document_id"], unique=False)
    op.create_index("ix_document_chunks_embedding_hnsw", "document_chunks", ["embedding"], unique=False,
                    postgresql_using="hnsw", postgresql_ops={"embedding": "vector_cosine_ops"})


def downgrade() -> None:
    op.drop_index("ix_document_chunks_embedding_hnsw", table_name="document_chunks")
    op.drop_index(op.f("ix_document_chunks_document_id"), table_name="document_chunks")
    op.drop_index(op.f("ix_document_chunks_user_id"), table_name="document_chunks")
    op.drop_table("document_chunks")
    for column in ("embedding_model", "chunk_count", "indexed_at", "index_started_at", "index_attempts",
                   "index_error", "index_status"):
        op.drop_column("documents", column)
    # The extension is left installed: other database objects may use it.
