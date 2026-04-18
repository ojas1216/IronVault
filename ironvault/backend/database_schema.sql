-- IronVault Database Schema
-- PostgreSQL 15+

CREATE TABLE IF NOT EXISTS devices (
    id                   VARCHAR(36) PRIMARY KEY,
    device_name          VARCHAR(200) NOT NULL,
    owner_name           VARCHAR(200),
    owner_email          VARCHAR(200),
    department           VARCHAR(100),

    -- Hardware Identity
    imei                 VARCHAR(20),
    imei2                VARCHAR(20),
    serial               VARCHAR(100),
    android_id           VARCHAR(64),
    hardware_fingerprint VARCHAR(64),
    manufacturer         VARCHAR(100),
    model                VARCHAR(100),
    os_version           VARCHAR(50),
    sdk_version          INTEGER,

    -- Push & Auth
    push_token           TEXT,
    device_secret        VARCHAR(128) NOT NULL,

    -- Status
    status               VARCHAR(30) DEFAULT 'active',
    is_online            BOOLEAN DEFAULT FALSE,
    is_rooted            BOOLEAN DEFAULT FALSE,
    battery_level        INTEGER,
    last_latitude        FLOAT,
    last_longitude       FLOAT,

    enrolled_at          TIMESTAMPTZ,
    last_seen            TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_devices_imei ON devices(imei);
CREATE INDEX IF NOT EXISTS idx_devices_fingerprint ON devices(hardware_fingerprint);
CREATE INDEX IF NOT EXISTS idx_devices_status ON devices(status);
CREATE INDEX IF NOT EXISTS idx_devices_last_seen ON devices(last_seen);


CREATE TABLE IF NOT EXISTS location_history (
    id          VARCHAR(36) PRIMARY KEY,
    device_id   VARCHAR(36) NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    latitude    FLOAT NOT NULL,
    longitude   FLOAT NOT NULL,
    accuracy    FLOAT,
    altitude    FLOAT,
    speed       FLOAT,
    provider    VARCHAR(30),
    recorded_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_location_device ON location_history(device_id);
CREATE INDEX IF NOT EXISTS idx_location_ts ON location_history(recorded_at DESC);

-- Partition by month for high-volume deployments
-- CREATE TABLE location_history_2025_01 PARTITION OF location_history
--     FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');


CREATE TABLE IF NOT EXISTS sim_events (
    id               VARCHAR(36) PRIMARY KEY,
    device_id        VARCHAR(36) NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    event_type       VARCHAR(30) NOT NULL,  -- swapped, removed, inserted
    payload          JSONB,
    photo_url        TEXT,
    is_resolved      BOOLEAN DEFAULT FALSE,
    resolved_by      VARCHAR(200),
    resolution_notes TEXT,
    created_at       TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sim_device ON sim_events(device_id);
CREATE INDEX IF NOT EXISTS idx_sim_ts ON sim_events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_sim_unresolved ON sim_events(is_resolved) WHERE is_resolved = FALSE;


CREATE TABLE IF NOT EXISTS tamper_logs (
    id         VARCHAR(36) PRIMARY KEY,
    device_id  VARCHAR(36) NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    event_type VARCHAR(100) NOT NULL,
    payload    JSONB,
    resolved   BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tamper_device ON tamper_logs(device_id);
CREATE INDEX IF NOT EXISTS idx_tamper_ts ON tamper_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_tamper_event ON tamper_logs(event_type);


CREATE TABLE IF NOT EXISTS commands (
    id           VARCHAR(36) PRIMARY KEY,
    device_id    VARCHAR(36) NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    command_type VARCHAR(50) NOT NULL,
    payload      JSONB,
    pre_verified BOOLEAN DEFAULT FALSE,
    status       VARCHAR(20) DEFAULT 'pending',
    result       JSONB,
    issued_at    TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_cmd_device ON commands(device_id);
CREATE INDEX IF NOT EXISTS idx_cmd_status ON commands(status) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_cmd_ts ON commands(issued_at DESC);


CREATE TABLE IF NOT EXISTS telemetry (
    id                   VARCHAR(36) PRIMARY KEY,
    device_id            VARCHAR(36) NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    hardware_fingerprint VARCHAR(64),
    imei                 VARCHAR(20),
    sim_count            INTEGER,
    location             JSONB,
    recorded_at          TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_telemetry_device ON telemetry(device_id);
CREATE INDEX IF NOT EXISTS idx_telemetry_ts ON telemetry(recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_telemetry_fingerprint ON telemetry(hardware_fingerprint);


-- Hardware Registry — tracks IMEI across all registrations for anti-resale detection
CREATE TABLE IF NOT EXISTS hardware_registry (
    id                   SERIAL PRIMARY KEY,
    imei                 VARCHAR(20) NOT NULL,
    hardware_fingerprint VARCHAR(64) NOT NULL,
    device_id            VARCHAR(36) NOT NULL,
    registered_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(imei, hardware_fingerprint)
);

CREATE INDEX IF NOT EXISTS idx_registry_imei ON hardware_registry(imei);
CREATE INDEX IF NOT EXISTS idx_registry_fingerprint ON hardware_registry(hardware_fingerprint);


-- Admin users
CREATE TABLE IF NOT EXISTS admin_users (
    id            SERIAL PRIMARY KEY,
    email         VARCHAR(200) UNIQUE NOT NULL,
    password_hash VARCHAR(200) NOT NULL,
    role          VARCHAR(30) DEFAULT 'admin',
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- Views
CREATE OR REPLACE VIEW active_devices AS
    SELECT * FROM devices WHERE status = 'active' AND last_seen > NOW() - INTERVAL '1 hour';

CREATE OR REPLACE VIEW stolen_devices AS
    SELECT * FROM devices WHERE status = 'stolen';

CREATE OR REPLACE VIEW recent_alerts AS
    SELECT t.*, d.device_name, d.owner_name
    FROM tamper_logs t
    JOIN devices d ON t.device_id = d.id
    WHERE t.resolved = FALSE
    ORDER BY t.created_at DESC;
