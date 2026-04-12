import os
import sys
from PyQt5 import QtGui, QtCore, QtWidgets, uic
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from cringe.shared import terminal_colors as tc
from cringe.shared import log
from cringe.shared.rack_transport import write_wreg


class badChn(QWidget):

    def __init__(self,
                 parent=None,
                 layout=None,
                 chn=0,
                 cardaddr=3,
                 serialport=None,
                 master=None):

        super(badChn, self).__init__()

        self.parent = parent
        self.layout = layout

        self.chn = chn
        self.address = cardaddr
        self.serialport = serialport

        tc.green = "90EE90"
        tc.red = "F08080"

        self.unlocked = 1

        self.dc = False
        self.lohi = True
        self.tri = False

        if master is None:
            uic.loadUi(os.path.join(os.path.dirname(__file__), 'badchn.ui'),
                       self)
        else:
            uic.loadUi(
                os.path.join(os.path.dirname(__file__), 'badchn_master.ui'),
                self)

        self.counter_label.setStyleSheet("background-color: #" + tc.yellow +
                                         ";")
        self.dc_button.setStyleSheet("background-color: #" + tc.red + ";")
        self.LoHi_button.setStyleSheet("background-color: #" + tc.green + ";")
        self.Tri_button.setStyleSheet("background-color: #" + tc.red + ";")
        self.lock_button.setStyleSheet("background-color: #" + tc.green + ";")
        self.counter_label.setText(str(self.chn))

        if master is None:
            self.dc_button.toggled.connect(self.dc_changed)
            self.LoHi_button.toggled.connect(self.LoHi_changed)
            self.Tri_button.toggled.connect(self.tri_changed)
            self.d2a_lo_spin.valueChanged.connect(self.d2a_lo_spin_changed)
            self.d2a_lo_min_button.clicked.connect(self.d2a_lo_setMin)
            self.d2a_lo_slider.valueChanged.connect(self.d2a_lo_slider_changed)
            self.d2a_lo_max_button.clicked.connect(self.d2a_lo_setMax)
            self.d2a_hi_spin.valueChanged.connect(self.d2a_hi_spin_changed)
            self.d2a_hi_min_button.clicked.connect(self.d2a_hi_setMin)
            self.d2a_hi_slider.valueChanged.connect(self.d2a_hi_slider_changed)
            self.d2a_hi_max_button.clicked.connect(self.d2a_hi_setMax)
            self.chn_send.clicked.connect(self.send_channel)
            #             self.lock_button.mode_menu.triggered('static').connect(self.lock_channel)
            self.lock_button.toggled.connect(self.lock_channel)

        if master is not None:
            self.dc_button.toggled.connect(parent.dc_changed,
                                           self.dc_button.isChecked())
            self.LoHi_button.toggled.connect(parent.LoHi_changed,
                                             self.LoHi_button.isChecked())
            self.Tri_button.toggled.connect(parent.tri_changed,
                                            self.Tri_button.isChecked())
            self.d2a_lo_spin.valueChanged.connect(parent.d2a_lo_spin_changed,
                                                  self.d2a_lo_spin.value())
            self.d2a_lo_min_button.clicked.connect(parent.d2a_lo_setMin)
            self.d2a_lo_slider.valueChanged.connect(
                parent.d2a_lo_slider_changed, self.d2a_lo_slider.value())
            self.d2a_lo_max_button.clicked.connect(parent.d2a_lo_setMax)
            self.d2a_hi_spin.valueChanged.connect(parent.d2a_hi_spin_changed)
            self.d2a_hi_min_button.clicked.connect(parent.d2a_hi_setMin)
            self.d2a_hi_slider.valueChanged.connect(
                parent.d2a_hi_slider_changed, self.d2a_hi_slider.value())
            self.d2a_hi_max_button.clicked.connect(parent.d2a_hi_setMax)
            self.chn_send.clicked.connect(parent.send_channel)
            self.lock_button.toggled.connect(parent.lock_channel,
                                             self.lock_button.isChecked())

#         self.setStyleSheet("background-color: #" + tc.grey + ";")

        if self.parent is not None:
            self.layout.addWidget(self)

#         self.show()

    def dc_changed(self):
        self.dc = self.dc_button.isChecked()
        if self.dc == 1:
            self.dc_button.setStyleSheet("background-color: #" + tc.green +
                                         ";")
        else:
            self.dc_button.setStyleSheet("background-color: #" + tc.red + ";")
#         if self.unlocked == 1:
        self.send_channel()

    def LoHi_changed(self):
        self.lohi = self.LoHi_button.isChecked()
        if self.lohi == 1:
            self.LoHi_button.setStyleSheet("background-color: #" + tc.green +
                                           ";")
            self.LoHi_button.setText('HI')
        else:
            self.LoHi_button.setStyleSheet("background-color: #" + tc.red +
                                           ";")
            self.LoHi_button.setText('LO')
#         if self.unlocked == 1:
        self.send_channel()

    def tri_changed(self):
        self.tri = self.Tri_button.isChecked()
        if self.tri == 1:
            self.Tri_button.setStyleSheet("background-color: #" + tc.green +
                                          ";")
        else:
            self.Tri_button.setStyleSheet("background-color: #" + tc.red + ";")


#         if self.unlocked == 1:
        self.send_channel()

    def d2a_lo_spin_changed(self):
        self.d2a_lo_slider.setValue(self.d2a_lo_spin.value())
        if self.unlocked == 1:
            self.send_channel()

    def d2a_lo_slider_changed(self):
        self.d2a_lo_spin.setValue(self.d2a_lo_slider.value())

    def d2a_lo_setMin(self):
        self.d2a_lo_slider.setValue(0)

    def d2a_lo_setMax(self):
        self.d2a_lo_slider.setValue(16383)

    def d2a_hi_spin_changed(self):
        self.d2a_hi_slider.setValue(self.d2a_hi_spin.value())
        if self.unlocked == 1:
            self.send_channel()

    def d2a_hi_slider_changed(self):
        self.d2a_hi_spin.setValue(self.d2a_hi_slider.value())

    def d2a_hi_setMin(self):
        self.d2a_hi_slider.setValue(0)

    def d2a_hi_setMax(self):
        self.d2a_hi_slider.setValue(16383)

    def send_channel(self):
        log.debug(tc.FCTCALL + "send BAD16 CHN", self.chn,
                  ": index & arrayed register values", tc.ENDC)
        self.send_wreg2()
        self.send_wreg4()
        self.send_wreg5()

    def lock_channel(self):
        self.unlocked = self.lock_button.isChecked()
        if self.unlocked == 1:
            self.lock_button.setStyleSheet("background-color: #" + tc.green +
                                           ";")
            self.lock_button.setText('dynamic')
        else:
            self.lock_button.setStyleSheet("background-color: #" + tc.red +
                                           ";")
            self.lock_button.setText('static')

    def send_wreg2(self):
        log.debug("BAD16:WREG2: channel index")
        wreg = 2 << 25
        wregval = wreg | self.chn
        self.sendReg(wregval)

    def send_wreg4(self):
        log.debug("BAD16:WREG4: channel booleans & DAC high value")
        wreg = 4 << 25
        wreg = wreg | (int(self.dc) << 21)
        wreg = wreg | (int(self.lohi) << 20)
        wreg = wreg | (int(self.tri) << 19)
        wregval = wreg | self.d2a_hi_spin.value()
        self.sendReg(wregval)

    def send_wreg5(self):
        log.debug("BAD16:WREG5: channel DAC low value")
        wreg = 5 << 25
        wregval = wreg | (self.d2a_lo_slider.value() << 8)
        self.sendReg(wregval)

    def sendReg(self, wregval):
        write_wreg(self.serialport, wregval, self.address)

    def packChannel(self):
        self.ChannelVector = {
            'dc': self.dc_button.isChecked(),
            'LoHi': self.LoHi_button.isChecked(),
            'tri': self.Tri_button.isChecked(),
            'd2a_lo': self.d2a_lo_spin.value(),
            'd2a_hi': self.d2a_hi_spin.value(),
        }

    def unpackChannel(self, loadChannel):
        self.dc_button.setChecked(loadChannel['dc'])
        self.LoHi_button.setChecked(loadChannel['LoHi'])
        self.Tri_button.setChecked(loadChannel['tri'])
        self.d2a_lo_spin.setValue(loadChannel['d2a_lo'])
        self.d2a_hi_spin.setValue(loadChannel['d2a_hi'])


def main():

    app = QApplication(sys.argv)
    ex = badChn()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()