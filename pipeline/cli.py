"""Ingestion pipeline CLI.

    pipeline reset
    pipeline run --batch B03
    pipeline run --all
    pipeline status
"""
import argparse
import sys
from pathlib import Path

from . import db
from .load import load_batch
from .normalize import normalize_batch

RAW = Path(__file__).resolve().parent.parent / "raw"
SCHEMA = Path(__file__).resolve().parent / "schema.sql"


def all_batch_ids():
    return sorted(p.stem.replace("batch_", "") for p in RAW.glob("batch_*.ndjson"))


def batch_path(batch_id: str) -> Path:
    p = RAW / f"batch_{batch_id}.ndjson"
    if not p.exists():
        sys.exit(f"no such batch: {batch_id} (have {', '.join(all_batch_ids())})")
    return p


def cmd_reset(_args):
    with db.connect() as conn:
        with conn.cursor() as cur:
            cur.execute(SCHEMA.read_text())
        conn.commit()
    print("reset: schema recreated, database empty")


def cmd_run(args):
    ids = all_batch_ids() if args.all else args.batch
    if not ids:
        sys.exit("nothing to run: pass --batch <id> or --all")
    with db.connect() as conn:
        for bid in ids:
            records = normalize_batch(batch_path(bid))
            load_batch(conn, bid, records)
            print(f"run {bid}: {len(records)} records loaded")


def cmd_status(_args):
    with db.connect() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT batch_id, record_count, processed_at "
            "FROM processed_batches ORDER BY batch_id"
        )
        rows = cur.fetchall()
        print(f"{'batch':<8}{'records':>9}  processed_at")
        for bid, n, ts in rows:
            print(f"{bid:<8}{n:>9}  {ts:%Y-%m-%d %H:%M:%S}")
        cur.execute("SELECT count(*) FROM findings")
        findings = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM sightings")
        sightings = cur.fetchone()[0]
        cur.execute("SELECT coalesce(sum(n), 0) FROM daily_severity_rollup")
        rollup = cur.fetchone()[0]
    print(f"\n{len(rows)} batches processed")
    print(f"findings   {findings:>8}")
    print(f"sightings  {sightings:>8}")
    print(f"rollup sum {rollup:>8}")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="pipeline")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("reset", help="truncate everything, recreate the schema").set_defaults(fn=cmd_reset)

    run = sub.add_parser("run", help="ingest one or more batches")
    run.add_argument("--batch", action="append", default=[], metavar="ID")
    run.add_argument("--all", action="store_true", help="ingest every batch in order")
    run.set_defaults(fn=cmd_run)

    sub.add_parser("status", help="what this database thinks it has processed").set_defaults(fn=cmd_status)

    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
