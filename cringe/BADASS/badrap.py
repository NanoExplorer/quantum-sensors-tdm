import sys
import optparse

from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

import named_serial
from .badchn_builder import badChn
from cringe.shared import terminal_colors as tc
from cringe.shared import log
from cringe.shared.rack_transport import write_wreg


class badrap(QWidget):

    #   def __init__(self, parent=None, **kwargs):
    #       print kwargs
    def __init__(self,
                 parent=None,
                 addr=None,
                 slot=None,
                 seqln=None,
                 lsync=32):

        super(badrap, self).__init__()

        self.serialport = named_serial.Serial(port='rack', shared=True)

        self.chns = 16

        #       if parent == None:
        self.parent = parent
        self.address = addr
        self.slot = slot
        self.seqln = seqln
        self.lsync = lsync
        #       else:
        #           self.address = parent.addr
        #           self.slot = parent.slot
        #           self.seqln = parent.seqln
        #           self.lsync = parent.lsync

        self.frame = self.lsync * self.seqln

        self.delay = 0
        self.led = 0
        self.status = 0
        self.init = 0

        self.dwell_val = 0
        self.dwellDACunits = float(0)
        self.range_val = 1
        self.rangeDACunits = float(2)
        self.step_val = 1
        self.stepDACunits = float(1)
        self.tri_idx = 0

        self.mode = 1

        self.chn_vectors = []
        self.allChannels = {}
        #       self.enb = [0,0,0,0,0,0,0]
        #       self.cal_coeffs = [0,0,0,0,0,0,0]
        #       self.appTrim =[0,0,0,0,0,0,0]

        self.setWindowTitle("BADRAP")  # Phase Offset Widget
        self.setGeometry(30, 30, 1200, 800)
        self.setContentsMargins(0, 0, 0, 0)

        self.layout_widget = QWidget(self)
        self.layout = QVBoxLayout(self)
        '''
        build widget for MASTER CONTROL VECTOR: these controls effect all channels on a card
        '''
        self.master_ctrl_widget = QGroupBox(self)
        self.master_ctrl_widget.setTitle("MASTER CONTROL VECTOR")
        self.master_ctrl_layout = QGridLayout(self.master_ctrl_widget)

        self.master_vector = badChn(self,
                                    self.master_ctrl_layout,
                                    chn=-1,
                                    cardaddr=self.address,
                                    serialport=self.serialport,
                                    master='master')
        self.master_vector.counter_label.setText("all")
        self.master_vector.chn_send.setText("send ALL channels")

        self.scale_factor = self.master_vector.width()

        self.layout.addWidget(self.master_ctrl_widget)
        '''
        build widget for arrayed channel parameters
        '''
        self.arrayframe = QWidget(self.layout_widget)
        self.array_layout = QVBoxLayout(self.arrayframe)
        self.array_layout.setSpacing(5)
        self.array_layout.setContentsMargins(10, 10, 10, 10)

        for idx in range(self.chns):
            self.chn_vectors.append(
                badChn(self,
                       self.array_layout,
                       chn=idx,
                       cardaddr=self.address,
                       serialport=self.serialport))

        self.scrollarea = QScrollArea(self.layout_widget)
        self.scrollarea.setWidget(self.arrayframe)
        self.layout.addWidget(self.scrollarea)
        #       self.show()
        #       print self.arrayframe.width()
        self.master_ctrl_widget.setFixedWidth(self.arrayframe.width() + 0)

    '''
    child called methods
    '''


    def dc_changed(self, state):
        for idx in range(self.chns):
            self.chn_vectors[idx].dc_button.setChecked(state)
        if state == 1:
            self.master_vector.dc_button.setStyleSheet("background-color: #" +
                                                       tc.green + ";")
        else:
            self.master_vector.dc_button.setStyleSheet("background-color: #" +
                                                       tc.red + ";")

    def LoHi_changed(self, state):
        for idx in range(self.chns):
            self.chn_vectors[idx].LoHi_button.setChecked(state)
        if state == 1:
            self.master_vector.LoHi_button.setStyleSheet(
                "background-color: #" + tc.green + ";")
            self.master_vector.LoHi_button.setText('HI')
        else:
            self.master_vector.LoHi_button.setStyleSheet(
                "background-color: #" + tc.red + ";")
            self.master_vector.LoHi_button.setText('LO')

    def tri_changed(self, state):
        for idx in range(self.chns):
            self.chn_vectors[idx].Tri_button.setChecked(state)
        if state == 1:
            self.master_vector.Tri_button.setStyleSheet("background-color: #" +
                                                        tc.green + ";")
        else:
            self.master_vector.Tri_button.setStyleSheet("background-color: #" +
                                                        tc.red + ";")

    def d2a_lo_spin_changed(self, level):
        for idx in range(self.chns):
            self.chn_vectors[idx].d2a_lo_slider.setValue(level)
        self.master_vector.d2a_lo_slider.setValue(level)

    def d2a_lo_slider_changed(self, level):
        for idx in range(self.chns):
            self.chn_vectors[idx].d2a_lo_slider.setValue(level)
        self.master_vector.d2a_lo_spin.setValue(level)

    def d2a_lo_setMin(self):
        for idx in range(self.chns):
            self.chn_vectors[idx].d2a_lo_setMin()
        self.master_vector.d2a_lo_slider.setValue(0)

    def d2a_lo_setMax(self):
        for idx in range(self.chns):
            self.chn_vectors[idx].d2a_lo_setMax()
        self.master_vector.d2a_lo_slider.setValue(16383)

    def d2a_hi_spin_changed(self, level):
        for idx in range(self.chns):
            self.chn_vectors[idx].d2a_hi_slider.setValue(level)
        self.master_vector.d2a_hi_slider.setValue(level)

    def d2a_hi_slider_changed(self, level):
        for idx in range(self.chns):
            self.chn_vectors[idx].d2a_hi_slider.setValue(level)
        self.master_vector.d2a_hi_spin.setValue(level)

    def d2a_hi_setMin(self):
        for idx in range(self.chns):
            self.chn_vectors[idx].d2a_hi_setMin()
        self.master_vector.d2a_hi_slider.setValue(0)

    def d2a_hi_setMax(self):
        for idx in range(self.chns):
            self.chn_vectors[idx].d2a_hi_setMax()
        self.master_vector.d2a_hi_slider.setValue(16383)

    '''
    self called methods
    '''

    def send_channel(self):
        for idx in range(self.chns):
            self.chn_vectors[idx].send_channel()

    def lock_channel(self, state):
        for idx in range(self.chns):
            self.chn_vectors[idx].lock_button.setChecked(state)
        if state == 1:
            self.master_vector.lock_button.setStyleSheet(
                "background-color: #" + tc.green + ";")
            self.master_vector.lock_button.setText('dynamic')
        else:
            self.master_vector.lock_button.setStyleSheet(
                "background-color: #" + tc.red + ";")
            self.master_vector.lock_button.setText('static')

    def card_delay_changed(self, newDelay):
        self.delay = newDelay
        if self.mode == 1:
            self.send_wreg0()

    def LED_changed(self):
        self.led = self.LED_button.isChecked()
        if self.led == 1:
            self.LED_button.setStyleSheet("background-color: #" + tc.red + ";")
            self.LED_button.setText('OFF')
        else:
            self.LED_button.setStyleSheet("background-color: #" + tc.green +
                                          ";")
            self.LED_button.setText('ON')
#        if self.unlocked == 1:
        self.send_wreg0()

    def status_changed(self):
        self.status = self.status_button.isChecked()
        if self.status == 1:
            self.status_button.setStyleSheet("background-color: #" + tc.green +
                                             ";")
        else:
            self.status_button.setStyleSheet("background-color: #" + tc.red +
                                             ";")
        self.send_wreg0()

    def send_globals(self):
        log.debug(tc.FCTCALL + "send BAD16 globals:", tc.ENDC)
        self.send_wreg0()
#       self.send_wreg1()

    def dwell_changed(self):
        self.dwell_val = self.dwell.value()
        self.dwellDACunits = 2**(self.dwell_val)
        self.dwell_indicator.setText('%5i' % self.dwellDACunits)
        self.period_changed()
        if self.mode == 1:
            self.send_wreg1()

    def range_changed(self):
        self.range_val = self.range.value()
        self.rangeDACunits = 2**self.range_val
        self.range_indicator.setText('%5i' % self.rangeDACunits)
        self.amp_changed()
        self.period_changed()
        #       periodDACunits = 2*2**self.dwell_val*2**self.range_val
        #       self.period_indicator.setText('%11i'%periodDACunits)
        #       self.period_eng_indicator.setText('%12.4d'%periodDACunits*self.lsync*0.008)
        #       self.freq_eng_indicator.setText(str(1000/float(self.period_eng_indicator.text()))[:6])
        if self.mode == 1:
            self.send_wreg1()

    def step_changed(self):
        self.step_val = self.step.value()
        self.stepDACunits = self.step_val
        self.amp_changed()
        #       self.period_changed()
        #       self.amp_indicator.setText(str((2**self.range_val)*self.step_val))
        #       self.amp_eng_indicator.setText(str(int(self.amp_indicator.text())/16.383)[:6])
        if self.mode == 1:
            self.send_wreg1()

    def amp_changed(self):
        log.debug("amp_changed")
        self.ampDACunits = self.rangeDACunits * self.stepDACunits
        log.debug(self.ampDACunits)
        if self.ampDACunits > 16383:
            self.ampDACunits = 16383
        self.amp_indicator.setText('%5i' % self.ampDACunits)
        mV = 1000 * self.ampDACunits / 16383.0
        log.debug(mV, str(mV))
        self.amp_eng_indicator.setText('%4.3f' % mV)


#       self.amp_eng_indicator.setText('%6.3d'%volts)

    def period_changed(self):
        log.debug("period changed")
        self.periodDACunits = float(2 * self.dwellDACunits *
                                    self.rangeDACunits)
        self.period_indicator.setText('%12i' % self.periodDACunits)
        uSecs = self.periodDACunits * self.lsync * 0.008
        log.debug(uSecs)
        kHz = 1000 / uSecs
        log.debug(kHz)
        self.period_eng_indicator.setText('%8.4f' % uSecs)
        self.freq_eng_indicator.setText('%6.3f' % kHz)

    def tri_idx_changed(self):
        self.tri_idx = self.tri_idx_button.isChecked()
        if self.tri_idx == 1:
            self.tri_idx_button.setStyleSheet("background-color: #" +
                                              tc.green + ";")
            self.tri_idx_button.setText('FRAME')
        else:
            self.tri_idx_button.setStyleSheet("background-color: #" + tc.red +
                                              ";")
            self.tri_idx_button.setText('LSYNC')
        self.send_wreg1()

    def send_wreg0(self):
        log.debug("BAD16: WREG0: legacy globals")
        wreg = 0 << 25
        wregval = wreg | (self.status << 16) | (self.led << 14) | (
            self.delay << 10) | (self.init << 8) | self.seqln
        #       wregval = wreg | (self.led << 24) | (self.status << 16) | (self.delay << 10) | (self.seqln << 1)
        self.sendReg(wregval)

    def send_wreg1(self):
        log.debug("BAD16:WREG1: triangle parameters")
        wreg = 1 << 25
        wregval = wreg + (self.tri_idx << 24) + (self.dwell_val << 20) + (
            self.range_val << 16) + self.step_val
        self.sendReg(wregval)

    def sendReg(self, wregval):
        write_wreg(self.serialport, wregval, self.address)

    def packMasterVector(self):
        self.MasterState = {
            'dc': self.master_vector.dc_button.isChecked(),
            'LoHi': self.master_vector.LoHi_button.isChecked(),
            'tri': self.master_vector.Tri_button.isChecked(),
            'd2a_lo': self.master_vector.d2a_lo_spin.value(),
            'd2a_hi': self.master_vector.d2a_hi_spin.value(),
        }

    def unpackMasterVector(self, masterVector):
        self.master_vector.dc_button.setChecked(masterVector['dc'])
        self.master_vector.LoHi_button.setChecked(masterVector['LoHi'])
        self.master_vector.Tri_button.setChecked(masterVector['tri'])
        self.master_vector.d2a_lo_spin.setValue(masterVector['d2a_lo'])
        self.master_vector.d2a_hi_spin.setValue(masterVector['d2a_hi'])

    def packChannels(self):
        for idx in range(self.chns):
            self.chn_vectors[idx].packChannel()
            self.allChannels['channel%i' %
                             idx] = self.chn_vectors[idx].ChannelVector

    def unpackChannels(self, badAllChannels):
        for idx in range(self.chns):
            self.chn_vectors[idx].unpackChannel(badAllChannels['channel%i' %
                                                               idx])
