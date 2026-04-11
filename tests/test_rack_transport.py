"""Tests for cringe.shared.rack_transport.write_wreg.

These pin down the wire format that was previously implemented (and
duplicated) in ~18 sendReg copies across cringe/. If a future change to
write_wreg alters the bytes on the wire, these tests fail loudly.
"""
import struct
from unittest import mock

import pytest

from cringe.shared.rack_transport import write_wreg


class FakeSerial:
    """Minimal stand-in for named_serial.Serial. Records every write."""

    def __init__(self):
        self.writes = []

    def write(self, data):
        self.writes.append(bytes(data))
        return len(data)


def _legacy_pack(wregval, address):
    """Verbatim copy of the byte-pack used by every pre-refactor sendReg.

    Kept here so the test asserts equivalence against the old formula
    rather than just against itself. If write_wreg ever drifts from the
    pre-refactor wire format, this comparison fails.
    """
    b0 = (wregval & 0x7f) << 1
    b1 = ((wregval >> 7) & 0x7f) << 1
    b2 = ((wregval >> 14) & 0x7f) << 1
    b3 = ((wregval >> 21) & 0x7f) << 1
    b4 = (address << 1) + 1
    return struct.pack("BBBBB", b0, b1, b2, b3, b4)


def test_writes_exactly_five_bytes():
    s = FakeSerial()
    write_wreg(s, wregval=0, address=0, sleep_after=0)
    assert len(s.writes) == 1
    assert len(s.writes[0]) == 5


def test_zero_value_zero_address():
    s = FakeSerial()
    write_wreg(s, wregval=0, address=0, sleep_after=0)
    # b4 = (0 << 1) + 1 = 1
    assert s.writes[0] == b"\x00\x00\x00\x00\x01"


def test_max_value_max_address():
    s = FakeSerial()
    # 25-bit max payload, 7-bit max address
    write_wreg(s, wregval=0x1FFFFFF, address=0x7F, sleep_after=0)
    # b3 = ((0x1FFFFFF >> 21) & 0x7f) << 1 = 0xF << 1 = 0x1E
    # b4 = (0x7F << 1) + 1 = 0xFF
    assert s.writes[0] == b"\xFE\xFE\xFE\x1E\xFF"


def test_dfb_wreg3_known_payload():
    """A real DFB WREG3 call with I=10, everything else zero, address=3."""
    s = FakeSerial()
    wregval = (3 << 25) | (10 & 0x3FF)  # 0x0600000A
    write_wreg(s, wregval=wregval, address=3, sleep_after=0)
    assert s.writes[0] == b"\x14\x00\x00\x60\x07"


def test_dfb_wreg0_known_payload():
    """DFB WREG0 (page index) for chn=2, state=5, address=3."""
    s = FakeSerial()
    wregval = (2 << 6) | 5  # 0x85
    write_wreg(s, wregval=wregval, address=3, sleep_after=0)
    assert s.writes[0] == b"\x0A\x02\x00\x00\x07"


@pytest.mark.parametrize("wregval", [
    0, 1, 0x7f, 0x80, 0xff, 0x3fff, 0x1fffff, 0xffffff, 0x1ffffff,
    0x06000000, 0x02000000, 0x0a000000, 0x12345,
])
@pytest.mark.parametrize("address", [0, 1, 3, 7, 0x3F, 0x7F])
def test_matches_legacy_pack(wregval, address):
    """write_wreg must produce the same bytes as the pre-refactor formula
    for every (wregval, address) we care about."""
    s = FakeSerial()
    write_wreg(s, wregval=wregval, address=address, sleep_after=0)
    assert s.writes[0] == _legacy_pack(wregval, address)


def test_default_sleep_after_is_one_millisecond():
    s = FakeSerial()
    with mock.patch("cringe.shared.rack_transport.time.sleep") as sleep_mock:
        write_wreg(s, wregval=0, address=0)
    sleep_mock.assert_called_once_with(0.001)


def test_sleep_after_zero_skips_sleep():
    s = FakeSerial()
    with mock.patch("cringe.shared.rack_transport.time.sleep") as sleep_mock:
        write_wreg(s, wregval=0, address=0, sleep_after=0)
    sleep_mock.assert_not_called()


def test_sleep_after_custom_value():
    s = FakeSerial()
    with mock.patch("cringe.shared.rack_transport.time.sleep") as sleep_mock:
        write_wreg(s, wregval=0, address=0, sleep_after=0.005)
    sleep_mock.assert_called_once_with(0.005)


def test_consecutive_writes_are_independent():
    s = FakeSerial()
    write_wreg(s, wregval=0x100, address=1, sleep_after=0)
    write_wreg(s, wregval=0x200, address=2, sleep_after=0)
    assert len(s.writes) == 2
    assert s.writes[0] == _legacy_pack(0x100, 1)
    assert s.writes[1] == _legacy_pack(0x200, 2)
