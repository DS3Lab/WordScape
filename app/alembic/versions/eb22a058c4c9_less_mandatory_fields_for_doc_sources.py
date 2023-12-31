"""Less mandatory fields for doc_sources

Revision ID: eb22a058c4c9
Revises: 2de829bd1ca3
Create Date: 2023-05-29 21:25:05.888669

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'eb22a058c4c9'
down_revision = '2de829bd1ca3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('sources_record', 'filename',
               existing_type=sa.VARCHAR(length=10000),
               nullable=True)
    op.alter_column('sources_record', 'bytehash',
               existing_type=sa.VARCHAR(length=10000),
               nullable=True)
    op.alter_column('sources_record', 'status_code',
               existing_type=sa.VARCHAR(length=200),
               nullable=True)
    op.alter_column('sources_record', 'content_encoding',
               existing_type=sa.VARCHAR(length=1000),
               nullable=True)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('sources_record', 'content_encoding',
               existing_type=sa.VARCHAR(length=1000),
               nullable=False)
    op.alter_column('sources_record', 'status_code',
               existing_type=sa.VARCHAR(length=200),
               nullable=False)
    op.alter_column('sources_record', 'bytehash',
               existing_type=sa.VARCHAR(length=10000),
               nullable=False)
    op.alter_column('sources_record', 'filename',
               existing_type=sa.VARCHAR(length=10000),
               nullable=False)
    # ### end Alembic commands ###
