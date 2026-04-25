'''
Created on July 20, 2011

@author: schimaf

Versions:

1.0.2   10/16/2012   Check if the power supplies are powered in the GUI. Remove unused imports.

'''

import sys
import os
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from . import tower_power_supplies
from .tower_power_supplies_worker import TowerPowerSuppliesWorker

class MainWindow(QMainWindow):
    def __init__(self, app):
        ''' Constructor '''
        super(MainWindow,self).__init__()

        self.app = app
        self.power_on = False
        self.power_state_string = "Power is OFF"
        my_dir = os.path.dirname(__file__)
        pixmap = QPixmap(os.path.join(my_dir,"towerpowericon.png"))
        self.setWindowIcon(QIcon(pixmap))

        self.version = "1.0.2"

        self.setWindowTitle(f"Tower Power Supply GUI {self.version}")
        self.setGeometry(100, 100, 360, 100)

        self.power_supplies = None

        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)

        self.layout_widget = QWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        self.top_text_label = QLabel("Tower Power Supply Control", self.central_widget)
        self.psa_label = QLabel("Power Supply A: connecting...", self.central_widget)
        self.psb_label = QLabel("Power Supply B: connecting...", self.central_widget)
        self.power_state_label = QLabel(self.power_state_string, self.central_widget)
        self.power_on_button = QPushButton("Power ON", self.central_widget)
        self.power_off_button = QPushButton("Power OFF", self.central_widget)
        self.quit_button = QPushButton("Quit", self.central_widget)
        self.readingLabel = QLabel("no readings yet", self.central_widget)

        self.buttons_layout_widget = QWidget(self.central_widget)
        self.buttons_layout = QHBoxLayout(self.buttons_layout_widget)

        self.layout.addWidget(self.top_text_label, 0, Qt.AlignHCenter)
        self.layout.addWidget(self.psa_label)
        self.layout.addWidget(self.psb_label)
        self.layout.addWidget(self.buttons_layout_widget)
        self.layout.addWidget(self.power_state_label, 0, Qt.AlignHCenter)
        self.layout.addWidget(self.readingLabel)
        # self.readingLabel.setPixmap(pixmap) # test that the pixmap was loaded


        self.buttons_layout.addWidget(self.power_on_button)
        self.buttons_layout.addWidget(self.power_off_button)
        self.buttons_layout.addWidget(self.quit_button)

        self.power_on_button.clicked.connect(self.power_on_event)
        self.power_off_button.clicked.connect(self.power_off_event)
        self.quit_button.clicked.connect(self.quit_event)

        self.power_on_button.setEnabled(False)
        self.power_off_button.setEnabled(False)

        self._thread = QThread()
        self._worker = TowerPowerSuppliesWorker()
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.ready.connect(self._on_instruments_ready)
        self._worker.failed.connect(self._on_instruments_failed)
        self._thread.start()

    def _on_instruments_ready(self, power_supplies):
        self.power_supplies = power_supplies
        self._thread.quit()
        ps1 = power_supplies.power_supply_1
        ps2 = power_supplies.power_supply_2
        self.psa_label.setText(f"Power Supply A: {ps1.manufacturer} {ps1.model_number} (pad={ps1.pad})")
        self.psb_label.setText(f"Power Supply B: {ps2.manufacturer} {ps2.model_number} (pad={ps2.pad})")
        self.power_on_button.setEnabled(True)
        self.power_off_button.setEnabled(True)
        self.updatePowerOnString()

    def _on_instruments_failed(self, error):
        self._thread.quit()
        self.psa_label.setText("Power Supply A: failed to connect")
        self.psb_label.setText("Power Supply B: failed to connect")
        self.readingLabel.setText("Error: " + error)

    def _set_buttons_enabled(self, enabled):
        self.power_on_button.setEnabled(enabled)
        self.power_off_button.setEnabled(enabled)

    def _run_in_thread(self, worker, slot):
        thread = QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(slot)
        worker.failed.connect(lambda e: (self._on_instruments_failed(e), self._set_buttons_enabled(True)))
        thread.start()
        return thread

    def power_on_event(self):
        self._set_buttons_enabled(False)
        worker = TowerPowerSuppliesWorker(self.power_supplies)
        worker.power_on_done.connect(self._on_power_on_done)
        self._power_on_thread = self._run_in_thread(worker, worker.run_power_on)

    def _on_power_on_done(self, s):
        self._power_on_thread.quit()
        self.updatePowerOnString()
        self.readingLabel.setText("most recent readings:\n" + s)
        self._set_buttons_enabled(True)

    def power_off_event(self):
        self._set_buttons_enabled(False)
        worker = TowerPowerSuppliesWorker(self.power_supplies)
        worker.power_off_done.connect(self._on_power_off_done)
        self._power_off_thread = self._run_in_thread(worker, worker.run_power_off)

    def _on_power_off_done(self):
        self._power_off_thread.quit()
        self.updatePowerOnString()
        self._set_buttons_enabled(True)

    def quit_event(self):

        self.app.quit()

    def updatePowerOnString(self):
        if self.power_supplies is None:
            return
        if self.power_supplies.powered == True:
            self.power_state_string = "Power is ON"
        else:
            self.power_state_string = "Power is OFF"
        self.power_state_label.setText(self.power_state_string)

def main():
    app = QApplication(sys.argv)
    win = MainWindow(app)
    win.show()
    win.setWindowIcon(QIcon("towerpowericon.png"))
    app.exec_()

if __name__=="__main__":
    main()