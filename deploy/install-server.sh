#!/usr/bin/env bash
set -euo pipefail
umask 077

release=${1:?Usage: install-server.sh /opt/amnezia-panel/releases/REV PUBLIC_ENDPOINT}
endpoint=${2:?Public endpoint is required}
[[ $(id -u) == 0 ]] || { echo 'Run as root' >&2; exit 1; }
[[ $release =~ ^/opt/amnezia-panel/releases/[a-f0-9]{7,40}$ ]] || exit 1
[[ -f $release/frontend/dist/index.html && -f $release/deploy/requirements.txt ]] || exit 1
[[ ! -e /opt/amnezia-panel/current && ! -e /etc/systemd/system/amnezia-panel.service ]] || {
    echo 'Already installed: use the documented update and backup procedure' >&2; exit 1;
}
[[ ! -e /opt/amnezia-control && ! -e /var/lib/amnezia-control ]] || {
    echo 'Existing helper found: preserve and review it before installing' >&2; exit 1;
}
if ss -H -lnt '( sport = :8000 )' | grep -q .; then
    echo 'Port 8000 is in use' >&2; exit 1
fi
python3 -m venv /opt/amnezia-panel/venv
/opt/amnezia-panel/venv/bin/pip install --require-hashes -r "$release/deploy/requirements.txt"
install -d -m 755 /opt/amnezia-control
install -m 644 "$release/backend/src/amnezia_panel/mutation_core.py" /opt/amnezia-control/
install -m 644 "$release/backend/src/amnezia_panel/remote_helper.py" /opt/amnezia-control/
install -m 644 "$release/tools/enroll_helper.py" /opt/amnezia-control/
install -m 644 "$release/tools/server_acceptance.py" /opt/amnezia-control/
python3 /opt/amnezia-control/enroll_helper.py --endpoint "$endpoint" --protocol awg
ln -s "$release" /opt/amnezia-panel/current
install -m 644 "$release/deploy/amnezia-panel.service" /etc/systemd/system/amnezia-panel.service
systemctl daemon-reload
systemctl enable --now amnezia-panel.service
for attempt in $(seq 1 20); do
    if curl --fail --silent http://127.0.0.1:8000/api/health; then
        printf '\nPanel ready on localhost:8000\n'
        exit 0
    fi
    sleep 1
done
systemctl stop amnezia-panel.service
echo 'Readiness failed; panel stopped. VPN containers were not restarted.' >&2
exit 1
