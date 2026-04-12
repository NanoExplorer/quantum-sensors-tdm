#-*- coding: utf-8 -*-
import os
import sys
import optparse

from PyQt5 import QtGui, QtCore, QtWidgets, uic
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

import named_serial
from . import scream
from . import dprS
from cringe.shared import terminal_colors as tc
from cringe.shared import log


class dfbscard(QWidget):

    def __init__(self, parent=None, addr=None, slot=None, lsync=32):

        super(dfbscard, self).__init__()

        self.serialport = named_serial.Serial(port='rack', shared=True)

        self.states = 64

        self.parent = parent
        self.address = addr
        self.slot = slot
        #       self.seqln = seqln
        self.lsync = lsync
        '''global booleans'''

        self.LED = False
        self.ST = False
        self.CLK = False

        self.PS = False
        self.GR = True
        '''global variables'''

        self.XPT = 0
        self.NSAMP = 4
        self.prop_delay = 0
        self.card_delay = 0
        self.SETT = 12
        '''ARL default parameters'''

        self.ARLsense = 10
        self.RLDpos = 6
        self.RLDneg = 2

        #       self.frame_period = self.lsync * self.seqln * 0.008
        '''triangle default parameters'''

        self.TriDwell = 0
        self.TriRange = 10
        self.TriStep = 8

        self.dwell_val = 0
        self.dwellDACunits = float(1)
        self.range_val = 10
        self.rangeDACunits = float(1024)
        self.step_val = 8
        self.stepDACunits = float(256)
        self.tri_idx = 0
        '''card global default variables'''

        self.mode = 1
        self.wreg6 = 201761284
        self.wreg7 = 235668492

        self.chn_vectors = []
        #       self.enb = [0,0,0,0,0,0,0]
        #       self.cal_coeffs = [0,0,0,0,0,0,0]
        #       self.appTrim =[0,0,0,0,0,0,0]

        self.setWindowTitle("DFBx2: %d/%d" %
                            (slot, addr))  # Phase Offset Widget
        self.setGeometry(30, 30, 1300, 1000)
        self.setContentsMargins(0, 0, 0, 0)

        self.layout_widget = QWidget(self)
        self.layout = QGridLayout(self)

        log.debug(tc.INIT + "building DFBscream card: slot", self.slot,
                  "/ address", self.address, tc.ENDC)

        _glb = QWidget()
        uic.loadUi(
            os.path.join(os.path.dirname(__file__), '../shared/card_global.ui'), _glb)
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

        self.layout.addWidget(self.card_glb_widget, 4, 0, 1, 1)
        self.layout.addWidget(self.class_interface_widget, 4, 1, 1, 1,
                              QtCore.Qt.AlignRight)
        '''
        create TAB widget for embedding BAD16 functional widgets
        '''
        self.dfbs_widget = QTabWidget(self)

        self.dfbs_widget1 = scream.scream(parent=self,
                                          addr=addr,
                                          slot=slot,
                                          channel=1,
                                          lsync=lsync)
        self.dfbs_widget.addTab(self.dfbs_widget1, " CH1 ")

        self.dfbs_widget2 = scream.scream(parent=self,
                                          addr=addr,
                                          slot=slot,
                                          channel=2,
                                          lsync=lsync)
        self.dfbs_widget.addTab(self.dfbs_widget2, " CH2 ")

        self.dfbs_widget3 = dprS.dprS(ctype="DFBs", addr=addr, slot=slot)
        self.dfbs_widget.addTab(self.dfbs_widget3, " phase ")

        self.layout.addWidget(self.dfbs_widget, 5, 0, 1, 2)
        '''
        resize widgets for relative, platform dependent variability
        '''
        rm = 45
        #       self.file_mgmt_widget.setFixedWidth(self.dfbx2_widget1.width()+rm)
        #       self.sys_glob_hdr_widget.setFixedWidth(self.dfbx2_widget1.width()+rm)
        #       self.class_glob_hdr_widget.setFixedWidth(self.dfbx2_widget1.width()+rm)
        #       self.arl_widget.setFixedWidth(self.dfbx2_widget1.width()/2+10)
        #       self.tri_wvfm_widget.setFixedWidth(self.dfbx2_widget1.width()/2+10)
        self.card_glb_widget.setFixedWidth(self.dfbs_widget1.width() / 2 + 10)
        self.class_interface_widget.setFixedWidth(self.dfbs_widget1.width() /
                                                  2 + 10)

    def LED_changed(self):
        self.LED = self.LED_button.isChecked()
        log.debug("SCREAM LED boolean (True = OFF):", self.LED, tc.ENDC)
        if self.LED == 1:
            self.LED_button.setStyleSheet("background-color: #" + tc.red + ";")
            self.LED_button.setText('OFF')
        else:
            self.LED_button.setStyleSheet("background-color: #" + tc.green +
                                          ";")
            self.LED_button.setText('ON')
#        if self.unlocked == 1:
        self.send_cmd(2, self.LED)

    def status_changed(self):
        self.ST = self.status_button.isChecked()
        log.debug("SCREAM ST boolean:", self.ST, tc.ENDC)
        if self.ST == 1:
            self.status_button.setStyleSheet("background-color: #" + tc.green +
                                             ";")
        else:
            self.status_button.setStyleSheet("background-color: #" + tc.red +
                                             ";")
        self.send_cmd(3, self.ST)
        self.dfbs_widget1.enbDiagnostic(self.ST)
        self.dfbs_widget2.enbDiagnostic(self.ST)
        self.dfbs_widget3.enbDiagnostic(self.ST)

    def send_card_globals(self):

        log.debug(tc.FCTCALL + "send card globals to SCREAM card:", tc.ENDC)
        self.LED_changed()
        self.status_changed()

    def send_channel_globals(self):
        self.dfbs_widget1.send_channel_globals()
        self.dfbs_widget2.send_channel_globals()

    def decode_tp(self):
        if self.TP == 0:
            return
        if self.TP == 1:
            self.lobytes = 0x5555
            self.hibytes = 0x5555
        if self.TP == 2:
            self.lobytes = 0xaaaa
            self.hibytes = 0xaaaa
        if self.TP == 3:
            self.lobytes = 0x3333
            self.hibytes = 0x3333
        if self.TP == 4:
            self.lobytes = 0x0f0f
            self.hibytes = 0x0f0f
        if self.TP == 5:
            self.lobytes = 0x00ff
            self.hibytes = 0x00ff
        if self.TP == 6:
            self.lobytes = 0xffff
            self.hibytes = 0x0000
        if self.TP == 7:
            self.lobytes = 0x0000
            self.hibytes = 0x0000
        if self.TP == 8:
            self.lobytes = 0xffff
            self.hibytes = 0xffff
        if self.TP == 9:
            self.lobytes = 0xf00d
            self.hibytes = 0x8bad

    def send_global(self, parameter, value):
        if parameter == "PS":
            self.PS = value
            GPI = 8
            log.debug("SCREAM PS:", value, tc.ENDC)
        if parameter == "XPT":
            self.XPT = value
            GPI = 9
            log.debug("SCREAM XPT:", value, tc.ENDC)
        if parameter == "TP":
            self.TP = value
            self.TPboolean = 0
            if value != 0:
                self.TPboolean = 1
                self.decode_tp()
                log.debug("SCREAM Test Pattern Hi Byte:", hex(self.hibytes),
                          tc.ENDC)
                GPI = 12
                self.send_cmd(GPI, self.hibytes)
                log.debug("SCREAM Test Pattern Lo Byte:", hex(self.lobytes),
                          tc.ENDC)
                GPI = 13
                self.send_cmd(GPI, self.lobytes)
            GPI = 11
            value = self.TPboolean
            log.debug("SCREAM Test Pattern Boolean:", self.TPboolean, tc.ENDC)
        if parameter == "NSAMP":
            self.NSAMP = value
            GPI = 40
            log.debug("SCREAM NSAMP:", value, tc.ENDC)
        if parameter == "SETT":
            self.SETT = value
            GPI = 41
            log.debug("SCREAM SETT:", value, tc.ENDC)
        if parameter == "CARD":
            self.card_delay = value
            GPI = 42
            log.debug("SCREAM CARD_DELAY:", value, tc.ENDC)
        if parameter == "PROP":
            self.prop_delay = value
            GPI = 43
            log.debug("SCREAM PROP_DELAY:", value, tc.ENDC)
        self.send_cmd(GPI, value)

    def send_ARL(self, parameter, value):
        if parameter == "ARLsense":
            self.ARLsense = value
            GPI = 16
            log.debug("SCREAM ARLsense:", value, tc.ENDC)
        if parameter == "RLDpos":
            self.RLDpos = value
            GPI = 17
            log.debug("SCREAM RLDpos:", value, tc.ENDC)
        if parameter == "RLDneg":
            self.RLDneg = value
            GPI = 18
            log.debug("SCREAM RLDneg:", value, tc.ENDC)
        self.send_cmd(GPI, value)

    def send_triangle(self, parameter, value):
        if parameter == "dwell":
            self.TriDwell = value
            log.debug("SCREAM DWELL:", value)
            self.send_cmd(33, value)
        if parameter == "range":
            self.TriRange = value
            log.debug("SCREAM RANGE:", value)
            self.send_cmd(34, value)
        if parameter == "step":
            self.TriStep = value
            log.debug("SCREAM STEP:", value)
            self.send_cmd(35, value)

    def send_cmd(self, GPI, val):
        wregval = (GPI << 20) | val
        log.debug(tc.COMMAND + "send to card address", self.address, "/ GPI",
                  GPI, ":", tc.BOLD, wregval, "(", val, ")", tc.ENDC)
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
        self.dfbs_widget1.packCHglobals()
        self.dfbs_widget1.packMasterVector()
        #       self.dfbs_widget1.packStates()
        self.dfbs_widget2.packCHglobals()
        self.dfbs_widget2.packMasterVector()
        #       self.dfbs_widget2.packStates()
        self.dfbs_widget3.packCal()
        self.classParameters = {
            'CARDglobals': self.CARDglobals,
            'CHglobals1': self.dfbs_widget1.CHglobals,
            'CHglobals2': self.dfbs_widget2.CHglobals,
            'dfbMasterVector1': self.dfbs_widget1.MasterState,
            'dfbMasterVector2': self.dfbs_widget2.MasterState,
            'CARDphase': self.dfbs_widget3.CalCoeffs,
        }


#                                   'dfbAllStates1'     :   self.dfbs_widget1.allStates,
#                                   'dfbAllStates2'     :   self.dfbs_widget2.allStates,

    def unpackClass(self, classParameters):
        CARDglobals = classParameters['CARDglobals']
        self.unpackCARDglobals(CARDglobals)
        CHglobals1 = classParameters['CHglobals1']
        self.dfbs_widget1.unpackCHglobals(CHglobals1)
        masterVector1 = classParameters['dfbMasterVector1']
        self.dfbs_widget1.unpackMasterVector(masterVector1)
        #       dfbAllStates1 = classParameters['dfbAllStates1']
        #       self.dfbx2_widget1.unpackStates(dfbAllStates1)
        CHglobals2 = classParameters['CHglobals2']
        self.dfbs_widget2.unpackCHglobals(CHglobals2)
        masterVector2 = classParameters['dfbMasterVector2']
        self.dfbs_widget2.unpackMasterVector(masterVector2)
        #       dfbAllStates2 = classParameters['dfbAllStates2']
        #       self.dfbx2_widget2.unpackStates(dfbAllStates2)
        CARDphase = classParameters['CARDphase']
        self.dfbs_widget3.unpackCal(CARDphase)


def main():

    app = QApplication(sys.argv)
    app.setStyle("plastique")
    app.setStyleSheet("""   QPushbutton{font: 10px; padding: 6px}
                            QToolButton{font: 10px; padding: 6px}
                            QLineEdit {background-color: #FFFFCC;}""")
    win = dfbscard(addr=addr, slot=slot, seqln=seqln)
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
    p.set_defaults(addr=3)
    p.set_defaults(slot=3)
    p.set_defaults(seqln=4)
    opt, args = p.parse_args()
    #   ctype = opt.ctype
    addr = opt.addr
    slot = opt.slot
    seqln = opt.seqln
    main()
