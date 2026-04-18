"""Initial schema — all tables

Revision ID: 001
Revises:
Create Date: 2026-04-18
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ─── users ────────────────────────────────────────────────────────────────
    op.create_table(
        'users',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('hashed_password', sa.Text, nullable=False),
        sa.Column('full_name', sa.String(200)),
        sa.Column('role', sa.String(30), nullable=False, server_default='viewer'),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('last_login', sa.DateTime(timezone=True)),
    )
    op.create_index('ix_users_email', 'users', ['email'])

    # ─── devices ──────────────────────────────────────────────────────────────
    op.create_table(
        'devices',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('device_name', sa.String(200), nullable=False),
        sa.Column('employee_name', sa.String(200)),
        sa.Column('employee_email', sa.String(255)),
        sa.Column('department', sa.String(100)),
        sa.Column('platform', sa.String(20), nullable=False),
        sa.Column('os_version', sa.String(50)),
        sa.Column('agent_version', sa.String(20)),
        sa.Column('manufacturer', sa.String(100)),
        sa.Column('model', sa.String(100)),
        sa.Column('imei', sa.String(20)),
        sa.Column('serial_number', sa.String(100)),
        sa.Column('android_id', sa.String(64)),
        sa.Column('hardware_fingerprint', sa.String(64)),
        sa.Column('push_token', sa.Text),
        sa.Column('enrollment_token', sa.String(64)),
        sa.Column('status', sa.String(30), nullable=False, server_default='active'),
        sa.Column('is_online', sa.Boolean, server_default='false'),
        sa.Column('is_rooted', sa.Boolean, server_default='false'),
        sa.Column('is_uninstall_blocked', sa.Boolean, server_default='true'),
        sa.Column('battery_level', sa.Integer),
        sa.Column('last_latitude', sa.Float),
        sa.Column('last_longitude', sa.Float),
        sa.Column('last_seen', sa.DateTime(timezone=True)),
        sa.Column('enrolled_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_devices_status', 'devices', ['status'])
    op.create_index('ix_devices_platform', 'devices', ['platform'])
    op.create_index('ix_devices_last_seen', 'devices', ['last_seen'])
    op.create_index('ix_devices_imei', 'devices', ['imei'])

    # ─── location_history ─────────────────────────────────────────────────────
    op.create_table(
        'location_history',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('device_id', sa.String(36), sa.ForeignKey('devices.id', ondelete='CASCADE'), nullable=False),
        sa.Column('latitude', sa.Float, nullable=False),
        sa.Column('longitude', sa.Float, nullable=False),
        sa.Column('accuracy', sa.Float),
        sa.Column('altitude', sa.Float),
        sa.Column('speed', sa.Float),
        sa.Column('provider', sa.String(30)),
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_location_device_id', 'location_history', ['device_id'])
    op.create_index('ix_location_recorded_at', 'location_history', ['recorded_at'])

    # ─── app_usage ────────────────────────────────────────────────────────────
    op.create_table(
        'app_usage',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('device_id', sa.String(36), sa.ForeignKey('devices.id', ondelete='CASCADE'), nullable=False),
        sa.Column('app_name', sa.String(200), nullable=False),
        sa.Column('package_name', sa.String(200)),
        sa.Column('duration_seconds', sa.Integer, nullable=False),
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_app_usage_device_id', 'app_usage', ['device_id'])
    op.create_index('ix_app_usage_recorded_at', 'app_usage', ['recorded_at'])

    # ─── commands ─────────────────────────────────────────────────────────────
    op.create_table(
        'commands',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('device_id', sa.String(36), sa.ForeignKey('devices.id', ondelete='CASCADE'), nullable=False),
        sa.Column('issued_by', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL')),
        sa.Column('command_type', sa.String(50), nullable=False),
        sa.Column('payload', postgresql.JSONB),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('otp_id', sa.String(36)),
        sa.Column('result', postgresql.JSONB),
        sa.Column('issued_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(timezone=True)),
    )
    op.create_index('ix_commands_device_id', 'commands', ['device_id'])
    op.create_index('ix_commands_status', 'commands', ['status'])
    op.create_index('ix_commands_issued_at', 'commands', ['issued_at'])

    # ─── otp_codes ────────────────────────────────────────────────────────────
    op.create_table(
        'otp_codes',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('device_id', sa.String(36), sa.ForeignKey('devices.id', ondelete='CASCADE'), nullable=False),
        sa.Column('command_type', sa.String(50), nullable=False),
        sa.Column('otp_hash', sa.Text, nullable=False),
        sa.Column('attempts', sa.Integer, nullable=False, server_default='0'),
        sa.Column('is_used', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('locked_until', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_otp_device_id', 'otp_codes', ['device_id'])
    op.create_index('ix_otp_expires_at', 'otp_codes', ['expires_at'])

    # ─── audit_logs ───────────────────────────────────────────────────────────
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('admin_id', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL')),
        sa.Column('admin_email', sa.String(255)),
        sa.Column('device_id', sa.String(36)),
        sa.Column('device_name', sa.String(200)),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('details', postgresql.JSONB),
        sa.Column('ip_address', sa.String(45)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_audit_admin_id', 'audit_logs', ['admin_id'])
    op.create_index('ix_audit_device_id', 'audit_logs', ['device_id'])
    op.create_index('ix_audit_action', 'audit_logs', ['action'])
    op.create_index('ix_audit_created_at', 'audit_logs', ['created_at'])

    # ─── sim_events ───────────────────────────────────────────────────────────
    op.create_table(
        'sim_events',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('device_id', sa.String(36), sa.ForeignKey('devices.id', ondelete='CASCADE'), nullable=False),
        sa.Column('event_type', sa.String(30), nullable=False),
        sa.Column('slot_index', sa.Integer),
        sa.Column('iccid', sa.String(30)),
        sa.Column('imsi', sa.String(20)),
        sa.Column('carrier_name', sa.String(100)),
        sa.Column('mcc', sa.String(10)),
        sa.Column('mnc', sa.String(10)),
        sa.Column('country_iso', sa.String(5)),
        sa.Column('is_roaming', sa.Boolean),
        sa.Column('security_photo_url', sa.Text),
        sa.Column('location_lat', sa.Float),
        sa.Column('location_lng', sa.Float),
        sa.Column('is_resolved', sa.Boolean, server_default='false'),
        sa.Column('resolved_by', sa.String(255)),
        sa.Column('resolution_notes', sa.Text),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_sim_device_id', 'sim_events', ['device_id'])
    op.create_index('ix_sim_created_at', 'sim_events', ['created_at'])
    op.create_index('ix_sim_unresolved', 'sim_events', ['is_resolved'],
                    postgresql_where=sa.text("is_resolved = false"))

    # ─── device_identity ──────────────────────────────────────────────────────
    op.create_table(
        'device_identity',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('device_id', sa.String(36), sa.ForeignKey('devices.id', ondelete='CASCADE'),
                  nullable=False, unique=True),
        sa.Column('imei_slot1', sa.String(20)),
        sa.Column('imei_slot2', sa.String(20)),
        sa.Column('serial_number', sa.String(100)),
        sa.Column('android_id', sa.String(64)),
        sa.Column('hardware_fingerprint', sa.String(64)),
        sa.Column('soc_manufacturer', sa.String(100)),
        sa.Column('soc_model', sa.String(100)),
        sa.Column('manufacturer', sa.String(100)),
        sa.Column('model', sa.String(100)),
        sa.Column('sdk_version', sa.Integer),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ─── uwb_ranging ──────────────────────────────────────────────────────────
    op.create_table(
        'uwb_ranging',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('device_id', sa.String(36), sa.ForeignKey('devices.id', ondelete='CASCADE'), nullable=False),
        sa.Column('distance_meters', sa.Float),
        sa.Column('azimuth_degrees', sa.Float),
        sa.Column('elevation_degrees', sa.Float),
        sa.Column('rssi', sa.Integer),
        sa.Column('mode', sa.String(20)),
        sa.Column('recorded_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_uwb_device_id', 'uwb_ranging', ['device_id'])
    op.create_index('ix_uwb_recorded_at', 'uwb_ranging', ['recorded_at'])


def downgrade() -> None:
    op.drop_table('uwb_ranging')
    op.drop_table('device_identity')
    op.drop_table('sim_events')
    op.drop_table('audit_logs')
    op.drop_table('otp_codes')
    op.drop_table('commands')
    op.drop_table('app_usage')
    op.drop_table('location_history')
    op.drop_table('devices')
    op.drop_table('users')
