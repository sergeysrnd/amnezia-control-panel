"""Dependency-free configuration transforms, also shipped to the SSH helper.

Existing sections are preserved byte-for-byte. Unknown/ambiguous input fails closed.
"""

from __future__ import annotations

import base64
import hashlib
import ipaddress
import json
import re
from dataclasses import dataclass


class MutationError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def require(condition: bool, code: str = "invalid_config") -> None:
    if not condition:
        raise MutationError(code)


def valid_key(value: str) -> bool:
    try:
        return len(base64.b64decode(value, validate=True)) == 32
    except (ValueError, TypeError):
        return False


def peer_id(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()[:20]


def revision(config: str, table: str) -> str:
    return hashlib.sha256(json.dumps([config, table]).encode()).hexdigest()


AWG_FIELDS = frozenset(
    {
        "Jc",
        "Jmin",
        "Jmax",
        "S1",
        "S2",
        "S3",
        "S4",
        "H1",
        "H2",
        "H3",
        "H4",
        "I1",
        "I2",
        "I3",
        "I4",
        "I5",
        "HeaderProtectionKey",
        "ContentPaddingAddition",
        "RekeyAfterTime",
        "RekeyTimeout",
        "RejectAfterTime",
        "KeepaliveTimeout",
        "MaxHandshakeAttempts",
        "RandomTrailers",
        "DisableCookies",
    }
)
INTERFACE_FIELDS = AWG_FIELDS | {
    "PrivateKey",
    "Address",
    "ListenPort",
    "MTU",
    "DNS",
    "Table",
    "FwMark",
    "PreUp",
    "PostUp",
    "PreDown",
    "PostDown",
    "SaveConfig",
}
PEER_FIELDS = {"PublicKey", "PresharedKey", "AllowedIPs", "Endpoint", "PersistentKeepalive"}


@dataclass
class Section:
    name: str
    raw: str
    values: dict[str, str]


def sections(config: str) -> list[Section]:
    require(len(config) <= 4_000_000 and "\r" not in config and "\x00" not in config)
    result: list[Section] = []
    prefix = ""
    for line in config.splitlines(keepends=True):
        clean = line.strip()
        match = re.fullmatch(r"\[(Interface|Peer)]", clean)
        if match:
            result.append(Section(match[1], prefix + line, {}))
            prefix = ""
        elif not result:
            require(not clean or clean.startswith("#"))
            prefix += line
        else:
            result[-1].raw += line
            if not clean or clean.startswith("#"):
                continue
            require("=" in clean)
            key, value = (part.strip() for part in clean.split("=", 1))
            allowed = INTERFACE_FIELDS if result[-1].name == "Interface" else PEER_FIELDS
            require(key in allowed and key not in result[-1].values and bool(value))
            result[-1].values[key] = value
    require(bool(result) and result[0].name == "Interface")
    require(all(s.name == "Peer" for s in result[1:]))
    interface = result[0].values
    require(valid_key(interface.get("PrivateKey", "")))
    require(interface.get("SaveConfig", "false").lower() == "false", "saveconfig_unsupported")
    try:
        require(1 <= int(interface.get("ListenPort", "0")) <= 65535)
        addresses = [ipaddress.ip_interface(v.strip()) for v in interface["Address"].split(",")]
        require(len(addresses) == 1 and addresses[0].version == 4, "subnet_unsupported")
        require(16 <= addresses[0].network.prefixlen <= 30, "subnet_unsupported")
        keys: set[str] = set()
        for section in result[1:]:
            key = section.values.get("PublicKey", "")
            require(valid_key(key) and key not in keys)
            keys.add(key)
            if "PresharedKey" in section.values:
                require(valid_key(section.values["PresharedKey"]))
            networks = section.values.get("AllowedIPs", "").split(",")
            require(bool(networks))
            for network in networks:
                ipaddress.ip_network(network.strip(), strict=False)
            keepalive = section.values.get("PersistentKeepalive", "0")
            require(0 <= int(keepalive) <= 65535)
    except (ValueError, KeyError) as error:
        raise MutationError("invalid_config") from error
    return result


def metadata(table: str) -> list | dict:
    try:
        parsed = json.loads(table)
        require(isinstance(parsed, (dict, list)), "invalid_metadata")
        records = parsed if isinstance(parsed, list) else list(parsed.values())
        require(all(isinstance(r, dict) for r in records), "invalid_metadata")
        if isinstance(parsed, list):
            ids = [r.get("clientId") for r in parsed]
            require(all(isinstance(k, str) and valid_key(k) for k in ids), "invalid_metadata")
            require(len(ids) == len(set(ids)), "invalid_metadata")
        else:
            require(all(valid_key(k) for k in parsed), "invalid_metadata")
        return parsed
    except (ValueError, TypeError) as error:
        raise MutationError("invalid_metadata") from error


def free_ip(config: str) -> str:
    parsed = sections(config)
    interface = ipaddress.ip_interface(parsed[0].values["Address"])
    occupied = [
        ipaddress.ip_network(value.strip(), strict=False)
        for section in parsed[1:]
        for value in section.values["AllowedIPs"].split(",")
    ]
    for address in interface.network.hosts():
        if address != interface.ip and not any(address in net for net in occupied):
            return str(address)
    raise MutationError("subnet_full")


def validate_name(name: str) -> None:
    require(isinstance(name, str) and 1 <= len(name.strip()) <= 80, "invalid_name")
    require(all(ord(c) >= 32 and ord(c) != 127 for c in name), "invalid_name")


def add_peer(
    config: str, table: str, key: str, psk: str, name: str, date: str
) -> tuple[str, str, str]:
    parsed = sections(config)
    validate_name(name)
    require(valid_key(key) and valid_key(psk), "invalid_key")
    require(all(s.values["PublicKey"] != key for s in parsed[1:]), "duplicate_peer")
    address = free_ip(config)
    records = metadata(table)
    record = {"clientId": key, "userData": {"clientName": name.strip(), "creationDate": date}}
    if isinstance(records, list):
        require(not any(r["clientId"] == key for r in records), "duplicate_peer")
        records.append(record)
    else:
        require(key not in records, "duplicate_peer")
        records[key] = record
    updated = config + ("" if config.endswith("\n") else "\n")
    updated += f"\n[Peer]\nPublicKey = {key}\nPresharedKey = {psk}\nAllowedIPs = {address}/32\n"
    sections(updated)
    return updated, json.dumps(records, ensure_ascii=False, indent=2) + "\n", address


def remove_peer(config: str, table: str, selected_id: str, name: str) -> tuple[str, str]:
    parsed = sections(config)
    matches = [s for s in parsed[1:] if peer_id(s.values["PublicKey"]) == selected_id]
    require(len(matches) == 1, "peer_not_found")
    key = matches[0].values["PublicKey"]
    records = metadata(table)
    record = (
        next((r for r in records if r["clientId"] == key), None)
        if isinstance(records, list)
        else records.get(key)
    )
    user_data = record.get("userData", record) if record else {}
    actual_name = user_data.get("clientName") if isinstance(user_data, dict) else None
    index = parsed.index(matches[0])
    require(name == (actual_name or f"Обнаруженный клиент {index:02d}"), "confirmation_mismatch")
    if isinstance(records, list):
        records = [r for r in records if r["clientId"] != key]
    else:
        records.pop(key, None)
    return (
        "".join(s.raw for s in parsed if s is not matches[0]),
        json.dumps(records, ensure_ascii=False, indent=2) + "\n",
    )


def peer_state(config: str) -> dict[str, tuple[str, tuple[str, ...], int]]:
    """Compare persistent peer state with showconf, ignoring roaming endpoints."""
    result = {}
    for block in re.split(r"(?m)^\s*\[Peer]\s*$", config)[1:]:
        values = {}
        for line in block.splitlines():
            if "=" in line and not line.strip().startswith("#"):
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip()
        require(valid_key(values.get("PublicKey", "")), "invalid_runtime")
        key = values["PublicKey"]
        require(key not in result, "invalid_runtime")
        ips = tuple(
            sorted(
                str(ipaddress.ip_network(v.strip(), strict=False))
                for v in values.get("AllowedIPs", "").split(",")
                if v.strip()
            )
        )
        result[key] = (
            values.get("PresharedKey", ""),
            ips,
            int(values.get("PersistentKeepalive", "0")),
        )
    return result


def runtime_header(config: str) -> str:
    return re.split(r"(?m)^\s*\[Peer]\s*$", config, maxsplit=1)[0]


def interface_state(config: str) -> dict[str, str]:
    return dict(
        tuple(part.strip() for part in line.split("=", 1))
        for line in runtime_header(config).splitlines()
        if "=" in line and not line.strip().startswith("#")
    )


def preserve_runtime_interface(candidate: str, runtime: str) -> str:
    header = runtime_header(candidate)
    return runtime_header(runtime).rstrip() + "\n\n" + candidate[len(header) :]


def validate_endpoint(host: str) -> None:
    require(isinstance(host, str) and 1 <= len(host) <= 253, "invalid_endpoint")
    try:
        address = ipaddress.ip_address(host)
        require(not address.is_unspecified and not address.is_multicast, "invalid_endpoint")
    except ValueError:
        require(
            bool(
                re.fullmatch(
                    r"(?=.{1,253}$)(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*"
                    r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?",
                    host,
                )
            ),
            "invalid_endpoint",
        )


def export_client(
    config: str,
    private_key: str,
    server_key: str,
    psk: str,
    address: str,
    host: str,
    dns: str,
    keepalive: bool,
) -> str:
    validate_endpoint(host)
    interface = sections(config)[0].values
    require(all(valid_key(k) for k in (private_key, server_key, psk)), "invalid_key")
    try:
        ipaddress.ip_address(dns)
    except ValueError as error:
        raise MutationError("invalid_dns") from error
    endpoint = f"[{host}]" if ":" in host else host
    lines = [
        "[Interface]",
        f"PrivateKey = {private_key}",
        f"Address = {address}/32",
        f"DNS = {dns}",
    ]
    lines += [f"{key} = {value}" for key, value in interface.items() if key in AWG_FIELDS]
    if "MTU" in interface:
        lines.append(f"MTU = {interface['MTU']}")
    lines += [
        "",
        "[Peer]",
        f"PublicKey = {server_key}",
        f"PresharedKey = {psk}",
        "AllowedIPs = 0.0.0.0/0",
        f"Endpoint = {endpoint}:{interface['ListenPort']}",
    ]
    if keepalive:
        lines.append("PersistentKeepalive = 25")
    return "\n".join(lines) + "\n"
