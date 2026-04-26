import os
import sys
from PyQt5 import QtGui, QtCore, QtWidgets, uic
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from cringe.shared import terminal_colors as tc
from cringe.shared import log
from cringe.shared.rack_transport import write_wreg


class dfbChn(QWidget):

    def __init__(self,
                 parent=None,
                 layout=None,
                 state=0,
                 chn=0,
                 cardaddr=3,
                 serialport=None,
                 master=None):

        super(dfbChn, self).__init__()

        self.parent = parent
        self.layout = layout

        self.address = cardaddr
        self.serialport = serialport

        self.state = state
        self.chn = chn
        self.triA = 0
        self.triB = 0
        self.a2d_lockpt = 0
        self.d2a_A = 0
        self.d2a_B = 0
        self.SM = 0
        self.P = 0
        self.I = 0
        self.FBA = 0
        self.FBB = 0
        self.ARL = 0

        self.unlocked = 1

        self.dc = False
        self.lohi = True
        self.tri = False

        self.saveState = {}

        if master is None:
            uic.loadUi(os.path.join(os.path.dirname(__file__), 'dfbchn.ui'),
                       self)
        else:
            uic.loadUi(
                os.path.join(os.path.dirname(__file__), 'dfbchn_master.ui'),
                self)

        self.counter_label.setStyleSheet("background-color: #" + tc.yellow +
                                         ";")
        self.TriA_button.setStyleSheet("background-color: #" + tc.red + ";")
        self.TriB_button.setStyleSheet("background-color: #" + tc.red + ";")
        self.FBA_button.setStyleSheet("background-color: #" + tc.red + ";")
        self.FBB_button.setStyleSheet("background-color: #" + tc.red + ";")
        self.ARL_button.setStyleSheet("background-color: #" + tc.red + ";")
        self.lock_button.setStyleSheet("background-color: #" + tc.green + ";")
        self.counter_label.setText(str(self.state))
        '''
        call self routines
        '''
        if master is None:
            self.TriA_button.toggled.connect(self.triA_changed)
            self.TriB_button.toggled.connect(self.triB_changed)
            self.a2d_lockpt_spin.valueChanged.connect(
                self.a2d_lockpt_spin_changed)
            self.a2d_lockpt_slider.valueChanged.connect(
                self.a2d_lockpt_slider_changed)
            self.d2a_A_spin.valueChanged.connect(self.d2a_A_spin_changed)
            self.d2a_A_slider.valueChanged.connect(self.d2a_A_slider_changed)
            self.d2a_B_spin.valueChanged.connect(self.d2a_B_spin_changed)
            self.d2a_B_slider.valueChanged.connect(self.d2a_B_slider_changed)
            self.data_packet.currentIndexChanged.connect(
                self.data_packet_changed)
            self.P_spin.valueChanged.connect(self.P_spin_changed)
            self.I_spin.valueChanged.connect(self.I_spin_changed)
            self.FBA_button.toggled.connect(self.FBA_changed)
            self.FBB_button.toggled.connect(self.FBB_changed)
            self.ARL_button.toggled.connect(self.ARL_changed)
            self.chn_send.clicked.connect(self.send_channel)
            self.lock_button.toggled.connect(self.lock_channel)
        '''
        call parent routines
        '''
        if master is not None:
            self.TriA_button.toggled.connect(parent.triA_changed,
                                             self.TriA_button.isChecked())
            self.TriB_button.toggled.connect(parent.triB_changed,
                                             self.TriB_button.isChecked())
            self.a2d_lockpt_spin.valueChanged.connect(
                parent.a2d_lockpt_spin_changed, self.a2d_lockpt_spin.value())
            self.a2d_lockpt_slider.valueChanged.connect(
                parent.a2d_lockpt_slider_changed,
                self.a2d_lockpt_slider.value())
            self.d2a_A_spin.valueChanged.connect(parent.d2a_A_spin_changed,
                                                 self.d2a_A_spin.value())
            self.d2a_A_slider.valueChanged.connect(parent.d2a_A_slider_changed,
                                                   self.d2a_A_slider.value())
            self.d2a_B_spin.valueChanged.connect(parent.d2a_B_spin_changed,
                                                 self.d2a_B_spin.value())
            self.d2a_B_slider.valueChanged.connect(parent.d2a_B_slider_changed,
                                                   self.d2a_B_slider.value())
            self.data_packet.currentIndexChanged.connect(
                parent.data_packet_changed, self.data_packet.currentIndex())
            self.P_spin.valueChanged.connect(parent.P_spin_changed,
                                             self.P_spin.value())
            self.I_spin.valueChanged.connect(parent.I_spin_changed,
                                             self.I_spin.value())
            self.FBA_button.toggled.connect(parent.FBA_changed,
                                            self.FBA_button.isChecked())
            self.FBB_button.toggled.connect(parent.FBB_changed,
                                            self.FBB_button.isChecked())
            self.ARL_button.toggled.connect(parent.ARL_changed,
                                            self.ARL_button.isChecked())
            self.chn_send.clicked.connect(parent.send_channel)
            self.lock_button.toggled.connect(parent.lock_channel,
                                             self.lock_button.isChecked())

        if self.parent is not None:
            self.layout.addWidget(self)

        if parent is None:
            self.show()


#             print self.width()

    def triA_changed(self):
        self.triA = self.TriA_button.isChecked()
        if self.triA == 1:
            self.TriA_button.setStyleSheet("background-color: #" + tc.green +
                                           ";")
        else:
            self.TriA_button.setStyleSheet("background-color: #" + tc.red +
                                           ";")
        self.send_wreg0()
        self.send_wreg2()

    def triB_changed(self):
        self.triB = self.TriB_button.isChecked()
        if self.triB == 1:
            self.TriB_button.setStyleSheet("background-color: #" + tc.green +
                                           ";")
        else:
            self.TriB_button.setStyleSheet("background-color: #" + tc.red +
                                           ";")
        self.send_wreg0()
        self.send_wreg2()

    def a2d_lockpt_spin_changed(self):
        self.a2d_lockpt = self.a2d_lockpt_spin.value()
        self.a2d_lockpt_slider.setValue(self.a2d_lockpt_spin.value())
        if self.unlocked == 1:
            self.send_wreg0()
            self.send_wreg1()


    def a2d_lockpt_slider_changed(self):
        self.a2d_lockpt_spin.setValue(self.a2d_lockpt_slider.value())

    def d2a_A_spin_changed(self):
        self.d2a_A = self.d2a_A_spin.value()
        self.d2a_A_slider.setValue(self.d2a_A_spin.value())
        if self.unlocked == 1:
            self.send_wreg0()
            self.send_wreg2()

    def d2a_A_slider_changed(self):
        self.d2a_A_spin.setValue(self.d2a_A_slider.value())

    def d2a_B_spin_changed(self):
        self.d2a_B = self.d2a_B_spin.value()
        self.d2a_B_slider.setValue(self.d2a_B_spin.value())
        if self.unlocked == 1:
            self.send_wreg0()
            self.send_wreg5()

    def d2a_B_slider_changed(self):
        self.d2a_B_spin.setValue(self.d2a_B_slider.value())

    def data_packet_changed(self):
        self.SM = self.data_packet.currentIndex()
        if self.unlocked == 1:
            self.send_wreg0()
            self.send_wreg5()

    def P_spin_changed(self):
        self.P = self.P_spin.value()
        if self.unlocked == 1:
            self.send_wreg0()
            self.send_wreg3()

    def I_spin_changed(self):
        self.I = self.I_spin.value()
        if self.unlocked == 1:
            self.send_wreg0()
            self.send_wreg3()

    def FBA_changed(self):
        self.FBA = self.FBA_button.isChecked()
        if self.FBA == 1:
            self.FBA_button.setStyleSheet("background-color: #" + tc.green +
                                          ";")
            self.FBB_button.setChecked(0)
        else:
            self.FBA_button.setStyleSheet("background-color: #" + tc.red + ";")
        self.send_wreg0()
        self.send_wreg3()

    def FBB_changed(self):
        self.FBB = self.FBB_button.isChecked()
        if self.FBB == 1:
            self.FBB_button.setStyleSheet("background-color: #" + tc.green +
                                          ";")
            self.FBA_button.setChecked(0)
        else:
            self.FBB_button.setStyleSheet("background-color: #" + tc.red + ";")
        self.send_wreg0()
        self.send_wreg3()

    def ARL_changed(self):
        self.ARL = self.ARL_button.isChecked()
        if self.ARL == 1:
            self.ARL_button.setStyleSheet("background-color: #" + tc.green +
                                          ";")
        else:
            self.ARL_button.setStyleSheet("background-color: #" + tc.red + ";")
        self.send_wreg0()
        self.send_wreg3()

    def send_channel(self):
        log.debug(tc.FCTCALL + "send DFB STATE parameters", self.state,
                  ": index & arrayed register values", tc.ENDC)
        self.send_wreg0()
        self.send_wreg1()
        self.send_wreg2()
        self.send_wreg3()
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

    def send_wreg0(self):
        log.debug("DFB:WREG0: page index (GPI/channel/state)")
        wreg = 0 << 25
        wregval = wreg | (self.chn << 6) | self.state
        self.sendReg(wregval)

    def send_wreg1(self):
        log.debug("DFB:WREG1: arrayed state variables: ADC lock point")
        wreg = 1 << 25
        wregval = wreg | self.a2d_lockpt
        self.sendReg(wregval)

    def send_wreg2(self):
        log.debug(
            "DFB:WREG2: arrayed state variables: triangle booleans & DAC offset A"
        )
        wreg = 2 << 25
        wregval = wreg | (self.triA << 16) | (self.triB << 17) | self.d2a_A
        self.sendReg(wregval)

    def send_wreg3(self):
        log.debug(
            "DFB:WREG3: arrayed state feedback parameters: tri, arl, P, I")
        wreg = 3 << 25
        wreg = wreg | (int(self.FBA) << 24)
        wreg = wreg | (int(self.FBB) << 23)
        wreg = wreg | (int(self.ARL) << 21)
        wreg = wreg | ((int(self.P) & 0x3ff) << 10)
        wregval = wreg | (int(self.I) & 0x3ff)
        self.sendReg(wregval)

    def send_wreg5(self):

        log.debug("DFB:WREG5: DAC offset B & send mode")
        wreg = 5 << 25
        wregval = wreg | (self.d2a_B << 11) | self.SM
        self.sendReg(wregval)

    def sendReg(self, wregval):
        write_wreg(self.serialport, wregval, self.address)

    def packState(self):
        self.stateVector = {
            'triA': self.TriA_button.isChecked(),
            'triB': self.TriB_button.isChecked(),
            'a2d_lockpt': self.a2d_lockpt_spin.value(),
            'd2a_A': self.d2a_A_spin.value(),
            'd2a_B': self.d2a_B_spin.value(),
            'SM': self.data_packet.currentIndex(),
            'P': self.P_spin.value(),
            'I': self.I_spin.value(),
            'FBA': self.FBA_button.isChecked(),
            'FBB': self.FBB_button.isChecked(),
            'ARL': self.ARL_button.isChecked()
        }

    def unpackState(self, loadState):
        self.TriA_button.setChecked(loadState['triA'])
        self.TriB_button.setChecked(loadState['triB'])
        self.a2d_lockpt_spin.setValue(loadState['a2d_lockpt'])
        self.d2a_A_spin.setValue(loadState['d2a_A'])
        self.d2a_B_spin.setValue(loadState['d2a_B'])
        self.data_packet.setCurrentIndex(loadState['SM'])
        self.P_spin.setValue(loadState['P'])
        self.I_spin.setValue(loadState['I'])
        self.FBA_button.setChecked(loadState['FBA'])
        self.FBB_button.setChecked(loadState['FBB'])
        self.ARL_button.setChecked(loadState['ARL'])


def main():

    app = QApplication(sys.argv)
    app.setStyle("plastique")
    app.setStyleSheet("""    QPushbutton{font: 10px; padding: 6px}
                            QToolButton{font: 10px; padding: 6px}""")
    ex = dfbChn()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()