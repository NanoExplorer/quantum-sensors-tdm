import os
import sys
import optparse

from PyQt5 import QtGui, QtCore, QtWidgets, uic
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

import named_serial
from . import badrap
from . import sv_array
from cringe.shared import terminal_colors as tc
from cringe.shared import log
from cringe.shared.rack_transport import write_wreg
import cringe.DFBx2.dprcal as dprcal


class badcard(QWidget):

    def __init__(self,
                 parent=None,
                 addr=None,
                 slot=None,
                 seqln=None,
                 lsync=32):

        super(badcard, self).__init__()

        self.serialport = named_serial.Serial(port='rack', shared=True)

        self.chns = 16

        self.parent = parent
        self.address = addr
        self.slot = slot
        self.seqln = seqln
        #       self.lsync = lsync
        #       self.frame = self.lsync * self.seqln

        self.bad_delay = 5
        self.LED = False
        self.ST = False
        self.INT = False

        #       self.wreg0 = (0 << 25) | (self.ST << 16) | (self.LED << 14) | (self.bad_delay << 10) | self.seqln
        #       self.wreg0 = 5128
        self.wreg1 = 34209800
        self.mode = 1

        self.chn_vectors = []
        #       self.enb = [0,0,0,0,0,0,0]
        #       self.cal_coeffs = [0,0,0,0,0,0,0]
        #       self.appTrim =[0,0,0,0,0,0,0]

        self.setWindowTitle("BAD16: %d/%d" %
                            (slot, addr))  # Phase Offset Widget
        self.setGeometry(30, 30, 800, 1000)
        self.setContentsMargins(0, 0, 0, 0)

        self.layout_widget = QWidget(self)
        self.layout = QGridLayout(self)

        log.debug(tc.INIT + "building BAD16 card: slot", self.slot,
                  "/ address", self.address, tc.ENDC)

        _glb = QWidget(self)
        uic.loadUi(
            os.path.join(os.path.dirname(__file__), '../shared/card_global.ui'),
            _glb)
        self.card_glb_widget = _glb.card_glb_widget
        self.class_interface_widget = _glb.class_interface_widget
        self.LED_button = _glb.LED_button
        self.status_button = _glb.status_button
        self.card_glb_send = _glb.card_glb_send
        self.slot_indicator = _glb.slot_indicator
        self.addr_indicator = _glb.addr_indicator

        self.LED_button.setStyleSheet("background-color: #" + tc.green + ";")
        self.LED_button.toggled.connect(self.LED_changed)
        self.status_button.setStyleSheet("background-color: #" + tc.red + ";")
        self.status_button.toggled.connect(self.status_changed)
        self.card_glb_send.clicked.connect(self.send_card_globals)
        self.slot_indicator.setText('%2d' % slot)
        self.addr_indicator.setText(str(addr))

        self.layout.addWidget(self.card_glb_widget, 0, 0, 1, 1,
                              QtCore.Qt.AlignRight)
        self.layout.addWidget(self.class_interface_widget, 0, 1, 1, 1,
                              QtCore.Qt.AlignLeft)
        '''
        create TAB widget for embedding BAD16 functional widgets
        '''
        self.bad16_widget = QTabWidget(self)
        self.bad16_widget.setFixedWidth(1100)

        self.badrap_widget1 = badrap.badrap(parent=self,
                                            addr=addr,
                                            slot=slot,
                                            seqln=seqln,
                                            lsync=lsync)
        self.scale_factor = self.badrap_widget1.master_vector.width()
        self.bad16_widget.addTab(self.badrap_widget1, " channels ")

        self.badrap_widget2 = sv_array.SV_array(parent=self,
                                                seqln=seqln,
                                                addr=addr)
        self.bad16_widget.addTab(self.badrap_widget2, " states ")

        self.badrap_widget3 = dprcal.dprcal(ctype="BAD16",
                                            addr=addr,
                                            slot=slot)
        self.bad16_widget.addTab(self.badrap_widget3, " phase ")

        self.layout.addWidget(self.bad16_widget, 1, 0, 1, 2,
                              QtCore.Qt.AlignHCenter)
        '''
        resize widgets for relative, platform dependent variability
        '''
        self.scale_factor = self.badrap_widget1.arrayframe.width()

        rm = 10
        self.bad16_widget.setFixedWidth(int(self.scale_factor * 1.05))
        self.class_interface_widget.setFixedWidth(
            int((self.scale_factor * 1.05) / 2 - rm / 2))
        self.card_glb_widget.setFixedWidth(
            int((self.scale_factor * 1.05) / 2 - rm / 2))
#       self.file_mgmt_widget.setFixedWidth(self.badrap_widget1.arrayframe.width()+rm)
#       self.sys_glob_hdr_widget.setFixedWidth(self.badrap_widget1.arrayframe.width()+rm)
#       self.class_glob_hdr_widget.setFixedWidth(self.badrap_widget1.arrayframe.width()+rm)
#       self.class_interface_widget.setFixedWidth(self.badrap_widget1.arrayframe.width()+rm)

    def seqln_changed(self, seqln):
        log.debug(tc.FCTCALL + "send SEQLN to BAD16 card:", tc.ENDC)
        self.seqln = seqln
        self.send_wreg0()
        #       self.wreg0 = ((self.wreg0 & 0xFFFFF00) | self.seqln)
        #       self.send_wreg0()
        self.badrap_widget2.seqln_changed(seqln)

    def LED_changed(self):
        log.debug(tc.FCTCALL + "send LED boolean (True = OFF) to BAD16 card:" +
                  tc.ENDC)
        self.LED = self.LED_button.isChecked()
        if self.LED == 1:
            self.LED_button.setStyleSheet("background-color: #" + tc.red + ";")
            self.LED_button.setText('OFF')
        else:
            self.LED_button.setStyleSheet("background-color: #" + tc.green +
                                          ";")
            self.LED_button.setText('ON')
        self.send_wreg0()

    def status_changed(self):
        log.debug(tc.FCTCALL + "send ST boolean to BAD16 card:" + tc.ENDC)
        self.ST = self.status_button.isChecked()
        if self.ST == 1:
            self.status_button.setStyleSheet("background-color: #" + tc.green +
                                             ";")
        else:
            self.status_button.setStyleSheet("background-color: #" + tc.red +
                                             ";")
        self.send_wreg0()
        self.badrap_widget3.enbDiagnostic(self.ST)

    def initMem(self, init):
        tc.INIT_state = self.INT
        self.INT = init
        if self.INT != tc.INIT_state:
            if self.INT == 1:
                log.debug(
                    tc.FCTCALL +
                    "BAD16 state vector memory initialized: update init status boolean: 1"
                    + tc.ENDC)
            else:
                log.debug(
                    tc.FCTCALL +
                    "BAD16 state vector memory contents updated: update init status boolean: 0"
                    + tc.ENDC)
            self.send_wreg0()

    def send_triangle(self, wreg1):
        log.debug(tc.FCTCALL + "send triangle parameters to BAD16 card:",
                  tc.ENDC)
        self.wreg1 = wreg1
        self.send_wreg1()

    def send_class_globals(self, wreg0):
        log.debug(tc.FCTCALL + "send card globals to BAD16 card:", tc.ENDC)
        self.wreg0 = wreg0
        self.send_wreg0()

    def send_card_globals(self):
        log.debug(tc.FCTCALL + "send card globals to BAD16 card:", tc.ENDC)
        self.send_wreg0()


#   def card_delay_changed(self):
#       '''
#       not sure what the best structure is for class global commanding
#       at child level need to change control to indicator (QSpinBOx to QLineEdit)
#       1 - can preserve function call triggered from within child as 'QLineEdit.textChanged'
#       or
#       2 - can pass parent.QSpinBox.value() to child function as parameter
#       '''
#       self.badrap_widget1.card_delay.setText(str("%2d"%self.card_delay.value()))
#       self.badrap_widget1.card_delay_changed(self.card_delay.value())

    def send_wreg0(self):
        if self.parent != None:
            self.parent.send_bad16_wreg0(self.ST, self.LED, self.INT,
                                         self.address)
        else:
            log.debug(
                "BAD16:WREG0: ST, LED, card delay, INIT, sequence length:",
                self.ST, self.LED, self.bad_delay, self.INT, self.seqln)

            self.wreg0 = (0 << 25) | (self.ST << 16) | (self.LED << 14) | (
                self.bad_delay << 10) | (self.INT << 8) | self.seqln
            self.sendReg(self.wreg0)

    def send_wreg1(self):
        cmd_reg = bin(self.wreg1)[5:].zfill(25)
        dwell = int(cmd_reg[1:5], base=2)
        steps = int(cmd_reg[5:9], base=2)
        step = int(cmd_reg[11:], base=2)
        log.debug("BAD16:WREG1: triangle parameters DWELL, STEPS, STEP SIZE:",
                  dwell, steps, step)
        self.sendReg(self.wreg1)

    def sendReg(self, wregval):
        write_wreg(self.serialport, wregval, self.address)

    def packCARDglobals(self):
        self.CARDglobals = {
            'LED': self.LED_button.isChecked(),
            'ST': self.status_button.isChecked()
        }

    def unpackCARDglobals(self, CARDglobals):
        self.LED_button.setChecked(CARDglobals['LED'])
        self.status_button.setChecked(CARDglobals['ST'])

    def packClass(self):
        self.packCARDglobals()
        self.badrap_widget1.packMasterVector()
        self.badrap_widget1.packChannels()
        self.badrap_widget2.packStates()
        self.badrap_widget3.packCal()
        self.classParameters = {
            'CARDglobals': self.CARDglobals,
            'bad16MasterVector': self.badrap_widget1.MasterState,
            'badAllChannels': self.badrap_widget1.allChannels,
            'badAllStates': self.badrap_widget2.allStates,
            'CARDphase': self.badrap_widget3.CalCoeffs,
            'states': self.badrap_widget2.packState(),
        }

    def unpackClass(self, classParameters):
        CARDglobals = classParameters['CARDglobals']
        self.unpackCARDglobals(CARDglobals)
        masterVector = classParameters['bad16MasterVector']
        self.badrap_widget1.unpackMasterVector(masterVector)
        badAllChannels = classParameters['badAllChannels']
        self.badrap_widget1.unpackChannels(badAllChannels)
        badAllStates = classParameters['badAllStates']
        self.badrap_widget2.unpackStates(badAllStates)
        CARDphase = classParameters['CARDphase']
        self.badrap_widget3.unpackCal(CARDphase)
        self.badrap_widget2.unpackState(classParameters["states"])


def main():

    app = QApplication(sys.argv)
    app.setStyle("plastique")
    app.setStyleSheet("""   QPushbutton{font: 10px; padding: 6px}
                            QToolButton{font: 10px; padding: 6px}
                            QLineEdit {background-color: #FFFFCC;}
                            QToolTip {background-color: #FFFFCC;}""")
    win = badcard(addr=addr, slot=slot, seqln=seqln)
    win.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    p = optparse.OptionParser()
    #   p.add_option('-C','--card_type', action='store', dest='ctype', type='str',
    #                help='Type of card to calibrate (default=DFBx2).')
    p.add_option('-A',
                 '--card_address',
                 action='store',
                 dest='addr',
                 type='int',
                 help='Hardware address of card (default=32).')
    p.add_option('-S',
                 '--slot',
                 action='store',
                 dest='slot',
                 type='int',
                 help='Host slot in crate (default=9)')
    p.add_option('-L',
                 '--length',
                 action='store',
                 dest='seqln',
                 type='int',
                 help='Number of states in sequence (default=4')
    #   p.set_defaults(ctype="DFBx2")
    p.set_defaults(addr=32)
    p.set_defaults(slot=9)
    p.set_defaults(seqln=4)
    opt, args = p.parse_args()
    #   ctype = opt.ctype
    addr = opt.addr
    slot = opt.slot
    seqln = opt.seqln
    main()
