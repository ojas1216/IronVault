"""Add hardware anti-resale tracking columns to devices and hardware_registry table

Revision ID: 002
Revises: 001
Create Date: 2026-04-18
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add hardware tracking columns to devices table
    op.add_column("devices", sa.Column("hardware_fingerprint", sa.String(64), nullable=True))
    op.add_column("devices", sa.Column("baseboard_serial", sa.String(255), nullable=True))
    op.add_column("devices", sa.Column("bios_uuid", sa.String(64), nullable=True))
    op.add_column("devices", sa.Column("is_enrolled", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("devices", sa.Column("last_hardware_check", sa.DateTime(timezone=True), nullable=True))
    op.add_column("devices", sa.Column("last_tpm_chip_id", sa.String(64), nullable=True))
    op.add_column("devices", sa.Column("last_secure_boot_status", sa.Boolean(), nullable=True))
    op.add_column("devices", sa.Column("last_firmware_fingerprint", sa.String(64), nullable=True))
    op.add_column("devices", sa.Column("is_flagged", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("devices", sa.Column("flag_reason", sa.String(255), nullable=True))
    op.add_column("devices", sa.Column("flagged_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("devices", sa.Column("security_flags", sa.Text(), nullable=True))

    op.create_index("ix_devices_hardware_fingerprint", "devices", ["hardware_fingerprint"])
    op.create_index("ix_devices_is_flagged", "devices", ["is_flagged"])

    # Create hardware_registry table for cross-device stolen/resold tracking
    op.create_table(
        "hardware_registry",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("hardware_fingerprint", sa.String(64), nullable=False, unique=True),
        sa.Column("baseboard_serial_hash", sa.String(64), nullable=True),
        sa.Column("bios_uuid_hash", sa.String(64), nullable=True),
        sa.Column("tpm_chip_id_hash", sa.String(64), nullable=True),
        sa.Column("original_device_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("original_company_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("enrolled_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("is_stolen", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_resold", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("flagged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("flag_reason", sa.String(255), nullable=True),
        sa.Column("flag_notes", sa.Text(), nullable=True),
        sa.Column("last_seen_device_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_hw_registry_fingerprint", "hardware_registry", ["hardware_fingerprint"])
    op.create_index("ix_hw_registry_board_hash", "hardware_registry", ["baseboard_serial_hash"])


def downgrade() -> None:
    op.drop_table("hardware_registry")

    for col in [
        "hardware_fingerprint", "baseboard_serial", "bios_uuid", "is_enrolled",
        "last_hardware_check", "last_tpm_chip_id", "last_secure_boot_status",
        "last_firmware_fingerprint", "is_flagged", "flag_reason", "flagged_at",
        "security_flags",
    ]:
        op.drop_column("devices", col)
