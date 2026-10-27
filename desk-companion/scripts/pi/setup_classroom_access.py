#!/usr/bin/python3
"""Add owner-selected private LAN SSH access while preserving USB and key-only auth."""
import argparse
import ipaddress
import json
import os
from pathlib import Path
import pwd
import subprocess
import tempfile

GUARD = Path('/etc/desk-usb-ssh.nft')
UNIT = Path('/etc/systemd/system/desk-usb-ssh-guard.service')
INSTALLED_SCRIPT = '/usr/local/lib/desk-classroom-access.py'
MARKER = Path('/var/lib/desk-companion-classroom-20261026-ready')
WIFI_PROFILE = '/etc/NetworkManager/system-connections/FYP-NETGEAR02.nmconnection'
WIFI_UUID = 'c3a1aa85-7e29-4d91-9e97-6733a2c20226'


def private_subnet(value):
    network = ipaddress.IPv4Network(value, strict=True)
    ranges = [ipaddress.IPv4Network(v) for v in ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16')]
    if network.prefixlen < 24 or not any(network.subnet_of(r) for r in ranges):
        raise ValueError('Select one private LAN of /24 or smaller')
    return str(network)


def private_host(value):
    address = ipaddress.IPv4Address(value)
    private_subnet(str(address) + '/32')
    return str(address)


def rules_for(subnet, owner_hosts=()):
    subnet = private_subnet(subnet)
    host_rules = ''.join(
        f'    tcp dport 22 iifname {{ "eth0", "wlan0" }} ip saddr {private_host(host)}/32 accept\n'
        for host in sorted(set(owner_hosts))
    )
    return f'''table inet desk_usb_ssh {{
  chain input {{
    type filter hook input priority -5; policy accept;
    tcp dport 22 iifname "lo" accept
    tcp dport 22 iifname "usb0" accept
    tcp dport 22 iifname {{ "eth0", "wlan0" }} ip saddr {subnet} accept
{host_rules}    tcp dport 22 drop
  }}
}}
'''


def run(*args, **kwargs):
    return subprocess.run(args, check=True, capture_output=True, text=True, **kwargs)


def atomic_write(path, text, mode=0o600):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.desk-network-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as out:
            out.write(text)
            out.flush()
            os.fsync(out.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def check_owner_auth():
    owner = pwd.getpwnam('desk')
    key = Path(owner.pw_dir) / '.ssh/authorized_keys'
    if not key.is_file() or not key.read_text().strip():
        raise RuntimeError('Existing owner public key is required')
    config = run('/usr/sbin/sshd', '-T').stdout.splitlines()
    required = {'passwordauthentication no', 'kbdinteractiveauthentication no',
                'permitrootlogin no', 'authenticationmethods publickey', 'allowusers desk'}
    if not required.issubset(set(config)):
        raise RuntimeError('Existing key-only SSH policy must remain in force')


def apply_guard(subnet, owner_hosts=()):
    rules = rules_for(subnet, owner_hosts)
    existing = subprocess.run(['/usr/sbin/nft', 'list', 'table', 'inet', 'desk_usb_ssh'],
                              capture_output=True, text=True)
    if existing.returncode and 'No such file or directory' not in existing.stderr:
        raise RuntimeError('Unable to inspect owned firewall table')
    batch = ('delete table inet desk_usb_ssh\n' if existing.returncode == 0 else '') + rules
    run('/usr/sbin/nft', '--check', '-f', '-', input=batch)
    run('/usr/sbin/nft', '-f', '-', input=batch)  # One atomic transaction; other tables retained.
    return rules


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--subnet', required=True, type=private_subnet)
    parser.add_argument('--guard-only', action='store_true')
    parser.add_argument('--owner-host', action='append', default=[], type=private_host)
    args = parser.parse_args()
    if os.geteuid() != 0:
        raise SystemExit('Run on the prepared Pi as root')
    check_owner_auth()
    if not args.guard_only:
        if not Path('/var/lib/desk-companion-provisioned').is_file():
            raise RuntimeError('Existing application installation marker is required')
        if not GUARD.is_file() or not UNIT.is_file():
            raise RuntimeError('Existing USB access configuration is required')
        for path in (GUARD, UNIT):
            backup = path.with_name(path.name + '.before-classroom')
            if not backup.exists():
                atomic_write(backup, path.read_text())
    rules = apply_guard(args.subnet, args.owner_host)
    if args.guard_only:
        return
    atomic_write(GUARD, rules)
    atomic_write(UNIT, f'''[Unit]
Description=Limit Desk Companion SSH to USB and the selected private LAN
Before=ssh.service

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 {INSTALLED_SCRIPT} --subnet {args.subnet} --guard-only{''.join(' --owner-host '+h for h in args.owner_host)}
RemainAfterExit=yes
''', 0o644)
    run('systemctl', 'daemon-reload')
    run('systemctl', 'enable', '--now', 'ssh.service')
    run('rfkill', 'unblock', 'wifi')
    run('nmcli', 'radio', 'wifi', 'on')
    run('nmcli', 'connection', 'load', WIFI_PROFILE)
    wifi = subprocess.run(
        ['nmcli', '--wait', '30', 'connection', 'up', 'uuid', WIFI_UUID],
        capture_output=True, text=True, timeout=40,
    )
    addresses = json.loads(run('ip', '-j', '-4', 'address', 'show').stdout)
    host_key = Path('/etc/ssh/ssh_host_ed25519_key.pub')
    status = {'subnet': args.subnet, 'key_only': True,
              'wifi_activated': wifi.returncode == 0,
              'application_and_vnc': 'unchanged loopback listeners',
              'interfaces': [{'name': x['ifname'], 'ipv4': [a['local'] for a in x['addr_info']]}
                             for x in addresses if x['ifname'] in ('eth0', 'wlan0', 'usb0')],
              'ssh_host_public_key': host_key.read_text().strip() if host_key.exists() else None}
    atomic_write(MARKER, json.dumps(status)+'\n')
    # Address/public-host-key diagnostics only, never the Wi-Fi secret.
    if Path('/boot/firmware').is_dir():
        atomic_write(Path('/boot/firmware/desk-classroom-status.json'), json.dumps(status)+'\n')
    print('Selected LAN SSH access configured; existing users, keys and application data preserved.')
    if wifi.returncode:
        print('Wi-Fi activation pending; the saved profile will keep trying automatically.')


if __name__ == '__main__':
    main()
