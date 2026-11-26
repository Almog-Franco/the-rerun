# Ingestion Pipeline Contract

Version 1.4

Scanners deliver findings as hourly NDJSON batches. This pipeline normalises a
batch, appends it to the sighting history, updates current state per finding
identity, and refreshes the daily rollup that dashboards and exports read.

## Tables

| Table | Meaning |
| --- | --- |
| `sightings` | Append-only detail. One row per record accepted from a batch. |
| `findings` | Current state. One row per finding identity. |
| `daily_severity_rollup` | Serving cache. Sightings per UTC calendar day per severity. |
| `processed_batches` | Ledger of what has been ingested. |

A **finding identity** is the triple `(source, asset_key, rule_key)`.

## Guarantees

### G1 — Idempotent

Processing the same batch more than once leaves the database in exactly the
state it would be in had that batch been processed once. This applies to
`sightings`, `findings` and `daily_severity_rollup` alike.

### G2 — Order-independent

Final state is a function of the **set** of batches processed, not the order in
which they were processed. Any permutation of the same set converges to the
same database.

### G3 — Complete and single-instanced

Every record in every processed batch is represented in `sightings` exactly
once. Every finding identity is represented in `findings` exactly once. No
record is dropped and no identity appears twice.

Note that identity includes `source`. Two scanners reporting the same
underlying issue on the same host are two identities, and correlating them is
out of scope for this pipeline.

### G4 — Monotonic sighting history

A finding's `last_seen_at` never moves backwards and its `first_seen_at` never
moves forwards, whatever arrives later. Downstream auto-close retires a finding
that has not been seen for 48 hours, so it depends on this.

### G5 — Rollup agrees with detail

At rest, every row of `daily_severity_rollup` equals the live aggregate over
`sightings` for that UTC calendar day and severity. The rollup is a cache,
never a second opinion.

The day bucket is the **UTC** calendar day. Sources deliver timestamps with
mixed offsets and the local timezone of a database session is not UTC.

### G6 — Late arrival tolerated

A batch whose window is older than batches already processed may be submitted
at any time and is absorbed correctly, without a rebuild.

## Sources

Three scanners, three payload shapes, one normalised record.

```
scanner_a   {"source","host","check_id","sev","ts","cvss"}
scanner_b   {"source","asset":{"hostname","ip"},"vuln":{"id","severity"},"observed_at","score"}
scanner_c   {"source","target","finding":{"key","title","cvss":{"base_score","vector"}},"level","first_observed"}
```

`scanner_b` reports timestamps at `+02:00`. The other two report UTC.
