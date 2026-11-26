"""Serving API over the rollup and findings, plus the dashboard page."""
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse

from pipeline import db

app = FastAPI(title="Exposure Rollup API")
HERE = Path(__file__).resolve().parent


@app.get("/", response_class=HTMLResponse)
def dashboard():
    return (HERE / "dashboard.html").read_text()


@app.get("/api/rollup")
def rollup():
    with db.connect() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT day, severity, n FROM daily_severity_rollup ORDER BY day, severity"
        )
        rows = cur.fetchall()
    return {"rows": [{"day": str(d), "severity": s, "n": n} for d, s, n in rows]}


@app.get("/api/summary")
def summary():
    with db.connect() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT severity, sum(n)::int FROM daily_severity_rollup "
            "GROUP BY severity ORDER BY severity"
        )
        by_sev = dict(cur.fetchall())
        cur.execute("SELECT coalesce(sum(n), 0)::int FROM daily_severity_rollup")
        total = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM findings")
        findings = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM processed_batches")
        batches = cur.fetchone()[0]
    return {
        "total_sightings": total,
        "by_severity": by_sev,
        "findings": findings,
        "batches_processed": batches,
    }


@app.get("/api/findings")
def findings(
    source: str | None = None,
    severity: str | None = None,
    asset_key: str | None = None,
    rule_key: str | None = None,
    limit: int = Query(100, le=1000),
    offset: int = 0,
):
    where, params = [], []
    for col, val in (("source", source), ("severity", severity),
                     ("asset_key", asset_key), ("rule_key", rule_key)):
        if val is not None:
            where.append(f"{col} = %s")
            params.append(val)
    clause = ("WHERE " + " AND ".join(where)) if where else ""
    sql = (
        "SELECT source, asset_key, rule_key, severity, cvss, first_seen_at, last_seen_at "
        f"FROM findings {clause} ORDER BY source, asset_key, rule_key "
        "LIMIT %s OFFSET %s"
    )
    with db.connect() as conn, conn.cursor() as cur:
        cur.execute(sql, params + [limit, offset])
        rows = cur.fetchall()
        cur.execute(f"SELECT count(*) FROM findings {clause}", params)
        total = cur.fetchone()[0]
    return {
        "total": total,
        "rows": [
            {
                "source": r[0], "asset_key": r[1], "rule_key": r[2],
                "severity": r[3], "cvss": float(r[4]) if r[4] is not None else None,
                "first_seen_at": r[5].isoformat(), "last_seen_at": r[6].isoformat(),
            }
            for r in rows
        ],
    }
