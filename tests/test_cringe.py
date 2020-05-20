from cringe import cringe
from cringe import zmq_rep
from PyQt5 import QtCore, QtWidgets
from named_serial import named_serial
import zmq
import time

named_serial._setup_for_testing({"rack" : "dummy_rack", "tower": "dummy_tower"})
cringe.log.set_debug()


def test_cringe(qtbot): # see pytest-qt for info qtbot
    widget = cringe.Cringe(None, addr_vector=[0, 1, 2], slot_vector=[0, 1, 2], 
    class_vector=["DFBCLK", "DFBx2", "BAD16"],
    seqln=13, lsync=32, tower_vector=["DB1", 13], calibrationtab=True)
    qtbot.addWidget(widget)

    assert widget.seqln == 13
    assert widget.lsync == 32
    assert widget.tune_widget._test_check_true

    qtbot.mouseClick(widget.sys_glob_send, QtCore.Qt.LeftButton)

def test_zmq_rep(qtbot):
    widget = zmq_rep.ZmqRep(parent=None, address_with_port="tcp://*:77998")
    ctx = zmq.Context()
    sock = ctx.socket(zmq.REQ)
    sock.LINGER = 0
    sock.RCVTIMEO = 10
    sock.connect("tcp://localhost:77998")
    for i in range(3):
        with qtbot.waitSignal(widget.gotMessage, raising=False, timeout=500) as blocker:
            sock.send_string(f"yo{i}")
        assert blocker.signal_triggered
        assert blocker.args[0] == f"yo{i}"
        widget.resolve_message(True, "")
        reply = sock.recv().decode()
        assert reply == "ok: "
        with qtbot.waitSignal(widget.gotMessage, raising=False, timeout=500) as blocker:
            sock.send_string("schmo")
        assert blocker.signal_triggered
        assert blocker.args[0] == "schmo"
        widget.resolve_message(False, "testing")
        reply = sock.recv().decode()
        assert reply == "failure: testing"
    del widget._context, ctx
    # this test hangs the 2nd time through if you use pytest-watch -- -s
    # it has something to do with the zmq contexts failing to terminate
    # and I've already added sock.LINGER = 0 on both sockets, so I don't know what
    # else to try, but it seems to work well enough and the tests work one time through



