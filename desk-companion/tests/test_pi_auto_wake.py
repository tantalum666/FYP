import pytest

from scripts.pi.auto_wake import change_alarm


class Rtc:
    def __init__(self, now=1000, alarm=0):
        self.time = now
        self.value = alarm
        self.writes = []
        self.fail_next_set = False

    def now(self):
        return self.time

    def alarm(self):
        return self.value

    def set_alarm(self, value):
        self.writes.append(value)
        if self.fail_next_set and value:
            self.fail_next_set = False
            raise OSError('interrupted renewal')
        self.value = value


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
    rtc.fail_next_set = True
    with pytest.raises(OSError):
        change_alarm(rtc, path)
    assert rtc.value == 0
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
