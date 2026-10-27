#!/usr/bin/python3
"""One bounded campus Wi-Fi trial with existing LAN recovery and private logs."""

import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import time

VTC_UUID = 'c0a12d72-834c-4b80-b454-70f9adac9137'
RECOVERY_UUID = 'c3a1aa85-7e29-4d91-9e97-6733a2c20226'
PROFILE = '/etc/NetworkManager/system-connections/FYP-VTC-Student.nmconnection'
STATUS = Path('/var/lib/desk-companion/vtc-trial-20261026.json')
BOOT_STATUS = Path('/boot/firmware/desk-vtc-status.json')
ACK = Path('/home/desk/.local/state/desk-companion/vtc-confirmed-20261026')


def run(*args, timeout=15, check=True):
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=check)


def write_status(helper, result):
    addresses = json.loads(run('ip', '-j', '-4', 'address', 'show').stdout)
    result['interfaces'] = [
        {'name': i['ifname'], 'ipv4': [a['local'] for a in i['addr_info']]}
        for i in addresses if i['ifname'] in ('wlan0', 'eth0', 'usb0')
    ]
    if result.get('vtc_activated') and 'vtc_ipv4' not in result and 'recovery' not in result:
        result['vtc_ipv4'] = [a['local'] for i in addresses if i['ifname'] == 'wlan0'
                              for a in i['addr_info']]
    result['recorded_unix'] = time.time()
    for path in (STATUS, BOOT_STATUS):
        helper.atomic_write(path, json.dumps(result)+'\n')


def restore_network():
    """Restore the known network even if a previous NetworkManager call hung."""
    for attempt in range(2):
        try:
            run('nmcli', 'connection', 'modify', VTC_UUID, 'connection.autoconnect', 'no')
            run('nmcli', 'connection', 'modify', RECOVERY_UUID, 'connection.autoconnect', 'yes')
            run('rfkill', 'unblock', 'wifi')
            run('nmcli', 'radio', 'wifi', 'on')
            result = run('nmcli', '--wait', '30', 'connection', 'up', 'uuid', RECOVERY_UUID,
                         timeout=40, check=False)
            if result.returncode == 0:
                return True
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            pass
        if attempt == 0:
            run('systemctl', 'restart', 'NetworkManager.service', timeout=30)
    return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--owner-host', required=True)
    parser.add_argument('--recover', action='store_true')
    parser.add_argument('--restore-only', action='store_true')
    args = parser.parse_args()
    if os.geteuid() != 0:
        raise SystemExit('Run only on the prepared Pi as root')
    spec = importlib.util.spec_from_file_location('classroom', '/usr/local/lib/desk-classroom-access.py')
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    host = helper.private_host(args.owner_host)
    if args.restore_only:
        restored = restore_network()
        write_status(helper, {'vtc_activated': False, 'state': 'recovery_only',
                             'recovery': 'NETGEAR02', 'recovery_active': restored})
        return
    if args.recover:
        for _ in range(150):
            if ACK.is_file():
                status = json.loads(STATUS.read_text())
                status['remote_confirmed'] = True
                write_status(helper, status)
                return
            time.sleep(2)
        restored = restore_network()
        status = json.loads(STATUS.read_text())
        status.update(remote_confirmed=False, recovery='NETGEAR02', recovery_active=restored)
        write_status(helper, status)
        return

    helper.check_owner_auth()
    if not Path('/var/lib/desk-companion-provisioned').is_file():
        raise RuntimeError('Existing installation is required; no implicit reinstall')
    STATUS.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    ACK.unlink(missing_ok=True)
    for path in (helper.GUARD, helper.UNIT):
        backup = path.with_name(path.name+'.before-vtc')
        if not backup.exists():
            helper.atomic_write(backup, path.read_text())
    rules = helper.apply_guard('192.168.49.0/24', [host])
    helper.atomic_write(helper.GUARD, rules)
    helper.atomic_write(helper.UNIT, f'''[Unit]
Description=Owner-key SSH on recovery LAN and the selected campus Mac address
Before=ssh.service
[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /usr/local/lib/desk-classroom-access.py --subnet 192.168.49.0/24 --owner-host {host} --guard-only
RemainAfterExit=yes
''', 0o644)
    recovery = Path('/etc/systemd/system/desk-vtc-recovery.service')
    helper.atomic_write(recovery, f'''[Unit]
Description=Recover the existing classroom Wi-Fi if the VTC trial is not confirmed
After=NetworkManager.service
[Service]
Type=oneshot
TimeoutStartSec=480
ExecStart=/usr/bin/python3 /usr/local/lib/desk-vtc-access.py --owner-host {host} --recover
''', 0o644)
    run('systemctl', 'daemon-reload')
    run('systemctl', 'enable', '--now', 'ssh.service')
    write_status(helper, {'vtc_activated': False, 'state': 'trial_starting', 'owner_ipv4': host})
    # Start the independent recovery process before any connection switch.
    run('systemctl', 'start', '--no-block', 'desk-vtc-recovery.service')
    run('rfkill', 'unblock', 'wifi')
    run('nmcli', 'radio', 'wifi', 'on')
    profile = Path(PROFILE)
    previous = profile.with_name(profile.name+'.before-vtc')
    if profile.exists() and not previous.exists():
        helper.atomic_write(previous, profile.read_text())
    staged = Path('/etc/desk-provision/vtc-profile.nmconnection')
    helper.atomic_write(profile, staged.read_text())
    staged.unlink()
    run('nmcli', 'connection', 'load', PROFILE)
    # The profile starts with autoconnect=false and auth-retries=1. It must not
    # repeatedly submit a bad credential while the owner cannot reach the Pi.
    try:
        attempt = run('nmcli', '--wait', '60', 'connection', 'up', 'uuid', VTC_UUID,
                      timeout=70, check=False)
        code = attempt.returncode
    except subprocess.TimeoutExpired:
        code = 124
    # Keep detailed logs local and root-only; never copy account identity or
    # credential-bearing command output into the public boot status.
    log = run('journalctl', '-b', '-u', 'NetworkManager', '--no-pager', '-n', '180', check=False)
    helper.atomic_write(STATUS.parent/'vtc-diagnostics-private.log', log.stdout)
    result = {'vtc_activated': code == 0, 'activation_exit': code, 'remote_confirmed': False,
              'owner_ipv4': host, 'eap': 'PEAP/MSCHAPv2', 'ca_validation': 'system CA and vtc.edu.hk'}
    write_status(helper, result)
    if code == 0:
        run('nmcli', 'connection', 'modify', VTC_UUID, 'connection.autoconnect', 'yes')
    else:
        restored = restore_network()
        result.update(recovery='NETGEAR02', recovery_active=restored)
        write_status(helper, result)
        if restored:
            run('systemctl', 'stop', 'desk-vtc-recovery.service')
    print('VTC connection trial completed; nonsecret status is saved on the boot partition.')


if __name__ == '__main__':
    main()
