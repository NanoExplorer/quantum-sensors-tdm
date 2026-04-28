from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtCore import QThread
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from . import towercard
from cringe.shared import log
from instruments.tower_power_supplies_worker import TowerPowerSuppliesWorker

BAY_NAMES = ["0", "1", "2", "3", "4", "5", "6", "7"]


class LabelWidget(QWidget):

    def __init__(self, parent=None):
        super(type(self), self).__init__(parent)
        self.layout = QGridLayout(self)


class TowerWidget(QWidget):

    def __init__(self,
                 parent=None,
                 nameaddrlist=["DB1", "13", "SAb", "4", "SQ1b", "12"],
                 serialport="tower",
                 shockvalue=65535):

        super(type(self), self).__init__()

        self.parent = parent
        self.layout = QVBoxLayout(self)

        label = LabelWidget()
        self.layout.addWidget(label)
        self.towercards = {}
        for i in range(len(nameaddrlist) // 2):
            name = nameaddrlist[2 * i]
            addr = int(nameaddrlist[2 * i + 1])
            tc = towercard.TowerCard(parent=self,
                                     name=name,
                                     cardaddr=addr,
                                     serialport=serialport,
                                     shockvalue=shockvalue)
            self.towercards[name] = tc
            self.layout.addWidget(tc)

        for i, s in enumerate(["addr", "name"] + BAY_NAMES +
                              ["all chn", "shock"]):
            l = QLabel(s)
            label.layout.addWidget(l, 0, i, 1, 1)

        sendallbutton = QPushButton("send all tower")
        sendallbutton.clicked.connect(self.sendall)
        self.layout.addWidget(sendallbutton)

        self.power_on_button = QPushButton("Tower Power ON")
        self.power_off_button = QPushButton("Tower Power OFF")
        self.power_on_button.setEnabled(False)
        self.power_off_button.setEnabled(False)
        self.power_on_button.clicked.connect(self.tower_power_on_event)
        self.power_off_button.clicked.connect(self.tower_power_off_event)
        ps_layout=QHBoxLayout()
        ps_layout.addWidget(self.power_on_button)
        ps_layout.addWidget(self.power_off_button)
        self.layout.addLayout(ps_layout)

        self.power_supplies = None
        self._connect_thread = QThread(self)
        self._connect_worker = TowerPowerSuppliesWorker()
        self._connect_worker.moveToThread(self._connect_thread)
        self._connect_thread.started.connect(self._connect_worker.run)
        self._connect_worker.ready.connect(self._on_ps_connected)
        self._connect_worker.failed.connect(self._on_ps_failed)
        self._connect_thread.start()

        if parent == None:
            self.show()
            #print self.width()

    def get_bayindex(self, bayname):
        return BAY_NAMES.index(bayname)

    def set_channel_dac(self, cardname, bay_index, dacvalue):
        self.towercards[cardname].towerchannels[bay_index].dacspin.setValue(
            dacvalue)

    def set_card_dac(self, cardname, dacvalue):
        self.towercards[cardname].allcontrolchannel.dacspin.setValue(dacvalue)

    def sendall(self):
        for key, tc in self.towercards.items():
            for tchn in tc.towerchannels:
                value = tchn.dacspin.value()
                tchn.sendvalue(value)

    def packState(self):
        dacvalues = []
        for key, tc in self.towercards.items():
            for tchn in tc.towerchannels:
                dacvalues.append(tchn.dacspin.value())
        self.stateVector = {'dacvalues': dacvalues}
        return self.stateVector

    def unpackState(self, loadState):
        dacvalues = loadState["dacvalues"][:]
        log.debug("towerwidget:dacvalues", dacvalues)
        if len(dacvalues) != len(self.towercards) * 8:
            # silentley ignore saved values if there are the wrong number
            # used to allow changiing the tower setup from the command line
            log.debug("wrong number of dacvalues for towerwidget.unpackState")
            return
        for key, tc in self.towercards.items():
            for tchn in tc.towerchannels:
                dacvalues.append(tchn.dacspin.setValue(dacvalues.pop(0)))

    def _on_ps_connected(self, power_supplies):
        self.power_supplies = power_supplies
        self._connect_thread.quit()
        self.power_on_button.setEnabled(True)
        self.power_off_button.setEnabled(True)

    def _on_ps_failed(self, error):
        log.debug(f"tower power supply connection failed: {error}")

    def _set_ps_buttons_enabled(self, enabled):
        self.power_on_button.setEnabled(enabled)
        self.power_off_button.setEnabled(enabled)

    def _on_ps_command_failed(self, error):
        self._on_ps_failed(error)
        self._set_ps_buttons_enabled(True)

    def _run_ps_in_thread(self, worker, slot):
        thread = QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(slot)
        worker.failed.connect(self._on_ps_command_failed)
        thread.start()
        return thread

    def tower_power_on_event(self):
        self._set_ps_buttons_enabled(False)
        worker = TowerPowerSuppliesWorker(self.power_supplies)
        worker.power_on_done.connect(self._on_tower_power_on_done)
        self._power_on_thread = self._run_ps_in_thread(worker, worker.run_power_on)

    def _on_tower_power_on_done(self, s):
        self._power_on_thread.quit()
        self._set_ps_buttons_enabled(True)
        self.sendall()

    def tower_power_off_event(self):
        self._set_ps_buttons_enabled(False)
        worker = TowerPowerSuppliesWorker(self.power_supplies)
        worker.power_off_done.connect(self._on_tower_power_off_done)
        self._power_off_thread = self._run_ps_in_thread(worker, worker.run_power_off)

    def _on_tower_power_off_done(self):
        self._power_off_thread.quit()
        self._set_ps_buttons_enabled(True)

