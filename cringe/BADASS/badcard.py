import sys
import optparse
import struct
import time

from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import Qt, SIGNAL
from PyQt4.QtGui import QFileDialog, QPalette, QSpinBox, QToolButton

import named_serial
import badrap
import sv_array
import dprcal

# from ./DFBx2.dfbrap import dfbrap
# from ./DFBx2.dprcal import dprcal
# from dprcal import dprcal

class badcard(QtGui.QWidget):

    def __init__(self, parent=None, addr=None, slot=None, seqln=None, lsync=32):

        super(badcard, self).__init__()


        self.COMMAND = '\033[95m'
        self.FCTCALL = '\033[94m'
        self.INIT = '\033[92m'
        self.WARNING = '\033[93m'
        self.FAIL = '\033[91m'
        self.ENDC = '\033[0m'
        self.BOLD = "\033[1m"

        self.green = "90EE90"
        self.red ="F08080"
        self.yellow = "FFFFCC"
        self.grey = "808080"
        self.white = "FFFFFF"
        self.grey = "808080"

        self.serialport = named_serial.Serial(port='rack', shared = True)

        self.chns = 16

        self.parent = parent
        self.address = addr
        self.slot = slot
        self.seqln = seqln
# 		self.lsync = lsync
# 		self.frame = self.lsync * self.seqln

        self.bad_delay = 5
        self.LED = False
        self.ST = False
        self.INT = False

# 		self.wreg0 = (0 << 25) | (self.ST << 16) | (self.LED << 14) | (self.bad_delay << 10) | self.seqln
# 		self.wreg0 = 5128
        self.wreg1 = 34209800
        self.mode = 1


        self.chn_vectors = []
# 		self.enb = [0,0,0,0,0,0,0]
# 		self.cal_coeffs = [0,0,0,0,0,0,0]
# 		self.appTrim =[0,0,0,0,0,0,0]

        self.setWindowTitle("BAD16: %d/%d"%(slot, addr))	# Phase Offset Widget
        self.setGeometry(30,30,800,1000)
        self.setContentsMargins(0,0,0,0)

        self.layout_widget = QtGui.QWidget(self)
        self.layout = QtGui.QGridLayout(self)

        print self.INIT + "building BAD16 card: slot", self.slot, "/ address", self.address, self.ENDC
        print

        '''
        build widget for card INTERFACE PARAMETERS header
        '''
        self.class_interface_widget = QtGui.QGroupBox(self)
        self.class_interface_widget.setFixedWidth(1080)
        self.class_interface_widget.setFocusPolicy(Qt.NoFocus)
        self.class_interface_widget.setTitle("CARD INTERFACE PARAMETERS")

        self.controls_layout = QtGui.QGridLayout(self.class_interface_widget)
        self.controls_layout.setContentsMargins(5,5,5,5)
        self.controls_layout.setSpacing(5)

# 		self.controls_widget = QtGui.QWidget(self.layout_widget)
# 		self.globals_layout = QtGui.QGridLayout(self.globals_widget)		


        self.addr_indicator = QtGui.QLineEdit()
        self.addr_indicator.setReadOnly(True)
        self.addr_indicator.setText(str(addr))
        self.addr_indicator.setAlignment(QtCore.Qt.AlignRight)
        self.addr_indicator.setFocusPolicy(Qt.NoFocus)
        self.controls_layout.addWidget(self.addr_indicator,0,2,1,1,QtCore.Qt.AlignRight)

        self.addr_label = QtGui.QLabel("card address")
        self.controls_layout.addWidget(self.addr_label,0,3,1,1,QtCore.Qt.AlignLeft)

        self.slot_indicator = QtGui.QLineEdit()
        self.slot_indicator.setReadOnly(True)
# 		self.addr_indicator.setFixedWidth(40)
        self.slot_indicator.setText('%2d'%slot)
        self.slot_indicator.setAlignment(QtCore.Qt.AlignRight)
        self.slot_indicator.setFocusPolicy(Qt.NoFocus)
        self.controls_layout.addWidget(self.slot_indicator,0,0,1,1,QtCore.Qt.AlignRight)

        self.slot_label = QtGui.QLabel("card slot")
        self.controls_layout.addWidget(self.slot_label,0,1,1,1,QtCore.Qt.AlignLeft)

        self.layout.addWidget(self.class_interface_widget,0,1,1,1,QtCore.Qt.AlignLeft)

        '''
        build widget for CARD GLOBAL VARIABLE control
        '''
        self.card_glb_widget = QtGui.QGroupBox(self)
        self.card_glb_widget.setTitle("CARD GLOBAL VARIABLES")
        self.card_glb_layout = QtGui.QGridLayout(self.card_glb_widget)
        self.card_glb_layout.setContentsMargins(5,5,10,5)
        self.card_glb_layout.setSpacing(5)

        self.LED_button = QToolButton(self, text = 'ON')
        self.LED_button.setFixedHeight(25)
        self.LED_button.setCheckable(1)
        self.LED_button.setChecked(self.LED)
        self.LED_button.setStyleSheet("background-color: #" + self.green + ";")
        self.card_glb_layout.addWidget(self.LED_button,0,0,1,1)
        self.LED_button.toggled.connect(self.LED_changed)
        self.LED_button.setEnabled(1)

        self.led_lbl = QtGui.QLabel("LED control")
        self.card_glb_layout.addWidget(self.led_lbl,0,1,1,1,QtCore.Qt.AlignLeft)

        self.status_button = QToolButton(self, text = 'ST')
        self.status_button.setFixedHeight(25)
        self.status_button.setCheckable(1)
        self.status_button.setChecked(self.ST)
        self.status_button.setStyleSheet("background-color: #" + self.red + ";")
        self.card_glb_layout.addWidget(self.status_button,0,2,1,1)
        self.status_button.toggled.connect(self.status_changed)

        self.status_lbl = QtGui.QLabel("status bit")
        self.card_glb_layout.addWidget(self.status_lbl,0,3,1,1,QtCore.Qt.AlignLeft)

        self.card_glb_send = QtGui.QPushButton(self, text = "send CARD globals")
        self.card_glb_send.setFixedHeight(25)
        self.card_glb_send.setFixedWidth(200)
        self.card_glb_layout.addWidget(self.card_glb_send,0,4,1,1,QtCore.Qt.AlignRight)
        self.card_glb_send.clicked.connect(self.send_card_globals)

        self.layout.addWidget(self.card_glb_widget,0,0,1,1,QtCore.Qt.AlignRight)

        '''
        create TAB widget for embedding BAD16 functional widgets
        '''
        self.bad16_widget = QtGui.QTabWidget(self)
        self.bad16_widget.setFixedWidth(1100)

        self.badrap_widget1 = badrap.badrap(parent=self, addr=addr, slot=slot, seqln=seqln, lsync=lsync)
        self.scale_factor = self.badrap_widget1.master_vector.width()
        self.bad16_widget.addTab(self.badrap_widget1, " channels ")

        self.badrap_widget2 = sv_array.SV_array(parent=self, seqln=seqln, addr=addr)
        self.bad16_widget.addTab(self.badrap_widget2, " states ")

        self.badrap_widget3 = dprcal.dprcal(ctype="BAD16", addr=addr, slot=slot)
        self.bad16_widget.addTab(self.badrap_widget3, " phase ")

        self.layout.addWidget(self.bad16_widget,1,0,1,2,QtCore.Qt.AlignHCenter)

        '''
        resize widgets for relative, platform dependent variability
        '''
        self.scale_factor = self.badrap_widget1.arrayframe.width()


        rm = 10
        self.bad16_widget.setFixedWidth(self.scale_factor*1.05)
        self.class_interface_widget.setFixedWidth((self.scale_factor*1.05)/2 - rm/2)
        self.card_glb_widget.setFixedWidth((self.scale_factor*1.05)/2 - rm/2)
# 		self.file_mgmt_widget.setFixedWidth(self.badrap_widget1.arrayframe.width()+rm)
# 		self.sys_glob_hdr_widget.setFixedWidth(self.badrap_widget1.arrayframe.width()+rm)
# 		self.class_glob_hdr_widget.setFixedWidth(self.badrap_widget1.arrayframe.width()+rm)
# 		self.class_interface_widget.setFixedWidth(self.badrap_widget1.arrayframe.width()+rm)


    def seqln_changed(self, seqln):
        print self.FCTCALL + "send SEQLN to BAD16 card:", self.ENDC
        self.seqln = seqln
        self.send_wreg0()
# 		self.wreg0 = ((self.wreg0 & 0xFFFFF00) | self.seqln)
# 		self.send_wreg0()
        self.badrap_widget2.seqln_changed(seqln)
        print

    def LED_changed(self):
        print self.FCTCALL + "send LED boolean (True = OFF) to BAD16 card:" + self.ENDC
        self.LED = self.LED_button.isChecked()
        if self.LED ==1:
            self.LED_button.setStyleSheet("background-color: #" + self.red + ";")
            self.LED_button.setText('OFF')
        else:
            self.LED_button.setStyleSheet("background-color: #" + self.green + ";")
            self.LED_button.setText('ON')
        self.send_wreg0()
        print

    def status_changed(self):
        print self.FCTCALL + "send ST boolean to BAD16 card:" + self.ENDC
        self.ST = self.status_button.isChecked()
        if self.ST ==1:
            self.status_button.setStyleSheet("background-color: #" + self.green + ";")
        else:
            self.status_button.setStyleSheet("background-color: #" + self.red + ";")
        self.send_wreg0()
        self.badrap_widget3.enbDiagnostic(self.ST)
        print

    def initMem(self, init):
        self.init_state = self.INT
        self.INT = init
        if self.INT != self.init_state:
            if self.INT == 1:
                print self.FCTCALL + "BAD16 state vector memory initialized: update init status boolean: 1" + self.ENDC
            else:
                print self.FCTCALL + "BAD16 state vector memory contents updated: update init status boolean: 0" + self.ENDC
            self.send_wreg0()
            print

    def send_triangle(self, wreg1):
        print self.FCTCALL + "send triangle parameters to BAD16 card:", self.ENDC
        self.wreg1 = wreg1
        self.send_wreg1()
        print

    def send_class_globals(self, wreg0):
        print self.FCTCALL + "send card globals to BAD16 card:", self.ENDC
        self.wreg0 = wreg0
        self.send_wreg0()
        print

    def send_card_globals(self):
        print self.FCTCALL + "send card globals to BAD16 card:", self.ENDC
        self.send_wreg0()
        print

# 	def card_delay_changed(self):
# 		'''
# 		not sure what the best structure is for class global commanding
# 		at child level need to change control to indicator (QSpinBOx to QLineEdit)
# 		1 - can preserve function call triggered from within child as 'QLineEdit.textChanged'
# 		or
# 		2 - can pass parent.QSpinBox.value() to child function as parameter
# 		'''
# 		self.badrap_widget1.card_delay.setText(str("%2d"%self.card_delay.value()))
# 		self.badrap_widget1.card_delay_changed(self.card_delay.value())

    def send_wreg0(self):
        if self.parent != None:
            self.parent.send_bad16_wreg0(self.ST, self.LED, self.INT, self.address)
        else:
            print "BAD16:WREG0: ST, LED, card delay, INIT, sequence length:", self.ST, self.LED, self.bad_delay, self.INT, self.seqln
            print
            self.wreg0 = (0 << 25) | (self.ST << 16) | (self.LED << 14) | (self.bad_delay << 10) | (self.INT << 8) | self.seqln
            self.sendReg(self.wreg0)

    def send_wreg1(self):
        cmd_reg = bin(self.wreg1)[5:].zfill(25)
        dwell = int(cmd_reg[1:5], base=2)
        steps = int(cmd_reg[5:9], base=2)
        step = int(cmd_reg[11:], base=2)
        print "BAD16:WREG1: triangle parameters DWELL, STEPS, STEP SIZE:", dwell, steps, step
        self.sendReg(self.wreg1)
        print

    def sendReg(self, wregval):
        print self.COMMAND + "send to address", self.address, ":", self.BOLD, wregval, self.ENDC
        b0 = (wregval & 0x7f ) << 1			# 1st 7 bits shifted up 1
        b1 = ((wregval >> 7) & 0x7f) <<  1	 # 2nd 7 bits shifted up 1
        b2 = ((wregval >> 14) & 0x7f) << 1	 # 3rd 7 bits shifted up 1
        b3 = ((wregval >> 21) & 0x7f) << 1	 # 4th 7 bits shifted up 1
        b4 = (self.address << 1) + 1		   # Address shifted up 1 bit with address bit set
        msg = struct.pack('BBBBB', b0, b1, b2, b3, b4)
        self.serialport.write(msg)
        time.sleep(0.001)

    def packCARDglobals(self):
        self.CARDglobals = {	'LED'	:	self.LED_button.isChecked(),
                                'ST'	:	self.status_button.isChecked()}

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
                                'CARDglobals'		:	self.CARDglobals,
                                'bad16MasterVector'	:	self.badrap_widget1.MasterState,
                                'badAllChannels'	:	self.badrap_widget1.allChannels,
                                'badAllStates'		:	self.badrap_widget2.allStates,
                                'CARDphase'			:	self.badrap_widget3.CalCoeffs,
                                'states'			:	self.badrap_widget2.packState(),
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

    app = QtGui.QApplication(sys.argv)
    app.setStyle("plastique")
    app.setStyleSheet("""	QPushbutton{font: 10px; padding: 6px}
                            QToolButton{font: 10px; padding: 6px}
                            QLineEdit {background-color: #FFFFCC;}
                            QToolTip {background-color: #FFFFCC;}""")
    win = badcard(addr=addr, slot=slot, seqln=seqln)
    win.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    p = optparse.OptionParser()
# 	p.add_option('-C','--card_type', action='store', dest='ctype', type='str',
# 				 help='Type of card to calibrate (default=DFBx2).')
    p.add_option('-A','--card_address', action='store', dest='addr', type='int',
                 help='Hardware address of card (default=32).')
    p.add_option('-S','--slot', action='store', dest='slot', type='int',
                 help='Host slot in crate (default=9)')
    p.add_option('-L','--length', action='store', dest='seqln', type='int',
                 help='Number of states in sequence (default=4')
# 	p.set_defaults(ctype="DFBx2")
    p.set_defaults(addr=32)
    p.set_defaults(slot=9)
    p.set_defaults(seqln=4)
    opt, args = p.parse_args()
# 	ctype = opt.ctype
    addr = opt.addr
    slot = opt.slot
    seqln = opt.seqln
    main()

