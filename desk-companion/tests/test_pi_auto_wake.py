import errno
import json

import pytest

from scripts.pi import auto_wake

from scripts.pi.auto_wake import change_alarm


class Rtc:
    def __init__(self, now=1000, alarm=0):
        self.time = now
        self.value = alarm
        self.writes = []
        self.fail_next_set = False
        self.after_write = []
        self.reads = []

    def now(self):
        return self.time

    def alarm(self):
        if self.reads:
            observation = self.reads.pop(0)
            if isinstance(observation, BaseException):
                raise observation
            return observation
        return self.value

    def set_alarm(self, value):
        self.writes.append(value)
        if self.fail_next_set and value:
            self.fail_next_set = False
            raise OSError('interrupted renewal')
        if isinstance(value, str):
            assert value.startswith('+=')
            if not self.value:
                raise OSError(errno.EINVAL, 'no alarm to move')
            self.value += int(value[2:])
        else:
            if value and self.value > self.time:
                raise OSError(errno.EBUSY, 'active alarm')
            self.value = value
        self.reads = self.after_write
        self.after_write = []


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(auto_wake.time, 'sleep', lambda _delay: None)


def test_renews_from_rtc_time_and_disarms_its_alarm(tmp_path):
    rtc = Rtc()
    path = tmp_path / 'state/alarm.json'
    assert change_alarm(rtc, path)['wake_at'] == 1180
    rtc.time = 1030
    assert change_alarm(rtc, path)['wake_at'] == 1210
    assert change_alarm(rtc, path, disarm=True)['enabled'] is False
    assert rtc.alarm() == 0


@pytest.mark.parametrize('disarm', [False, True])
def test_never_overwrites_another_future_alarm(tmp_path, disarm):
    rtc = Rtc(alarm=1400)
    with pytest.raises(RuntimeError, match='Another RTC alarm'):
        change_alarm(rtc, tmp_path / 'alarm.json', disarm=disarm)
    assert rtc.writes == []


def test_external_alarm_replacing_ours_is_preserved(tmp_path):
    rtc = Rtc()
    path = tmp_path / 'alarm.json'
    change_alarm(rtc, path)
    rtc.value = 1900
    with pytest.raises(RuntimeError, match='Another RTC alarm'):
        change_alarm(rtc, path)
    assert rtc.value == 1900


def test_interrupted_renewal_can_recover(tmp_path):
    rtc = Rtc()
    path = tmp_path / 'alarm.json'
    change_alarm(rtc, path)
    rtc.time = 1030
    rtc.fail_next_set = True
    with pytest.raises(RuntimeError, match='previous_retained'):
        change_alarm(rtc, path)
    assert rtc.value == 1180
    rtc.time = 1040
    assert change_alarm(rtc, path)['wake_at'] == 1220


def test_expired_alarm_does_not_block_new_boot(tmp_path):
    rtc = Rtc(alarm=990)
    assert change_alarm(rtc, tmp_path / 'alarm.json')['wake_at'] == 1180


def test_incorrect_hardware_readback_is_not_success(tmp_path):
    rtc = Rtc()
    rtc.set_alarm = lambda value: None
    with pytest.raises(RuntimeError, match='readback'):
        change_alarm(rtc, tmp_path / 'alarm.json')


@pytest.mark.parametrize('delay', [0, 59, 901])
def test_invalid_delay_does_not_touch_hardware(tmp_path, delay):
    rtc = Rtc()
    with pytest.raises(ValueError):
        change_alarm(rtc, tmp_path / 'alarm.json', delay=delay)
    assert not rtc.writes


@pytest.fixture
def renewing(tmp_path):
    rtc = Rtc()
    state = tmp_path / 'alarm.json'
    change_alarm(rtc, state)
    rtc.time = 1030
    rtc.writes.clear()
    return rtc, state


def test_empty_and_failed_reads_do_not_repeat_a_write(renewing):
    rtc, state = renewing
    rtc.after_write = [0, OSError(errno.EIO, 'private error text'), 1210, 9876]
    result = change_alarm(rtc, state)
    assert result['wake_at'] == 1210
    assert rtc.writes == ['+=30'] and rtc.reads == [9876]
    saved = json.loads(state.read_text())
    assert saved['owned'] == [1210] and saved['verified'] == 1210
    assert saved['readback'] == [
        {'value': 0}, {'error': 'OSError', 'errno': errno.EIO}, {'value': 1210},
    ]
    assert 'private error text' not in state.read_text()


def test_lost_replacement_restores_only_verified_earlier_deadline(renewing):
    rtc, state = renewing
    absolute_write = rtc.set_alarm

    def lose_replacement(value):
        if value == '+=30':
            rtc.writes.append(value)
            rtc.value = 0
        else:
            absolute_write(value)

    rtc.set_alarm = lose_replacement
    with pytest.raises(RuntimeError, match='previous_restored'):
        change_alarm(rtc, state)
    assert rtc.writes == ['+=30', 1180] and rtc.value == 1180
    saved = json.loads(state.read_text())
    assert saved['readback'] == [{'value': 0}] * len(auto_wake.READ_DELAYS)
    assert saved['restore_readback'] == [{'value': 1180}]
    assert saved['verified'] == 1180 and saved['owned'] == [1180]


def test_different_future_deadline_after_write_never_becomes_owned(renewing):
    rtc, state = renewing

    def replace_with_unexpected(value):
        rtc.writes.append(value)
        rtc.value = 1211

    rtc.set_alarm = replace_with_unexpected
    with pytest.raises(RuntimeError, match='foreign_alarm_preserved'):
        change_alarm(rtc, state)
    assert 1211 not in json.loads(state.read_text())['owned']
    with pytest.raises(RuntimeError, match='Another RTC alarm'):
        change_alarm(rtc, state, disarm=True)
    assert rtc.writes == ['+=30'] and rtc.value == 1211


def test_external_writer_wins_slot_before_rollback(renewing):
    rtc, state = renewing
    absolute_write = rtc.set_alarm

    def interfere(value):
        if value == '+=30':
            rtc.writes.append(value)
            rtc.value = 0
        else:
            rtc.value = 1900
            absolute_write(value)

    rtc.set_alarm = interfere
    with pytest.raises(RuntimeError, match='restore_unconfirmed'):
        change_alarm(rtc, state)
    saved = json.loads(state.read_text())
    assert rtc.value == 1900 and 0 not in rtc.writes and 1900 not in saved['owned']
    assert saved['restore_error']['errno'] == errno.EBUSY


def test_unreadable_register_never_triggers_blind_rollback(renewing):
    rtc, state = renewing
    rtc.after_write = [OSError(errno.EIO, 'read failed')] * len(auto_wake.READ_DELAYS)
    with pytest.raises(RuntimeError, match='readback_unavailable'):
        change_alarm(rtc, state)
    assert rtc.writes == ['+=30']
    assert json.loads(state.read_text())['owned'] == [1180, 1210]
    rtc.time = 1060
    assert change_alarm(rtc, state)['wake_at'] == 1240


@pytest.mark.parametrize('disarm', [False, True])
def test_foreign_change_between_intent_and_write_is_preserved(renewing, monkeypatch, disarm):
    rtc, state = renewing
    save = auto_wake.save_state

    def replace_after_intent(path, record):
        save(path, record)
        if record['outcome'] == 'pending':
            rtc.value = 1950

    monkeypatch.setattr(auto_wake, 'save_state', replace_after_intent)
    with pytest.raises(RuntimeError, match='changed before our write'):
        change_alarm(rtc, state, disarm=disarm)
    assert rtc.writes == [] and rtc.value == 1950
    assert 1950 not in json.loads(state.read_text())['owned']


def test_crash_after_write_recovers_with_legacy_ownership(tmp_path):
    state = tmp_path / 'alarm.json'
    state.write_text(json.dumps({'owned': [0, 1180]}))
    rtc = Rtc(1030, 1180)
    real_write = rtc.set_alarm

    def interrupted(value):
        real_write(value)
        raise KeyboardInterrupt()

    rtc.set_alarm = interrupted
    with pytest.raises(KeyboardInterrupt):
        change_alarm(rtc, state)
    assert rtc.value == 1210
    saved = json.loads(state.read_text())
    assert saved['outcome'] == 'pending' and set(saved['owned']) == {1180, 1210}
    rtc.set_alarm = real_write
    rtc.time = 1060
    assert change_alarm(rtc, state)['wake_at'] == 1240
    assert json.loads(state.read_text())['owned'] == [1240]


def test_disarm_rechecks_stale_value_and_never_rearms(renewing):
    rtc, state = renewing
    rtc.after_write = [1180, 0, 9999]
    assert change_alarm(rtc, state, disarm=True)['enabled'] is False
    assert rtc.writes == [0] and rtc.reads == [9999]
    assert json.loads(state.read_text())['owned'] == []


def test_previously_valid_alarm_is_not_restored_after_expiry(renewing):
    rtc, state = renewing
    rtc.time = 1179

    def expire(value):
        rtc.writes.append(value)
        rtc.value = 0
        rtc.time = 1181

    rtc.set_alarm = expire
    with pytest.raises(RuntimeError, match='readback_mismatch'):
        change_alarm(rtc, state)
    assert len(rtc.writes) == 1 and rtc.value == 0


def test_driver_error_after_applying_write_uses_readback_for_success(renewing):
    rtc, state = renewing
    do_write = rtc.set_alarm

    def applied_with_error(value):
        do_write(value)
        raise OSError(errno.EIO, 'reported after applying')

    rtc.set_alarm = applied_with_error
    assert change_alarm(rtc, state)['wake_at'] == 1210
    assert rtc.writes == ['+=30']
    assert json.loads(state.read_text())['write_error']['errno'] == errno.EIO


def test_initial_read_failure_preserves_legacy_owner_state(renewing):
    rtc, state = renewing
    state.write_text(json.dumps({'owned': [0, 1180]}))
    rtc.reads = [OSError(errno.EIO, 'unavailable')] * len(auto_wake.READ_DELAYS)
    with pytest.raises(RuntimeError, match='could not be read'):
        change_alarm(rtc, state)
    saved = json.loads(state.read_text())
    assert saved['owned'] == [0, 1180] and saved['outcome'] == 'initial_read_failed'
    assert len(saved['initial']) == len(auto_wake.READ_DELAYS) and rtc.writes == []


def test_disarming_an_unresponsive_owned_alarm_does_not_retry_writes(renewing):
    rtc, state = renewing
    rtc.set_alarm = rtc.writes.append
    with pytest.raises(RuntimeError, match='previous_retained'):
        change_alarm(rtc, state, disarm=True)
    assert rtc.value == 1180 and rtc.writes == [0]
    assert json.loads(state.read_text())['verified'] == 1180


def test_sysfs_adapter_serializes_absolute_and_active_relative_forms(tmp_path):
    from scripts.pi.auto_wake import Rtc as KernelRtc

    (tmp_path / 'since_epoch').write_text('1000\n')
    (tmp_path / 'wakealarm').write_text('1180\n')
    device = KernelRtc(tmp_path)
    assert (device.now(), device.alarm()) == (1000, 1180)
    device.set_alarm('+=30')
    assert (tmp_path / 'wakealarm').read_bytes() == b'+=30\n'
    device.set_alarm(1210)
    assert device.alarm() == 1210
    (tmp_path / 'wakealarm').write_bytes(b'')
    assert device.alarm() == 0


@pytest.mark.parametrize('register_lost', [False, True])
def test_disproved_intent_cannot_own_a_later_foreign_alarm(renewing, register_lost):
    rtc, state = renewing
    real_write = rtc.set_alarm

    def failed_move(value):
        if isinstance(value, str):
            rtc.writes.append(value)
            if register_lost:
                rtc.value = 0
        else:
            real_write(value)

    rtc.set_alarm = failed_move
    with pytest.raises(RuntimeError, match='previous_(retained|restored)'):
        change_alarm(rtc, state)
    assert json.loads(state.read_text())['owned'] == [1180]
    rtc.set_alarm = real_write
    # A different owner later selects the same epoch as our failed intent.
    rtc.value = 1210
    rtc.writes.clear()
    with pytest.raises(RuntimeError, match='Another RTC alarm'):
        change_alarm(rtc, state, disarm=True)
    assert rtc.value == 1210 and rtc.writes == []
    assert json.loads(state.read_text())['owned'] == []
