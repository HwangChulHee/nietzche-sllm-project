"""vn save_slots — drop chatbot tables, add single save_slot

Revision ID: 002
Revises: 001
Create Date: 2026-05-01

비주얼 노벨 전환:
- conversations / messages 테이블 제거 (옛 챗봇 자산, archived/로 이동)
- save_slots 테이블 신설 (단일 슬롯, id=1 고정)
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 옛 챗봇 테이블 제거
    op.drop_table("messages")
    op.drop_table("conversations")

    # 비주얼 노벨 세이브 슬롯
    op.create_table(
        "save_slots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("episode", sa.String(8), nullable=False),
        sa.Column("scene_index", sa.Integer(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("recent_messages", sa.Text(), nullable=False),
        sa.Column(
            "timestamp",
            sa.DateTime(),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("save_slots")

    op.create_table(
        "conversations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_table(
        "messages",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "conversation_id",
            sa.Uuid(),
            sa.ForeignKey("conversations.id"),
            nullable=False,
        ),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
