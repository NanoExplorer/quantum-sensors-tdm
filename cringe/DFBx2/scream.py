import sys
import optparse

from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

import named_serial
from .dfbchn import dfbChn
from cringe.shared import terminal_colors as tc
from cringe.shared import log
from cringe.shared.rack_transport import write_wreg

class scream(QWidget):
    def __init__(self, parent=None, addr=None, slot=None, channel=1, lsync=32):
        
        super(scream, self).__init__()

        self.parent = parent
        self.address = addr
        self.slot = slot
        self.lsync = lsync
        self.ch = channel

        self.serialport = named_serial.Serial(port='rack', shared = True)
            
#       self.delay = 0
        
        '''global booleans'''
        
        self.GR = True
        self.ENC = True

        self.LED = False
        self.ST = False
        self.PS = False
        self.CLK = False
        
        '''global variables'''
        
        self.XPT = 0
        self.NSAMP = 4
        self.prop_delay = 0
        self.card_delay = 0
#       self.seqln = seqln
        self.SETT = 12
        
        '''ARL parameters'''
        
        self.ARLsense = 0
        self.RLDpos = 0
        self.RLDneg = 0
        
#       self.frame_period = self.lsync * self.seqln * 0.008
        
            
        '''triangle parameters'''
        
        self.dwell_val = 0
        self.dwellDACunits = float(0)
        self.range_val = 1
        self.rangeDACunits = float(2)
        self.step_val = 1
        self.stepDACunits = float(1)
        self.tri_idx = 0

#       self.frame = self.lsync * self.seqln
        self.mode = 1
        self.wreg4 = 134905864
        self.force_cmd = 0

                
        self.state_vectors = []
        self.allStates = {}
#       self.enb = [0,0,0,0,0,0,0]
#       self.cal_coeffs = [0,0,0,0,0,0,0]
#       self.appTrim =[0,0,0,0,0,0,0]

        self.setWindowTitle("SCREAM")
        self.setGeometry(30,30,1200,800)
        self.setContentsMargins(0,0,0,0)
        
        self.layout_widget = QWidget(self)
        self.layout = QVBoxLayout(self)
    
        
        '''
        build widget for CHANNEL GLOBAL VARIABLE control
        '''
        self.glb_var_widget = QGroupBox(self)
        self.glb_var_widget.setTitle("CHANNEL GLOBAL VARIABLES")
        self.glb_var_layout = QGridLayout(self.glb_var_widget)
        self.glb_var_layout.setContentsMargins(5,5,10,5)
        self.glb_var_layout.setSpacing(5)

        self.GR_button = QToolButton(self, text = 'ENB')
        self.GR_button.setFixedHeight(25)
        self.GR_button.setCheckable(1)
        self.GR_button.setChecked(self.GR)
        self.GR_button.setStyleSheet("background-color: #" + tc.green + ";")
        self.glb_var_layout.addWidget(self.GR_button,0,0,1,1)
        self.GR_button.toggled.connect(self.GR_changed)

        self.led_lbl = QLabel("channel lock enable")
        self.glb_var_layout.addWidget(self.led_lbl,0,1,1,1,QtCore.Qt.AlignLeft)

        self.ENC_button = QToolButton(self, text = '8b10b')
        self.ENC_button.setFixedHeight(25)
        self.ENC_button.setCheckable(1)
        self.ENC_button.setChecked(self.ENC)
        self.ENC_button.setEnabled(0)
        self.ENC_button.setStyleSheet("background-color: #" + tc.green + ";")
        self.glb_var_layout.addWidget(self.ENC_button,0,2,1,1)
        self.ENC_button.toggled.connect(self.ENC_changed)

        self.led_lbl = QLabel("encode data stream")
        self.glb_var_layout.addWidget(self.led_lbl,0,3,1,1,QtCore.Qt.AlignLeft)
                
        self.glb_send = QPushButton(self, text = "send CHANNEL globals")
        self.glb_send.setFixedHeight(25)
        self.glb_send.setFixedWidth(200)
        self.glb_var_layout.addWidget(self.glb_send,0,10,1,1,QtCore.Qt.AlignRight)
        self.glb_send.clicked.connect(self.send_channel_globals)

        self.layout.addWidget(self.glb_var_widget, QtCore.Qt.AlignTop)

        '''
        build widget for MASTER CONTROL VECTOR: these controls effect all channels on a card
        '''
        self.master_ctrl_widget = QGroupBox(self)
        self.master_ctrl_widget.setTitle("SINGLE CHANNEL CONTROL VECTOR")
        self.master_ctrl_layout = QGridLayout(self.master_ctrl_widget)

        self.master_vector = dfbChn(self, self.master_ctrl_layout, state=-1, chn=0, cardaddr=self.address, serialport=self.serialport, master = 'master')
        self.master_vector.counter_label.setText("0")
        self.master_vector.chn_send.setText("send")
        self.master_vector.counter_label.hide()
        self.master_vector.chn_lbl.hide()
        
        self.layout.addWidget(self.master_ctrl_widget, QtCore.Qt.AlignTop)
        
        '''
        scale widgets
        '''

        self.master_ctrl_widget.setFixedHeight(self.master_vector.height()/4)
        self.glb_var_widget.setFixedHeight(self.master_vector.height()/8)

    '''
    child called methods
    '''                     
    def triA_changed(self, state):
        
        log.debug(tc.FCTCALL + "SCREAM CH", self.ch, "triangle A enable:", state, tc.ENDC)
        GPI = (self.ch - 1) * 24 + 50
        self.send_cmd(GPI, state)
        if state == 1:
            self.master_vector.TriA_button.setStyleSheet("background-color: #" + tc.green + ";")
        else:
            self.master_vector.TriA_button.setStyleSheet("background-color: #" + tc.red + ";")
            
    def triB_changed(self, state):
        
        log.debug(tc.FCTCALL + "SCREAM CH", self.ch, "triangle B enable:", state, tc.ENDC)
        GPI = (self.ch - 1) * 24 + 51
        self.send_cmd(GPI, state)
        if state == 1:
            self.master_vector.TriB_button.setStyleSheet("background-color: #" + tc.green + ";")
        else:
            self.master_vector.TriB_button.setStyleSheet("background-color: #" + tc.red + ";")
            
    def a2d_lockpt_spin_changed(self, level):
        if self.master_vector.lock_button.isChecked() or self.force_cmd == 1:
            
            log.debug(tc.FCTCALL + "SCREAM CH", self.ch, "ADC lock point:", level, tc.ENDC)
            GPI = (self.ch - 1) * 24 + 56
            self.send_cmd(GPI, level)
        self.master_vector.a2d_lockpt_slider.setValue(level)
            
    def a2d_lockpt_slider_changed(self, level):
        self.master_vector.a2d_lockpt_spin.setValue(level)
    
    def d2a_A_spin_changed(self, level):
        if self.master_vector.lock_button.isChecked() or self.force_cmd == 1:
            
            log.debug(tc.FCTCALL + "SCREAM CH", self.ch, "DAC A offset:", level, tc.ENDC)
            GPI = (self.ch - 1) * 24 + 57
            self.send_cmd(GPI, level)
        self.master_vector.d2a_A_slider.setValue(level)
            
    def d2a_A_slider_changed(self, level):
        self.master_vector.d2a_A_spin.setValue(level)
        
    def d2a_B_spin_changed(self, level):
        if self.master_vector.lock_button.isChecked() or self.force_cmd == 1:
            
            log.debug(tc.FCTCALL + "SCREAM CH", self.ch, "DAC B offset:", level, tc.ENDC)
            GPI = (self.ch - 1) * 24 + 58
            self.send_cmd(GPI, level)
        self.master_vector.d2a_B_slider.setValue(level)
            
    def d2a_B_slider_changed(self, level):
        self.master_vector.d2a_B_spin.setValue(level)
        
    def data_packet_changed(self, index):
        if self.master_vector.lock_button.isChecked() or self.force_cmd == 1:
            
            log.debug(tc.FCTCALL + "SCREAM CH", self.ch, "SEND MODE:", index, tc.ENDC)
            GPI = (self.ch - 1) * 24 + 64
            self.send_cmd(GPI, index)

    def P_spin_changed(self, level):
        if self.master_vector.lock_button.isChecked() or self.force_cmd == 1:
            
            log.debug(tc.FCTCALL + "SCREAM CH", self.ch, "P:", level, tc.ENDC)
            GPI = (self.ch - 1) * 24 + 59
            level = level & 0b1111111111
            self.send_cmd(GPI, level)

    def I_spin_changed(self, level):
        if self.master_vector.lock_button.isChecked() or self.force_cmd == 1:
            
            log.debug(tc.FCTCALL + "SCREAM CH", self.ch, "I:", level, tc.ENDC)
            GPI = (self.ch - 1) * 24 + 60
            level = level & 0b1111111111
            self.send_cmd(GPI, level)
            
    def FBA_changed(self, state):
        
        log.debug(tc.FCTCALL + "SCREAM CH", self.ch, "FB A enable:", state, tc.ENDC)
        GPI = (self.ch - 1) * 24 + 48
        self.send_cmd(GPI, state)
        if state == 1:
            self.master_vector.FBA_button.setStyleSheet("background-color: #" + tc.green + ";")
            self.master_vector.FBB_button.setChecked(0)
        else:
            self.master_vector.FBA_button.setStyleSheet("background-color: #" + tc.red + ";")
            
    def FBB_changed(self, state):
        
        log.debug(tc.FCTCALL + "SCREAM CH", self.ch, "FB B enable:", state, tc.ENDC)
        GPI = (self.ch - 1) * 24 + 49
        self.send_cmd(GPI, state)
        if state == 1:
            self.master_vector.FBB_button.setStyleSheet("background-color: #" + tc.green + ";")
            self.master_vector.FBA_button.setChecked(0)
        else:
            self.master_vector.FBB_button.setStyleSheet("background-color: #" + tc.red + ";")
            
    def ARL_changed(self, state):
        
        log.debug(tc.FCTCALL + "SCREAM CH", self.ch, "ARL enable:", state, tc.ENDC)
        GPI = (self.ch - 1) * 24 + 52
        self.send_cmd(GPI, state)
        if state == 1:
            self.master_vector.ARL_button.setStyleSheet("background-color: #" + tc.green + ";")
        else:
            self.master_vector.ARL_button.setStyleSheet("background-color: #" + tc.red + ";")
            
                        
    '''
    self called methods
    '''

    def send_channel_globals(self):
        
        log.debug(tc.FCTCALL + "send channel globals to SCREAM channel", self.ch, tc.ENDC)
        self.GR_changed()

    def GR_changed(self):
        self.GR = self.GR_button.isChecked()
        log.debug("SCREAM channel", self.ch, "global relock enable:", self.GR, tc.ENDC)
        if self.GR == 1:
            self.GR_button.setStyleSheet("background-color: #" + tc.green + ";")
            self.GR_button.setText('ENB')
        else:
            self.GR_button.setStyleSheet("background-color: #" + tc.red + ";")          
            self.GR_button.setText('OFF')
        GPI = 3 + self.ch
        self.send_cmd(GPI, self.GR)

    def ENC_changed(self):
        self.ENC = self.ENC_button.isChecked()
        log.debug("SCREAM channel", self.ch, "encode data enable:", self.ENC, tc.ENDC)
        if self.ENC == 1:
            self.ENC_button.setStyleSheet("background-color: #" + tc.green + ";")
            self.ENC_button.setText('8b10b')
        else:
            self.ENC_button.setStyleSheet("background-color: #" + tc.red + ";")         
            self.ENC_button.setText('raw')
        GPI = 13 + self.ch
        self.send_cmd(GPI, self.ENC)
            
    def enbDiagnostic(self, mode):
        self.ENC_button.setEnabled(mode)
    
    def send_channel(self):
        
        log.debug(tc.FCTCALL + "send SCREAM CH", self.ch, "control parameters:", tc.ENDC)
        self.force_cmd = 1
        self.triA_changed(self.master_vector.TriA_button.isChecked())
        self.triB_changed(self.master_vector.TriB_button.isChecked())
        self.a2d_lockpt_spin_changed(self.master_vector.a2d_lockpt_spin.value())
        self.d2a_A_spin_changed(self.master_vector.d2a_A_spin.value())
        self.d2a_B_spin_changed(self.master_vector.d2a_B_spin.value())
        self.data_packet_changed(self.master_vector.data_packet.currentIndex())
        self.P_spin_changed(self.master_vector.P_spin.value())
        self.I_spin_changed(self.master_vector.I_spin.value())
        self.FBA_changed(self.master_vector.FBA_button.isChecked())
        self.FBB_changed(self.master_vector.FBB_button.isChecked())
        self.ARL_changed(self.master_vector.ARL_button.isChecked())
        self.force_cmd = 0

    def send_card_globals(self):
        
        log.debug(tc.FCTCALL + "send class globals:", tc.ENDC)
        self.send_wreg0()
        self.send_wreg4()
        self.send_wreg6()
        self.send_wreg7()
        
        
    def lock_channel(self, state):
        self.master_vector.lock_button.setChecked(state)
        if state == 1:
            self.master_vector.lock_button.setStyleSheet("background-color: #" + tc.green + ";")
            self.master_vector.lock_button.setText('dynamic')
        else:
            self.master_vector.lock_button.setStyleSheet("background-color: #" + tc.red + ";")          
            self.master_vector.lock_button.setText('static')
        
    def card_delay_changed(self, value):
        self.card_delay = value
        if self.mode == 1:
            self.send_wreg7()
        
    def prop_delay_changed(self):
        self.prop_delay = self.prop_delay_spin.value()
        if self.mode == 1:
            self.send_wreg7()
        
    def XPT_changed(self):
        self.XPT = self.xpt_mode.currentIndex()
        if self.mode == 1:
            self.send_wreg6()
            
    def NSAMP_changed(self):
        self.NSAMP = self.NSAMP_spin.value()
        if self.mode == 1:
            self.send_wreg6()
            
    def SETT_changed(self):
        self.SETT = self.SETT_spin.value()
        if self.mode == 1:
            self.send_wreg7()

    def PS_changed(self):
        self.PS = self.PS_button.isChecked()
        if self.PS ==1:
            self.PS_button.setStyleSheet("background-color: #" + tc.green + ";")
        else:
            self.PS_button.setStyleSheet("background-color: #" + tc.red + ";")          
        self.send_wreg6()
        
    def ARLsense_changed(self):
        self.ARLsense = self.ARLsense_spin.value()
        self.ARLsense_indicator.setText("%5i"%(2**self.ARLsense))
        self.ARLsense_eng_indicator.setText(str((2**self.ARLsense)/16.383)[:6])
        self.send_wreg6()
        
    def RLDpos_changed(self):
        self.RLDpos = self.RLDpos_spin.value()
        self.RLDpos_indicator.setText("%5i"%(2**self.RLDpos))
        self.RLDpos_eng_indicator.setText(str((2**self.RLDpos)*self.frame_period)[:6])
        self.send_wreg6()
        
    def RLDneg_changed(self):
        self.RLDneg = self.RLDneg_spin.value()
        self.RLDneg_indicator.setText("%5i"%(2**self.RLDneg))
        self.RLDneg_eng_indicator.setText(str((2**self.RLDneg)*self.frame_period)[:6])
        self.send_wreg6()

    def LED_changed(self):
        self.LED = self.LED_button.isChecked()
        if self.LED ==1:
            self.LED_button.setStyleSheet("background-color: #" + tc.red + ";")         
            self.LED_button.setText('OFF')
        else:
            self.LED_button.setStyleSheet("background-color: #" + tc.green + ";")
            self.LED_button.setText('ON')
#        if self.unlocked == 1:
        self.send_wreg7()

    def status_changed(self):
        self.ST = self.status_button.isChecked()
        if self.ST ==1:
            self.status_button.setStyleSheet("background-color: #" + tc.green + ";")
        else:
            self.status_button.setStyleSheet("background-color: #" + tc.red + ";")          
        self.send_wreg7()


#   def mode_changed(self):
#       self.mode = self.mode_button.isChecked()
#       if self.mode ==1:
#           self.mode_button.setStyleSheet("background-color: #" + tc.green + ";")
#           self.mode_button.setText('dynamic')
#       else:
#           self.mode_button.setStyleSheet("background-color: #" + tc.red + ";")            
#           self.mode_button.setText('static')

    def dwell_changed(self):
        self.dwell_val = self.dwell.value()
        self.dwellDACunits = 2**(self.dwell_val)
        self.dwell_indicator.setText('%5i'%self.dwellDACunits)
        self.period_changed()
        if self.mode == 1:
            self.send_wreg0()
            self.send_wreg4()

    def range_changed(self):
        self.range_val = self.range.value()
        self.rangeDACunits = 2**self.range_val
        self.range_indicator.setText('%5i'%self.rangeDACunits)
        self.amp_changed()
        self.period_changed()
#       periodDACunits = 2*2**self.dwell_val*2**self.range_val
#       self.period_indicator.setText('%11i'%periodDACunits)
#       self.period_eng_indicator.setText('%12.4d'%periodDACunits*self.lsync*0.008)
#       self.freq_eng_indicator.setText(str(1000/float(self.period_eng_indicator.text()))[:6])
        if self.mode == 1:
            self.send_wreg0()
            self.send_wreg4()

    def step_changed(self):
        self.step_val = self.step.value()
        self.stepDACunits = self.step_val
        self.amp_changed()
#       self.period_changed()
#       self.amp_indicator.setText(str((2**self.range_val)*self.step_val))
#       self.amp_eng_indicator.setText(str(int(self.amp_indicator.text())/16.383)[:6])
        if self.mode == 1:
            self.send_wreg0()
            self.send_wreg4()
            
    def amp_changed(self):
        log.debug("amp_changed")
        self.ampDACunits = self.rangeDACunits * self.stepDACunits
        log.debug(self.ampDACunits)
        if self.ampDACunits > 16383:
            self.ampDACunits = 16383
        self.amp_indicator.setText('%5i'%self.ampDACunits)
        mV = 1000*self.ampDACunits/16383.0
        log.debug(mV, str(mV))
        self.amp_eng_indicator.setText('%4.3f'%mV)
#       self.amp_eng_indicator.setText('%6.3d'%volts)
        
    def period_changed(self):
        log.debug("period changed")
        self.periodDACunits = float(2*self.dwellDACunits*self.rangeDACunits)
        self.period_indicator.setText('%12i'%self.periodDACunits)
        uSecs = self.periodDACunits*self.lsync*0.008
        log.debug(uSecs)
        kHz = 1000/uSecs
        log.debug(kHz)
        self.period_eng_indicator.setText('%8.4f'%uSecs)
        self.freq_eng_indicator.setText('%6.3f'%kHz)


    def tri_idx_changed(self):
        self.tri_idx = self.tri_idx_button.isChecked()
        if self.tri_idx ==1:
            self.tri_idx_button.setStyleSheet("background-color: #" + tc.green + ";")
            self.tri_idx_button.setText('FRAME')
        else:
            self.tri_idx_button.setStyleSheet("background-color: #" + tc.red + ";")         
            self.tri_idx_button.setText('LSYNC')
        self.send_wreg0()
        self.send_wreg4()

    def send_wreg0(self):
        log.debug("WREG0: page register: COL", self.col)
        wreg = 0 << 25
        wregval = wreg + (self.col << 6)
        self.sendReg(wregval)

    def send_wreg4(self, wreg4):
        if self.parent != None:
            self.parent.parent.send_dfb_wreg4(self.GR, self.address)
        else:
#       print "WREG4: triangle parameters & GR"
            self.wreg4 = wreg4
#       self.wreg4 = parent.parent.dfb_wreg4()
            cmd_reg = bin(self.wreg4)[5:].zfill(25)
            dwell = int(cmd_reg[1:5], base=2)
            steps = int(cmd_reg[5:9], base=2)
            step = int(cmd_reg[11:], base=2)
            log.debug("WREG4: triangle parameters DWELL, STEPS, STEP SIZE (& global relock):", dwell, steps, step, "(",self.GR,")") 
            self.sendReg((self.wreg4 & 0xFFF7FFF) | (self.GR << 15))

    def sendReg(self, wregval): 
        write_wreg(self.serialport, wregval, self.address)
        
    def send_cmd(self, GPI, val): 
        wregval = (GPI << 20) | val
        log.debug(tc.COMMAND + "send to card address", self.address, "/ GPI", GPI, ":", tc.BOLD, wregval, "(", val, ")",tc.ENDC)
        write_wreg(self.serialport, wregval, self.address)
        
    def packCHglobals(self):
        self.CHglobals = {  'enb'   :   self.GR_button.isChecked(),
                            'enc'   :   self.ENC_button.isChecked()}
        
    def unpackCHglobals(self, CHglobals):
        self.GR_button.setChecked(CHglobals['enb'])
        self.ENC_button.setChecked(CHglobals['enc'])

    def packMasterVector(self):
        self.MasterState    =   {
            'triA'          :   self.master_vector.TriA_button.isChecked(),
            'triB'          :   self.master_vector.TriB_button.isChecked(),
            'a2d_lockpt'    :   self.master_vector.a2d_lockpt_spin.value(),
            'd2a_A'         :   self.master_vector.d2a_A_spin.value(),
            'd2a_B'         :   self.master_vector.d2a_B_spin.value(),
            'SM'            :   self.master_vector.data_packet.currentIndex(),
            'P'             :   self.master_vector.P_spin.value(),
            'I'             :   self.master_vector.I_spin.value(),
            'FBA'           :   self.master_vector.FBA_button.isChecked(),
            'FBB'           :   self.master_vector.FBB_button.isChecked(),
            'ARL'           :   self.master_vector.ARL_button.isChecked()
                                }
        
    def unpackMasterVector(self, masterVector):
        self.master_vector.TriA_button.setChecked(masterVector['triA'])
        self.master_vector.TriB_button.setChecked(masterVector['triB'])
        self.master_vector.a2d_lockpt_spin.setValue(masterVector['a2d_lockpt'])
        self.master_vector.d2a_A_spin.setValue(masterVector['d2a_A'])
        self.master_vector.d2a_B_spin.setValue(masterVector['d2a_B'])
        self.master_vector.data_packet.setCurrentIndex(masterVector['SM'])
        self.master_vector.P_spin.setValue(masterVector['P'])
        self.master_vector.I_spin.setValue(masterVector['I'])
        self.master_vector.FBA_button.setChecked(masterVector['FBA'])
        self.master_vector.FBB_button.setChecked(masterVector['FBB'])
        self.master_vector.ARL_button.setChecked(masterVector['ARL'])
            


    
    
