import adr_system
import time
import zaber


class TempControl():
    def __init__(self, app=None, tempTarget = 0.035, adr_system_in = None, controlThermExcitation = 10e-9, baseTempResistance = 60e3,
                 rampRate = 0.050):
        if adr_system_in is None:
            self.a = adr_system.AdrSystem(app)
        else:
            self.a = adr_system_in

        self.controlThermExcitation = controlThermExcitation
        self.baseTempResistance = baseTempResistance
        self.rampRate = rampRate
        self.readyToControl = False
        self.readyToRamp = False


    def setupRamp(self):
        heaterOut = self.getHeaterOut()
        if heaterOut == 0:
            self.setHeaterOut(0)
            self.a.temperature_controller.magUpSetup()
            self.setHeaterOut(0)
            self.readyToRamp = True
            self.readyToControl = False
            self.a.magnet_control_relay.setRelayToRamp()
            time.sleep(5)



    def setupTempControl(self):
        heaterOut = self.getHeaterOut()
        if heaterOut == 0:
            self.a.magnet_control_relay.setRelayToControl()
            self.a.temperature_controller.setScan(channel = 1, autoscan = 'off')
            time.sleep(5)
            self.a.temperature_controller.setReadChannelSetup(exciterange=self.controlThermExcitation, resistancerange=self.baseTempResistance)
            time.sleep(5) # let the transition from changing the thermometer settle

            self.a.temperature_controller.setHeaterRange(range=0)
            # temp setpoint should respond instantly when heater range is zero
            self.a.temperature_controller.setTemperatureControlSetup(channel=1, units='Kelvin', maxrange=100, delay=2, output='current', filterread='unfiltered')
            self.a.temperature_controller.setControlMode(controlmode = 'closed')
            self.a.temperature_controller.setControlPolarity(polarity = 'unipolar')
            self.a.temperature_controller.setTemperatureSetPoint(setpoint=0.035)
            self.a.temperature_controller.setRamp(rampmode = 'on' , ramprate = self.rampRate)
            self.a.temperature_controller.setHeaterRange(range=100)
            self.readyToRamp = False
            self.readyToControl = True
            time.sleep(2)

        elif self.readyToControl is False:
            print('tempControlTupac wont take control until the heaterOut is 0, get it there manually and try again')
        else:
            print('tempControlTupac thinks it is already controlling the temperature, so it didnt change anything')

    def goToTemp(self, tempTarget = 0.035):
        if self.readyToControl is True:
            self.a.temperature_controller.setReadChannelSetup(exciterange=self.controlThermExcitation, resistancerange=self.baseTempResistance)
            time.sleep(3)
            self.a.temperature_controller.setTemperatureSetPoint(tempTarget)
        else:
            print("did not goToTemp because readyToControl is False")

    def safeAutorange(self):
        resistance = self.a.temperature_controller.getResistance(channel=1)
        newstring = self.resistanceToResistanceRangeString(resistance)
        nowstring = self.getCurrentResistanceRangeString()
        if newstring != nowstring:
            self.a.temperature_controller.setReadChannelSetup(exciterange=self.controlThermExcitation, resistancerange=resistance*1.1)
            print("safeAutorange changing from %s to %s"%(nowstring, newstring))
            return True
        else:
            return False

    def getSetTemp(self):
        return self.a.temperature_controller.getTemperatureSetPoint()
    def setSetTemp(self,v):
        self.a.temperature_controller.setTemperatureSetPoint(v)
    def getTemp(self, channel=1):
        return self.a.temperature_controller.getTemperature(channel)

    def getHeaterOut(self, channel=1):
        return self.a.temperature_controller.getHeaterOut()

    def setHeaterOut(self,v):
        self.a.temperature_controller.setManualHeaterOut(v)

    def getTempError(self, channel=1):
        setPoint = self.a.temperature_controller.getTemperatureSetPoint()
        currentTemp = self.getTemp(channel)
        return currentTemp-setPoint

    def resistanceToResistanceRangeString(self, resistancerange):
            #Get Resistance Range String
        if resistancerange < 2e-3:
            resistancerangestring= '1'
        elif resistancerange > 2e-3 and resistancerange <= 6.32e-3:
            resistancerangestring = '2'
        elif resistancerange > 6.32e-3 and resistancerange <= 20e-3:
            resistancerangestring = '3'
        elif resistancerange > 20e-3 and resistancerange <= 63.2e-3:
            resistancerangestring = '4'
        elif resistancerange > 63.2e-3 and resistancerange <= 200e-3:
            resistancerangestring = '5'
        elif resistancerange > 200e-3 and resistancerange <= 632e-3:
            resistancerangestring = '6'
        elif resistancerange > 632e-3 and resistancerange <= 2.0:
            resistancerangestring = '7'
        elif resistancerange > 2.0 and resistancerange <= 6.32:
            resistancerangestring = '8'
        elif resistancerange > 6.32 and resistancerange <= 20:
            resistancerangestring = '9'
        elif resistancerange > 20 and resistancerange <= 63.2:
            resistancerangestring = '10'
        elif resistancerange > 63.2 and resistancerange <= 200:
            resistancerangestring = '11'
        elif resistancerange > 200 and resistancerange <= 632:
            resistancerangestring = '12'
        elif resistancerange > 632 and resistancerange <= 2e3:
            resistancerangestring = '13'
        elif resistancerange > 2e3 and resistancerange <= 6.32e3:
            resistancerangestring = '14'
        elif resistancerange > 6.32e3 and resistancerange <= 20e3:
            resistancerangestring = '15'
        elif resistancerange > 20e3 and resistancerange <= 63.2e3:
            resistancerangestring = '16'
        elif resistancerange > 63.2e3 and resistancerange <= 200e3:
            resistancerangestring = '17'
        elif resistancerange > 200e3 and resistancerange <= 632e3:
            resistancerangestring = '18'
        elif resistancerange > 632e3 and resistancerange <= 2e6:
            resistancerangestring = '19'
        elif resistancerange > 2e6 and resistancerange <= 6.32e6:
            resistancerangestring = '20'
        elif resistancerange > 6.32e6 and resistancerange <= 20e6:
            resistancerangestring = '21'
        elif resistancerange > 20e6 and resistancerange <= 63.2e6:
            resistancerangestring = '22'
        elif resistancerange > 63.2e6 and resistancerange <= 200e6:
            resistancerangestring = '23'
        else:
            resistancerangestring = '1'
        return resistancerangestring

    def getCurrentResistanceRangeString(self):
        data = self.a.temperature_controller.ask("RDGRNG? 1")
        return data.split(",")[2]
