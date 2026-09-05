import json
import uuid

from amnezia_panel.remote_helper import dispatch, read_journal


def test_journal_exposes_only_safe_fields_and_never_recovers(tmp_path):
    folder = tmp_path / "wireguard" / str(uuid.uuid4())
    folder.mkdir(parents=True)
    state = {
        "action": "create",
        "phase": "recovery_required",
        "peer_id": "a" * 20,
        "created_at": "2026-09-05T12:00:00+00:00",
        "private_key": "SECRET",
        "request_hash": "INTERNAL",
        "container_id": "INTERNAL",
    }
    path = folder / "state.json"
    path.write_text(json.dumps(state))
    before = path.read_bytes()
    result = dispatch({"action": "journal"}, tmp_path)
    assert result["total"] == 1 and result["skipped"] == 0
    assert set(result["events"][0]) == {
        "id",
        "protocol",
        "action",
        "status",
        "peer_id",
        "created_at",
    }
    assert "SECRET" not in json.dumps(result) and "INTERNAL" not in json.dumps(result)
    assert path.read_bytes() == before


def test_corrupt_journal_record_does_not_hide_other_records(tmp_path):
    folder = tmp_path / "awg" / str(uuid.uuid4())
    folder.mkdir(parents=True)
    (folder / "state.json").write_text("bad-json")
    assert read_journal(tmp_path) == {"events": [], "total": 0, "skipped": 1}


def test_journal_orders_and_limits_records(tmp_path):
    for index in range(102):
        folder = tmp_path / "awg" / str(uuid.uuid4())
        folder.mkdir(parents=True)
        (folder / "state.json").write_text(
            json.dumps(
                {
                    "action": "delete",
                    "phase": "committed",
                    "peer_id": "b" * 20,
                    "created_at": f"2026-09-05T12:{index // 60:02d}:{index % 60:02d}+00:00",
                }
            )
        )
    result = read_journal(tmp_path)
    assert result["total"] == 102 and len(result["events"]) == 100
    assert result["events"][0]["created_at"] > result["events"][-1]["created_at"]
