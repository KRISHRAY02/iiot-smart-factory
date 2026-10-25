import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth import create_access_token
from app.export_csv import csv_row, safe_cell
from app.routers import export_router


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(export_router.router)
    return TestClient(app)


@pytest.fixture
def auth_headers():
    return {"Authorization": f"Bearer {create_access_token('admin')}"}


def test_safe_cell_prefixes_formula_characters():
    assert safe_cell("=1+1") == "'=1+1"
    assert safe_cell("+1") == "'+1"
    assert safe_cell("-1") == "'-1"
    assert safe_cell("@cmd") == "'@cmd"
    assert safe_cell("normal") == "normal"
    assert safe_cell(None) == ""


def test_csv_row_escapes_commas_quotes_and_newlines():
    row = csv_row(["a,b", 'has"quote', "line\nbreak", "=evil"])
    assert row == '"a,b","has""quote","line\nbreak",\'=evil\r\n'


def test_alerts_csv_rejects_end_before_start(client, auth_headers, fresh_db):
    now = datetime.now(timezone.utc)
    r = client.get(
        "/api/export/alerts.csv",
        params={"start": now.isoformat(), "end": (now - timedelta(hours=1)).isoformat()},
        headers=auth_headers,
    )
    assert r.status_code == 400
    assert "end must be after start" in r.json()["detail"]


def test_alerts_csv_rejects_range_over_7_days(client, auth_headers, fresh_db):
    now = datetime.now(timezone.utc)
    r = client.get(
        "/api/export/alerts.csv",
        params={"start": (now - timedelta(days=10)).isoformat(), "end": now.isoformat()},
        headers=auth_headers,
    )
    assert r.status_code == 400
    assert "7 days" in r.json()["detail"]


def test_alerts_csv_rejects_empty_result(client, auth_headers, fresh_db):
    now = datetime.now(timezone.utc)
    r = client.get(
        "/api/export/alerts.csv",
        params={"start": (now - timedelta(hours=2)).isoformat(), "end": (now - timedelta(hours=1)).isoformat()},
        headers=auth_headers,
    )
    assert r.status_code == 400
    assert "No alerts found" in r.json()["detail"]


def test_alerts_csv_requires_auth(client, fresh_db):
    now = datetime.now(timezone.utc)
    r = client.get(
        "/api/export/alerts.csv",
        params={"start": (now - timedelta(hours=1)).isoformat(), "end": now.isoformat()},
    )
    assert r.status_code == 401


def test_alerts_csv_column_order_and_escaping(client, auth_headers, fresh_db):
    from app import alerts_db
    from app.models import Alert

    alert = Alert(
        id=str(uuid.uuid4()),
        node_id="temp-line1",
        sensor_type="temperature",
        value=95.0,
        threshold=90.0,
        condition="above",
        severity="critical",
        message="hot",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    record = alerts_db.create_alert(alert)
    alerts_db.resolve_alert(record.id, "system", resolution_note='=cmd|, has "quotes"\nand a newline')

    now = datetime.now(timezone.utc)
    r = client.get(
        "/api/export/alerts.csv",
        params={"start": (now - timedelta(hours=1)).isoformat(), "end": (now + timedelta(hours=1)).isoformat()},
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert r.headers["content-disposition"].startswith('attachment; filename="alerts_')

    lines = r.text.splitlines()
    assert lines[0].split(",") == [
        "created_at",
        "asset_name",
        "node_id",
        "sensor_type",
        "alert_type",
        "severity",
        "status",
        "value",
        "z_score",
        "baseline_mean",
        "baseline_stddev",
        "acknowledged_by",
        "acknowledged_at",
        "resolved_by",
        "resolved_at",
        "resolution_note",
    ]
    assert "'=cmd|" in r.text  # formula-injection guard applied


def test_readings_csv_rejects_unknown_asset(client, auth_headers, fresh_db):
    now = datetime.now(timezone.utc)
    r = client.get(
        "/api/export/readings.csv",
        params={"start": (now - timedelta(hours=1)).isoformat(), "end": now.isoformat(), "asset_id": "nope"},
        headers=auth_headers,
    )
    assert r.status_code == 400
    assert "Unknown asset_id" in r.json()["detail"]


def test_readings_csv_streams_rows_in_expected_columns(client, auth_headers, fresh_db, monkeypatch):
    from app import influx

    now = datetime.now(timezone.utc)
    monkeypatch.setattr(influx, "count_range", lambda *a, **k: 2)
    monkeypatch.setattr(
        influx,
        "stream_range",
        lambda *a, **k: iter(
            [
                {"node_id": "temp-line1", "sensor_type": "temperature", "value": 65.1, "timestamp": now.isoformat()},
                {"node_id": "temp-line1", "sensor_type": "temperature", "value": 65.4, "timestamp": now.isoformat()},
            ]
        ),
    )

    r = client.get(
        "/api/export/readings.csv",
        params={"start": (now - timedelta(hours=1)).isoformat(), "end": (now + timedelta(hours=1)).isoformat()},
        headers=auth_headers,
    )
    assert r.status_code == 200
    lines = r.text.strip().splitlines()
    assert lines[0] == "timestamp_utc,node_id,asset_name,sensor_type,value,unit"
    assert len(lines) == 3
    assert lines[1].startswith(f"{now.isoformat()},temp-line1,")


def test_readings_csv_rejects_when_row_count_exceeds_cap(client, auth_headers, fresh_db, monkeypatch):
    from app import influx

    now = datetime.now(timezone.utc)
    monkeypatch.setattr(influx, "count_range", lambda *a, **k: export_router.MAX_EXPORT_ROWS + 1)

    r = client.get(
        "/api/export/readings.csv",
        params={"start": (now - timedelta(hours=1)).isoformat(), "end": now.isoformat()},
        headers=auth_headers,
    )
    assert r.status_code == 400
    assert "exceeds" in r.json()["detail"]
