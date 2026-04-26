# -*- coding: utf-8 -*-
import sys

import argparse
import time
import pickle
import json
import os

import IPython  # ADDED JG

from PyQt5 import QtGui, QtCore, QtWidgets, uic

import named_serial

from cringe.shared import terminal_colors as tc
from cringe.shared import log, logging

from cringe.DFBx2.dfbcard import dfbcard
from cringe.BADASS.badcard import badcard
from cringe.DFBx2.dfbclkcard import dfbclkcard
from cringe.emu_card import EMU_Card
from cringe.tune.tunetab import TuneTab
from cringe.tower import towerwidget
from cringe.calibration.caltab import CalTab

from cringe.cringe_control import CRINGE_COMMANDS, build_zmq_addr
from cringe.zmq_rep import ZmqRep
from cringe.shared.rack_transport import write_wreg


class Cringe(QtWidgets.QWidget):
    '''CRate Interface for NextGen Electronics'''

    def __init__(self,
                 parent=None,
                 addr_vector=None,
                 slot_vector=None,
                 class_vector=None,
                 seqln=30,
                 lsync=40,
                 tower_vector=None,
                 argfilename=None,
                 calibrationtab=False):

        super(Cringe, self).__init__()
        my_directory = os.path.dirname(__file__)
        self.setWindowIcon(
            QtGui.QIcon(os.path.join(my_directory, "cringe_img.jpg")))

        self.serialport = named_serial.Serial(port='rack', shared=True)
        self.seqln_timer = None
        self.lsync_timer = None
        self.dfb_delay_timer = None
        self.bad_delay_timer = None
        self.prop_delay_timer = None
        self.NSAMP_delay_timer = None
        self.SETT_delay_timer = None
        self.ARLsense_timer = None
        self.RLDpos_timer = None
        self.RLDneg_timer = None

        self.states = 64

        #       self.address = addr
        #       self.slot = slot
        self.seqln = seqln
        self.lsync = lsync
        self.last_lsync = lsync
        self.frame_period = self.lsync * self.seqln * 0.008
        self.locked = False
        self.scale_factor = 1400  # will be redefined later, hopefully this value doesnt matter

        self.saveGlobals = {}
        self.saveClassParameters = {}
        self.loadGlobals = {}
        #       self.saveFilename = None
        '''global booleans'''

        self.PS = False

        #       self.LED = 0
        #       self.ST = 0
        #       self.GR = 0
        '''global variables'''

        self.dfbclk_XPT = 5
        self.dfbx2_XPT = 0
        self.NSAMP = 4
        self.prop_delay = 3
        self.dfb_delay = 0
        self.seqln = seqln
        self.SETT = 12
        self.TP = 0
        '''ARL default parameters'''

        self.ARLsense = 1024
        self.RLDpos = 64
        self.RLDneg = 4
        self.RLD_track_state = True
        self.RLDpos_delay = self.RLDpos * self.frame_period
        self.RLDneg_delay = self.RLDneg * self.frame_period
        '''triangle default parameters'''

        self.dwell_val = 0
        self.dwellDACunits = float(1)
        self.range_val = 10
        self.rangeDACunits = float(1024)
        self.step_val = 8
        self.stepDACunits = float(256)
        self.tri_idx = False
        '''BAD16 class globals'''

        self.bad_delay = 5
        #       self.bad_wreg0 = (0 << 25) | (self.ST << 16) | (self.LED << 14) | (self.bad_delay << 10) | self.seqln
        '''DFB class global registers'''
        self.dfb_wreg4 = 0
        self.dfb_wreg6 = 0
        self.dfb_wreg7 = 0
        '''card global default variables'''

        self.mode = 1
        self.CLK = True

        self.slot_vector = slot_vector
        self.addr_vector = addr_vector
        self.class_vector = class_vector
        self.tower_vector = tower_vector
        #       self.slot_vector = [1,3,10]
        #       self.addr_vector = [1,3,32]
        #       self.class_vector = ['DFBCLK', 'DFBx2','BAD16']
        #       self.slot_vector = [1,3,4,5,6,10,11]
        #       self.addr_vector = [1,3,5,7,9,32,33]
        #       self.class_vector = ['DFBCLK', 'DFBx2', 'DFBx2', 'DFBx2', 'DFBx2', 'BAD16', 'BAD16']
        self.crate_widgets = []
        #       self.enb = [0,0,0,0,0,0,0]
        #       self.cal_coeffs = [0,0,0,0,0,0,0]
        #       self.appTrim =[0,0,0,0,0,0,0]

        uic.loadUi(os.path.join(my_directory, 'cringe.ui'), self)

        log.debug(tc.INIT + tc.BOLD + "building GUI" + tc.ENDC)

        # Apply stylesheets that depend on runtime color values
        self.crate_power.setStyleSheet("background-color: #" + tc.green + ";")
        self.server_lock.setStyleSheet("background-color: #" + tc.green + ";")
        self.PS_button.setStyleSheet("background-color: #" + tc.red + ";")
        self.tri_idx_button.setStyleSheet("background-color: #" + tc.red + ";")

        # Set initial values from constructor arguments (override .ui defaults)
        self.seqln_spin.setValue(self.seqln)
        self.lsync_spin.setValue(self.lsync)
        self.server_lock.setChecked(self.locked)
        self.RLD_frame.setChecked(self.RLD_track_state)
        self.RLD_time.setChecked(not self.RLD_track_state)

        # Set computed indicator text
        self.ARLsense_eng_indicator.setText(str((self.ARLsense) / 16.383)[:6])
        self.RLDpos_eng_indicator.setText(
            str((self.RLDpos) * self.frame_period)[:6])
        self.RLDneg_eng_indicator.setText(
            str(self.RLDneg * self.frame_period)[:6])
        self.period_indicator.setText(
            str(2 * (2**self.dwell_val) * (2**self.range_val)))
        self.period_eng_indicator.setText(
            str(int(self.period_indicator.text()) * self.lsync * 0.008))
        self.amp_indicator.setText(str((2**self.range_val) * self.step_val))
        self.amp_eng_indicator.setText(
            str(int(self.amp_indicator.text()) / 16.383)[:6])
        self.freq_eng_indicator.setText(
            str(1000 / float(self.period_eng_indicator.text()))[:6])

        # Connect signals
        self.loadsetup.clicked.connect(self.loadSettings)
        self.savesetup.clicked.connect(self.saveSettings)
        self.sendsetup.clicked.connect(self.assertSettings)
        self.seqln_spin.valueChanged.connect(self.seqln_changed)
        self.lsync_spin.valueChanged.connect(self.lsync_changed)
        self.sys_glob_send.clicked.connect(self.send_all_sys_globals)
        self.crate_power.toggled.connect(self.cratePower)
        self.server_lock.toggled.connect(self.lockServer)
        self.send_all_globals.clicked.connect(self.send_ALL_globals)
        self.send_all_states_chns.clicked.connect(self.send_ALL_states_chns)
        self.cal_system.clicked.connect(self.phcal_system)
        self.resync_system.clicked.connect(self.system_resync)
        self.full_init_button.clicked.connect(self.full_crate_init)
        self.SETT_spin.valueChanged.connect(self.SETT_changed)
        self.NSAMP_spin.valueChanged.connect(self.NSAMP_changed)
        self.prop_delay_spin.valueChanged.connect(self.prop_delay_changed)
        self.dfb_delay_spin.valueChanged.connect(self.dfb_delay_changed)
        self.bad_delay_spin.valueChanged.connect(self.bad_delay_changed)
        self.dfbx2_xpt_mode.currentIndexChanged.connect(self.dfbx2_XPT_changed)
        self.tp_mode.currentIndexChanged.connect(self.TP_changed)
        self.class_glb_send.clicked.connect(self.send_all_class_globals)
        self.dfbclk_xpt_mode.currentIndexChanged.connect(
            self.dfbclk_XPT_changed)
        self.PS_button.toggled.connect(self.PS_changed)
        self.ARLsense_spin.valueChanged.connect(self.ARLsense_changed)
        self.RLDpos_spin.valueChanged.connect(self.RLDpos_changed)
        self.RLDneg_spin.valueChanged.connect(self.RLDneg_changed)
        self.RLD_frame.clicked.connect(self.track_changed)
        self.RLD_time.clicked.connect(self.track_changed)
        self.dwell.valueChanged.connect(self.dwell_changed)
        self.range.valueChanged.connect(self.range_changed)
        self.step.valueChanged.connect(self.step_changed)
        self.tri_idx_button.toggled.connect(self.tri_idx_changed)
        self.tri_send.clicked.connect(self.send_triangle)

        # Conditional debug button (not in .ui — depends on runtime verbosity)
        if log.verbosity >= logging.VERBOSITY_DEBUG:
            self.debug_full_tune_button = QtWidgets.QPushButton(
                "debug: extern tune")
            self.debug_full_tune_button.setFixedHeight(25)
            self.sys_glob_layout.addWidget(self.debug_full_tune_button, 0, 3,
                                           1, 2, QtCore.Qt.AlignLeft)
            self.debug_full_tune_button.clicked.connect(self.extern_tune)

        log.debug(tc.INIT + tc.BOLD + "building GUI" + tc.ENDC)
        '''
        build tab widget for crate cards
        '''
        for idx, val in enumerate(self.class_vector):
            if val == "DFBCLK":
                self.card_widget = dfbclkcard(parent=self,
                                              addr=self.addr_vector[idx],
                                              slot=self.slot_vector[idx],
                                              seqln=self.seqln,
                                              lsync=self.lsync)
                tab_lbl = " DFBx1CLK: " + \
                    str(self.slot_vector[idx]) + "/" + \
                    str(self.addr_vector[idx]) + " "
                self.scale_factor = self.card_widget.dfbclk_widget1.state_vectors[
                    0].width()
            if val == "DFBx2":
                self.card_widget = dfbcard(parent=self,
                                           addr=self.addr_vector[idx],
                                           slot=self.slot_vector[idx],
                                           seqln=self.seqln,
                                           lsync=self.lsync)
                tab_lbl = " DFBx2: " + \
                    str(self.slot_vector[idx]) + "/" + \
                    str(self.addr_vector[idx]) + " "
            if val == "BAD16":
                self.card_widget = badcard(parent=self,
                                           addr=self.addr_vector[idx],
                                           slot=self.slot_vector[idx],
                                           seqln=self.seqln,
                                           lsync=self.lsync)
                tab_lbl = " BAD16: " + \
                    str(self.slot_vector[idx]) + "/" + \
                    str(self.addr_vector[idx]) + " "

            # There used to be a DFBs card here but ctr determined it
            # was not used by anyone due to a bug that would prevent
            # basically all communication with it.
            self.crate_widgets.append(card_widget)
            self.crate_widget.addTab(card_widget, tab_lbl)

        self.tune_widget = TuneTab(self)
        self.crate_widget.addTab(self.tune_widget, "Tune")
        self.crate_widgets.append(self.tune_widget)
        if calibrationtab:
            self.cal_widget = CalTab(self)
            self.crate_widget.addTab(self.cal_widget, "Calibration")
        self.crate_widgets.append(self.tune_widget)

        if not self.tower_vector is None:
            log.debug("building tower widget")
            self.tower_widget = towerwidget.TowerWidget(
                parent=self, nameaddrlist=self.tower_vector)
            self.scroll = QtWidgets.QScrollArea(self)
            self.scroll.setWidgetResizable(True)
            self.scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
            self.scroll.setWidget(self.tower_widget)
            self.crate_widget.addTab(self.scroll, "Tower")
        else:
            self.tower_widget = None

        log.debug("code checkpoint 1")
        '''
        resize widgets for relative, platform dependent variability
        '''
        rm = 90
        self.file_mgmt_widget.setFixedWidth(int(self.scale_factor + rm))
        self.sys_glob_hdr_widget.setFixedWidth(
            int(self.scale_factor / 2 + rm / 3))
        self.sys_control_hdr_widget.setFixedWidth(
            int(self.scale_factor / 2 + rm / 3))
        self.class_glob_hdr_widget.setFixedWidth(int(self.scale_factor + rm))
        self.arl_widget.setFixedWidth(int(self.scale_factor / 2 + rm / 3))
        self.tri_wvfm_widget.setFixedWidth(int(self.scale_factor / 2 + rm / 3))
        self.setFixedWidth(int(self.scale_factor + rm + 20))
        self.setFixedHeight(1000)

        self.emu = EMU_Card()

        log.debug("before loadSettings")

        if argfilename is not None:
            self.loadSettings(argfilename)

        log.debug("after loadSettings")

        self.control_socket = ZmqRep(self, build_zmq_addr(host='*'))
        self.control_socket.gotMessage.connect(self.handleMessage)
        # maybe abstracted too far?  Have the data structure point to
        # the method name - here add a element 'func' as unbound method
        self.cringe_commands = CRINGE_COMMANDS.copy()
        for command in self.cringe_commands:
            self.cringe_commands[command]['func'] = self.__getattribute__(
                self.cringe_commands[command]['fname'])

    def handleMessage(self, message):
        llog = log.child("handleMessage")
        llog.info(message)
        command_words = message.split()
        # original commands were uppercase - still accept those
        command = command_words[0].lower()
        command_args = command_words[1:]
        if command in self.cringe_commands:
            f = self.cringe_commands[command]['func']
            llog.info(f"calling: {f}")
            try:
                success, extra_info = f(*command_args)
            except Exception as ex:
                success = False
                import traceback
                import sys
                exc_type, exc_value, exc_traceback = sys.exc_info()
                s = traceback.format_exception(exc_type, exc_value,
                                               exc_traceback)
                print("TRACEBACK")
                print("".join(s))
                print("TRACEBACK DONE")
                extra_info = f"Exception: {ex}\n{s}"
        else:
            success = False
            extra_info = f"`{message}` invalid, must be one of {list(self.cringe_commands.keys())}"
        self.control_socket.resolve_message(success, extra_info)

    def full_crate_init(self):
        llog = log.child("full_crate_init")
        llog.info("started")
        crate_sleep_s = 1.0
        crate_sleep_final_s = 2.0
        if not self.crate_power.isChecked():
            self.crate_power.click()  # turn on crate
            time.sleep(crate_sleep_s)
        self.crate_power.click()  # turn off crate
        time.sleep(crate_sleep_s)
        llog.info("crate power turned off")
        self.crate_power.click()  # turn on crate
        time.sleep(crate_sleep_final_s)
        llog.info("crate power turned on")
        self.send_all_sys_globals()  # send globals system globals button
        llog.info("sent all sys globals")
        self.send_all_class_globals()  # 2nd half of send globals button
        llog.info("sent all class globals")
        self.send_ALL_states_chns(resync=False)  # send arrayed button
        llog.info("sent arrayed")
        self.phcal_system(resync=False)  # CALIBRATE button
        llog.info("sent calibration")
        llog.info("begin resync")
        self.system_resync()
        llog.info("done")
        return True, ""

    def extern_tune(self):
        llog = log.child("extern_tune")
        llog.debug("start")
        connected = self.tune_widget.vphidemo.c.startclient()
        if not connected:
            return False, "tune client failed to connect, is dastard lancero source running?"
        self.tune_widget.vphidemo.fullTune()
        llog.debug("done")
        return True, ""

    def rpc_set_tower_channel(self, cardname, bayname, dacvalue):
        self.tune_widget.mm.setTowerChannelDAC(cardname, bayname,
                                               int(dacvalue))
        return True, ""

    def rpc_set_tower_card_all_channels(self, cardname, dacvalue):
        self.tune_widget.mm.setTowerCardAllChannelsToSameDAC(
            cardname, int(dacvalue))

    def rpc_relock_fba(self, col, row):
        self.tune_widget.mm.relockFBA(int(col), int(row))
        return True, ""

    def rpc_relock_fbb(self, col, row):
        self.tune_widget.mm.relockFBB(int(col), int(row))
        return True, ""

    def rpc_relock_all_locked_fba(self, col):
        for row in range(self.seqln):
            self.tune_widget.mm.relockFBAifLocked(int(col), row)
        return True, ""

    def rpc_set_fb_i(self, col, fb_i):
        # two step setting to make sure the gui doesn't ignore it
        self.tune_widget.mm.changedfbrow(col=int(col), row="master", I=0)
        self.tune_widget.mm.changedfbrow(col=int(col),
                                         row="master",
                                         I=int(fb_i))
        return True, ""

    def rpc_set_arl_off(self, col):
        # if the master is already off, setting it to off won't change any others
        # so we first set master true, then false
        self.tune_widget.mm.changedfbrow(col=int(col), row="master", ARL=True)
        self.tune_widget.mm.changedfbrow(col=int(col), row="master", ARL=False)
        return True, ""

    def rpc_set_fba_offset(self, col, fba_offset):
        # two step setting to make sure the gui doesn't ignore it
        self.tune_widget.mm.changedfbrow(col=int(col), row="master", d2aA=0)
        self.tune_widget.mm.changedfbrow(col=int(col),
                                         row="master",
                                         d2aA=int(fba_offset))
        return True, ""

    def rpc_set_seq_len(self, length):
        self.seqln_spin.setValue(int(length))
        return True, ""

    def rpc_save_config(self, filename):
        self._save_settings(filename)
        return True, ""

    def seqln_changed(self):
        if self.seqln_timer == None:
            self.seqln_timer = QtCore.QTimer()
            self.seqln_timer.timeout.connect(self.change_seqln)
        self.seqln_timer.start(750)

    def change_seqln(self):
        log.debug(tc.WARNING + "SEQLN changed:", tc.ENDC)

        log.debug(tc.FCTCALL + "send SEQLN parameter to all cards:", tc.ENDC)
        self.seqln = self.seqln_spin.value()
        for idx, val in enumerate(self.class_vector):
            self.card_addr = self.addr_vector[idx]
            if val == "DFBCLK":
                self.crate_widgets[idx].seqln_changed(self.seqln)
            if val == "DFBx2":
                self.crate_widgets[idx].seqln_changed(self.seqln)
            if val == "BAD16":
                self.crate_widgets[idx].seqln_changed(self.seqln)
        if self.tri_idx == 1:
            self.tri_period_changed()
        self.frame_period_changed()
        self.system_resync()
        self.seqln_timer.stop()
        self.seqln_timer = None

    def lsync_changed(self):
        if self.lsync_timer == None:
            self.lsync_timer = QtCore.QTimer()
            self.lsync_timer.timeout.connect(self.change_lsync)
        self.lsync_timer.start(750)

    def change_lsync(self):
        self.lsync_timer.stop()
        self.lsync_timer = None
        self.last_lsync = self.lsync
        self.lsync = self.lsync_spin.value()
        if self.lsync == self.last_lsync:
            return
        log.debug(tc.WARNING + "Line period changed:", self.lsync * 8, "ns",
                  tc.ENDC)

        # when the clock widget sends wreg2 it actually sends lsync to the clock card
        self.crate_widgets[0].dfbclk_widget2.lsync_indicator.setText(
            str(self.lsync))
        if self.lsync < 40:
            #           print tc.FCTCALL + "parallel stream engaged" + tc.ENDC
            #           print
            self.PS_button.setChecked(1)
        self.tri_period_changed()
        self.frame_period_changed()
        self.system_resync()

    def frame_period_changed(self):
        self.frame_period = self.lsync * self.seqln * 0.008
        log.debug(tc.WARNING + "frame period changed:", self.frame_period,
                  "\u00B5s", tc.ENDC)

        if self.RLD_frame.isChecked() == True:
            self.RLDwarning()
            self.RLDpos_eng_indicator.setText(
                str((self.RLDpos) * self.frame_period)[:6])
            self.RLDneg_eng_indicator.setText(
                str((self.RLDneg) * self.frame_period)[:6])
        if self.RLD_time.isChecked() == True:
            self.RLDpos_spin.setValue(
                int(self.RLDpos_delay / self.frame_period))
            self.RLDneg_spin.setValue(
                int(self.RLDneg_delay / self.frame_period))

    def dfb_delay_changed(self):
        if self.dfb_delay_timer == None:
            self.dfb_delay_timer = QtCore.QTimer()
            self.dfb_delay_timer.timeout.connect(self.change_dfb_delay)
        self.dfb_delay_timer.start(750)

    def change_dfb_delay(self):
        log.debug(tc.FCTCALL + "send card delay to all DFB cards:" + tc.ENDC)

        self.dfb_delay = self.dfb_delay_spin.value()
        for idx, val in enumerate(self.class_vector):
            self.card_addr = self.addr_vector[idx]
            if val == "DFBCLK":
                LED = self.crate_widgets[idx].LED
                ST = self.crate_widgets[idx].ST
                self.send_dfb_wreg7(LED, ST, self.card_addr)
            if val == "DFBx2":
                LED = self.crate_widgets[idx].LED
                ST = self.crate_widgets[idx].ST
                self.send_dfb_wreg7(LED, ST, self.card_addr)
        if self.locked == 0:
            self.system_resync()
        self.dfb_delay_timer.stop()
        self.dfb_delay_timer = None

    def bad_delay_changed(self):
        if self.bad_delay_timer == None:
            self.bad_delay_timer = QtCore.QTimer()
            self.bad_delay_timer.timeout.connect(self.change_bad_delay)
        self.bad_delay_timer.start(750)

    def change_bad_delay(self):
        log.debug(tc.FCTCALL + "send card delay to all BAD16 cards:" + tc.ENDC)
        self.bad_delay = self.bad_delay_spin.value()
        #       mask = 0xfffc3ff
        #       self.bad_wreg0 = (self.bad_wreg0 & mask) | (self.bad_delay << 10)
        for idx, val in enumerate(self.class_vector):
            self.card_addr = self.addr_vector[idx]
            if val == "BAD16":
                LED = self.crate_widgets[idx].LED
                ST = self.crate_widgets[idx].ST
                INT = self.crate_widgets[idx].INT
                self.send_bad16_wreg0(ST, LED, INT, self.card_addr)
        if self.locked == 0:
            self.system_resync()
        self.bad_delay_timer.stop()
        self.bad_delay_timer = None

    def prop_delay_changed(self):
        if self.prop_delay_timer == None:
            self.prop_delay_timer = QtCore.QTimer()
            self.prop_delay_timer.timeout.connect(self.change_prop_delay)
        self.prop_delay_timer.start(750)

    def change_prop_delay(self):
        log.debug(tc.FCTCALL + "send propagation delay to all DFB cards:" +
                  tc.ENDC)

        self.prop_delay = self.prop_delay_spin.value()
        for idx, val in enumerate(self.class_vector):
            self.card_addr = self.addr_vector[idx]
            if val == "DFBCLK":
                LED = self.crate_widgets[idx].LED
                ST = self.crate_widgets[idx].ST
                self.send_dfb_wreg7(LED, ST, self.card_addr)
            if val == "DFBx2":
                LED = self.crate_widgets[idx].LED
                ST = self.crate_widgets[idx].ST
                self.send_dfb_wreg7(LED, ST, self.card_addr)

        if self.locked == 0:
            self.system_resync()
        self.prop_delay_timer.stop()
        self.prop_delay_timer = None

    def dfbclk_XPT_changed(self):
        log.debug(tc.FCTCALL +
                  "send crosspoint switch setting to DFBx1CLK card:" + tc.ENDC)
        self.dfbclk_XPT = self.dfbclk_xpt_mode.currentIndex()
        for idx, val in enumerate(self.class_vector):
            self.card_addr = self.addr_vector[idx]
            if val == "DFBCLK":
                self.send_dfbclk_wreg6(self.card_addr)

    def dfbx2_XPT_changed(self):
        log.debug(tc.FCTCALL +
                  "send crosspoint switch setting to all DFBx2 cards:" +
                  tc.ENDC)

        self.dfbx2_XPT = self.dfbx2_xpt_mode.currentIndex()
        for idx, val in enumerate(self.class_vector):
            self.card_addr = self.addr_vector[idx]
            if val == "DFBx2":
                self.send_dfbx2_wreg6(self.card_addr)


    def TP_changed(self):
        log.debug(tc.FCTCALL +
                  "send test pattern parameters to all DFB cards:" + tc.ENDC)

        self.TP = self.tp_mode.currentIndex()
        for idx, val in enumerate(self.class_vector):
            self.card_addr = self.addr_vector[idx]
            if self.TP != 0:
                if val == "DFBCLK":
                    self.send_GPI5()
                    self.send_GPI6()
                if val == "DFBx2":
                    self.send_GPI5()
                    self.send_GPI6()
            if val == "DFBCLK":
                self.send_GPI4()
            if val == "DFBx2":
                self.send_GPI4()

    def NSAMP_changed(self):
        if self.NSAMP_delay_timer == None:
            self.NSAMP_delay_timer = QtCore.QTimer()
            self.NSAMP_delay_timer.timeout.connect(self.change_NSAMP)
        self.NSAMP_delay_timer.start(750)

    def change_NSAMP(self):
        log.debug(tc.FCTCALL + "send NSAMP to all DFB cards:" + tc.ENDC)

        self.NSAMP = self.NSAMP_spin.value()
        for idx, val in enumerate(self.class_vector):
            self.card_addr = self.addr_vector[idx]
            if val == "DFBCLK":
                self.send_dfbclk_wreg6(self.card_addr)
            if val == "DFBx2":
                self.send_dfbx2_wreg6(self.card_addr)

        self.writeGlobalsToDotCringeDirectory()
        self.NSAMP_delay_timer.stop()
        self.NSAMP_delay_timer = None

    def SETT_changed(self):
        if self.SETT_delay_timer == None:
            self.SETT_delay_timer = QtCore.QTimer()
            self.SETT_delay_timer.timeout.connect(self.change_SETT)
        self.SETT_delay_timer.start(750)

    def change_SETT(self):
        log.debug(tc.FCTCALL + "send SETT to all DFB cards:" + tc.ENDC)

        self.SETT = self.SETT_spin.value()
        for idx, val in enumerate(self.class_vector):
            self.card_addr = self.addr_vector[idx]
            if val == "DFBCLK":
                LED = self.crate_widgets[idx].LED
                ST = self.crate_widgets[idx].ST
                self.send_dfb_wreg7(LED, ST, self.card_addr)
            if val == "DFBx2":
                LED = self.crate_widgets[idx].LED
                ST = self.crate_widgets[idx].ST
                self.send_dfb_wreg7(LED, ST, self.card_addr)

        self.writeGlobalsToDotCringeDirectory()
        self.SETT_delay_timer.stop()
        self.SETT_delay_timer = None

    def PS_changed(self):
        self.PS = self.PS_button.isChecked()
        if self.PS == 1:
            self.PS_button.setStyleSheet("background-color: #" + tc.green +
                                         ";")
            log.debug(
                tc.FCTCALL +
                "send parallel stream to all DFB cards: parallel stream engaged"
                + tc.ENDC)

        else:
            self.PS_button.setStyleSheet("background-color: #" + tc.red + ";")
            log.debug(
                tc.FCTCALL +
                "send parallel stream to all DFB cards: parallel stream disengaged"
                + tc.ENDC)

        for idx, val in enumerate(self.class_vector):
            self.card_addr = self.addr_vector[idx]
            if val == "DFBCLK":
                self.send_dfbclk_wreg6(self.card_addr)
            if val == "DFBx2":
                self.send_dfbx2_wreg6(self.card_addr)

    def DFBx2class_glb_chg_msg(self):
        log.debug(tc.FCTCALL + "DFBx2 CLASS global changed:", tc.ENDC)

    def ARLsense_changed(self):
        if self.ARLsense_timer == None:
            self.ARLsense_timer = QtCore.QTimer()
            self.ARLsense_timer.timeout.connect(self.change_ARLsense)
        self.ARLsense_timer.start(750)

    def change_ARLsense(self):
        log.debug(
            tc.FCTCALL + "send ARL sensitivity parameter to all DFB cards:",
            tc.ENDC)

        self.ARLsense = self.ARLsense_spin.value()
        #       self.ARLsense_indicator.setText("%5i"%(self.ARLsense))
        self.ARLsense_eng_indicator.setText(str((self.ARLsense) / 16.383)[:6])
        for idx, val in enumerate(self.class_vector):
            self.card_addr = self.addr_vector[idx]
            if val == "DFBCLK" or val == "DFBx2":
                log.debug(tc.FCTCALL + "send ARL sensitivity parameter to",
                          val, "card:", tc.ENDC)

                self.send_dfb_GPI16()

        self.ARLsense_timer.stop()
        self.ARLsense_timer = None

    def RLDpos_changed(self):
        if self.RLDpos_timer == None:
            self.RLDpos_timer = QtCore.QTimer()
            self.RLDpos_timer.timeout.connect(self.change_RLDpos)
        self.RLDpos_timer.start(750)

    def change_RLDpos(self):
        log.debug(
            tc.FCTCALL +
            "send ARL positive relock delay parameter to all DFB cards:",
            tc.ENDC)

        self.RLDpos = self.RLDpos_spin.value()
        self.RLDpos_delay = self.frame_period * self.RLDpos
        #       self.RLDpos_indicator.setText("%5i"%(self.RLDpos))
        self.RLDpos_eng_indicator.setText(
            str((self.RLDpos) * self.frame_period)[:6])
        for idx, val in enumerate(self.class_vector):
            self.card_addr = self.addr_vector[idx]
            if (val == "DFBCLK" or val == "DFBx2"):
                log.debug(tc.FCTCALL + "send RLD positive delay parameter to",
                          val, "card:", tc.ENDC)

                self.send_dfb_GPI17()

        self.RLDpos_timer.stop()
        self.RLDpos_timer = None

    def RLDneg_changed(self):
        if self.RLDneg_timer == None:
            self.RLDneg_timer = QtCore.QTimer()
            self.RLDneg_timer.timeout.connect(self.change_RLDneg)
        self.RLDneg_timer.start(750)

    def change_RLDneg(self):
        log.debug(
            tc.FCTCALL +
            "send ARL negative relock delay parameter to all DFB cards:",
            tc.ENDC)

        self.RLDneg = self.RLDneg_spin.value()
        self.RLDneg_delay = self.frame_period * self.RLDneg
        #       self.RLDneg_indicator.setText("%5i"%(self.RLDneg))
        self.RLDneg_eng_indicator.setText(
            str((self.RLDneg) * self.frame_period)[:6])
        for idx, val in enumerate(self.class_vector):
            self.card_addr = self.addr_vector[idx]
            if (val == "DFBCLK" or val == "DFBx2"):
                log.debug(tc.FCTCALL + "send RLD negative delay parameter to",
                          val, "card:", tc.ENDC)

                self.send_dfb_GPI18()

        self.RLDneg_timer.stop()
        self.RLDneg_timer = None

    def track_changed(self):
        self.RLD_track_state = self.RLD_frame.isChecked()

    def RLDwarning(self):
        log.debug(
            tc.WARNING +
            "ARL physical relock delay changed: this may impact relocking",
            tc.ENDC)

    '''triangle methods'''

    def dwell_changed(self):
        log.debug(tc.FCTCALL + "triangle step dwell changed:", tc.ENDC)
        self.dwell_val = self.dwell.value()
        self.dwellDACunits = 2**(self.dwell_val)
        self.tri_period_changed()
        self.send_triangle()

    def range_changed(self):
        log.debug(tc.FCTCALL + "triangle number of steps changed:", tc.ENDC)
        self.range_val = self.range.value()
        self.rangeDACunits = 2**(self.range_val)
        self.tri_amp_changed()
        self.tri_period_changed()
        self.send_triangle()

    def step_changed(self):
        log.debug(tc.FCTCALL + "triangle step size changed:", tc.ENDC)
        self.step_val = self.step.value()
        self.stepDACunits = self.step_val
        self.tri_amp_changed()
        self.send_triangle()

    def tri_amp_changed(self):
        self.ampDACunits = self.rangeDACunits * self.stepDACunits
        if self.ampDACunits > 16383:
            self.ampDACunits = 16383
        self.amp_indicator.setText('%5i' % self.ampDACunits)
        mV = 1000 * self.ampDACunits / 16383.0
        log.debug(tc.WARNING + "triangle amplitude changed:", mV, "mV",
                  tc.ENDC)
        self.amp_eng_indicator.setText('%4.3f' % mV)

    def tri_period_changed(self):
        self.periodDACunits = float(2 * self.dwellDACunits *
                                    self.rangeDACunits)
        self.period_indicator.setText('%6i' % self.periodDACunits)
        if self.tri_idx == 0:
            uSecs = self.periodDACunits * self.lsync * 0.008
        else:
            uSecs = self.periodDACunits * self.lsync * self.seqln * 0.008
        kHz = 1000 / uSecs
        self.period_eng_indicator.setText('%7.3f' % uSecs)
        self.freq_eng_indicator.setText('%6.3f' % kHz)
        log.debug(tc.WARNING + "triangle period changed:", '%7.3f' % uSecs,
                  "\u00B5s", tc.ENDC)

    def tri_idx_changed(self):
        log.debug(tc.FCTCALL + "triangle time base changed:", tc.ENDC)
        self.tri_idx = self.tri_idx_button.isChecked()
        self.tri_period_changed()
        self.send_triangle()
        if self.tri_idx == 1:
            self.tri_idx_button.setStyleSheet("background-color: #" +
                                              tc.green + ";")
            self.tri_idx_button.setText('FRAME')
        else:
            self.tri_idx_button.setStyleSheet("background-color: #" + tc.red +
                                              ";")
            self.tri_idx_button.setText('LSYNC')

    '''system global methods'''

    def cratePower(self, sleep_s=0.1):
        self.power_state = self.crate_power.isChecked()
        self.send_all_globals.setEnabled(self.power_state)
        self.send_all_states_chns.setEnabled(self.power_state)
        self.cal_system.setEnabled(self.power_state)
        self.resync_system.setEnabled(self.power_state)
        if self.power_state == 1:

            log.info(tc.INIT + "cycle power to crate through EMU: power ON",
                     tc.ENDC)

            self.crate_power.setStyleSheet("background-color: #" + tc.green +
                                           ";")
            self.crate_power.setText('crate power ON')
            self.emu.powerOn()
            log.debug(
                tc.FAIL +
                "calibration has been lost as result of power cycle:", tc.ENDC)

            log.debug(tc.INIT + "reset ALL phase offsets for DFB/BAD cards:",
                      tc.ENDC)

            for idx, val in enumerate(self.class_vector):
                self.card_addr = self.addr_vector[idx]
                if val == "DFBCLK":
                    log.debug(
                        tc.FCTCALL +
                        "reset phase offsets for DFBCLK card address",
                        self.addr_vector[idx], tc.ENDC)

                    self.crate_widgets[idx].dfbclk_widget3.resetALLphase()
                if val == "DFBx2":
                    log.debug(
                        tc.FCTCALL +
                        "reset phase offsets for DFBx2 card address",
                        self.addr_vector[idx], tc.ENDC)

                    self.crate_widgets[idx].dfbx2_widget3.resetALLphase()
                if val == "BAD16":
                    log.debug(
                        tc.FCTCALL +
                        "reset phase offsets for BAD16 card address",
                        self.addr_vector[idx], tc.ENDC)

                    self.crate_widgets[idx].badrap_widget3.resetALLphase()
        else:

            log.info(tc.INIT + "cycle power to crate through EMU: power OFF",
                     tc.ENDC)

            self.crate_power.setStyleSheet("background-color: #" + tc.red +
                                           ";")
            self.crate_power.setText('crate power OFF')
            self.emu.powerOff()
        time.sleep(sleep_s)
        QtCore.QCoreApplication.processEvents()

    def send_ALL_globals(self):

        log.debug(tc.INIT + tc.BOLD + "send ALL globals to ALL cards:",
                  tc.ENDC)

        self.send_all_sys_globals()
        self.send_all_class_globals()

    def send_ALL_states_chns(self, resync=False):

        log.debug(
            tc.INIT + tc.BOLD + "send ALL states & channels to DFB/BAD cards:",
            tc.ENDC)

        for idx, val in enumerate(self.class_vector):
            self.card_addr = self.addr_vector[idx]
            if val == "DFBCLK":

                log.debug(tc.INIT + "send ALL states to DFBCLK card address",
                          self.addr_vector[idx], ":", tc.ENDC)

                self.crate_widgets[
                    idx].dfbclk_widget1.master_vector.chn_send.click()
            if val == "DFBx2":

                log.debug(tc.INIT + "send ALL states to DFBx2 card address",
                          self.addr_vector[idx], ", channel 1:", tc.ENDC)
                self.crate_widgets[
                    idx].dfbx2_widget1.master_vector.chn_send.click()

                log.debug(tc.INIT + "send ALL states to DFBx2 card address",
                          self.addr_vector[idx], ", channel 2:", tc.ENDC)

                self.crate_widgets[
                    idx].dfbx2_widget2.master_vector.chn_send.click()

            if val == "BAD16":

                log.debug(tc.INIT + "send channels to BAD16 card address",
                          self.addr_vector[idx], ":", tc.ENDC)
                self.crate_widgets[
                    idx].badrap_widget1.master_vector.chn_send.click()

                log.debug(tc.INIT + "send ALL states to BAD16 card address",
                          self.addr_vector[idx], ":", tc.ENDC)

                self.crate_widgets[idx].badrap_widget2.SendAllStates()
        if resync:
            self.system_resync()

    def phcal_system(self, resync=True):

        log.debug(
            tc.INIT + tc.BOLD + "auto phase calibrate all DFB/BAD cards:",
            tc.ENDC)

        for idx, val in enumerate(self.class_vector):
            self.card_addr = self.addr_vector[idx]
            if val == "DFBCLK":
                #               print
                #               print tc.INIT + "auto calibrate DFBCLK card address",self.addr_vector[idx],":", tc.ENDC
                self.crate_widgets[idx].dfbclk_widget3.autocal.click()
            if val == "DFBx2":
                #               print
                #               print tc.INIT + "auto calibrate DFBx2 card address",self.addr_vector[idx], tc.ENDC
                self.crate_widgets[idx].dfbx2_widget3.autocal.click()

            if val == "BAD16":
                #               print
                #               print tc.INIT + "auto calibrate BAD16 card address",self.addr_vector[idx],":", tc.ENDC
                self.crate_widgets[idx].badrap_widget3.autocal.click()
        if resync:
            self.system_resync()

    def system_resync(self):

        log.debug(tc.INIT + "resynchronize ALL cards AND SENDING LSYNC:",
                  tc.ENDC)

        self.send_CLK_globals()
        for idx, val in enumerate(self.class_vector):
            self.card_addr = self.addr_vector[idx]
            if val == "DFBCLK":
                self.crate_widgets[idx].dfbclk_widget2.resync_button.click()
        self.writeGlobalsToDotCringeDirectory()

    def lockServer(self):
        self.locked = self.server_lock.isChecked()
        if self.locked == 0:
            message = "restore"
            self.server_lock.setStyleSheet("background-color: #" + tc.green +
                                           ";")
            self.server_lock.setText('server LOCK OFF')

            log.debug(tc.INIT + "critical parameter lock out disengaged:")

            log.debug(
                tc.WARNING +
                "auto re-sync engaged for delay parameter changes:", tc.ENDC)

            log.debug(
                tc.FAIL +
                "changing SYSTEM globals, re-sync, or send mode may crash SERVER (if running):",
                tc.ENDC)

        else:
            message = "limit"
            self.server_lock.setStyleSheet("background-color: #" + tc.red +
                                           ";")
            self.server_lock.setText('server LOCK ON')

            log.debug(
                tc.INIT +
                "critical parameter lock out engaged for SERVER keep alive:",
                tc.ENDC)

            log.debug(
                tc.WARNING +
                "auto re-sync disengaged for delay parameter changes:",
                tc.ENDC)

        self.sys_glob_hdr_widget.setEnabled(not (self.locked))
        self.sendsetup.setEnabled(not (self.locked))
        self.NSAMP_spin.setEnabled(not (self.locked))
        self.dfbclk_xpt_mode.setEnabled(not (self.locked))
        self.dfbx2_xpt_mode.setEnabled(not (self.locked))
        for idx, val in enumerate(self.class_vector):
            self.card_addr = self.addr_vector[idx]
            if val == "DFBCLK":
                log.debug(tc.FCTCALL + message, "SEND MODE on", val, "card:",
                          self.slot_vector[idx], "/", self.card_addr, tc.ENDC)

                #               self.crate_widgets[idx].dfbclk_widget1.master_vector.data_packet.setEnabled(not(self.locked))
                if self.locked == 1:
                    self.crate_widgets[
                        idx].dfbclk_widget1.master_vector.data_packet.setCurrentIndex(
                            0)
                    self.crate_widgets[
                        idx].dfbclk_widget1.master_vector.data_packet.removeItem(
                            3)
                    self.crate_widgets[
                        idx].dfbclk_widget1.master_vector.data_packet.removeItem(
                            2)
                    for i in range(self.seqln):
                        self.crate_widgets[idx].dfbclk_widget1.state_vectors[
                            i].data_packet.removeItem(3)
                        self.crate_widgets[idx].dfbclk_widget1.state_vectors[
                            i].data_packet.removeItem(2)
                else:
                    self.crate_widgets[
                        idx].dfbclk_widget1.master_vector.data_packet.addItem(
                            'FBB, FBA')
                    self.crate_widgets[
                        idx].dfbclk_widget1.master_vector.data_packet.addItem(
                            'test pattern')
                    for i in range(self.seqln):
                        self.crate_widgets[idx].dfbclk_widget1.state_vectors[
                            i].data_packet.addItem('FBB, FBA')
                        self.crate_widgets[idx].dfbclk_widget1.state_vectors[
                            i].data_packet.addItem('test pattern')
                    #                       self.crate_widgets[idx].dfbclk_widget1.state_vectors[i].data_packet.setEnabled(not(self.locked))
            if val == "DFBx2":
                log.debug(tc.FCTCALL + message,
                          "SEND MODE on both channels of", val, "card:",
                          self.slot_vector[idx], "/", self.card_addr, tc.ENDC)

                if self.locked == 1:
                    self.crate_widgets[
                        idx].dfbx2_widget1.master_vector.data_packet.setCurrentIndex(
                            0)
                    self.crate_widgets[
                        idx].dfbx2_widget1.master_vector.data_packet.removeItem(
                            3)
                    self.crate_widgets[
                        idx].dfbx2_widget1.master_vector.data_packet.removeItem(
                            2)
                    self.crate_widgets[
                        idx].dfbx2_widget2.master_vector.data_packet.setCurrentIndex(
                            0)
                    self.crate_widgets[
                        idx].dfbx2_widget2.master_vector.data_packet.removeItem(
                            3)
                    self.crate_widgets[
                        idx].dfbx2_widget2.master_vector.data_packet.removeItem(
                            2)
                    for i in range(self.seqln):
                        self.crate_widgets[idx].dfbx2_widget1.state_vectors[
                            i].data_packet.removeItem(3)
                        self.crate_widgets[idx].dfbx2_widget1.state_vectors[
                            i].data_packet.removeItem(2)
                        self.crate_widgets[idx].dfbx2_widget2.state_vectors[
                            i].data_packet.removeItem(3)
                        self.crate_widgets[idx].dfbx2_widget2.state_vectors[
                            i].data_packet.removeItem(2)
                else:
                    self.crate_widgets[
                        idx].dfbx2_widget1.master_vector.data_packet.addItem(
                            'FBB, FBA')
                    self.crate_widgets[
                        idx].dfbx2_widget1.master_vector.data_packet.addItem(
                            'test pattern')
                    self.crate_widgets[
                        idx].dfbx2_widget2.master_vector.data_packet.addItem(
                            'FBB, FBA')
                    self.crate_widgets[
                        idx].dfbx2_widget2.master_vector.data_packet.addItem(
                            'test pattern')
                    for i in range(self.seqln):
                        self.crate_widgets[idx].dfbx2_widget1.state_vectors[
                            i].data_packet.addItem('FBB, FBA')
                        self.crate_widgets[idx].dfbx2_widget1.state_vectors[
                            i].data_packet.addItem('test pattern')
                        self.crate_widgets[idx].dfbx2_widget2.state_vectors[
                            i].data_packet.addItem('FBB, FBA')
                        self.crate_widgets[idx].dfbx2_widget2.state_vectors[
                            i].data_packet.addItem('test pattern')

    def send_all_sys_globals(self):

        log.debug(tc.INIT + tc.BOLD + "send system globals to all cards:",
                  tc.ENDC)

        self.send_CLK_globals()
        log.debug(
            tc.INIT +
            "send system globals to DFBCLK (DFB CH 1), DFB, and BAD16 cards:",
            tc.ENDC)

        for idx, val in enumerate(self.class_vector):
            self.card_addr = self.addr_vector[idx]
            if (val == "DFBCLK"):
                log.debug(tc.FCTCALL + "send SEQLN parameter to DFB CH1 on",
                          val, "card:", tc.ENDC)

                LED = self.crate_widgets[idx].LED
                ST = self.crate_widgets[idx].ST
                self.send_dfb_wreg7(LED, ST, self.card_addr)
            if (val == "DFBx2"):
                log.debug(tc.FCTCALL + "send SEQLN parameter to", val, "card:",
                          tc.ENDC)

                LED = self.crate_widgets[idx].LED
                ST = self.crate_widgets[idx].ST
                self.send_dfb_wreg7(LED, ST, self.card_addr)
            if val == ("BAD16"):
                log.debug(tc.FCTCALL + "send SEQLN parameter to", val, "card:",
                          tc.ENDC)

                LED = self.crate_widgets[idx].LED
                ST = self.crate_widgets[idx].ST
                INT = self.crate_widgets[idx].INT
                self.send_bad16_wreg0(ST, LED, INT, self.card_addr)
            #               self.crate_widgets[idx].send_class_globals(self.bad_wreg0)

    def send_CLK_globals(self):

        log.debug(
            tc.INIT + "send system globals to DFBCLK card (clock controller):",
            tc.ENDC)

        log.debug(tc.FCTCALL + "send LSYNC parameter to CLK:", tc.ENDC)
        self.crate_widgets[0].dfbclk_widget2.send_wreg2()
        log.debug(tc.FCTCALL + "send SEQLN parameter to CLK:", tc.ENDC)
        self.crate_widgets[0].dfbclk_widget2.send_wreg7()

    def writeGlobalsToDotCringeDirectory(self):
        dirname = os.path.expanduser("~/.cringe")
        if not os.path.isdir(dirname):
            os.mkdir(dirname)
        globals = {
            "lsync": self.lsync,
            "SETT": self.SETT,
            "seqln": self.seqln,
            "NSAMP": self.NSAMP,
            "propagationdelay": self.prop_delay,
            "carddelay": self.dfb_delay,
            "XPT": self.dfbx2_XPT,
            "testpattern": self.TP
        }
        for k, v in list(globals.items()):
            filename = os.path.join(dirname, k)
            log.debug("Writing {}={} to: {}".format(k, v, filename))
            with open(filename, "w") as f:
                f.write(str(v))
        jsonFilename = os.path.join(dirname, "cringeGlobals.json")
        log.debug("Writing all values to {}".format(jsonFilename))
        with open(jsonFilename, "w") as f:
            json.dump(globals, f, indent=4)

    '''class global methods'''

    def send_all_class_globals(self):

        log.debug(tc.INIT + tc.BOLD + "send class globals to all cards:",
                  tc.ENDC)

        self.send_dfb_class_globals()
        self.send_bad_class_globals()
        self.send_triangle()
        self.send_ARL()
        self.send_TP()

    def send_dfb_class_globals(self):
        #       print
        #       print tc.INIT + "send class globals to DFB cards:", tc.ENDC
        #       self.dfbclk_wreg6 = (6 << 25) | (self.PS << 24) | (self.dfbclk_XPT << 21) | (self.CLK << 20) | self.NSAMP
        #       self.dfbx2_wreg6 = (6 << 25) | (self.PS << 24) | (self.dfbx2_XPT << 21) | self.NSAMP
        #       self.dfbclk_wreg6 = (6 << 25) | (self.PS << 24) | (self.dfbclk_XPT << 21) | (self.CLK << 20) | (self.RLDpos << 16) | (self.ARLsense << 12) |(self.RLDneg << 8) | self.NSAMP
        #       self.dfbx2_wreg6 = (6 << 25) | (self.PS << 24) | (self.dfbx2_XPT << 21) | (self.RLDpos << 16) | (self.ARLsense << 12) |(self.RLDneg << 8) | self.NSAMP
        #       self.dfb_wreg7 = (7 << 25) | (self.prop_delay << 18) | (self.dfb_delay << 14) | (self.seqln << 8) | self.SETT
        for idx, val in enumerate(self.class_vector):
            self.card_addr = self.addr_vector[idx]
            if val == "DFBCLK":
                log.debug(
                    tc.FCTCALL + "send DFB class globals to DFBCLK card:",
                    tc.ENDC)

                LED = self.crate_widgets[idx].LED
                ST = self.crate_widgets[idx].ST
                self.send_dfbclk_wreg6(self.card_addr)
                self.send_dfb_wreg7(LED, ST, self.card_addr)
            if val == "DFBx2":
                log.debug(tc.FCTCALL + "send DFB class globals to DFBx2 card:",
                          tc.ENDC)

                LED = self.crate_widgets[idx].LED
                ST = self.crate_widgets[idx].ST
                self.send_dfbx2_wreg6(self.card_addr)
                self.send_dfb_wreg7(LED, ST, self.card_addr)

    def send_bad_class_globals(self):
        #       print
        #       print tc.INIT + "send BAD16 class globals to all BAD16 cards:", tc.ENDC
        for idx, val in enumerate(self.class_vector):
            self.card_addr = self.addr_vector[idx]
            if val == "BAD16":
                log.debug(tc.FCTCALL + "send BAD class globals to BAD16 card:",
                          tc.ENDC)

                LED = self.crate_widgets[idx].LED
                ST = self.crate_widgets[idx].ST
                INT = self.crate_widgets[idx].INT
                self.send_bad16_wreg0(ST, LED, INT, self.card_addr)

    def send_triangle(self):
        #       print
        #       print tc.INIT + "send triangle parameters to DFB, and BAD16 cards:", tc.ENDC
        for idx, val in enumerate(self.class_vector):
            self.card_addr = self.addr_vector[idx]
            if val == ("DFBCLK"):
                log.debug(
                    tc.FCTCALL +
                    "send triangle parameters to DFB CH1 on DFBCLK card:",
                    tc.ENDC)

                self.send_wreg0(1)
                GR = self.crate_widgets[idx].dfbclk_widget1.GR
                self.send_dfb_wreg4(GR, self.card_addr)
            if val == ("DFBx2"):
                log.debug(
                    tc.FCTCALL +
                    "send triangle parameters to DFB CH1 on DFBx2 card:",
                    tc.ENDC)
                self.send_wreg0(1)
                GR = self.crate_widgets[idx].dfbx2_widget1.GR
                self.send_dfb_wreg4(GR, self.card_addr)
                log.debug(
                    tc.FCTCALL +
                    "send triangle parameters to DFB CH2 on DFBx2 card:",
                    tc.ENDC)

                self.send_wreg0(2)
                GR = self.crate_widgets[idx].dfbx2_widget2.GR
                self.send_dfb_wreg4(GR, self.card_addr)

            if val == ("BAD16"):
                log.debug(
                    tc.FCTCALL + "send triangle parameters to BAD16 card:",
                    tc.ENDC)

                self.send_bad16_wreg1()

    def send_ARL(self):
        #       print
        #       print tc.INIT + "send ARL parameters to DFB cards:", tc.ENDC
        for idx, val in enumerate(self.class_vector):
            self.card_addr = self.addr_vector[idx]
            if (val == "DFBCLK" or val == "DFBx2"):
                log.debug(tc.FCTCALL + "send ARL parameters to", val, "card:",
                          tc.ENDC)

                self.send_dfb_GPI16()
                self.send_dfb_GPI17()
                self.send_dfb_GPI18()

    def send_TP(self):
        #       print
        #       print tc.INIT + "send test pattern parameters to DFB cards:", tc.ENDC
        for idx, val in enumerate(self.class_vector):
            self.card_addr = self.addr_vector[idx]
            if (val == "DFBCLK" or val == "DFBx2"):
                log.debug(tc.FCTCALL + "send test pattern parameters to", val,
                          "card:", tc.ENDC)

                self.send_GPI5()
                self.send_GPI6()
                self.send_GPI4()


    ''' child called methods '''

    def broadcast_channel(self, state, var):
        #       print "BROADCAST CHANNEL:"
        #       print
        for idx, val in enumerate(self.class_vector):
            addr = str(self.addr_vector[idx])
            slot = str(self.slot_vector[idx])
            #           if (val == "DFBCLK"):
            #               print tc.FCTCALL + "broadcast to", val,"card:", tc.ENDC
            #               print
            #               self.crate_widgets[idx].dfbclk_widget1.triA_changed(state, True)
            if val == "DFBCLK":
                if self.crate_widgets[idx].dfbclk_widget1.MVRX:
                    log.debug(tc.FCTCALL + "broadcast to", val, "card",
                              slot + "/" + addr + "/1", "(slot/addr/ch):", var,
                              tc.ENDC)

                    if var == "triA":
                        self.crate_widgets[idx].dfbclk_widget1.triA_changed(
                            state, True)
                    if var == "triB":
                        self.crate_widgets[idx].dfbclk_widget1.triB_changed(
                            state, True)
                    if var == "a2d_lp_spin":
                        self.crate_widgets[
                            idx].dfbclk_widget1.a2d_lockpt_spin_changed(
                                state, True)
                    if var == "a2d_lp_slider":
                        self.crate_widgets[
                            idx].dfbclk_widget1.a2d_lockpt_slider_changed(
                                state, True)
                    if var == "d2a_A_spin":
                        self.crate_widgets[
                            idx].dfbclk_widget1.d2a_A_spin_changed(
                                state, True)
                    if var == "d2a_A_slider":
                        self.crate_widgets[
                            idx].dfbclk_widget1.d2a_A_slider_changed(
                                state, True)
                    if var == "d2a_B_spin":
                        self.crate_widgets[
                            idx].dfbclk_widget1.d2a_B_spin_changed(
                                state, True)
                    if var == "d2a_B_slider":
                        self.crate_widgets[
                            idx].dfbclk_widget1.d2a_B_slider_changed(
                                state, True)
                    if var == "SM":
                        self.crate_widgets[
                            idx].dfbclk_widget1.data_packet_changed(
                                state, True)
                    if var == "P":
                        self.crate_widgets[idx].dfbclk_widget1.P_spin_changed(
                            state, True)
                    if var == "I":
                        self.crate_widgets[idx].dfbclk_widget1.I_spin_changed(
                            state, True)
                    if var == "FBa":
                        self.crate_widgets[idx].dfbclk_widget1.FBA_changed(
                            state, True)
                    if var == "FBb":
                        self.crate_widgets[idx].dfbclk_widget1.FBB_changed(
                            state, True)
                    if var == "ARL":
                        self.crate_widgets[idx].dfbclk_widget1.ARL_changed(
                            state, True)
                    if var == "send":
                        self.crate_widgets[idx].dfbclk_widget1.send_channel(
                            True)
                    if var == "lock":
                        self.crate_widgets[idx].dfbclk_widget1.lock_channel(
                            state, True)
            if val == "DFBx2":
                if self.crate_widgets[idx].dfbx2_widget1.MVRX:
                    log.debug(tc.FCTCALL + "broadcast to", val, "card",
                              slot + "/" + addr + "/1", "(slot/addr/ch):", var,
                              tc.ENDC)

                    if var == "triA":
                        self.crate_widgets[idx].dfbx2_widget1.triA_changed(
                            state, True)
                    if var == "triB":
                        self.crate_widgets[idx].dfbx2_widget1.triB_changed(
                            state, True)
                    if var == "a2d_lp_spin":
                        self.crate_widgets[
                            idx].dfbx2_widget1.a2d_lockpt_spin_changed(
                                state, True)
                    if var == "a2d_lp_slider":
                        self.crate_widgets[
                            idx].dfbx2_widget1.a2d_lockpt_slider_changed(
                                state, True)
                    if var == "d2a_A_spin":
                        self.crate_widgets[
                            idx].dfbx2_widget1.d2a_A_spin_changed(state, True)
                    if var == "d2a_A_slider":
                        self.crate_widgets[
                            idx].dfbx2_widget1.d2a_A_slider_changed(
                                state, True)
                    if var == "d2a_B_spin":
                        self.crate_widgets[
                            idx].dfbx2_widget1.d2a_B_spin_changed(state, True)
                    if var == "d2a_B_slider":
                        self.crate_widgets[
                            idx].dfbx2_widget1.d2a_B_slider_changed(
                                state, True)
                    if var == "SM":
                        self.crate_widgets[
                            idx].dfbx2_widget1.data_packet_changed(
                                state, True)
                    if var == "P":
                        self.crate_widgets[idx].dfbx2_widget1.P_spin_changed(
                            state, True)
                    if var == "I":
                        self.crate_widgets[idx].dfbx2_widget1.I_spin_changed(
                            state, True)
                    if var == "FBa":
                        self.crate_widgets[idx].dfbx2_widget1.FBA_changed(
                            state, True)
                    if var == "FBb":
                        self.crate_widgets[idx].dfbx2_widget1.FBB_changed(
                            state, True)
                    if var == "ARL":
                        self.crate_widgets[idx].dfbx2_widget1.ARL_changed(
                            state, True)
                    if var == "send":
                        self.crate_widgets[idx].dfbx2_widget1.send_channel(
                            True)
                    if var == "lock":
                        self.crate_widgets[idx].dfbx2_widget1.lock_channel(
                            state, True)
                if self.crate_widgets[idx].dfbx2_widget2.MVRX:
                    log.debug(tc.FCTCALL + "broadcast to", val, "card",
                              slot + "/" + addr + "/2", "(slot/addr/ch):", var,
                              tc.ENDC)

                    if var == "triA":
                        self.crate_widgets[idx].dfbx2_widget2.triA_changed(
                            state, True)
                    if var == "triB":
                        self.crate_widgets[idx].dfbx2_widget2.triB_changed(
                            state, True)
                    if var == "a2d_lp_spin":
                        self.crate_widgets[
                            idx].dfbx2_widget2.a2d_lockpt_spin_changed(
                                state, True)
                    if var == "a2d_lp_slider":
                        self.crate_widgets[
                            idx].dfbx2_widget2.a2d_lockpt_slider_changed(
                                state, True)
                    if var == "d2a_A_spin":
                        self.crate_widgets[
                            idx].dfbx2_widget2.d2a_A_spin_changed(state, True)
                    if var == "d2a_A_slider":
                        self.crate_widgets[
                            idx].dfbx2_widget2.d2a_A_slider_changed(
                                state, True)
                    if var == "d2a_B_spin":
                        self.crate_widgets[
                            idx].dfbx2_widget2.d2a_B_spin_changed(state, True)
                    if var == "d2a_B_slider":
                        self.crate_widgets[
                            idx].dfbx2_widget2.d2a_B_slider_changed(
                                state, True)
                    if var == "SM":
                        self.crate_widgets[
                            idx].dfbx2_widget2.data_packet_changed(
                                state, True)
                    if var == "P":
                        self.crate_widgets[idx].dfbx2_widget2.P_spin_changed(
                            state, True)
                    if var == "I":
                        self.crate_widgets[idx].dfbx2_widget2.I_spin_changed(
                            state, True)
                    if var == "FBa":
                        self.crate_widgets[idx].dfbx2_widget2.FBA_changed(
                            state, True)
                    if var == "FBb":
                        self.crate_widgets[idx].dfbx2_widget2.FBB_changed(
                            state, True)
                    if var == "ARL":
                        self.crate_widgets[idx].dfbx2_widget2.ARL_changed(
                            state, True)
                    if var == "send":
                        self.crate_widgets[idx].dfbx2_widget2.send_channel(
                            True)
                    if var == "lock":
                        self.crate_widgets[idx].dfbx2_widget2.lock_channel(
                            state, True)

    ''' commanding methods '''

    def send_wreg0(self, col):
        log.debug("DFB:WREG0: page register: col", col)
        wreg = 0 << 25
        wregval = wreg | (col << 6)
        self.sendReg(wregval, self.card_addr)

    def send_dfb_wreg4(self, GR, addr):
        log.debug(
            "DFB:WREG4: triangle parameters; time base, dwell, range, step: global relock boolean:",
            self.tri_idx, self.dwell_val, self.range_val, self.step_val, GR)
        self.dfb_wreg4 = (4 << 25) | (self.tri_idx << 24) | (
            self.dwell_val << 20) | (self.range_val << 16) | (
                GR << 15) | self.step_val
        #       wregval = (4 << 25) | (self.tri_idx << 24) | (self.dwell_val << 20) \
        #           | (self.range_val << 16) | self.GR | self.step_val
        self.sendReg(self.dfb_wreg4, addr)

    def send_dfbclk_wreg6(self, addr):
        log.debug("DFB:WREG6: global parameters: PS, DFBCLK_XPT, CLK, NSAMP:",
                  self.PS, self.dfbclk_XPT, self.CLK, self.NSAMP)
        wregval = (6 << 25) | (self.PS << 24) | (self.dfbclk_XPT << 21) | (
            self.CLK << 20) | self.NSAMP
        self.sendReg(wregval, addr)

    def send_dfbx2_wreg6(self, addr):
        log.debug("DFB:WREG6: global parameters: PS, DFBx2_XPT, NSAMP:",
                  self.PS, self.dfbx2_XPT, self.NSAMP)
        wregval = (6 << 25) | (self.PS << 24) | (
            self.dfbx2_XPT << 21) | self.NSAMP
        self.sendReg(wregval, addr)

    def send_dfb_wreg7(self, LED, ST, addr):
        log.debug(
            "DFB:WREG7: global parameters: LED, ST, prop delay, dfb delay, sequence length, SETT:",
            LED, ST, self.prop_delay, self.dfb_delay, self.seqln, self.SETT)
        wregval = (7 << 25) | (LED << 23) | (ST << 22) | (self.prop_delay << 18) \
            | (self.dfb_delay << 14) | (self.seqln << 8) | self.SETT
        self.sendReg(wregval, addr)

    def send_bad16_wreg0(self, ST, LED, INT, addr):
        log.debug("BAD16:WREG0: ST, LED, card delay, INIT, sequence length:",
                  ST, LED, self.bad_delay, INT, self.seqln)
        #       mask = 0xffebeff
        wregval = (0 << 25) | (ST << 16) | (LED << 14) | (
            self.bad_delay << 10) | (INT << 8) | self.seqln
        self.sendReg(wregval, addr)

    def send_bad16_wreg1(self):
        log.debug(
            "BAD16:WREG1: triangle parameters time base, dwell, range, step:",
            self.tri_idx, self.dwell_val, self.range_val, self.step_val)
        self.bad_wreg1 = (1 << 25) | (self.tri_idx << 24) | (
            self.dwell_val << 20) | (self.range_val << 16) | self.step_val
        self.sendReg(self.bad_wreg1, self.card_addr)

    def send_GPI4(self):
        log.debug("DFB:GPI4: test mode select:", self.TP)
        wreg = 4 << 17
        if self.TP != 0:
            wregval = wreg | 1
        else:
            wregval = wreg | 0
        self.sendReg(wregval, self.card_addr)

    def send_GPI5(self):
        lobytes, hibytes = self.lohibytes()
        log.debug("DFB:GPI5: test pattern hi-bytes [31..16]:",
                  hex(hibytes)[2:].zfill(4))
        wreg = 5 << 17
        wregval = wreg | hibytes
        self.sendReg(wregval, self.card_addr)

    def lohibytes(self):
        if self.TP == 0:
            lobytes = 0xDEAD
            hibytes = 0xBEEF
        if self.TP == 1:
            lobytes = 0x5555
        if self.TP == 2:
            lobytes = 0xaaaa
        if self.TP == 3:
            lobytes = 0x3333
        if self.TP == 4:
            lobytes = 0x0f0f
        if self.TP == 5:
            lobytes = 0x00ff
        if self.TP == 6:
            lobytes = 0xffff
        if self.TP == 7:
            lobytes = 0x0000
        if self.TP == 8:
            lobytes = 0xffff
        if self.TP == 9:
            lobytes = 0xf00d
        if self.TP == 1:
            hibytes = 0x5555
        if self.TP == 2:
            hibytes = 0xaaaa
        if self.TP == 3:
            hibytes = 0x3333
        if self.TP == 4:
            hibytes = 0x0f0f
        if self.TP == 5:
            hibytes = 0x00ff
        if self.TP == 6:
            hibytes = 0x0000
        if self.TP == 7:
            hibytes = 0x0000
        if self.TP == 8:
            hibytes = 0xffff
        if self.TP == 9:
            hibytes = 0x8bad
        return lobytes, hibytes

    def send_GPI6(self):
        lobytes, hibytes = self.lohibytes()
        log.debug("DFB:GPI6: test pattern lo-bytes [15..0]:",
                  hex(lobytes)[2:].zfill(4))
        wreg = 6 << 17
        wregval = wreg | lobytes
        self.sendReg(wregval, self.card_addr)

    def send_dfb_GPI16(self):
        log.debug("DFB:GPI16: ARL sensitivity level:", self.ARLsense)
        wreg = 16 << 17
        wregval = wreg | self.ARLsense
        self.sendReg(wregval, self.card_addr)

    def send_dfb_GPI17(self):
        log.debug("DFB:GPI17: ARL positive relock delay:", self.RLDpos)
        wreg = 17 << 17
        wregval = wreg | self.RLDpos
        self.sendReg(wregval, self.card_addr)

    def send_dfb_GPI18(self):
        log.debug("DFB:GPI18: ARL negative relock delay:", self.RLDneg)
        wreg = 18 << 17
        wregval = wreg | self.RLDneg
        self.sendReg(wregval, self.card_addr)

    def sendReg(self, wregval, addr):
        write_wreg(self.serialport, wregval, addr)

    def saveSettings(self):
        log.debug(tc.FCTCALL + "saving settings in pickle file:", tc.ENDC)
        filename = str(QtWidgets.QFileDialog.getSaveFileName()[0])
        if len(filename) > 0:
            #       if (filename != []):
            if filename[-4:] == '.pkl':
                savename = filename
            else:
                savename = filename + '.pkl'
            log.debug("saving settings file:", filename)

        else:
            log.debug(tc.FAIL + "save file cancelled:", tc.ENDC)

            return
        _save_settings(savename)

    def _save_settings(filename)
        """
        The non-interactive parts of saveSettings have been split into their own function
        (this function) so that saving can be commanded from an external script.
        """
        self.filenameEdit.setText(filename)
        self.packCrateConfig()
        self.packGlobals()
        self.loadGlobals = self.saveGlobals
        self.packClassParameters()
        self.loadClassParameters = self.saveClassParameters
        self.packTower()
        self.loadTower = self.saveTower
        self.packTune()
        self.loadTune = self.saveTune
        currentState = {
            'CrateConfig': self.saveCrateConfig,
            'globals': self.saveGlobals,
            'classParameters': self.saveClassParameters,
            "Tower": self.saveTower,
            "Tune": self.saveTune
        }

        f = open(filename, "wb")

        log.debug(
            tc.FCTCALL + ("Saving current settings in pickle format to %s" % filename), tc.ENDC
        )

        pickle.dump(currentState, f, protocol=0)
        f.close()

    def loadSettings(self, filename=None):
        log.debug(tc.FCTCALL + "load pickle settings:", tc.ENDC)

        if filename is None or filename == False:
            temp = str(QtWidgets.QFileDialog.getOpenFileName()[0])
            if temp == '':
                # If the user hits close this will cleanly exit the method call
                return
            else:
                self.load_filename = temp
        else:
            self.load_filename = filename
        self.filenameEdit.setText(self.load_filename)
        log.debug("loading file: [%s]" % self.load_filename)

        f = open(self.load_filename, "rb")
        load_sys_config = pickle.load(f)
        f.close()
        '''test here for matching crate dimensions
        Vectors are used for build, they represent the structure (cards, addresses, names, location)
        Parameters are settings like a DAC value, or LYSNC or ARL on/off
        '''
        self.loadCrateConfig = load_sys_config['CrateConfig']
        LoadSlotVector = self.loadCrateConfig['SlotVector']
        LoadAddressVector = self.loadCrateConfig['AddressVector']
        LoadClassVector = self.loadCrateConfig['ClassVector']

        log.debug(tc.INIT + "crate configuration settings (from file):")

        log.debug("number of cards in crate: %i" % len(LoadAddressVector))
        log.debug("Type Address Slot")
        for idx, val in enumerate(LoadClassVector):
            log.debug(val, "    ", LoadAddressVector[idx], "    ",
                      LoadSlotVector[idx])
        log.debug(tc.ENDC)
        if LoadSlotVector != self.slot_vector or LoadAddressVector != self.addr_vector or LoadClassVector != self.class_vector:
            log.debug(
                tc.FAIL +
                "load crate configuration does NOT match instantiated crate configuration"
            )
            log.debug("load configuration aborted" + tc.ENDC)

            return

        self.loadGlobals = load_sys_config['globals']
        self.loadClassParameters = load_sys_config['classParameters']
        self.loadTower = load_sys_config["Tower"]
        if "Tune" in list(load_sys_config.keys()):
            self.loadTune = load_sys_config["Tune"]
        self.assertSettings()

    def assertSettings(self):
        log.debug(tc.FCTCALL + ("asserting loaded or last saved settings"),
                  tc.ENDC)

        self.unpackGlobals()
        self.unpackClassParameters()
        self.unpackTower()
        self.unpackTune()

    def packTower(self):
        self.saveTower = {}
        self.saveTower['TowerVector'] = self.tower_vector
        if self.tower_widget is not None:
            self.saveTower["TowerParameters"] = self.tower_widget.packState()

    def packTune(self):
        self.saveTune = {}
        if self.tune_widget is not None:
            self.saveTune["TuneParameters"] = self.tune_widget.packState()

    def packCrateConfig(self):
        self.saveCrateConfig = {
            'SlotVector': self.slot_vector,
            'AddressVector': self.addr_vector,
            'ClassVector': self.class_vector,
        }

    def packGlobals(self):
        self.saveGlobals = {
            'SEQLN': self.seqln,
            'LSYNC': self.lsync,
            'SETT': self.SETT,
            'NSAMP': self.NSAMP,
            'PROP_DELAY': self.prop_delay,
            'DFB_DELAY': self.dfb_delay,
            'DFBx2_XPT': self.dfbx2_XPT,
            'DFBCLK_XPT': self.dfbclk_XPT,
            'TP': self.TP,
            'PS': self.PS,
            'ARL_SENSE': self.ARLsense,
            'RLD_POS': self.RLDpos,
            'RLD_NEG': self.RLDneg,
            'RLD_TRACK': self.RLD_track_state,
            'TRI_DWELL': self.dwell_val,
            'TRI_RANGE': self.range_val,
            'TRI_STEP': self.step_val,
            'TRI_IDX': self.tri_idx
        }

    def unpackGlobals(self):
        self.seqln_spin.setValue(self.loadGlobals['SEQLN'])
        self.lsync_spin.setValue(self.loadGlobals['LSYNC'])
        self.SETT_spin.setValue(self.loadGlobals['SETT'])
        self.NSAMP_spin.setValue(self.loadGlobals['NSAMP'])
        self.prop_delay_spin.setValue(self.loadGlobals['PROP_DELAY'])
        self.dfb_delay_spin.setValue(self.loadGlobals['DFB_DELAY'])
        self.dfbx2_xpt_mode.setCurrentIndex(self.loadGlobals['DFBx2_XPT'])
        self.dfbclk_xpt_mode.setCurrentIndex(self.loadGlobals['DFBCLK_XPT'])
        self.tp_mode.setCurrentIndex(self.loadGlobals['TP'])
        self.PS_button.setChecked(self.loadGlobals['PS'])
        self.ARLsense_spin.setValue(self.loadGlobals['ARL_SENSE'])
        self.RLDpos_spin.setValue(self.loadGlobals['RLD_POS'])
        self.RLDneg_spin.setValue(self.loadGlobals['RLD_NEG'])
        self.RLD_frame.setChecked(self.loadGlobals['RLD_TRACK'])
        self.dwell.setValue(self.loadGlobals['TRI_DWELL'])
        self.range.setValue(self.loadGlobals['TRI_RANGE'])
        self.step.setValue(self.loadGlobals['TRI_STEP'])
        self.tri_idx_button.setChecked(self.loadGlobals['TRI_IDX'])

    def packClassParameters(self):
        for idx, val in enumerate(self.class_vector):
            self.crate_widgets[idx].packClass()
            self.saveClassParameters[
                'classParameters%i' %
                idx] = self.crate_widgets[idx].classParameters

    def unpackClassParameters(self):
        for idx, val in enumerate(self.class_vector):
            self.crate_widgets[idx].unpackClass(
                self.loadClassParameters['classParameters%i' % idx])

    def unpackTower(self):
        if self.tower_widget is not None and "TowerParameters" in self.loadTower:
            self.tower_widget.unpackState(self.loadTower["TowerParameters"])

    def unpackTune(self):
        self.tune_widget.unpackState(self.loadTune["TuneParameters"])

    def closeEvent(self, event):
        self.saveSettings()
        event.accept()


def main():

    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("plastique")
    app.setStyleSheet("""   QPushbutton{font: 10px; padding: 6px}
                            QToolButton{font: 10px; padding: 6px}
                            QLineEdit {background-color: #FFFFCC;}
                            QToolTip {background-color: #FFFFCC}""")

    class MyParser(argparse.ArgumentParser):

        def error(self, message, help=True):
            """override error to print out the help"""
            if help:
                self.print_help()
            sys.stderr.write(message + "\n")
            sys.exit(2)

    p = MyParser(
        description=
        'Enter or import crate card details for GUI build: default 8x32 standard configuration'
    )
    p.add_argument(
        '-A',
        '--card_address',
        action='store',
        dest='addr_vector',
        type=int,
        nargs='+',
        help='List of hardware addresses of cards, example: -A 1 3 5 7 9 32 33.'
    )
    p.add_argument(
        '-S',
        '--slot',
        action='store',
        dest='slot_vector',
        type=int,
        nargs='+',
        help='List of slot positions in crate, example: -S 1 3 4 5 6 10 11')
    p.add_argument(
        '-C',
        '--type',
        action='store',
        dest='class_vector',
        type=str,
        nargs='+',
        help=
        'List of card types, example: DFBCLK DFBx2 DFBx2 DFBx2 DFBx2 BAD16 BAD16'
    )
    p.add_argument(
        '-T',
        '--tower',
        action="store",
        dest="tower_vector",
        type=str,
        nargs='+',
        help=
        "for tower provide a list of names and addresses, example: -T DB1 13 SAb 4 SQ1b 12"
    )
    p.add_argument(
        '-F',
        '--file',
        action='store',
        dest='setup_filename',
        type=str,
        nargs=1,
        default="",
        help=
        'Setup file from which to extract CRATE configuration, example: -F cringe_save.pkl'
    )
    p.add_argument(
        '-L',
        '--load',
        action='store_true',
        help=
        'Use file dialog to load file from which to extract CRATE configuration'
    )
    p.add_argument('-i',
                   '--interactive',
                   action='store_true',
                   dest='interactive',
                   help='Drop into an interactive IPython window')  # ADDED JG
    p.add_argument('-r',
                   '--raw',
                   action="store_true",
                   dest="raw",
                   help="add the Calibration tab (experimental)")
    p.add_argument(
        '-D',
        '--debug',
        action="store_true",
        help=
        "enable debug log level, aka print out EVERYTHING like what values are sent to what registers"
    )

    args = p.parse_args()

    if args.debug:
        log.set_debug()
    log.info("cringe.main with args={}".format(args))

    if not any(vars(args).values()):
        # this exits
        p.error(tc.BOLD +
                "No arguments provided. You probably want -L or -F." + tc.ENDC)

    def noneLen(x):
        if x is None:
            return 0
        return len(x)

    if not noneLen(args.addr_vector) == noneLen(args.slot_vector) == noneLen(
            args.class_vector):
        p.error(tc.BOLD +
                "-A, -S and -C must all have the same number of arguments" +
                tc.ENDC)

    # -F gives setup_file which takes a filename from the command line
    # -L gets a filename from a open file dialog
    if args.setup_filename != "" or args.load:
        load_file = None
        if args.load:
            load_filename = str(
                QtWidgets.QFileDialog.getOpenFileName(
                    caption="choose cringe file",
                    directory=os.path.expanduser("~/cringe_config"),
                    filter="(*.pkl)")[0])
        else:
            load_filename = args.setup_filename[0]
        load_file = open(load_filename, "rb")
        log.info("build GUI from file:")
        log.info(f"load filename: {load_filename}")
        log.info(f"load file: {load_file}")

        load_sys_config = pickle.load(load_file)
        load_file.close()
        load_on_launch = True
        log.info("failed to interpret file %s" % load_filename)
        # these are global variables accessed later
        tower_vector = load_sys_config['Tower']['TowerVector']
        loadCrateConfig = load_sys_config['CrateConfig']
        slot_vector = loadCrateConfig['SlotVector']
        addr_vector = loadCrateConfig['AddressVector']
        class_vector = loadCrateConfig['ClassVector']
        log.info("slot vector from file:")
        log.info(slot_vector)

        log.info("address vector from file:")
        log.info(addr_vector)

        log.info("class vector from file:")
        log.info(class_vector)

    else:
        load_on_launch = False

    if not load_on_launch:
        addr_vector = args.addr_vector
        slot_vector = args.slot_vector
        class_vector = args.class_vector
        tower_vector = args.tower_vector
    else:
        if not args.tower_vector is None:
            log.info("using tower vector from command line, not from file")
            tower_vector = args.tower_vector
            log.info(tower_vector)

    # old main below here
    app.processEvents()
    # later it will run load settings if argfilename is not None
    if load_on_launch:
        argfilename = load_filename
    else:
        argfilename = None

    win = Cringe(addr_vector=addr_vector,
                 slot_vector=slot_vector,
                 class_vector=class_vector,
                 tower_vector=tower_vector,
                 argfilename=argfilename,
                 calibrationtab=args.raw)

    win.show()
    if args.interactive:

        def to_interactive():
            print(
                "Going to interactive mode. Press ctrl-c to return to ipython")
            while True:
                app.processEvents()
                time.sleep(0.01)  # prevent cringe from using 100% cpu

        IPython.start_ipython(argv=[],
                              user_ns={
                                  "win": win,
                                  "app": app,
                                  "to_interactive": to_interactive
                              })
    app.exec_()


if __name__ == '__main__':
    main()
