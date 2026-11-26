DROP TABLE IF EXISTS sightings;
DROP TABLE IF EXISTS findings;
DROP TABLE IF EXISTS daily_severity_rollup;
DROP TABLE IF EXISTS processed_batches;

-- current state: one row per finding identity
CREATE TABLE findings (
    id            bigserial PRIMARY KEY,
    source        text NOT NULL,
    asset_key     text NOT NULL,
    rule_key      text NOT NULL,
    severity      text NOT NULL,
    cvss          numeric(3,1),
    first_seen_at timestamptz NOT NULL,
    last_seen_at  timestamptz NOT NULL,
    UNIQUE (source, asset_key, rule_key)
);

-- append-only detail: one row per record accepted from a batch
CREATE TABLE sightings (
    id          bigserial PRIMARY KEY,
    batch_id    text NOT NULL,
    source      text NOT NULL,
    asset_key   text NOT NULL,
    rule_key    text NOT NULL,
    severity    text NOT NULL,
    detected_at timestamptz NOT NULL,
    UNIQUE (batch_id, source, asset_key, rule_key)
);

-- serving cache: sightings per UTC calendar day per severity
CREATE TABLE daily_severity_rollup (
    day      date NOT NULL,
    severity text NOT NULL,
    n        integer NOT NULL,
    PRIMARY KEY (day, severity)
);

CREATE TABLE processed_batches (
    batch_id     text PRIMARY KEY,
    processed_at timestamptz NOT NULL DEFAULT now(),
    record_count integer NOT NULL
);

CREATE INDEX ON findings (source);
CREATE INDEX ON findings (last_seen_at);
CREATE INDEX ON sightings (source, asset_key, rule_key);
