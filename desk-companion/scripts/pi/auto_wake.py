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
MAX_WAKE_DELAY = 900


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


def in_wake_window(deadline, now, verified_at):
    # A saved absolute timestamp may belong to an RTC epoch that lost power.
    return (verified_at is None or verified_at <= now) and 0 < deadline - now <= MAX_WAKE_DELAY


def change_alarm(rtc, state_path, *, delay=180, disarm=False):
    if not 60 <= delay <= MAX_WAKE_DELAY:
        raise ValueError(f'Wake delay must be between 60 and {MAX_WAKE_DELAY} seconds')
    state_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (state_path.parent / 'lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        saved = json.loads(state_path.read_text()) if state_path.exists() else {'owned': []}
        owned = saved['owned']
        if not isinstance(owned, list) or any(type(value) is not int for value in owned):
            raise ValueError('Invalid RTC ownership record')
        # In the old two-value format the first value was actually read and the
        # second was write intent. A pending target is never a fallback by itself.
        previous_verified = saved.get('verified', owned[0] if owned else 0)
        if type(previous_verified) is not int or (previous_verified and previous_verified not in owned):
            raise ValueError('Invalid verified RTC ownership record')

        # Older two-value files have no clock sample; the horizon still applies.
        # Keep the verified sample independent of later unsuccessful attempts.
        verified_at = saved.get('verified_at', saved.get('rtc_now'))
        if verified_at is not None and type(verified_at) is not int:
            raise ValueError('Invalid RTC verification time')
        now = rtc.now()
        target = 0 if disarm else now + delay
        retained_verified = previous_verified if in_wake_window(previous_verified, now, verified_at) else 0
        # With a live ownership record, a single empty/stale initial read must
        # not orphan our deadline. An actual foreign alarm is only observed.
        live_owned = {value for value in owned if value > now}
        initial = read_alarm(rtc, live_owned or None)
        previous = initial[-1].get('value')
        state = {'owned': owned, 'verified': retained_verified, 'previous_verified': previous_verified,
                 'previous_verified_at': verified_at, 'verified_at': verified_at if retained_verified else None,
                 'rtc_now': now, 'expected': target,
                 'initial': initial}
        if previous is None:
            state['outcome'] = 'initial_read_failed'
            record_failure(state_path, state, 'RTC alarm could not be read')
        if previous > now and previous not in owned:
            state.update(owned=[], verified=0, verified_at=None, outcome='foreign_alarm_preserved')
            record_failure(state_path, state, 'Another RTC alarm is active; it was not replaced')

        # Ownership permits an in-place retarget of an enabled register after
        # an NTP step. It does not make that stale deadline a useful fallback.
        active_owned = previous if previous in owned else 0
        last_good = active_owned or previous_verified
        if last_good and not in_wake_window(last_good, now, verified_at):
            state['rejected_fallback'] = last_good
            last_good = 0
        state.update(owned=sorted({n for n in (active_owned, last_good, target) if n}),
                     verified=last_good, verified_at=now if last_good else None, outcome='pending')
        save_state(state_path, state)
        if previous != target:
            # The durable intent write can take time. Recheck ownership before
            # touching the register; an unrecognised value belongs to its writer.
            before_write = read_alarm(rtc, (previous,))
            if before_write[-1].get('value') != previous:
                state.update(owned=owned, verified=retained_verified, verified_at=verified_at if retained_verified else None,
                             before_write=before_write, outcome='changed_before_write')
                record_failure(state_path, state, 'RTC alarm changed before our write')
            write_now = rtc.now()
            if target and not in_wake_window(target, write_now, now):
                state.update(owned=owned, verified=retained_verified, verified_at=verified_at if retained_verified else None,
                             observed_rtc_now=write_now, outcome='clock_changed_before_write')
                record_failure(state_path, state, 'RTC clock changed before our write')
            # Linux wakealarm supports extending an active alarm in one store.
            # An absolute write to an empty slot refuses an already active alarm.
            value = f'+={target - active_owned}' if target and active_owned else target
            error = write_alarm(rtc, value)
            if error:
                state['write_error'] = error

        observations = read_alarm(rtc, (target,))
        observed = observations[-1].get('value')
        state['readback'] = observations
        observed_now = rtc.now()
        if observed == target:
            if target and not in_wake_window(target, observed_now, now):
                state.update(observed_rtc_now=observed_now, verified=0, verified_at=None,
                             outcome='clock_changed_during_write')
                record_failure(state_path, state, 'RTC clock changed during readback')
            state.update(owned=[target] if target else [], verified=target,
                         verified_at=observed_now if target else None, outcome='verified')
            save_state(state_path, state)
            return {'enabled': not disarm, 'rtc_now': now, 'wake_at': target,
                    'readback': observations}

        if last_good and not in_wake_window(last_good, observed_now, now):
            state.update(rejected_fallback=last_good, observed_rtc_now=observed_now, verified=0, verified_at=None)
            last_good = 0
        if observed == 0 and not disarm and last_good:
            # Restore only the last verified owned deadline to an empty slot.
            # Never clear here: Linux rejects this absolute write if a foreign
            # writer installed another alarm since our read.
            error = write_alarm(rtc, last_good)
            if error:
                state['restore_error'] = error
            state['restore_readback'] = read_alarm(rtc, (last_good,))
            restored = state['restore_readback'][-1].get('value')
            if restored == last_good:
                restore_now = rtc.now()
                if not in_wake_window(last_good, restore_now, observed_now):
                    state.update(observed_rtc_now=restore_now, verified=0, verified_at=None,
                                 outcome='clock_changed_during_restore')
                    record_failure(state_path, state, 'RTC clock changed during fallback readback')
                state.update(owned=[last_good], verified=last_good, verified_at=restore_now, outcome='previous_restored')
            else:
                state['outcome'] = 'restore_unconfirmed'
                if restored is not None and restored > now and restored not in state['owned']:
                    state.update(owned=[], verified=0, verified_at=None)
        elif observed is None:
            state['outcome'] = 'readback_unavailable'
        elif observed == last_good and last_good:
            state.update(owned=[last_good], verified=last_good, verified_at=observed_now, outcome='previous_retained')
        elif observed > now and observed not in state['owned']:
            state.update(owned=[], verified=0, verified_at=None, outcome='foreign_alarm_preserved')
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
