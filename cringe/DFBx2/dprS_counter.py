import os
import sys

from PyQt5 import QtGui, QtCore, QtWidgets, uic
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from cringe.shared import terminal_colors as tc
from cringe.shared import log
from cringe.shared.rack_transport import write_wreg

class dprS_counter(QWidget):
    
    def __init__(self, parent=None, layout=None, pcs=0, idx=0, slot=1, coeffs=[0], appTrim=[0], serialport=None, cardaddr=3):

        super(dprS_counter, self).__init__()
        
        self.serialport = serialport
        self.address = cardaddr
        self.cal_off = coeffs[pcs]
#         self.cal_off = 0
        self.slot = slot

        self.parent = parent
        self.layout = layout
        self.counter = pcs
        self.coeffs = coeffs
        self.ptrim = appTrim
                
        self.msg = 0
        self.lastSpinVal = 0
        self.lastTotVal = 0
        self.ctr_dsc = self.parent.ctr_dsc[idx]
        self.ctr_fct = self.parent.ctr_fct[idx]
        self.card_type = self.parent.card_type
        self.card_ID = str(self.card_type) + " [" + str(self.slot) + "/" + str(self.address) + "]"

        self.resetFlag = False
        self.commitFlag = False
        
        if pcs == 0:
            self.pcs_str = "ALL counters"
            sep_str = "+"
        else:
            sep_str = "|"
            if pcs == 1:
                self.pcs_str = "M counter"
            else:
                self.pcs_str = "C"+str(pcs-2)+" counter"
                
        uic.loadUi(os.path.join(os.path.dirname(__file__), 'dpr_counter.ui'), self)

        # Dynamic titles and text
        self.layout_widget.setTitle(self.pcs_str)
        self.counter_label.setText(self.ctr_dsc)
        self.counter_label2.setText(self.ctr_fct)
        self.seperator_label.setText(sep_str)
        self.seperator2_label.setText(sep_str)
        self.calibrate.setText("Calibrate " + self.pcs_str)

        # Set initial values
        self.cal_offset.setText(str(self.cal_off))
        self.phase_trim_spin.setValue(self.ptrim[self.counter])
        self.tot_steps.setText(str(self.cal_off + self.phase_trim_spin.value()))
        self.cal_off_deg.setText(str(self.cal_off * 9))
        self.trim_deg.setText(str(self.phase_trim_spin.value() * 9))
        self.tot_degs.setText(str((self.cal_off + self.phase_trim_spin.value()) * 9))

        # Connect signals
        self.phase_trim_spin.valueChanged.connect(self.newvalue)
        self.calibrate.clicked.connect(self.calcounter)
        self.commit.clicked.connect(self.commit_cal)

        if self.parent is not None:
            self.layout.addWidget(self.layout_widget)

    def newvalue(self, val):
        if self.resetFlag == True:
            return
        if self.commitFlag == True:
            return
        self.trim_deg.setText(str(self.phase_trim_spin.value()*9))

        if self.counter == 0:         
            self.tot_steps.setText(str(self.cal_off+self.phase_trim_spin.value()))
            log.debug(tc.FCTCALL + "step phase", self.card_ID,":", self.pcs_str, "from", self.lastTotVal,"to", self.tot_steps.text(), tc.ENDC)
        else:
            self.tot_steps.setText(str(self.phase_trim_spin.value()))
            log.debug(tc.FCTCALL + "step phase:", self.card_ID,":", self.pcs_str, "from", self.lastSpinVal,"to", val, tc.ENDC)
        

        self.tot_degs.setText(str(int(self.tot_steps.text())*9))
        self.ptrim[self.counter] = int(self.tot_steps.text())

        self.enableDPR()
        
        log.debug("set phase adjust counter (pll_counter)")
        self.send_cmd(29, self.counter)
        
        if val > self.lastSpinVal:
            log.debug("increment "+ self.pcs_str)
            self.send_cmd(30, 0b01)
        else:
            log.debug("decrement "+ self.pcs_str)
            self.send_cmd(30, 0b10)
            
        log.debug("reset phase step register (dyn_phase)")
        self.send_cmd(30, 0)

        self.disableDPR()
        

        self.lastSpinVal = val
        self.lastTotVal = int(self.tot_steps.text())

        if self.tot_steps.text() == self.cal_offset.text():
            self.tot_steps.setStyleSheet("background-color: #90EE90;")
        else:
            self.tot_steps.setStyleSheet("background-color: #F08080;")
            
    def commit_cal(self):
        log.debug(tc.FCTCALL + "commit calibration", self.card_ID,":",  self.pcs_str, tc.ENDC)
        self.commitFlag = True
        self.cal_offset.setStyleSheet("background-color: #90EE90;")
        self.tot_steps.setStyleSheet("background-color: #90EE90;")
        self.cal_off = int(self.tot_steps.text())
        self.coeffs[self.counter] = self.cal_off
        self.cal_offset.setText(str(self.cal_off))
        self.cal_off_deg.setText(str(self.cal_off*9))
        if self.counter == 0:
            self.phase_trim_spin.setValue(0)
            self.tot_steps.setText(str(self.cal_off))
            self.trim_deg.setText(str(0))
            self.tot_degs.setText(str(self.cal_off*9))
            log.debug("send slot:", self.slot)
            self.send_cmd(24, self.slot)
            log.debug("send phase trim coefficient:", self.cal_off)
            self.send_cmd(25, self.cal_off & 0x000ff)
        self.ptrim[self.counter] = int(self.tot_degs.text())
        self.commitFlag = False
        
        

    def calcounter(self):
        log.debug(tc.FCTCALL + "calibrate counter", self.card_ID,":", self.pcs_str, tc.ENDC)
        
        if self.counter == 0:
            '''
             This case implements a firmware PLL reset & auto calibration.
             The auto calibration applies the slot & phase trim offsets to ALL counters.
             As a result of the RESET process, the other individual counter offsets are reset as well.
             In this case the code must reset the spin values and total steps of the other counters to 0.
             But changing a spin value calls newvalue which automatically steps the phase.
             So we must use a flag, self.resetFlag, set in resetPhase, to branch out of NEWVALUE when called from there.
            '''
            log.debug(tc.FCTCALL + "firmware calibrate ALL counters:", tc.ENDC)
            log.debug("send slot:", self.slot)
            self.send_cmd(24, self.slot)
            log.debug("send phase trim coefficient:", self.cal_off)
            self.send_cmd(25, self.cal_off & 0x000ff)   # mask for 2's complement negative offsets
        
            log.debug("set phase adjust counter (pll_counter)")
            self.send_cmd(29, self.counter)

            self.parent.resetALLphase()         # reset ALL phase
            self.tot_steps.setText(self.cal_offset.text())
            self.tot_degs.setText(str(int(self.tot_steps.text())*9))

            log.debug(tc.FCTCALL + "firmware autocal (for phase trim calibration coefficient & slot offsets):", tc.ENDC)
            
            self.enableDPR()

            log.debug("phase calibrate = True")
            
            self.send_cmd(28, 1)                # PC => HI
            
            log.debug("phase calibrate = False")
            
            self.send_cmd(28, 0)                # PC => LO
             
            self.disableDPR()

        else:
            steps = self.phase_trim_spin.value() - int(self.cal_offset.text())
            log.debug("software calibrate (for phase trim):", -steps, "phase steps applied")
            
            while steps != 0:
                if steps > 0:
                    self.phase_trim_spin.setValue(self.phase_trim_spin.value() - 1)
                    steps = steps -1
                if steps < 0:
                    self.phase_trim_spin.setValue(self.phase_trim_spin.value() + 1)
                    steps = steps +1
        
        self.cal_offset.setStyleSheet("background-color: #90EE90;")
        self.tot_steps.setStyleSheet("background-color: #90EE90;")
        self.ptrim[self.counter] = int(self.tot_steps.text())
        
    def loadCal(self, cal_val):
        log.debug(tc.FCTCALL + "load calibration", self.card_ID,":", self.pcs_str, tc.ENDC)
        self.cal_off = cal_val
#         self.cal_off = self.coeffs[self.counter]
        self.cal_offset.setText(str(self.cal_off))
        self.cal_off_deg.setText(str(self.cal_off*9))
        if self.tot_steps.text() == self.cal_offset.text():
            self.tot_steps.setStyleSheet("background-color: #90EE90;")
        else:
            self.tot_steps.setStyleSheet("background-color: #F08080;")            
        
               
    def enableDPR(self):            # set True before sending DPR commands
        log.debug("enable DPR", tc.ENDC)
        self.send_cmd(26, 1)

    def disableDPR(self):            # set False after sending DPR commands
        log.debug("disable DPR", tc.ENDC)
        self.send_cmd(26, 0)

    def resetPhase(self):
        log.debug(tc.FCTCALL + "reset phase", self.card_ID,":", self.pcs_str, tc.ENDC)
        
        self.resetFlag = True
        if self.counter == 0:                   # firmware PLL reset
            self.enableDPR()
            log.debug("phase reset = True")
            self.send_cmd(27, 1)                # PR HI
            log.debug("phase reset = False")
            self.send_cmd(27, 0)                # PR LO
            self.disableDPR()
            self.allCountersReset = True
            
        'reset spin & total values to 0'
        
        self.phase_trim_spin.setValue(0)
        self.tot_steps.setText(str(0))
        self.trim_deg.setText(str(0))
        self.tot_degs.setText(str(0))
        
        self.ptrim[self.counter] = int(self.tot_steps.text())
        
        self.lastSpinVal = 0
        self.lastTotVal = 0

        'if total value differ from calibration offsets set total cells RED to indicate out of calibration'
        
        if self.tot_steps.text() == self.cal_offset.text():
            self.tot_steps.setStyleSheet("background-color: #90EE90;")
        else:
            self.tot_steps.setStyleSheet("background-color: #F08080;")
        
        self.resetFlag = False
        
    def send_cmd(self, GPI, val): 
        wregval = (GPI << 20) | val
        log.debug(tc.COMMAND + "send to card address", self.address, "/ GPI", GPI, ":", tc.BOLD, wregval, "(", val, ")",tc.ENDC)
        write_wreg(self.serialport, wregval, self.address)
            
    def sendReg(self, wregval):
        write_wreg(self.serialport, wregval, self.address, sleep_after=0)

def main():
     
    app = QApplication(sys.argv)
    ex = dprS_counter()
    sys.exit(app.exec_())
 
if __name__ == '__main__':
    main()
