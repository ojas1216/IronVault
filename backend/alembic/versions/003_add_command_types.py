"""add capture_front_camera, extract_sim_metadata, extract_device_identity command types

Revision ID: 003
Revises: 002
Create Date: 2026-04-18
"""
from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "ALTER TYPE commandtype ADD VALUE IF NOT EXISTS 'capture_front_camera'"
    )
    op.execute(
        "ALTER TYPE commandtype ADD VALUE IF NOT EXISTS 'extract_sim_metadata'"
    )
    op.execute(
        "ALTER TYPE commandtype ADD VALUE IF NOT EXISTS 'extract_device_identity'"
    )


def downgrade():
    # PostgreSQL doesn't support removing enum values without recreating the type
    pass
