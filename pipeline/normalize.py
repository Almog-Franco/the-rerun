"""Per-source normalisation.

Each scanner delivers a different payload shape. Normalisation flattens them
into a common record: source, asset_key, rule_key, severity, cvss, detected_at.
"""
import json


def _sev(value) -> str:
    return str(value).strip().lower()


def normalize_scanner_a(rec: dict) -> dict:
    return {
        "source": "scanner_a",
        "asset_key": rec["host"],
        "rule_key": rec["check_id"],
        "severity": _sev(rec["sev"]),
        "cvss": rec.get("cvss"),
        "detected_at": rec["ts"],
    }


def normalize_scanner_b(rec: dict) -> dict:
    return {
        "source": "scanner_b",
        "asset_key": rec["asset"]["hostname"],
        "rule_key": rec["vuln"]["id"],
        "severity": _sev(rec["vuln"]["severity"]),
        "cvss": rec.get("score"),
        "detected_at": rec["observed_at"],
    }


def normalize_scanner_c(rec: dict) -> dict:
    return {
        "source": "scanner_c",
        "asset_key": rec["target"],
        "rule_key": rec["finding"]["key"],
        "severity": _sev(rec["level"]),
        "cvss": rec["finding"]["cvss"]["base_score"],
        "detected_at": rec["first_observed"],
    }


NORMALIZERS = {
    "scanner_a": normalize_scanner_a,
    "scanner_b": normalize_scanner_b,
    "scanner_c": normalize_scanner_c,
}


def normalize_batch(path) -> list:
    """Read one NDJSON batch and return normalised records."""
    out = []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                out.append(NORMALIZERS[rec["source"]](rec))
            except Exception:
                continue
    return out
