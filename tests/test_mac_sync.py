"""Tests de la file locale de synchronisation du collecteur macOS."""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "balance"))

from mac_sync import SyncOutbox


def test_mesures_en_attente_survivent_a_la_reouverture(tmp_path):
    database = tmp_path / "pending.sqlite3"
    payload = {
        "timestamp_utc": "2026-10-16T15:00:00+00:00",
        "weight_g": 12.5,
        "stable": True,
        "balance_id": "dp15m",
    }

    first = SyncOutbox(database)
    row_id = first.enqueue(payload)
    reopened = SyncOutbox(database)

    assert reopened.pending() == [(row_id, payload)]
    assert reopened.count() == 1

    reopened.acknowledge([row_id])
    assert SyncOutbox(database).pending() == []


def test_flux_nodered_recoit_et_transmet_les_mesures_a_influx():
    flow_path = Path(__file__).resolve().parent.parent / "server" / "nodered" / "flow_balance_mac.json"
    nodes = json.loads(flow_path.read_text(encoding="utf-8"))
    by_id = {node["id"]: node for node in nodes}

    assert by_id["mac-balance-http-in"]["url"] == "/balance/measurement"
    assert "INFLUX_TOKEN" in by_id["mac-balance-validate"]["func"]
    assert "api/v2/write?org=ird&bucket=sondes" in by_id["mac-balance-validate"]["func"]
    assert by_id["mac-balance-influx"]["wires"] == [["mac-balance-result"]]
    assert by_id["mac-balance-result"]["wires"] == [["mac-balance-http-response"]]