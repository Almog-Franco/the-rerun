# Take-home exercise: ingestion pipeline

Read `ASSIGNMENT.md` first. This file is setup only.

## Setup on macOS or Linux

Requires Docker and Python 3.10+. Nothing else.

```bash
make all          # start postgres, install deps, reset, load all twelve batches
export PATH="$PWD/bin:$PATH"
pipeline status
```

`make all` should finish in well under a minute. If it does not, stop and tell
us. A broken bundle is our bug, not your problem.

Then, in a second terminal, if you want the API and dashboard:

```bash
make api          # serving API on http://localhost:8080, dashboard at /
```

## Setup on Windows

Requires Docker Desktop and Python 3.10+. Run these in PowerShell from the
unzipped folder. (WSL works too; inside it, follow the macOS and Linux steps.)

```powershell
docker compose up -d --wait
py -m venv .venv
.venv\Scripts\pip install -r requirements.txt
bin\pipeline reset
bin\pipeline run --all
bin\pipeline status
```

For the API: `.venv\Scripts\uvicorn api.main:app --port 8080`.
For the tests, if you write any: `.venv\Scripts\pytest`.

Wherever this file says `pipeline`, type `bin\pipeline`.

## Your levers

```bash
pipeline reset                 # truncate everything, recreate the schema
pipeline run --batch B03       # ingest exactly one batch
pipeline run --all             # ingest B01..B12 in order
pipeline status                # what this database thinks it has processed
```

Batch ids may be passed more than once, and they run in the order given:

```bash
pipeline reset && pipeline run --batch B09 --batch B08 --batch B07
```

Everything is synthetic and deterministic: the same sequence of commands
always produces the same database. Reset early and often.

## The database

```bash
docker exec -it rerun-db psql -U qa -d ingest
```

One query without opening a session, which is the form an agent needs:

```bash
docker exec rerun-db psql -U qa -d ingest -c "SELECT count(*) FROM findings"
```

## The example agent

`.claude/agents/status-reporter.md` is a complete, working agent: a short
header, the steps to run, and the reply format. In Claude Code, open this
folder and ask:

> Use the status-reporter agent to report the state of the pipeline.

With another AI coding assistant, give it the file and ask it to follow the
instructions. We will run your agent with Claude Code on macOS, so have it call
the pipeline as `./bin/pipeline` or tell it how to find the right command.

## Tests

No tests are required. If you or your agent want checks in code,
`tests/conftest.py` provides `db`, `replay`, `client`, `raw_records` and
`all_batch_ids`, and `make test` runs pytest against `tests/`.

## Layout

```
raw/                twelve NDJSON batches, as delivered
pipeline/           normalise -> sightings -> findings -> rollup
api/                serving API and the dashboard page
docs/CONTRACT.md    the six guarantees
.claude/agents/     the example agent; yours goes here too
tests/              fixtures, no tests
```
