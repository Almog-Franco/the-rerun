# Agent notes: contract-verifier

**Why this agent.** "Does it keep its contract?" is the one question that holds for every version of this pipeline, including the ones I haven't seen.
It is also what this team lacks: AI-written code checked against the spec, not against itself.
A fixed test suite would cover only this schema and these scenarios. The agent also sets up its own environment, adapts to renamed tables, separates a breach from an ambiguity, and returns a report a person can audit.
I chose it over the two agents at the end because both depend on it: an auditor needs a contract check to point to, and triage needs a proven way to reproduce a failure.

**How I checked it is right.**
1. **Expected answers first.** I ran the agent's SQL and steps as a plain script, so I knew each correct verdict before any AI run.
2. **Four repos.** I ran the agent through the Claude Code CLI on this bundle and on three seeded copies outside the repo, made only to test the agent. The pipeline in this repo is untouched. The copies:
   - one where all guarantees hold, with no `.venv`: CONTRACT HOLDS
   - one with only the `last_seen_at` bug: G2, G4 and G6 fail
   - one with a bug this bundle lacks, local-day rollup buckets: only G5 fails, though the totals match
3. **11 runs, every G line correct.** One run miscounted the headline: `CONTRACT BROKEN (0 of 6)` above six FAILs. The format `<k> of 6` did not say what `k` counts. I changed it to `<k> of 6 FAIL` and re-ran. The repo checksum was unchanged after every run.
4. **The agent's first dry run caught its own bug.** A schema named `qa` captured the pipeline's tables, because `search_path` starts with `$user`, and the user is `qa`.

**One complete reply** (this repo, final version):
```
VERDICT: CONTRACT BROKEN (6 of 6 FAIL)
G1 idempotent         FAIL  B07 replayed; rollup 4/4
G2 order-independent  FAIL  findings 3142/3142
G3 complete           FAIL  951 sightings missing, 120 findings missing; missing_by scanner_c CIS 951
G4 monotonic          FAIL  B01 late; 1970 last_seen_at moved back / 0 forward / 0 vanished; worst 2 days 18:44:29
G5 rollup = detail    FAIL  4 rows differing 29446/27113, worst in replay step
G6 late arrival       FAIL  findings 1970/1970 against in-order load
RAW -> ROLLUP         MISMATCH  9 rows differing, 27113/28064 in clean load
NOTES: 951 scanner_c CIS records dropped; 58 case-variant identities; replay corrupted rollup
CODE UNCHANGED: yes  fcd9a1a8d647b69093c62c9a847e97235a41f123 = fcd9a1a8d647b69093c62c9a847e97235a41f123
COMMANDS:
./bin/pipeline status
cat pipeline/*.py pipeline/*.sql | shasum
ls raw/batch_*.ndjson | sort
docker exec -i rerun-db psql -X -q -v ON_ERROR_STOP=1 -U qa -d ingest <<'SQL'
.venv/bin/python - <<'PY' | docker exec -i rerun-db psql -X -q -v ON_ERROR_STOP=1 -U qa -d ingest -c "COPY verifier.raw FROM STDIN (FORMAT csv)"
./bin/pipeline reset && ./bin/pipeline run --all && ./bin/pipeline status | tail -4
docker exec -i rerun-db psql -X -q -t -A -F'|' -v ON_ERROR_STOP=1 -U qa -d ingest <<'SQL'
./bin/pipeline run --batch B07
docker exec -i rerun-db psql -X -q -t -A -F'|' -v ON_ERROR_STOP=1 -U qa -d ingest <<'SQL'
./bin/pipeline reset && ./bin/pipeline run --batch B12 --batch B11 --batch B10 --batch B09 --batch B08 --batch B07 --batch B06 --batch B05 --batch B04 --batch B03 --batch B02 --batch B01
docker exec -i rerun-db psql -X -q -t -A -F'|' -v ON_ERROR_STOP=1 -U qa -d ingest <<'SQL'
./bin/pipeline reset && ./bin/pipeline run --batch B02 --batch B03 --batch B04 --batch B05 --batch B06 --batch B07 --batch B08 --batch B09 --batch B10 --batch B11 --batch B12
docker exec -i rerun-db psql -X -q -v ON_ERROR_STOP=1 -U qa -d ingest -c "CREATE TABLE verifier.before AS SELECT source, asset_key, rule_key, first_seen_at, last_seen_at FROM findings;"
./bin/pipeline run --batch B01
docker exec -i rerun-db psql -X -q -t -A -F'|' -v ON_ERROR_STOP=1 -U qa -d ingest <<'SQL'
./bin/pipeline reset && ./bin/pipeline run --all
docker exec -i rerun-db psql -X -q -U qa -d ingest -c "DROP SCHEMA verifier CASCADE"
cat pipeline/*.py pipeline/*.sql | shasum
```

**What I would not trust it with.**
- **Settling ambiguity.** It reports the 58 case-only identity pairs without judging them.
- **Its cause guesses.** Once it named a cause without citing a line.
- **Large schema changes.** It rewrites its own SQL, so read NOTES before believing a FAIL.
- **Concurrency, crashes mid-batch and production volume.** None of these was exercised.
- **A shared database.** It resets whatever it connects to.

**Two more agents I would build.**
1. **Test-oracle auditor, on every PR.** It flags tests whose expected value comes from the code under test. That is how a pipeline that only agrees with itself looks healthy.
2. **Production alert triage.** When a monitor fires, it names the cause (drop, replay, backfill or new payload shape), gives the query that proves it, and drafts the ticket.
