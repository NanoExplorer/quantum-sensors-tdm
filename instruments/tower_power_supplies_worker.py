from PyQt5.QtCore import QObject, pyqtSignal
from . import tower_power_supplies


class TowerPowerSuppliesWorker(QObject):
    ready = pyqtSignal(object)  # emits TowerPowerSupplies instance
    power_on_done = pyqtSignal(str)  # emits readings string
    power_off_done = pyqtSignal()
    failed = pyqtSignal(str)

    def __init__(self, power_supplies=None):
        super().__init__()
        self.power_supplies = power_supplies

    def run(self):
        try:
            ps = tower_power_supplies.TowerPowerSupplies()
            self.ready.emit(ps)
        except Exception as e:
            self.failed.emit(str(e))

    def run_power_on(self):
        try:
            s = self.power_supplies.powerOnSequence()
            self.power_on_done.emit(s)
        except Exception as e:
            self.failed.emit(str(e))

    def run_power_off(self):
        try:
            self.power_supplies.powerOffSupplies()
            self.power_off_done.emit()
        except Exception as e:
            self.failed.emit(str(e))
