"""Shared 5-byte rack-bus frame transport.

Replaces ~18 copies of sendReg() that were scattered across DFBx2/, BADASS/,
emu_card.py, and cringe.py. The wire format is identical across every card
that talks to the rack bus: four 7-bit payload bytes (each shifted up by 1)
carrying a 25-bit register value, followed by a fifth byte containing the
card address shifted up by 1 with the LSB set as a frame marker.

A module-level lock serializes writes so that concurrent callers (GUI
thread, ZMQ thread, scripts) cannot interleave 5-byte frames on the
physical bus. The lock is held across the write *and* the post-write
sleep so that the hardware-mandated quiet period is respected even
under contention. 

This module deliberately does NOT depend on Qt and is safe to import
and call from any thread. This does not mean you should import this 
yourself while CRINGE is running.
"""
import struct
import threading
import time

from cringe.shared import terminal_colors as tc
from cringe.shared import log


# One lock for the entire rack bus. Every write to the crate
# goes through here, so ensure if multiple threads are 
# talking to the crate at once they don't interrupt each other
# or violate the 1 ms send delay.
_rack_lock = threading.Lock()


def write_wreg(serialport, wregval, address, sleep_after=0.001):
    """Send one 25-bit register value to ``address`` on the rack bus.

    Parameters
    ----------
    serialport : object with a .write(bytes) method
        Typically a ``named_serial.Serial`` configured for ``port='rack'``.
    wregval : int
        25-bit register value + 3 most significant bits encoding the
        register index (e.g. ``3 << 25`` for WREG3); the lower 25 bits
        carry the per-register payload. The exact bit layout is
        card-specific and is the caller's responsibility.
    address : int
        7-bit card address on the rack bus.
    sleep_after : float, optional
        Seconds to sleep after the write, holding the bus lock. Defaults
        to 0.001 (the value used by most pre-refactor sendReg copies).
        Pass 0 to skip the sleep, matching the handful of pre-refactor
        sendReg copies that had no post-write delay (badrap, dprcal,
        dprS, dprS_counter, dfbcard_mm, badchn_builder, emu_card).
        Though it is unclear why some writes delayed and others did not. 
        Some of these, e.g. dfbcard_mm were never imported or used anywhere.

    Notes
    -----
    Thread-safe. Blocks for at most ``sleep_after`` seconds plus the
    serial write itself. Callers must NOT hold any Qt locks or block
    the GUI event loop while calling this.
    """
    log.debug(tc.COMMAND + "send to address", address, ":",
              tc.BOLD, wregval, tc.ENDC)
    b0 = (wregval & 0x7f) << 1            # bits  0-6,  shifted up 1
    b1 = ((wregval >> 7) & 0x7f) << 1     # bits  7-13, shifted up 1
    b2 = ((wregval >> 14) & 0x7f) << 1    # bits 14-20, shifted up 1
    b3 = ((wregval >> 21) & 0x7f) << 1    # bits 21-24 and register index
    b4 = (address << 1) + 1               # address shifted up 1, LSB = address bit
    msg = struct.pack("BBBBB", b0, b1, b2, b3, b4)

    with _rack_lock:
        serialport.write(msg)
        if sleep_after:
            time.sleep(sleep_after)
