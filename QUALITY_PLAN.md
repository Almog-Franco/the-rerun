# Quality plan: ingestion pipeline

**Goal:** the rollup the customer reports from equals what the scanners sent, after every run, retry and backfill.
Today five of six guarantees break ([EVIDENCE.md](EVIDENCE.md)), while every count the pipeline reports about itself agrees.
So every check below compares against raw input or an invariant, never against the pipeline's own numbers.

## Checks, by risk

| # | Check | Guards | Where / when | Who or what |
|---|---|---|---|---|
| 1 | **Reconcile raw → sightings** per batch and source. Bad records go to quarantine with a reason; they are never skipped. | G3 | Prod, every run. Alert if `landed + rejected ≠ raw` | The pipeline emits the counts, a monitor alerts, on-call triages |
| 2 | **Rollup = live aggregate**, by UTC day × severity ([EVIDENCE §2](EVIDENCE.md) query) | G5, G1 | Prod, every run, and a gate before each compliance export | A scheduled SQL monitor. A failure blocks the export |
| 3 | **Contract tests**: replay, reverse order, late batch, raw completeness, as pytest on the existing `tests/conftest.py` fixtures | G1–G6 | Every PR touching `pipeline/`. Merge-blocking once green | CI. The reviewer checks no test was weakened |
| 4 | **`findings` agrees with its own sightings**: `last_seen_at = max(detected_at)` | G4, G6 | Prod, every run. Auto-close pauses while this is non-zero | A SQL monitor, owned by whoever owns auto-close |
| 5 | **Normaliser fixtures**: one golden record per payload shape, including optional fields (CIS has no CVSS), case and timezone variants | G3 | PR, unit level, under a second | The developer who changes a normaliser |
| 6 | **[contract-verifier](.claude/agents/contract-verifier.md) agent**: all six guarantees, end to end | all | Nightly, and before a release | The agent. The QA lead reads any FAIL before it becomes a ticket |

**Order.** Checks 1 and 2 first, this week: the customer is about to read the rollup, and both look at production data.
Then a one-off reconciliation of the production rollup, which past retries may already have inflated. Then checks 3–6.

**Rule for AI-written tests:** the expected value comes from raw input or from the contract, never from calling the code under test.
That rule is how the agent catches the 951 dropped records.

## Deliberately not tested
- **All 12! batch orders.** Reverse order plus one late batch cover both code paths. A nightly random order adds breadth cheaply.
- **Dashboard rendering and API performance.** A wrong number in a fast page is worse than a right number in a slow one.
- **Severity against NVD, and cross-scanner correlation.** The contract takes severity at face value and puts correlation out of scope.

## Questions for the team
1. **Is `asset_key` case-insensitive?** `APP-DEV-32` and `app-dev-32` are two findings today: 58 pairs, all from scanner_b. The contract is silent, so I report it but do not call it a failure.
2. How often do retries and backfills happen in production? That decides how inflated today's rollup already is.
3. Who reads `processed_batches.record_count`? It stores the count after drops, which hides check 1's gap.
4. What do the existing AI-written tests assert against: raw files, mocks, or the pipeline's own output?

## How we'd know in three months
- Monitors 1, 2 and 4 show zero violations for 90 days, and no customer found a data error before a check did.
- 6/6 guarantees have a merge-blocking test, and none was disabled to get a merge through.
- A quarterly seeded-bug drill (break one guarantee on a branch) is caught by both CI and the agent.
