-- Raw prices ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS settlement_point_prices (
    ts                  TIMESTAMPTZ      NOT NULL,
    settlement_point    TEXT             NOT NULL,
    settlement_point_type TEXT,
    price               DOUBLE PRECISION,
    dst_flag            TEXT,
    loaded_at           TIMESTAMPTZ      NOT NULL DEFAULT now(),
    PRIMARY KEY (ts, settlement_point)
);
SELECT create_hypertable('settlement_point_prices', 'ts',
                         if_not_exists => TRUE,
                         chunk_time_interval => INTERVAL '7 days');

-- Generation resource data from the 60-day SCED disclosure -------------
CREATE TABLE IF NOT EXISTS sced_gen_resource (
    ts                  TIMESTAMPTZ      NOT NULL,
    resource_name       TEXT             NOT NULL,
    resource_type       TEXT,
    settlement_point    TEXT,
    hsl_mw              DOUBLE PRECISION,
    lsl_mw              DOUBLE PRECISION,
    base_point_mw       DOUBLE PRECISION,
    telem_net_mw        DOUBLE PRECISION,
    telem_status        TEXT,
    file_vintage        DATE,
    dq_flag             TEXT,
    loaded_at           TIMESTAMPTZ      NOT NULL DEFAULT now(),
    PRIMARY KEY (ts, resource_name)
);
SELECT create_hypertable('sced_gen_resource', 'ts',
                         if_not_exists => TRUE,
                         chunk_time_interval => INTERVAL '7 days');

-- Binding transmission constraints ------------------------------------
CREATE TABLE IF NOT EXISTS sced_shadow_prices (
    ts                  TIMESTAMPTZ      NOT NULL,
    constraint_name     TEXT             NOT NULL,
    contingency_name    TEXT,
    from_station        TEXT,
    to_station          TEXT,
    kv_level            DOUBLE PRECISION,
    shadow_price        DOUBLE PRECISION,
    max_shadow_price    DOUBLE PRECISION,
    constraint_limit    DOUBLE PRECISION,
    constraint_value    DOUBLE PRECISION,
    loaded_at           TIMESTAMPTZ      NOT NULL DEFAULT now()
);
SELECT create_hypertable('sced_shadow_prices', 'ts',
                         if_not_exists => TRUE,
                         chunk_time_interval => INTERVAL '7 days');

-- Node → physical asset → owner (loaded from your spreadsheet) --------
CREATE TABLE IF NOT EXISTS crosswalk (
    settlement_point    TEXT PRIMARY KEY,
    resource_name       TEXT,
    project_name        TEXT,
    county              TEXT,
    nameplate_mw        DOUBLE PRECISION,
    fuel_type           TEXT,
    owner               TEXT,
    cod                 DATE,
    notes               TEXT
);

-- Helpful indexes -----------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_spp_point      ON settlement_point_prices (settlement_point, ts DESC);
CREATE INDEX IF NOT EXISTS idx_sced_resource  ON sced_gen_resource (resource_name, ts DESC);
CREATE INDEX IF NOT EXISTS idx_sced_sp        ON sced_gen_resource (settlement_point, ts DESC);
CREATE INDEX IF NOT EXISTS idx_shadow_name    ON sced_shadow_prices (constraint_name, ts DESC);