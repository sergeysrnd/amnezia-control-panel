# Private VPN administrator access

Deployment for amnezia-awg2: administrator peer 10.8.1.5/32; browser URL
http://10.8.1.0:8000. HTTP runs inside the encrypted AWG tunnel.

The socat listener lives in the VPN container network namespace, binds only
10.8.1.0 and accepts only source 10.8.1.5/32. AWG authenticates peer keys and
enforces their AllowedIPs. Connections relay to the host loopback backend.
No public listener, Docker port publication or VPN configuration change is needed.
Anyone possessing the administrator profile has administrator access; this
does not introduce password authentication. Do not share that profile.

For split-tunnel clients, include 10.8.1.0/32 in the destinations routed
through Amnezia. A Windows route alone is insufficient if the client's
AWG AllowedIPs excludes this address. End-to-end acceptance is pending
until the administrator client includes this destination.

Install vpn-admin-proxy.sh as /opt/amnezia-panel/vpn-admin-proxy.sh (0755) and
amnezia-vpn-admin.service under /etc/systemd/system. Dependencies: socat,
nsenter, Docker CLI. The supervisor reattaches after container replacement.

Add a panel systemd drop-in with AMNEZIA_EXTRA_HOSTS=10.8.1.0 and
AMNEZIA_EXTRA_ORIGINS=http://10.8.1.0:8000. Restart only the panel, then enable
and start amnezia-vpn-admin.service. Keep the backend on 127.0.0.1:8000.

Rollback: disable and stop amnezia-vpn-admin.service, remove the added panel
drop-in and restart the panel. The original SSH tunnel remains available.
