#!/usr/bin/python3
"""One boot-time Student/Halls trial with durable, nonsecret phase records."""

import argparse
import importlib.util
import ipaddress
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request

CONFIG = Path('/etc/desk-dorm-access.json')
STATE = Path('/var/lib/desk-companion/dorm-status.json')
BOOT_STATE = Path('/boot/firmware/desk-dorm-status.json')
WINDOW = Path('/run/desk-dorm-enrollment.json')
ACK = Path('/run/desk-dorm-owner-confirmed.json')
PRIVATE = Path('/var/lib/desk-companion/dorm-private')
STUDENT = 'c0a12d72-834c-4b80-b454-70f9adac9137'
HALLS = '6285ca25-f2bd-48cf-a04c-18f70748d405'
HALLS_PASSWORD = Path('/etc/desk-provision/halls-activation.passwd')


def helper():
    spec = importlib.util.spec_from_file_location('access', '/usr/local/lib/desk-classroom-access.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def addresses():
    try:
        data = json.loads(subprocess.check_output(['ip', '-j', '-4', 'addr'], text=True, timeout=3))
        return [
            {'name': i['ifname'], 'ipv4': [a['local'] for a in i['addr_info']],
             'prefixes': [f"{a['local']}/{a['prefixlen']}" for a in i['addr_info']]}
            for i in data if i['ifname'] in ('wlan0', 'eth0', 'usb0')
        ]
    except (OSError, ValueError, subprocess.SubprocessError):
        return []


class Trial:
    def __init__(self, settings):
        self.settings = settings
        self.access = helper()
        self.events = []
        self.data = {'trial_id': settings['trial_id'], 'selected_network': None,
                     'phase': 'starting', 'events': self.events}

    def save(self, phase, **fields):
        self.data.update(phase=phase, interfaces=addresses(), **fields)
        self.events.append({'phase': phase, 'monotonic': round(time.monotonic(), 3),
                            'utc_unix': time.time(), **fields})
        for path in (STATE, BOOT_STATE):
            self.access.atomic_write(path, json.dumps(self.data)+'\n')

    def run(self, phase, args, timeout=15):
        self.save(phase+'_begin')
        PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
        log = PRIVATE / (phase+'.log')
        # Files, rather than a pipe tied to an SSH/boot caller, retain errors
        # even when wireless switching interrupts the management connection.
        with log.open('ab') as output:
            log.chmod(0o600)
            process = subprocess.Popen(args, stdout=output, stderr=subprocess.STDOUT,
                                       start_new_session=True)
            deadline = time.monotonic()+timeout
            while process.poll() is None and time.monotonic() < deadline:
                time.sleep(0.2)
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.save(phase+'_unresponsive')
                    raise RuntimeError('Command did not stop; phase saved before aborting')
                code = 124
            else:
                code = process.returncode
        self.save(phase+'_done', command_exit=code)
        return code

    def require(self, phase, args, timeout=15):
        if self.run(phase, args, timeout):
            raise RuntimeError('Setup command failed; consult its private phase log')


def guarded_halls_network(prefix):
    network = ipaddress.IPv4Network(prefix, strict=False)
    private = [ipaddress.IPv4Network(n) for n in ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16')]
    if network.prefixlen < 20 or not any(network.subnet_of(n) for n in private):
        raise ValueError('Halls enrollment must stay on a bounded private subnet')
    return str(network)


def activation_command(name, uuid):
    command = ['nmcli', '--wait', '45', 'connection', 'up', 'uuid', uuid]
    if name == 'VTC-Halls' and HALLS_PASSWORD.is_file():
        command += ['passwd-file', str(HALLS_PASSWORD)]
    return command


def runtime_diagnostics():
    result = {}
    for name, command in (
        ('listeners', ['ss', '-H', '-lnt']),
        ('ssh_service', ['systemctl', 'is-active', 'ssh.service']),
        ('ssh_guard', ['nft', '-j', 'list', 'table', 'inet', 'desk_usb_ssh']),
    ):
        try:
            value = subprocess.run(command, capture_output=True, text=True, timeout=3)
            if name == 'listeners':
                result[name] = [line.split()[3] for line in value.stdout.splitlines()
                                if len(line.split()) >= 4 and
                                line.split()[3].rsplit(':', 1)[-1] in ('22', '111', '8831', '5900')]
            elif name == 'ssh_service':
                result[name] = value.stdout.strip() or 'unavailable'
            else:
                data = json.loads(value.stdout) if value.returncode == 0 else {}
                result[name] = [
                    e['counter']['packets']
                    for item in data.get('nftables', [])
                    for e in item.get('rule', {}).get('expr', []) if 'counter' in e
                ]
        except (subprocess.TimeoutExpired, ValueError):
            result[name] = {'error': 'timeout'}
    return result


def internet_probe(access):
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    result = {}
    try:
        try:
            response = urllib.request.build_opener(NoRedirect).open(
                'http://captive.apple.com/hotspot-detect.html', timeout=6)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            body = response.read(4096)
            location = response.headers.get('Location', '')
            result.update(http_status=response.code, apple_success=b'<body>Success</body>' in body,
                          redirect_host=urllib.parse.urlsplit(location).hostname if location else None)
            access.atomic_write(PRIVATE/'portal-probe.html', body.decode(errors='replace'))
            if location:
                access.atomic_write(PRIVATE/'portal-location.txt', location+'\n')
    except (OSError, urllib.error.URLError):
        result['http_error'] = True
    try:
        request = urllib.request.Request('https://example.com/', method='HEAD')
        with urllib.request.urlopen(request, timeout=6) as response:
            result['verified_https_status'] = response.status
    except (OSError, urllib.error.URLError):
        result['verified_https_error'] = True
    return result


def apply_guard(settings, access):
    access.check_owner_auth()
    rules = access.rules_for('192.168.49.0/24', settings['owner_hosts'])
    if WINDOW.exists():
        window = json.loads(WINDOW.read_text())
        remaining = min(600, int(window['expires_monotonic']-time.monotonic()))
        if remaining > 0:
            network = guarded_halls_network(window['network'])
            enrollment = f'''  set halls_enrollment {{
    type ipv4_addr
    flags interval,timeout
    elements = {{ {network} timeout {remaining}s }}
  }}
'''
            rules = rules.replace('  chain input {', enrollment+'  chain input {')
            rules = rules.replace('    tcp dport 22 drop',
                                  '    tcp dport 22 iifname "wlan0" ip saddr @halls_enrollment accept\n'
                                  '    tcp dport 22 drop')
    rules = rules.replace(' accept\n', ' counter accept\n').replace(' drop\n', ' counter drop\n')
    old = subprocess.run(['nft', 'list', 'table', 'inet', 'desk_usb_ssh'],
                         capture_output=True, text=True, timeout=5)
    if old.returncode and 'No such file or directory' not in old.stderr:
        raise RuntimeError('Cannot inspect the owned guard')
    batch = ('delete table inet desk_usb_ssh\n' if old.returncode == 0 else '')+rules
    subprocess.run(['nft', '--check', '-f', '-'], input=batch, text=True, check=True, timeout=5)
    subprocess.run(['nft', '-f', '-'], input=batch, text=True, check=True, timeout=5)
    access.atomic_write(access.GUARD, rules)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--guard', action='store_true')
    parser.add_argument('--pin-owner')
    args = parser.parse_args()
    if os.geteuid() != 0:
        raise SystemExit('Run only as root on the prepared Pi')
    settings = json.loads(CONFIG.read_text())
    access = helper()
    settings['owner_hosts'] = [access.private_host(v) for v in settings['owner_hosts']]
    order = settings.get('network_order', ['VTC-Student', 'VTC-Halls'])
    if not order or len(set(order)) != len(order) or any(n not in ('VTC-Student', 'VTC-Halls') for n in order):
        raise ValueError('Select only the requested known networks')
    if args.pin_owner:
        settings['owner_hosts'] = [access.private_host(args.pin_owner)]
        access.atomic_write(CONFIG, json.dumps(settings)+'\n')
        WINDOW.unlink(missing_ok=True)
        if STATE.exists():
            access.atomic_write(ACK, json.dumps({'network': json.loads(STATE.read_text()).get('selected_network')}))
    if args.guard or args.pin_owner:
        apply_guard(settings, access)
        return
    trial = Trial(settings)
    trial.save('preflight')
    access.check_owner_auth()
    if not Path('/var/lib/desk-companion-provisioned').is_file():
        raise RuntimeError('Existing installation required; no reinstall')
    WINDOW.unlink(missing_ok=True)
    ACK.unlink(missing_ok=True)
    apply_guard(settings, access)
    backup = access.UNIT.with_name(access.UNIT.name+'.before-dorm')
    if not backup.exists():
        access.atomic_write(backup, access.UNIT.read_text())
    access.atomic_write(access.UNIT, '''[Unit]
Description=Desk Companion owner-key SSH on the selected network
Before=ssh.service
[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /usr/local/lib/desk-dorm-access.py --guard
RemainAfterExit=yes
''', 0o644)
    trial.require('daemon_reload', ['systemctl', 'daemon-reload'])
    trial.require('ssh_ready', ['systemctl', 'enable', '--now', 'ssh.service'])
    for name in ('FYP-VTC-Student', 'FYP-VTC-Halls'):
        staged = Path('/etc/desk-provision')/(name+'.nmconnection')
        if not staged.exists():
            continue
        target = Path('/etc/NetworkManager/system-connections')/staged.name
        old = target.with_name(target.name+'.before-dorm')
        if target.exists() and not old.exists():
            access.atomic_write(old, target.read_text())
        access.atomic_write(target, staged.read_text())
        staged.unlink()
        trial.require('load_'+name, ['nmcli', 'connection', 'load', str(target)])
    trial.require('radio_unblock', ['rfkill', 'unblock', 'wifi'])
    trial.require('radio_on', ['nmcli', 'radio', 'wifi', 'on'])
    for name in order:
        uuid = STUDENT if name == 'VTC-Student' else HALLS
        code = trial.run('connect_'+name, activation_command(name, uuid), 55)
        if code:
            log = (PRIVATE/('connect_'+name+'.log')).read_text(errors='replace')
            reason = ('secrets_required' if 'Secrets were required' in log else
                      'timeout' if code == 124 else 'activation_failed')
            trial.save('activation_failed', failed_network=name, failure_reason=reason)
            trial.run('stop_'+name, ['nmcli', '--wait', '5', 'connection', 'down', 'uuid', uuid], 10)
            continue
        trial.save('connected', selected_network=name)
        if name == 'VTC-Halls':
            prefixes = [p for i in addresses() if i['name'] == 'wlan0' for p in i['prefixes']]
            if prefixes:
                access.atomic_write(WINDOW, json.dumps({'network': guarded_halls_network(prefixes[0]),
                                                        'expires_monotonic': time.monotonic()+600}))
                apply_guard(settings, access)
                trial.save('halls_owner_key_enrollment', enrollment_seconds=600)
        trial.save('awaiting_owner_verification', selected_network=name)
        connectivity = internet_probe(access) if settings.get('diagnostics') else {}
        trial.save('connectivity_probe_done', connectivity=connectivity)
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            for _ in range(30 if settings.get('diagnostics') else 10):
                message = {'trial': settings['trial_id'], 'network': name,
                           'interfaces': addresses(), 'phase': trial.data['phase'],
                           'failed_network': trial.data.get('failed_network'),
                           'failure_reason': trial.data.get('failure_reason')}
                if settings.get('diagnostics'):
                    message['diagnostics'] = runtime_diagnostics()
                    message['connectivity'] = connectivity
                encoded = json.dumps(message).encode()
                for host in settings['owner_hosts']:
                    try:
                        sock.sendto(encoded, (host, 8892))
                    except OSError:
                        pass
                time.sleep(2)
        if name == 'VTC-Student' and not settings.get('keep_student_without_owner'):
            deadline = time.monotonic()+120
            while time.monotonic() < deadline:
                if ACK.exists() and json.loads(ACK.read_text()).get('network') == name:
                    break
                time.sleep(1)
            else:
                trial.save('student_owner_unreachable', selected_network=None)
                trial.run('stop_student', ['nmcli', '--wait', '5', 'connection', 'down', 'uuid', uuid], 10)
                continue
        trial.require('keep_selected', ['nmcli', 'connection', 'modify', uuid,
                                       'connection.autoconnect', 'yes'])
        trial.save('selected_network_ready', selected_network=name,
                   owner_confirmed=ACK.exists(), portal_verified=False)
        return
    trial.save('both_connections_failed')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # No exception arguments: external commands or file text may contain
        # private account information. Per-command raw logs remain root-only.
        if BOOT_STATE.exists():
            state = json.loads(BOOT_STATE.read_text())
            state['error_type'] = type(error).__name__
            for path in (STATE, BOOT_STATE):
                helper().atomic_write(path, json.dumps(state)+'\n')
        raise SystemExit('Dorm setup stopped; read the saved phase and private log') from None
