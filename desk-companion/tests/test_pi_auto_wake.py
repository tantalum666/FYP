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


@pytest.mark.parametrize('stale', [0, 1950, OSError(errno.EIO, 'transient initial read')])
def test_stale_initial_read_does_not_orphan_an_owned_alarm(renewing, stale):
    rtc, state = renewing
    rtc.reads = [stale, 1180]
    assert change_alarm(rtc, state)['wake_at'] == 1210
    saved = json.loads(state.read_text())
    assert saved['initial'][-1] == {'value': 1180}
    assert len(saved['initial']) == 2 and saved['owned'] == [1210]
    assert rtc.writes == ['+=30']


@pytest.mark.parametrize(
    ('now', 'previous_verified', 'recorded_now'),
    [
        (16, 1795421401, 1795421221),  # 2026 -> a reset RTC near the Unix epoch.
        (16, 1795421401, None),       # Earlier two-value ownership format.
        (1000, 1200, 1020),           # Backwards clock step within the 900-second limit.
        (16, 917, None),              # One second beyond the largest supported delay.
    ],
)
def test_empty_slot_never_restores_a_previous_clock_deadline(
    tmp_path, now, previous_verified, recorded_now
):
    state = tmp_path / 'alarm.json'
    saved = {'owned': [previous_verified, previous_verified + 30]}
    if recorded_now is not None:
        saved.update(verified=previous_verified, rtc_now=recorded_now)
    state.write_text(json.dumps(saved))
    rtc = Rtc(now=now)
    original_write = rtc.set_alarm

    def lose_current_target(value):
        if value == now + 180:
            rtc.writes.append(value)
        else:
            original_write(value)

    rtc.set_alarm = lose_current_target
    with pytest.raises(RuntimeError, match='readback'):
        change_alarm(rtc, state)
    assert previous_verified not in rtc.writes
    assert rtc.value == 0
    assert json.loads(state.read_text())['verified'] == 0


def test_in_window_legacy_fallback_at_supported_maximum_is_preserved(tmp_path):
    rtc = Rtc(now=16)
    state = tmp_path / 'alarm.json'
    state.write_text(json.dumps({'owned': [916, 946]}))
    original_write = rtc.set_alarm

    def lose_primary(value):
        if value == 196:
            rtc.writes.append(value)
        else:
            original_write(value)

    rtc.set_alarm = lose_primary
    with pytest.raises(RuntimeError, match='previous_restored'):
        change_alarm(rtc, state)
    assert rtc.value == 916 and rtc.writes == [196, 916]


def test_ntp_forward_retargets_our_still_enabled_prior_alarm_without_clearing(tmp_path):
    rtc = Rtc(now=16)
    state = tmp_path / 'alarm.json'
    assert change_alarm(rtc, state)['wake_at'] == 196
    rtc.time = 1795439481
    rtc.writes.clear()
    normal_write = rtc.set_alarm

    def kernel_enabled_slot(value):
        if not isinstance(value, str) and value > 0 and rtc.value:
            raise OSError(errno.EBUSY, 'enabled hardware slot')
        normal_write(value)

    rtc.set_alarm = kernel_enabled_slot
    target = rtc.time + 180
    assert change_alarm(rtc, state)['wake_at'] == target
    assert rtc.writes == [f'+={target - 196}']


@pytest.mark.parametrize(
    ('now', 'external_deadline'),
    [(16, 266), (16, 1795421402), (1795439481, 1795439731)],
)
def test_foreign_future_alarm_is_preserved_across_clock_generations(tmp_path, now, external_deadline):
    state = tmp_path / 'alarm.json'
    state.write_text(json.dumps({'owned': [1795421401], 'verified': 1795421401, 'rtc_now': 1795421221}))
    rtc = Rtc(now, external_deadline)
    for disarm in [False, True]:
        with pytest.raises(RuntimeError, match='Another RTC alarm'):
            change_alarm(rtc, state, disarm=disarm)
    assert rtc.value == external_deadline and rtc.writes == []


def test_far_owned_alarm_is_retargetable_without_ever_becoming_a_fallback(tmp_path):
    prior = 1795421401
    state = tmp_path / 'alarm.json'
    state.write_text(json.dumps({'owned': [prior], 'verified': prior, 'rtc_now': prior - 180}))
    rtc = Rtc(16, prior)
    real_write = rtc.set_alarm
    rtc.set_alarm = rtc.writes.append
    with pytest.raises(RuntimeError, match='readback_mismatch'):
        change_alarm(rtc, state)
    rejected = json.loads(state.read_text())
    assert rejected['verified'] == 0 and rejected['rejected_fallback'] == prior
    assert rtc.value == prior and prior in rejected['owned']

    rtc.set_alarm = real_write
    rtc.time = 46
    assert change_alarm(rtc, state)['wake_at'] == 226
    assert rtc.writes == [f'+={196-prior}', f'+={226-prior}']


def test_explicit_disarm_can_clear_identified_prior_domain_alarm(tmp_path):
    prior = 1795421401
    state = tmp_path / 'alarm.json'
    state.write_text(json.dumps({'owned': [prior], 'verified': prior, 'rtc_now': prior - 180}))
    rtc = Rtc(16, prior)
    assert not change_alarm(rtc, state, disarm=True)['enabled']
    assert rtc.writes == [0] and rtc.value == 0


def test_clock_step_before_arming_stops_without_writing(tmp_path, monkeypatch):
    state = tmp_path / 'alarm.json'
    rtc = Rtc(16)
    save = auto_wake.save_state

    def synchronize(path, record):
        save(path, record)
        if record['outcome'] == 'pending':
            rtc.time = 1795439481

    monkeypatch.setattr(auto_wake, 'save_state', synchronize)
    with pytest.raises(RuntimeError, match='clock changed before'):
        change_alarm(rtc, state)
    assert not rtc.writes
    assert change_alarm(rtc, state)['wake_at'] == 1795439661


def test_clock_step_after_writing_cannot_confirm_an_expired_target(tmp_path):
    state = tmp_path / 'alarm.json'
    rtc = Rtc(16)
    real_write = rtc.set_alarm

    def synchronize_after_write(value):
        real_write(value)
        rtc.time = 1795439481

    rtc.set_alarm = synchronize_after_write
    with pytest.raises(RuntimeError, match='clock changed during readback'):
        change_alarm(rtc, state)
    assert rtc.writes == [196] and json.loads(state.read_text())['verified'] == 0
    assert change_alarm(rtc, state)['wake_at'] == 1795439661


def test_clock_reset_while_restoring_cannot_claim_decades_of_wake_delay(tmp_path):
    state = tmp_path / 'alarm.json'
    old = 1795421401
    rtc = Rtc(old - 180)
    assert change_alarm(rtc, state)['wake_at'] == old
    rtc.time += 30
    rtc.writes.clear()
    real_write = rtc.set_alarm

    def failed_move_then_clock_reset(value):
        if isinstance(value, str):
            rtc.writes.append(value)
            rtc.value = 0
        else:
            real_write(value)
            rtc.time = 16

    rtc.set_alarm = failed_move_then_clock_reset
    with pytest.raises(RuntimeError, match='clock changed during fallback'):
        change_alarm(rtc, state)
    saved = json.loads(state.read_text())
    assert rtc.writes == ['+=30', old] and saved['verified'] == 0
    assert saved['outcome'] == 'clock_changed_during_restore'
