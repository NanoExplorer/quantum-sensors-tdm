#-*- coding: utf-8 -*-
import os
import sys
import optparse
import time

from PyQt5 import QtGui, QtCore, QtWidgets, uic
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

import named_serial
from .dfbchn import dfbChn
from cringe.shared import terminal_colors as tc
from cringe.shared import log
from cringe.shared.rack_transport import write_wreg


class clkrap(QWidget):

    #   def __init__(self, parent=None, **kwargs):
    #       print kwargs
    def __init__(self, parent=None, addr=0, slot=1, seqln=None, lsync=40):

        super(clkrap, self).__init__()

        self.parent = parent
        self.address = addr
        self.slot = slot
        self.seqln = seqln
        self.lsync = lsync

        self.serialport = named_serial.Serial(port='rack', shared=True)
        '''global booleans'''

        self.ST = 0
        self.CLKstate = 1
        '''global variables'''

        self.lsync = lsync
        self.lsync_minus1 = self.lsync - 1

        uic.loadUi(os.path.join(os.path.dirname(__file__), 'clkrap.ui'), self)

        # Apply stylesheets that depend on runtime color values
        self.resync_button.setStyleSheet("background-color: #" + tc.green +
                                         ";")
        self.CLKstate_button.setStyleSheet("background-color: #" + tc.green +
                                           ";")

        # Set computed initial indicator text
        self.lsync_indicator.setText(str(self.lsync))
        self.line_period_indicator.setText(str(8 * (self.lsync)))
        self.line_freq_indicator.setText(str(125 / (self.lsync))[:6])
        self.frame_period_indicator.setText(
            str(self.seqln * 0.008 * self.lsync)[:6])
        self.frame_freq_indicator.setText(
            str(125000 / (self.lsync * self.seqln))[:6])

        # Connect signals
        self.lsync_indicator.textChanged.connect(self.lsync_changed)
        self.resync_button.clicked.connect(self.resync)
        self.CLKstate_button.toggled.connect(self.CLKstate_changed)

    '''
    self called methods
    '''

    def lsync_changed(self):
        self.lsync = int(self.lsync_indicator.text())
        #       print tc.WARNING + "Line period changed:", self.lsync*8, "ns", tc.ENDC
        self.lsync_minus1 = self.lsync - 1
        self.line_period_changed()
        self.frame_period_changed()
        log.debug(tc.FCTCALL + "send LSYNC-1 to (DFB)CLK:", tc.ENDC)
        self.send_wreg2()

    def seqln_changed(self, seqln):
        self.seqln = seqln
        self.frame_period_changed()

    def update_lsync(self):
        wreg = 2 << 25
        wregval = wreg | self.lsync_minus1
        self.sendReg(wregval)

    def CLKstate_changed(self):
        self.CLKstate = self.CLKstate_button.isChecked()
        self.notCLKstate = not (self.CLKstate)
        if self.CLKstate == 1:
            log.debug(tc.FCTCALL + "line clock enabled:", tc.ENDC)
            self.CLKstate_button.setStyleSheet("background-color: #" +
                                               tc.green + ";")
            self.CLKstate_button.setText('RUN')
            self.resync_button.setStyleSheet("background-color: #" + tc.green +
                                             ";")
        else:
            log.debug(tc.FCTCALL + "line clock disabled:", tc.ENDC)
            self.CLKstate_button.setStyleSheet("background-color: #" + tc.red +
                                               ";")
            self.CLKstate_button.setText('STOP')
            self.resync_button.setStyleSheet("background-color: #" + tc.red +
                                             ";")
        self.send_wreg1()

    def resync(self):
        if self.CLKstate == 1:
            log.debug(tc.FCTCALL + "resynchronize system:", tc.ENDC)
            # I don't know how this works. 
            # My best guess is that when the cards 
            # don't see a clock signal for long enough
            # they eventually give up and reset their individual
            # clock counters to 0, so when it starts back up again
            # they are all in sync...
            self.CLKstate_button.click()
            time.sleep(1)
            self.CLKstate_button.click()
        else:
            log.debug(tc.FAIL + "line clock must be enabled for RESYNC:",
                      tc.ENDC)

    def line_period_changed(self):
        self.line_period_indicator.setText(str(8 * (self.lsync)))
        self.line_freq_indicator.setText(str(125.0 / (self.lsync))[:6])

    def frame_period_changed(self):
        self.frame_period_indicator.setText(
            str(self.seqln * 0.008 * self.lsync)[:6])
        self.frame_freq_indicator.setText(
            str(125000 / (self.lsync * self.seqln))[:6])


#       self.send_wreg7()

    def send_wreg1(self):
        log.debug("CLK:WREG1: clock state:", self.CLKstate)
        wreg = 1 << 25
        wregval = wreg | (self.notCLKstate << 24) | (self.CLKstate << 23)
        self.sendReg(wregval)

    def send_wreg2(self):
        log.debug("CLK:WREG2: LSYNC-1:", self.lsync_minus1)
        wreg = 2 << 25
        wregval = wreg | self.lsync_minus1
        self.sendReg(wregval)

    def send_wreg7(self):
        log.debug("CLK:WREG7: sequence length:", self.seqln)
        wreg = 7 << 25
        wregval = wreg | (self.seqln << 8)
        self.sendReg(wregval)

    def sendReg(self, wregval):
        write_wreg(self.serialport, wregval, self.address)
