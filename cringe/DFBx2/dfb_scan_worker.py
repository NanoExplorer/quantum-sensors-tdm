import threading
import time

from PyQt5.QtCore import QObject, pyqtSignal

from cringe.shared.rack_transport import write_wreg_sequence


class DfbScanWorker(QObject):
    """Continuously flushes pending DFB channel state to hardware off the GUI thread.

    The worker scans all registered dfbChn state-vector objects in order.  For each
    channel that has pending wreg flags set, it clears the flags and writes only the
    dirty wregs (always preceded by wreg0 as the page-select), all under a single
    rack-bus lock so no other caller can interleave between the page-select and data
    writes.

    Channels are written with whatever instance-variable values are current at write
    time.  If the user keeps scrolling, channels visited later in the scan get more
    recent values. I make the analogy to screen-tearing if you are writing data
    to your monitor with vertical synchronization off. There could be a visible
    "tear" on screen when the bottom half of the monitor contains more recent
    data than the top half. After the user stops, the next full idle
    pass guarantees all channels have converged to the final value.
    """

    error = pyqtSignal(str)

    def __init__(self, channels):
        super().__init__()
        self._channels = channels   # list of dfbChn (state_vectors only, never master_vectors
        # since those don't correspond to actual hardware)
        self._running = False

        # Flush-sync support: callers can block until the worker completes a full
        # idle pass (no pending writes remain).
        self._flush_done = threading.Condition()

    def run(self):
        self._running = True
        while self._running:
            if not self._scan_once():
                # the scanner checked all the pendings, found nothing.
                with self._flush_done:
                    self._flush_done.notify_all()
                time.sleep(0.005)   # 5 ms sleep when nothing pending
                # Just makes sure that we don't waste ALL the cpu time.
                # also lets other threads do work (releasing the python GIL) 

    def _scan_once(self):
        wrote_any = False
        for ch in self._channels:
            if not ch.unlocked:
                continue
            p1 = ch.pending_wreg1
            p2 = ch.pending_wreg2
            p3 = ch.pending_wreg3
            p5 = ch.pending_wreg5
            if not (p1 or p2 or p3 or p5):
                continue
            # Clear before writing: any new change arriving during the write 
            # will re-set the flag and be caught on the next scan pass.
            ch.pending_wreg1 = False
            ch.pending_wreg2 = False
            ch.pending_wreg3 = False
            ch.pending_wreg5 = False
            try:
                if ch.pending_relock:
                    # If the user has clicked the fba button twice in quick succession
                    # or muxmaster relock was used
                    # we need to write a "feedback off" followed by 
                    # updating feedback to whatever the user requested at the end of the day
                    ch.pending_relock = False
                    wregvals = [ch._build_wreg0()]
                    wregvals.append(0x6000000) 
                    # hardcoded wreg3: FBA off. FBB off.
                    # ARL off. P=0, I=0.
                    # These will all be rewritten in the next step
                    write_wreg_sequence(ch.serialport, wregvals, ch.address)

                wregvals = [ch._build_wreg0()]
                if p1:
                    wregvals.append(ch._build_wreg1())
                if p2:
                    wregvals.append(ch._build_wreg2())
                if p3:
                    wregvals.append(ch._build_wreg3())
                if p5:
                    wregvals.append(ch._build_wreg5())
                write_wreg_sequence(ch.serialport, wregvals, ch.address)
                wrote_any = True
            except Exception as e:
                self.error.emit(str(e))
        return wrote_any

    def flush_sync(self, timeout=10.0):
        """Block the calling thread until the worker completes a full idle pass.

        Safe to call from any thread (including the GUI thread — but note that
        doing so from the GUI thread will stall the event loop for up to one full
        scan cycle, which is ~500 ms if you have 4 DFBx2 cards at seqln=30).
        Returns True if flush completed within timeout, False otherwise.
        """

        with self._flush_done:
            status = self._flush_done.wait(timeout)
            # 'wait' releases the lock that the condition was created with
            # and blocks until timeout (remaining) or a call to notify or notify_all
            # If the timeout expired, status will be False 
        return status

    def stop(self):
        self._running = False
