#!/usr/bin/env python3
"""Maintain an owned RTC wake alarm without changing clocks or power protection.

Run only after opt-in and device-level RTC wake acceptance. A systemd timer can
renew the alarm while Linux is alive; the RTC, not this process, wakes a halted Pi.
"""

import argparse
import fcntl
import json
import os
from pathlib import Path
import tempfile


class Rtc:
    def __init__(self, path=Path('/sys/class/rtc/rtc0')):
        self.path = path

    def now(self):
        return int((self.path / 'since_epoch').read_text().strip())

    def alarm(self):
        return int((self.path / 'wakealarm').read_text().strip() or '0')

    def set_alarm(self, value):
        (self.path / 'wakealarm').write_text(str(value) + '\n')


def save_state(path, owned):
    """Persist intent before changing hardware so interrupted renewal can recover."""
    with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False) as file:
        temporary = Path(file.name)
        try:
            os.fchmod(file.fileno(), 0o600)
            json.dump({'owned': owned}, file)
            file.flush()
            os.fsync(file.fileno())
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    try:
        temporary.replace(path)
        descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    finally:
        temporary.unlink(missing_ok=True)


def change_alarm(rtc, state_path, *, delay=180, disarm=False):
    if not 60 <= delay <= 900:
        raise ValueError('Wake delay must be between 60 and 900 seconds')
    state_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (state_path.parent / 'lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        owned = json.loads(state_path.read_text())['owned'] if state_path.exists() else []
        if not isinstance(owned, list) or any(type(value) is not int for value in owned):
            raise ValueError('Invalid RTC ownership record')
        now, previous = rtc.now(), rtc.alarm()
        if previous > now and previous not in owned:
            raise RuntimeError('Another RTC alarm is active; it was not replaced')
        target = 0 if disarm else now + delay
        save_state(state_path, [previous, target])
        rtc.set_alarm(0)
        if target:
            rtc.set_alarm(target)
        if rtc.alarm() != target:
            raise RuntimeError('RTC alarm readback did not match')
        return {'enabled': not disarm, 'rtc_now': now, 'wake_at': target}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['arm', 'disarm'])
    parser.add_argument('--delay', type=int, default=180)
    args = parser.parse_args()
    print(json.dumps(change_alarm(
        Rtc(), Path('/var/lib/desk-auto-wake/alarm.json'),
        delay=args.delay, disarm=args.action == 'disarm',
    )))


if __name__ == '__main__':
    main()
