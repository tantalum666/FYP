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
import time


class Rtc:
    def __init__(self, path=Path('/sys/class/rtc/rtc0')):
        self.path = path

    def now(self):
        return int((self.path / 'since_epoch').read_text().strip())

    def alarm(self):
        return int((self.path / 'wakealarm').read_text().strip() or '0')

    def set_alarm(self, value):
        (self.path / 'wakealarm').write_text(str(value) + '\n')


def save_state(path, state):
    """Persist intent before changing hardware so interrupted renewal can recover."""
    with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False) as file:
        temporary = Path(file.name)
        try:
            os.fchmod(file.fileno(), 0o600)
            json.dump(state, file)
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


# A transient empty sysfs read or a firmware read error is followed by two more
# observations. Stop on the first exact match, without repeating the RTC write.
READ_DELAYS = (0, 0.05, 0.15)


def read_alarm(rtc, accepted=None):
    observations = []
    for delay in READ_DELAYS:
        if delay:
            time.sleep(delay)
        try:
            value = rtc.alarm()
        except (OSError, ValueError) as exc:
            observations.append({'error': type(exc).__name__, 'errno': getattr(exc, 'errno', None)})
        else:
            observations.append({'value': value})
            if accepted is None or value in accepted:
                break
    return observations


def write_alarm(rtc, value):
    try:
        rtc.set_alarm(value)
    except OSError as exc:
        # A driver may have applied a write before returning an error.
        return {'error': type(exc).__name__, 'errno': exc.errno}
    return None


def record_failure(path, state, message):
    save_state(path, state)
    raise RuntimeError(message + ' ' + json.dumps(state, separators=(',', ':')))


def change_alarm(rtc, state_path, *, delay=180, disarm=False):
    if not 60 <= delay <= 900:
        raise ValueError('Wake delay must be between 60 and 900 seconds')
    state_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (state_path.parent / 'lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        saved = json.loads(state_path.read_text()) if state_path.exists() else {'owned': []}
        owned = saved['owned']
        if not isinstance(owned, list) or any(type(value) is not int for value in owned):
            raise ValueError('Invalid RTC ownership record')
        # In the old two-value format the first value was actually read and the
        # second was write intent. A pending target is never a fallback by itself.
        last_good = saved.get('verified', owned[0] if owned else 0)
        if type(last_good) is not int or (last_good and last_good not in owned):
            raise ValueError('Invalid verified RTC ownership record')

        now = rtc.now()
        target = 0 if disarm else now + delay
        # With a live ownership record, a single empty/stale initial read must
        # not orphan our deadline. An actual foreign alarm is only observed.
        live_owned = {value for value in owned if value > now}
        initial = read_alarm(rtc, live_owned or None)
        previous = initial[-1].get('value')
        state = {'owned': owned, 'verified': last_good, 'previous_verified': last_good,
                 'rtc_now': now, 'expected': target,
                 'initial': initial}
        if previous is None:
            state['outcome'] = 'initial_read_failed'
            record_failure(state_path, state, 'RTC alarm could not be read')
        if previous > now and previous not in owned:
            state.update(owned=[], verified=0, outcome='foreign_alarm_preserved')
            record_failure(state_path, state, 'Another RTC alarm is active; it was not replaced')

        if previous > now:
            last_good = previous
        elif last_good <= now:
            last_good = 0
        state.update(owned=sorted({n for n in (last_good, target) if n}), verified=last_good,
                     outcome='pending')
        save_state(state_path, state)
        if previous != target:
            # The durable intent write can take time. Recheck ownership before
            # touching the register; an unrecognised value belongs to its writer.
            before_write = read_alarm(rtc, (previous,))
            if before_write[-1].get('value') != previous:
                state.update(owned=owned, verified=saved.get('verified', owned[0] if owned else 0),
                             before_write=before_write, outcome='changed_before_write')
                record_failure(state_path, state, 'RTC alarm changed before our write')
            # Linux wakealarm supports extending an active alarm in one store.
            # An absolute write to an empty slot refuses an already active alarm.
            value = f'+={target - previous}' if target and previous > now else target
            error = write_alarm(rtc, value)
            if error:
                state['write_error'] = error

        observations = read_alarm(rtc, (target,))
        observed = observations[-1].get('value')
        state['readback'] = observations
        if observed == target:
            state.update(owned=[target] if target else [], verified=target, outcome='verified')
            save_state(state_path, state)
            return {'enabled': not disarm, 'rtc_now': now, 'wake_at': target,
                    'readback': observations}

        if observed == 0 and not disarm and last_good > rtc.now():
            # Restore only the last verified owned deadline to an empty slot.
            # Never clear here: Linux rejects this absolute write if a foreign
            # writer installed another alarm since our read.
            error = write_alarm(rtc, last_good)
            if error:
                state['restore_error'] = error
            state['restore_readback'] = read_alarm(rtc, (last_good,))
            restored = state['restore_readback'][-1].get('value')
            if restored == last_good:
                state.update(owned=[last_good], verified=last_good, outcome='previous_restored')
            else:
                state['outcome'] = 'restore_unconfirmed'
                if restored is not None and restored > now and restored not in state['owned']:
                    state.update(owned=[], verified=0)
        elif observed is None:
            state['outcome'] = 'readback_unavailable'
        elif observed == last_good and last_good:
            state.update(owned=[last_good], verified=last_good, outcome='previous_retained')
        elif observed > now and observed not in state['owned']:
            state.update(owned=[], verified=0, outcome='foreign_alarm_preserved')
        else:
            state['outcome'] = 'readback_mismatch'
        record_failure(state_path, state, 'RTC alarm readback did not match')


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
