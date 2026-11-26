# Evidence: top three risks for the customer

All commands are run from the repo root after `export PATH="$PWD/bin:$PATH"`.
`psql` below is shorthand for `docker exec rerun-db psql -U qa -d ingest -c "<query>"`.
The data is deterministic, so the same commands give the same numbers.

Ranking: what the customer's compliance report gets wrong, how much, and how often it happens.
Risk 1 is wrong on every run today. Risk 2 needs a retried job. Risk 3 needs a backfill.

---

## 1. G3: every CIS hardening finding is silently dropped

```bash
pipeline reset && pipeline run --all                                        # run B01: 2024 records loaded, ...
wc -l raw/*.ndjson                                                          # B01: 2092 ... total: 28064
cat raw/*.ndjson | grep -c '"source":"scanner_c"'                           # 6686
cat raw/*.ndjson | grep '"source":"scanner_c"' | grep -c '"key":"CIS-'      # 951
cat raw/*.ndjson | grep '"source":"scanner_c"' | grep '"key":"CIS-' | grep -c '"cvss"'   # 0
cat raw/*.ndjson | grep '"source":"scanner_c"' | grep -v '"cvss"' | grep -o '"level":"[a-z]*"' | sort | uniq -c   # 130 high, 230 low, 591 medium
cat raw/*.ndjson | grep '"source":"scanner_c"' | grep -v '"cvss"' | python3 -c "import sys, json; print(len({(r['target'], r['finding']['key']) for r in map(json.loads, sys.stdin)}))"   # 120
```
```sql
SELECT source, count(*) FROM sightings GROUP BY 1 ORDER BY 1;
SELECT count(*) FROM findings WHERE rule_key LIKE 'CIS-%';
```

| | raw | sightings |
|---|---|---|
| all sources | 28,064 | **27,113** (951 missing, 3.4%) |
| scanner_c | 6,686 | **5,735** (exactly the 951 CIS records) |
| CIS findings | 120 distinct | **0** |

**Cause.** A CIS check has no CVSS, so scanner_c sends no `finding.cvss` object. [normalize.py:41](pipeline/normalize.py#L41) raises `KeyError`, and [normalize.py:64](pipeline/normalize.py#L64) swallows it.
The run still reports success (`run B01: 2024 records loaded` for a 2,092-line file). The ledger stores the count after the drop, and `pipeline status` shows sightings = rollup = 27,113.
Every internal number agrees, which is why nobody has reported it.

**Customer.** The compliance report shows zero hardening-benchmark failures. 120 real ones exist, behind 951 sightings (130 high, 591 medium, 230 low).
The report under-reports risk, and no alert fires.

---

## 2. G1 + G5: a replayed batch inflates the rollup, permanently

```bash
pipeline reset && pipeline run --all && pipeline status | tail -3   # sightings 27113, rollup sum 27113
pipeline run --batch B03 && pipeline status | tail -3               # sightings 27113, rollup sum 29269
pipeline run --batch B03 && pipeline status | tail -1               # rollup sum 31425
```
```sql
SELECT day, severity, coalesce(r.n,0) AS rollup, coalesce(s.n,0) AS live
FROM daily_severity_rollup r
FULL JOIN (SELECT (detected_at AT TIME ZONE 'UTC')::date AS day, severity, count(*) AS n
           FROM sightings GROUP BY 1, 2) s USING (day, severity)
WHERE r.n IS DISTINCT FROM s.n ORDER BY 1, 2;
```

After one replay of B03, the clean load's 0 mismatched rows become 4, all on 2026-03-07:

| severity | rollup | live | over-count |
|---|---|---|---|
| critical | 769 | 616 | +153 (+25%) |
| high | 2,289 | 1,825 | +464 |
| medium | 4,829 | 3,848 | +981 |
| low | 2,730 | 2,172 | +558 |

Each replay adds the batch size again (+2,156), so the error grows with every retry.

**Cause.** Sightings are protected by `ON CONFLICT DO NOTHING`. The rollup instead adds `count(*) FROM stg`, which counts every staged row, not the rows that were actually inserted ([load.py:44-49](pipeline/load.py#L44-L49)).

**Customer.** Any retried job inflates that day's compliance numbers, and only a full reset brings them back. The dashboard and `/api/summary` read this table.
The detail tables still look healthy, so a spot check of `findings` will not catch it.

---

## 3. G4 (and G2, G6): a late batch drags `last_seen_at` backwards, so auto-close retires live findings

```bash
pipeline reset
pipeline run --batch B02 --batch B03 --batch B04 --batch B05 --batch B06 --batch B07 \
             --batch B08 --batch B09 --batch B10 --batch B11 --batch B12   # collector outage: B01 missing
pipeline run --batch B01                                                  # backfill arrives last
```
```sql
WITH s AS (SELECT source, asset_key, rule_key, max(detected_at) AS true_last
           FROM sightings GROUP BY 1, 2, 3),
     clock AS (SELECT max(detected_at) AS now FROM sightings)
SELECT count(*) FILTER (WHERE f.last_seen_at < s.true_last)               AS moved_back,
       max(s.true_last - f.last_seen_at)                                  AS worst,
       count(*) FILTER (WHERE f.last_seen_at <  clock.now - interval '48 hours'
                          AND s.true_last    >= clock.now - interval '48 hours') AS falsely_stale
FROM findings f JOIN s USING (source, asset_key, rule_key), clock;
```

| scenario | moved_back | worst | falsely_stale (of 3,414) |
|---|---|---|---|
| in order, B01..B12 | 0 | 00:00:00 | 0 |
| **B01 delivered last** | **1,970** | **2 days 18:44** | **1,785 (52%)** |
| B05 delivered last | 2,171 | 1 day 18:44 | 0 |

The in-order row comes from `pipeline reset && pipeline run --all`, then the query.
The B05 row comes from `pipeline reset && pipeline run --batch B01 --batch B02 --batch B03 --batch B04 --batch B06 --batch B07 --batch B08 --batch B09 --batch B10 --batch B11 --batch B12 --batch B05`, then the query.
`falsely_stale` measures against the data's own clock, the newest sighting in the database, standing in for "now" in an hourly pipeline.
Order alone also breaks the state (G2). Compare a reverse-order load with the in-order load:

```bash
F="SELECT source, asset_key, rule_key, severity, cvss, first_seen_at, last_seen_at FROM findings"
R="SELECT day, severity, n FROM daily_severity_rollup"
pipeline reset && pipeline run --all
docker exec rerun-db psql -U qa -d ingest -At -c "$F" > /tmp/fwd.txt
docker exec rerun-db psql -U qa -d ingest -At -c "$R" > /tmp/fwd_rollup.txt
pipeline reset && pipeline run $(printf -- '--batch B%02d ' $(seq 12 -1 1))
docker exec rerun-db psql -U qa -d ingest -At -c "$F" > /tmp/rev.txt
docker exec rerun-db psql -U qa -d ingest -At -c "$R" > /tmp/rev_rollup.txt
comm -13 <(sort /tmp/fwd.txt) <(sort /tmp/rev.txt) | wc -l                                  # 3142
comm -13 <(cut -d'|' -f1-6 /tmp/fwd.txt | sort) <(cut -d'|' -f1-6 /tmp/rev.txt | sort) | wc -l  # 0
comm -3 <(sort /tmp/fwd_rollup.txt) <(sort /tmp/rev_rollup.txt) | wc -l                    # 0
```

3,142 findings differ, and only in `last_seen_at`: every column up to `first_seen_at` matches.
The rollup is identical either way (the last `comm` returns 0), so order changes what auto-close sees, not what the compliance report counts.
**Cause.** `last_seen_at = EXCLUDED.last_seen_at`, with no `GREATEST`. `first_seen_at` does get `LEAST` ([load.py:39-40](pipeline/load.py#L39-L40)).

**Customer.** A single routine backfill makes about half of the open exposures look unseen for over 48 hours. Auto-close retires them while they are still present, so they disappear from the open-findings view the customer audits.
The rollup does not change in the same way, so the two views contradict each other.

---

Checked and holding, so not claimed as risks:
- **Replay does not duplicate sightings or findings.** After risk 2's replays, `pipeline status` still shows `findings 3414` and `sightings 27113`.
- **Rollup day buckets are UTC-correct**, although the session runs in `Asia/Jerusalem`. Risk 2's query returns 0 rows on a clean load.
  This matters for whoever checks it: `SELECT count(*) FROM sightings WHERE detected_at::date <> (detected_at AT TIME ZONE 'UTC')::date` returns 6,856. A check that buckets by local day reports a G5 failure that is not there.
- **`severity` and `cvss` do not depend on order.** The second `comm` above returns 0.
- **The ledger's `processed_at` changes on replay.** `SELECT processed_at FROM processed_batches WHERE batch_id = 'B03'` returns a different time before and after `pipeline run --batch B03`. It is a wall-clock field, and G1 covers only the three data tables.

Open question, not a risk: 58 identities differ only by hostname case.
`SELECT count(*) FROM (SELECT source, lower(asset_key), rule_key FROM findings GROUP BY 1, 2, 3 HAVING count(*) > 1) x` returns 58. See [QUALITY_PLAN.md](QUALITY_PLAN.md), question 1.
