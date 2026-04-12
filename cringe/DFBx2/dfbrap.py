from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

import named_serial
from .dfbchn import dfbChn
from cringe.shared import terminal_colors as tc
from cringe.shared import log
from cringe.shared.rack_transport import write_wreg


class dfbrap(QWidget):

#   def __init__(self, parent=None, **kwargs):
#       print kwargs
    def __init__(self, parent=None, addr=None, slot=None, column=1, seqln=None, lsync=32):

        super(dfbrap, self).__init__()

        self.parent = parent
        self.address = addr
        self.slot = slot
        self.lsync = lsync
        self.col = column

        self.chID = str(slot) + "/" + str(addr) + "/" + str(column)

        self.serialport = named_serial.Serial(port='rack', shared = True)

        self.states = 64

#       self.delay = 0

        '''global booleans'''

        self.GR = True

        self.LED = False
        self.ST = False
        self.PS = False
        self.CLK = False

        '''global variables'''

        self.XPT = 0
        self.NSAMP = 4
        self.prop_delay = 0
        self.card_delay = 0
        self.seqln = seqln
        self.SETT = 12

        '''ARL parameters'''

        self.ARLsense = 0
        self.RLDpos = 0
        self.RLDneg = 0

        self.frame_period = self.lsync * self.seqln * 0.008


        '''triangle parameters'''

        self.dwell_val = 0
        self.dwellDACunits = float(0)
        self.range_val = 1
        self.rangeDACunits = float(2)
        self.step_val = 1
        self.stepDACunits = float(1)
        self.tri_idx = 0

        self.MVTX = 0
        self.MVRX = 1

#       self.frame = self.lsync * self.seqln
        self.mode = 1
        self.wreg4 = 134905864

        self.state_vectors = []
        self.allStates = {}
#       self.enb = [0,0,0,0,0,0,0]
#       self.cal_coeffs = [0,0,0,0,0,0,0]
#       self.appTrim =[0,0,0,0,0,0,0]

        self.setWindowTitle("DFBRAP")   # Phase Offset Widget
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

        self.MSTR_TX = QToolButton(self, text = 'OFF')
        self.MSTR_TX.setFixedHeight(25)
        self.MSTR_TX.setCheckable(1)
        self.MSTR_TX.setChecked(self.MVTX)
        self.MSTR_TX.setStyleSheet("background-color: #" + tc.red + ";")
        self.glb_var_layout.addWidget(self.MSTR_TX,0,0,1,1)
        self.MSTR_TX.toggled.connect(self.MSTR_TX_changed)

        self.MSTR_TX_lbl = QLabel("MASTER VECTOR Broadcast")
        self.glb_var_layout.addWidget(self.MSTR_TX_lbl,0,1,1,1,QtCore.Qt.AlignLeft)

        self.MSTR_RX = QToolButton(self, text = 'RX')
        self.MSTR_RX.setFixedHeight(25)
        self.MSTR_RX.setCheckable(1)
        self.MSTR_RX.setChecked(self.MVRX)
        self.MSTR_RX.setStyleSheet("background-color: #" + tc.green + ";")
        self.glb_var_layout.addWidget(self.MSTR_RX,0,2,1,1)
        self.MSTR_RX.toggled.connect(self.MSTR_RX_changed)

        self.MSTR_RX_lbl = QLabel("MASTER VECTOR Echo")
        self.glb_var_layout.addWidget(self.MSTR_RX_lbl,0,3,1,4,QtCore.Qt.AlignLeft)

        self.GR_button = QToolButton(self, text = 'ENB')
        self.GR_button.setFixedHeight(25)
        self.GR_button.setCheckable(1)
        self.GR_button.setChecked(self.GR)
        self.GR_button.setStyleSheet("background-color: #" + tc.green + ";")
        self.glb_var_layout.addWidget(self.GR_button,0,8,1,1)
        self.GR_button.toggled.connect(self.GR_changed)

        self.led_lbl = QLabel("channel lock enable")
        self.glb_var_layout.addWidget(self.led_lbl,0,7,1,1,QtCore.Qt.AlignRight)

        self.glb_send = QPushButton(self, text = "send CHANNEL globals")
        self.glb_send.setFixedHeight(25)
        self.glb_send.setFixedWidth(200)
        self.glb_var_layout.addWidget(self.glb_send,0,10,1,2,QtCore.Qt.AlignRight)
        self.glb_send.clicked.connect(self.send_channel_globals)

        self.layout.addWidget(self.glb_var_widget)

        '''
        build widget for MASTER CONTROL VECTOR: these controls effect all channels on a card
        '''
        self.master_ctrl_widget = QGroupBox(self)
        self.master_ctrl_widget.setTitle("MASTER CONTROL VECTOR")
        self.master_ctrl_layout = QGridLayout(self.master_ctrl_widget)

        self.master_vector = dfbChn(self, self.master_ctrl_layout, state=-1, chn=0, cardaddr=self.address, serialport=self.serialport, master = 'master')
        self.master_vector.counter_label.setText("all")
        self.master_vector.chn_send.setText("send ALL")

        self.layout.addWidget(self.master_ctrl_widget)

        '''
        build widget for arrayed channel parameters
        '''
        self.arrayframe = QWidget(self.layout_widget)
        self.array_layout = QVBoxLayout(self.arrayframe)
        self.array_layout.setSpacing(5)
        self.array_layout.setContentsMargins(10,10,10,10)

        for idx in range(self.states):
            self.state_vectors.append(dfbChn(self, self.array_layout, state=idx, chn=column, cardaddr=self.address, serialport=self.serialport))
#
        self.scrollarea = QScrollArea(self.layout_widget)
        self.scrollarea.setWidget(self.arrayframe)
        self.layout.addWidget(self.scrollarea)
#       self.show()
#       print self.arrayframe.width()

        self.master_ctrl_widget.setFixedWidth(self.arrayframe.width()+0)
        self.glb_var_widget.setFixedWidth(self.arrayframe.width()+0)
#       self.class_interface_widget.setFixedWidth(self.arrayframe.width()+0)

    def __str__(self):
        return "dfbrap: slot/addr %g/%g channel %g"%(self.slot, self.address, self.col)

    def __repr__(self):
        return self.__str__()

    '''
    child called methods
    '''
    def triA_changed(self, state, *bc):
        var = "triA"
        if (not(bc) and self.MVTX) == True:
            self.parent.parent.broadcast_channel(state, var)
        else:
            for idx in range(self.states):
                self.state_vectors[idx].TriA_button.setChecked(state)
                if state == 1:
                    self.master_vector.TriA_button.setStyleSheet("background-color: #" + tc.green + ";")
                else:
                    self.master_vector.TriA_button.setStyleSheet("background-color: #" + tc.red + ";")

    def triB_changed(self, state, *bc):
        var = "triB"
        if (not(bc) and self.MVTX) == True:
            self.parent.parent.broadcast_channel(state, var)
        else:
            for idx in range(self.states):
                self.state_vectors[idx].TriB_button.setChecked(state)
            if state == 1:
                self.master_vector.TriB_button.setStyleSheet("background-color: #" + tc.green + ";")
            else:
                self.master_vector.TriB_button.setStyleSheet("background-color: #" + tc.red + ";")

    def a2d_lockpt_spin_changed(self, level, *bc):
        var = "a2d_lp_spin"
        if (not(bc) and self.MVTX) == True:
            self.parent.parent.broadcast_channel(level, var)
        else:
            for idx in range(self.states):
                self.state_vectors[idx].a2d_lockpt_slider.setValue(level)
            self.master_vector.a2d_lockpt_slider.setValue(level)

    def a2d_lockpt_slider_changed(self, level, *bc):
        var = "a2d_lp_slider"
        if (not(bc) and self.MVTX) == True:
            self.parent.parent.broadcast_channel(level, var)
        else:
            for idx in range(self.states):
                self.state_vectors[idx].a2d_lockpt_slider.setValue(level)
            self.master_vector.a2d_lockpt_spin.setValue(level)

    def d2a_A_spin_changed(self, level, *bc):
        var = "d2a_A_spin"
        if (not(bc) and self.MVTX) == True:
            self.parent.parent.broadcast_channel(level, var)
        else:
            for idx in range(self.states):
                self.state_vectors[idx].d2a_A_slider.setValue(level)
            self.master_vector.d2a_A_slider.setValue(level)

    def d2a_A_slider_changed(self, level, *bc):
        var = "d2a_A_slider"
        if (not(bc) and self.MVTX) == True:
            self.parent.parent.broadcast_channel(level, var)
        else:
            for idx in range(self.states):
                self.state_vectors[idx].d2a_A_slider.setValue(level)
            self.master_vector.d2a_A_spin.setValue(level)

    def d2a_B_spin_changed(self, level, *bc):
        var = "d2a_B_spin"
        if (not(bc) and self.MVTX) == True:
            self.parent.parent.broadcast_channel(level, var)
        else:
            for idx in range(self.states):
                self.state_vectors[idx].d2a_B_slider.setValue(level)
            self.master_vector.d2a_B_slider.setValue(level)

    def d2a_B_slider_changed(self, level, *bc):
        var = "d2a_B_slider"
        if (not(bc) and self.MVTX) == True:
            self.parent.parent.broadcast_channel(level, var)
        else:
            for idx in range(self.states):
                self.state_vectors[idx].d2a_B_slider.setValue(level)
            self.master_vector.d2a_B_spin.setValue(level)

    def data_packet_changed(self, index, *bc):
        var = "SM"
        if (not(bc) and self.MVTX) == True:
            self.parent.parent.broadcast_channel(index, var)
        else:
            for idx in range(self.states):
                self.state_vectors[idx].data_packet.setCurrentIndex(index)
            self.master_vector.data_packet.setCurrentIndex(index)

    def P_spin_changed(self, level, *bc):
        var = "P"
        if (not(bc) and self.MVTX) == True:
            self.parent.parent.broadcast_channel(level, var)
        else:
            for idx in range(self.states):
                self.state_vectors[idx].P_spin.setValue(level)
            self.master_vector.P_spin.setValue(level)

    def I_spin_changed(self, level, *bc):
        var = "I"
        if (not(bc) and self.MVTX) == True:
            self.parent.parent.broadcast_channel(level, var)
        else:
            for idx in range(self.states):
                self.state_vectors[idx].I_spin.setValue(level)
            self.master_vector.I_spin.setValue(level)

    def FBA_changed(self, state, *bc):
        var = "FBa"
        if (not(bc) and self.MVTX) == True:
            self.parent.parent.broadcast_channel(state, var)
        else:
            for idx in range(self.states):
                self.state_vectors[idx].FBA_button.setChecked(state)
            if state == 1:
                self.master_vector.FBA_button.setStyleSheet("background-color: #" + tc.green + ";")
                self.master_vector.FBB_button.setChecked(0)
            else:
                self.master_vector.FBA_button.setStyleSheet("background-color: #" + tc.red + ";")

    def FBB_changed(self, state, *bc):
        var = "FBb"
        if (not(bc) and self.MVTX) == True:
            self.parent.parent.broadcast_channel(state, var)
        else:
            for idx in range(self.states):
                self.state_vectors[idx].FBB_button.setChecked(state)
            if state == 1:
                self.master_vector.FBB_button.setStyleSheet("background-color: #" + tc.green + ";")
                self.master_vector.FBA_button.setChecked(0)
            else:
                self.master_vector.FBB_button.setStyleSheet("background-color: #" + tc.red + ";")

    def ARL_changed(self, state, *bc):
        var = "ARL"
        if (not(bc) and self.MVTX) == True:
            self.parent.parent.broadcast_channel(state, var)
        else:
            for idx in range(self.states):
                self.state_vectors[idx].ARL_button.setChecked(state)
            if state == 1:
                self.master_vector.ARL_button.setStyleSheet("background-color: #" + tc.green + ";")
            else:
                self.master_vector.ARL_button.setStyleSheet("background-color: #" + tc.red + ";")

    def send_channel(self, *bc):
        var = "send"
        if (not(bc) and self.MVTX) == True:
            self.parent.parent.broadcast_channel(0, var)
        else:
            for idx in range(self.states):
                self.state_vectors[idx].send_channel()

    def lock_channel(self, state, *bc):
        var = "lock"
        if (not(bc) and self.MVTX) == True:
            self.parent.parent.broadcast_channel(state, var)
        else:
            for idx in range(self.states):
                self.state_vectors[idx].lock_button.setChecked(state)
            if state == 1:
                self.master_vector.lock_button.setStyleSheet("background-color: #" + tc.green + ";")
                self.master_vector.lock_button.setText('dynamic')
            else:
                self.master_vector.lock_button.setStyleSheet("background-color: #" + tc.red + ";")
                self.master_vector.lock_button.setText('static')

    '''
    self called methods
    '''

    def card_delay_changed(self):
        self.card_delay = self.card_delay_spin.value()
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

    def GR_changed(self):
        log.debug(tc.FCTCALL + "send global relock enable to DFB channel", self.col, tc.ENDC)
        self.GR = self.GR_button.isChecked()
        if self.GR == 1:
            self.GR_button.setStyleSheet("background-color: #" + tc.green + ";")
            self.GR_button.setText('ENB')
        else:
            self.GR_button.setStyleSheet("background-color: #" + tc.red + ";")
            self.GR_button.setText('OFF')
        self.send_channel_globals()
#       self.send_wreg0()
#       self.send_wreg4()
        

    def MSTR_TX_changed(self):
        self.MVTX = self.MSTR_TX.isChecked()
        log.debug(tc.FCTCALL + "set Master Vector Broadcast for DFB channel", self.col, ":", bool(self.MVTX), tc.ENDC)
        
        if self.MVTX == 1:
            self.MSTR_TX.setStyleSheet("background-color: #" + tc.green + ";")
            self.MSTR_TX.setText('TX')
            self.MSTR_RX.setChecked(1)
        else:
            self.MSTR_TX.setStyleSheet("background-color: #" + tc.red + ";")
            self.MSTR_TX.setText('OFF')

    def MSTR_RX_changed(self):
        self.MVRX = self.MSTR_RX.isChecked()
        log.debug(tc.FCTCALL + "set Master Vector Echo for DFB channel", self.col, ":", bool(self.MVRX), tc.ENDC)
        
        if self.MVRX == 1:
            self.MSTR_RX.setStyleSheet("background-color: #" + tc.green + ";")
            self.MSTR_RX.setText('RX')
        else:
            self.MSTR_RX.setStyleSheet("background-color: #" + tc.red + ";")
            self.MSTR_RX.setText('OFF')
            self.MSTR_TX.setChecked(0)

    def send_class_globals(self):
        log.debug(tc.FCTCALL + "send DFB class globals:", tc.ENDC)
        self.send_wreg0()
        self.send_wreg4()
        self.send_wreg6()
        self.send_wreg7()
        

    def send_channel_globals(self):
        log.debug(tc.FCTCALL + "send DFB channel globals:", tc.ENDC)
        self.send_wreg0()
        self.send_wreg4(self.wreg4)
#       self.send_wreg7()
        

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
        log.debug("DFB:WREG0: page register: COL", self.col)
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
            log.debug("DFB:WREG4: triangle parameters DWELL, STEPS, STEP SIZE (& global relock):", dwell, steps, step, "(",self.GR,")")
            self.sendReg((self.wreg4 & 0xFFF7FFF) | (self.GR << 15))
            

    def sendReg(self, wregval):
        write_wreg(self.serialport, wregval, self.address)

    def packCHglobals(self):
        self.CHglobals =    {
            'enb'           :   self.GR_button.isChecked(),
            'mvtx'          :   self.MSTR_TX.isChecked(),
            'mvrx'          :   self.MSTR_RX.isChecked(),
                            }

    def unpackCHglobals(self, CHglobals):
        self.GR_button.setChecked(CHglobals['enb'])
        self.MSTR_TX.setChecked(CHglobals['mvtx'])
        self.MSTR_RX.setChecked(CHglobals['mvrx'])

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

    def packStates(self):
        for idx in range(self.states):
            self.state_vectors[idx].packState()
            self.allStates['state%i'%idx] = self.state_vectors[idx].stateVector

    def unpackStates(self, dfbAllStates):
        for idx in range(self.states):
            self.state_vectors[idx].unpackState(dfbAllStates['state%i'%idx])


