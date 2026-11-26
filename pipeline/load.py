"""Batch load: stage -> sightings -> findings -> rollup -> ledger."""

STAGE = """
CREATE TEMP TABLE stg (
    source      text,
    asset_key   text,
    rule_key    text,
    severity    text,
    cvss        numeric(3,1),
    detected_at timestamptz
) ON COMMIT DROP
"""

# Records already held for this batch are skipped, so replaying a batch does
# not re-append. Whatever actually landed is captured for the findings step.
APPEND_SIGHTINGS = """
CREATE TEMP TABLE new_sightings ON COMMIT DROP AS
WITH ins AS (
    INSERT INTO sightings (batch_id, source, asset_key, rule_key, severity, detected_at)
    SELECT %s, source, asset_key, rule_key, severity, detected_at FROM stg
    ON CONFLICT (batch_id, source, asset_key, rule_key) DO NOTHING
    RETURNING source, asset_key, rule_key
)
SELECT stg.* FROM stg JOIN ins USING (source, asset_key, rule_key)
"""

UPSERT_FINDINGS = """
INSERT INTO findings (source, asset_key, rule_key, severity, cvss, first_seen_at, last_seen_at)
SELECT source, asset_key, rule_key,
       (array_agg(severity ORDER BY detected_at DESC))[1],
       max(cvss),
       min(detected_at),
       max(detected_at)
  FROM new_sightings
 GROUP BY source, asset_key, rule_key
ON CONFLICT (source, asset_key, rule_key) DO UPDATE SET
    severity      = EXCLUDED.severity,
    cvss          = EXCLUDED.cvss,
    first_seen_at = LEAST(findings.first_seen_at, EXCLUDED.first_seen_at),
    last_seen_at  = EXCLUDED.last_seen_at
"""

REFRESH_ROLLUP = """
INSERT INTO daily_severity_rollup (day, severity, n)
SELECT (detected_at AT TIME ZONE 'UTC')::date, severity, count(*)
  FROM stg
 GROUP BY 1, 2
ON CONFLICT (day, severity) DO UPDATE SET
    n = daily_severity_rollup.n + EXCLUDED.n
"""

RECORD_BATCH = """
INSERT INTO processed_batches (batch_id, record_count)
VALUES (%s, %s)
ON CONFLICT (batch_id) DO UPDATE SET
    processed_at = now(),
    record_count = EXCLUDED.record_count
"""


def load_batch(conn, batch_id: str, records: list) -> None:
    with conn.cursor() as cur:
        cur.execute(STAGE)
        with cur.copy(
            "COPY stg (source, asset_key, rule_key, severity, cvss, detected_at) FROM STDIN"
        ) as copy:
            for r in records:
                copy.write_row(
                    (r["source"], r["asset_key"], r["rule_key"],
                     r["severity"], r["cvss"], r["detected_at"])
                )
        cur.execute(APPEND_SIGHTINGS, (batch_id,))
        cur.execute(UPSERT_FINDINGS)
        cur.execute(REFRESH_ROLLUP)
        cur.execute(RECORD_BATCH, (batch_id, len(records)))
    conn.commit()
