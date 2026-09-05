import base64
import fcntl
import json
import uuid

import pytest

from amnezia_panel.mutation_core import (
    MutationError,
    add_peer,
    export_client,
    free_ip,
    peer_id,
    peer_state,
    remove_peer,
    revision,
    sections,
)
from amnezia_panel.remote_helper import TransactionEngine, dispatch


def key(byte):
    return base64.b64encode(bytes([byte]) * 32).decode()


CONFIG = (
    f"# Keep this comment\n[Interface]\nPrivateKey = {key(1)}\n"
    "Address = 10.8.0.1/24\nListenPort = 12345\nPostUp = echo unchanged\n"
    f"\n[Peer]\nPublicKey = {key(2)}\nAllowedIPs = 10.8.0.2/32\n"
)
TABLE = json.dumps([{"clientId": key(2), "userData": {"clientName": "Existing", "extra": 42}}])


class FakeStore:
    protocol = "wireguard"
    policy = {"endpoint": "vpn.example.com", "dns": "1.1.1.1"}

    def __init__(self):
        self.files = [CONFIG, TABLE]
        self.live = CONFIG
        self.fail_at = None
        self.replacements = 0
        self.syncs = 0
        self.external_change = False
        self.crash = False
        self.verify_failure = False

    def identity(self):
        return "pinned-container"

    def read(self):
        return tuple(self.files)

    def runtime(self):
        return self.live

    def server_key(self, config):
        return key(9)

    def keypair(self):
        return key(3), key(4), key(5)

    def strip(self, config):
        if self.fail_at == "strip":
            raise MutationError("invalid_candidate")
        if self.external_change:
            self.files[0] += "# external change\n"
        return config

    def replace(self, index, value):
        self.replacements += 1
        if self.fail_at == self.replacements:
            raise MutationError("remote_command_failed")
        self.files[index] = value
        if self.crash:
            raise KeyboardInterrupt

    def sync(self, value):
        self.syncs += 1
        if self.fail_at == "sync" and self.syncs == 1:
            raise MutationError("remote_command_failed")
        if self.fail_at == "rollback":
            raise MutationError("remote_command_failed")
        if self.verify_failure and self.syncs == 1:
            return
        self.live = value


def request(**fields):
    return {
        "protocol": "wireguard",
        "action": "create",
        "name": "Phone",
        "keepalive": True,
        "operation_id": str(uuid.uuid4()),
        "revision": revision(CONFIG, TABLE),
        **fields,
    }


def test_ip_uses_actual_ranges_and_preserves_original_sections():
    config = CONFIG.replace("10.8.0.2/32", "10.8.0.0/29")
    assert free_ip(config) == "10.8.0.8"
    updated, table, address = add_peer(config, TABLE, key(4), key(5), "Телефон", "date")
    assert updated.startswith(config)
    assert address == "10.8.0.8"
    assert json.loads(table)[0] == json.loads(TABLE)[0]
    removed, restored_table = remove_peer(updated, table, peer_id(key(4)), "Телефон")
    assert removed.strip() == config.strip()
    assert json.loads(restored_table) == json.loads(TABLE)


@pytest.mark.parametrize(
    "bad",
    [
        CONFIG + "[Interface]\nPrivateKey = x\n",
        CONFIG.replace("ListenPort = 12345", "ListenPort = 12345\nListenPort = 1"),
        CONFIG.replace("Address = 10.8.0.1/24", "Address = 10.8.0.1/24\nSaveConfig = true"),
        CONFIG.replace("PublicKey =", "Unsupported ="),
        CONFIG.replace("10.8.0.2/32", "not-an-ip"),
    ],
)
def test_ambiguous_configs_fail_closed(bad):
    with pytest.raises(MutationError):
        sections(bad)


def test_export_copies_awg_parameters_but_never_server_hooks_or_key():
    config = CONFIG.replace("Address =", "S1 = 42\nHeaderProtectionKey = 123\nAddress =")
    profile = export_client(
        config, key(3), key(9), key(5), "10.8.0.3", "2001:db8::1", "1.1.1.1", True
    )
    assert f"PrivateKey = {key(3)}" in profile
    assert key(1) not in profile and "PostUp" not in profile
    assert "S1 = 42" in profile and "HeaderProtectionKey = 123" in profile
    assert "Endpoint = [2001:db8::1]:12345" in profile
    assert "PersistentKeepalive = 25" in profile


def test_create_delete_and_private_backups(tmp_path):
    store = FakeStore()
    engine = TransactionEngine(store, tmp_path)
    req = request()
    result = engine.execute(req)
    assert result["status"] == "committed"
    assert len(peer_state(store.live)) == 2
    assert store.files[0].startswith(CONFIG)
    folder = tmp_path / req["operation_id"]
    assert (folder.stat().st_mode & 0o777) == 0o700
    for path in folder.iterdir():
        assert (path.stat().st_mode & 0o777) == 0o600
        assert key(3) not in path.read_text()  # Client private key never persisted.
    assert (folder / "config.before").read_text() == CONFIG
    repeated = engine.execute(req)
    assert repeated["replayed"] and "native_config" not in repeated
    delete = request(
        action="delete", revision=revision(*store.read()), peer_id=result["peer_id"], name="Phone"
    )
    delete.pop("keepalive")
    assert engine.execute(delete)["status"] == "committed"
    assert peer_state(store.live) == peer_state(CONFIG)
    assert json.loads(store.files[1]) == json.loads(TABLE)


@pytest.mark.parametrize("failure", [1, 2, "sync"])
def test_each_partial_write_rolls_back(tmp_path, failure):
    store = FakeStore()
    store.fail_at = failure
    req = request()
    with pytest.raises(MutationError, match="rolled_back"):
        TransactionEngine(store, tmp_path).execute(req)
    assert store.read() == (CONFIG, TABLE)
    assert peer_state(store.live) == peer_state(CONFIG)
    state = json.loads((tmp_path / req["operation_id"] / "state.json").read_text())
    assert state["phase"] == "rolled_back"


def test_verification_failure_rolls_back(tmp_path):
    store = FakeStore()
    store.verify_failure = True
    with pytest.raises(MutationError, match="rolled_back"):
        TransactionEngine(store, tmp_path).execute(request())
    assert store.read() == (CONFIG, TABLE)
    assert store.live == CONFIG


def test_stale_revision_does_not_write(tmp_path):
    store = FakeStore()
    with pytest.raises(MutationError, match="revision_conflict"):
        TransactionEngine(store, tmp_path).execute(request(revision="0" * 64))
    assert store.replacements == 0


def test_external_change_before_commit_is_preserved(tmp_path):
    store = FakeStore()
    store.external_change = True
    with pytest.raises(MutationError, match="revision_conflict"):
        TransactionEngine(store, tmp_path).execute(request())
    assert store.files[0].endswith("# external change\n")
    assert store.replacements == 0


def test_recovery_after_crash_between_file_replacements(tmp_path):
    store = FakeStore()
    store.crash = True
    engine = TransactionEngine(store, tmp_path)
    with pytest.raises(KeyboardInterrupt):
        engine.execute(request())
    store.crash = False
    engine.recover()
    assert store.read() == (CONFIG, TABLE)
    assert store.live == CONFIG


def test_failed_rollback_blocks_future_writes(tmp_path):
    store = FakeStore()
    store.fail_at = "rollback"
    engine = TransactionEngine(store, tmp_path)
    with pytest.raises(MutationError, match="recovery_required"):
        engine.execute(request())
    with pytest.raises(MutationError, match="recovery_required"):
        engine.recover()


def test_recovery_preserves_external_changes(tmp_path):
    store = FakeStore()
    store.crash = True
    engine = TransactionEngine(store, tmp_path)
    with pytest.raises(KeyboardInterrupt):
        engine.execute(request())
    store.crash = False
    store.files[1] += " \n"
    before = store.read()
    with pytest.raises(MutationError, match="recovery_required"):
        engine.recover()
    assert store.read() == before


def test_validation_and_runtime_drift_do_not_write(tmp_path):
    store = FakeStore()
    store.live = CONFIG.split("[Peer]")[0]
    with pytest.raises(MutationError, match="runtime_drift"):
        TransactionEngine(store, tmp_path).execute(request())
    assert store.replacements == 0


def test_delete_confirmation_checks_current_name():
    with pytest.raises(MutationError, match="confirmation_mismatch"):
        remove_peer(CONFIG, TABLE, peer_id(key(2)), "Wrong")


def test_peer_state_ignores_roaming_endpoint():
    assert peer_state(CONFIG) == peer_state(CONFIG + "Endpoint = 192.0.2.1:1234\n")


def test_recovery_never_applies_old_backup_to_replaced_container(tmp_path):
    store = FakeStore()
    store.crash = True
    engine = TransactionEngine(store, tmp_path)
    with pytest.raises(KeyboardInterrupt):
        engine.execute(request())
    store.crash = False
    store.identity = lambda: "replacement-container"
    before = store.read()
    with pytest.raises(MutationError, match="recovery_required"):
        engine.recover()
    assert store.read() == before


def test_pending_transaction_disables_preflight_without_writing(tmp_path):
    store = FakeStore()
    store.crash = True
    engine = TransactionEngine(store, tmp_path)
    with pytest.raises(KeyboardInterrupt):
        engine.execute(request())
    before = store.read()
    with pytest.raises(MutationError, match="recovery_required"):
        engine.snapshot()
    assert store.read() == before


def test_process_lock_rejects_concurrent_request(tmp_path):
    (tmp_path / "policy.json").write_text(json.dumps({"wireguard": {"endpoint": "vpn.example"}}))
    with (tmp_path / "wireguard.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(MutationError, match="busy"):
            dispatch({"protocol": "wireguard", "action": "preflight"}, root=tmp_path)
