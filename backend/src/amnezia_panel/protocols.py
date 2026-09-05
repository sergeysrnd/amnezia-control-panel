from dataclasses import dataclass

from amnezia_panel.models import ProtocolId


@dataclass(frozen=True, slots=True)
class ProtocolSpec:
    id: ProtocolId
    label: str
    container: str
    config_path: str
    clients_table_path: str
    binary: str
    interface: str


PROTOCOLS: tuple[ProtocolSpec, ...] = (
    ProtocolSpec(
        id=ProtocolId.AWG_LEGACY,
        label="AWG Legacy",
        container="amnezia-awg",
        config_path="/opt/amnezia/awg/wg0.conf",
        clients_table_path="/opt/amnezia/awg/clientsTable",
        binary="wg",
        interface="wg0",
    ),
    ProtocolSpec(
        id=ProtocolId.AWG,
        label="AmneziaWG",
        container="amnezia-awg2",
        config_path="/opt/amnezia/awg/awg0.conf",
        clients_table_path="/opt/amnezia/awg/clientsTable",
        binary="awg",
        interface="awg0",
    ),
    ProtocolSpec(
        id=ProtocolId.WIREGUARD,
        label="WireGuard",
        container="amnezia-wireguard",
        config_path="/opt/amnezia/wireguard/wg0.conf",
        clients_table_path="/opt/amnezia/wireguard/clientsTable",
        binary="wg",
        interface="wg0",
    ),
)
