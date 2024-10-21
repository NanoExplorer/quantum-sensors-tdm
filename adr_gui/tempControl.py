import adr_system
import time


class TempControl():
    def __init__(self, app=None, tempTarget = 0.035, adr_system_in = None, controlThermExcitation = 10e-9, baseTempResistance = 60e3,
                 rampRate = 0.05, channel = 1):
        if adr_system_in is None:
            self.a = adr_system.AdrSystem(app)
        else:
            self.a = adr_system_in

        self.controlThermExcitation = controlThermExcitation
        self.baseTempResistance = baseTempResistance
        self.rampRate = rampRate
        self.readyToControl = False
        self.readyToRamp = False
        self.controlChannel = channel


    def readAltChannelAndReturnToControlChannel(self, alt_ch):
        self.a.temperature_controller.setScan(alt_ch)
        time.sleep(5)
        temp_K = self.a.temperature_controller.getTemperature(alt_ch)
        self.a.temperature_controller.setScan(self.controlChannel)
        return temp_K
       

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
        print(("setup temp control channel={}".format(self.controlChannel)))
        print(("and excitation = {}".format(self.controlThermExcitation)))
        heaterOut = self.getHeaterOut()
        if heaterOut == 0:
            self.a.temperature_controller.setControlPolarity(polarity = 'unipolar')
            self.a.magnet_control_relay.setRelayToControl()
            self.a.temperature_controller.setScan(channel = self.controlChannel, autoscan = 'off')
            time.sleep(5)
            self.a.temperature_controller.setReadChannelSetup(channel=self.controlChannel,exciterange=self.controlThermExcitation, resistancerange=self.baseTempResistance)
            time.sleep(5) # let the transition from changing the thermometer settle

            self.a.temperature_controller.setHeaterRange(range=0)
            # temp setpoint should respond instantly when heater range is zero
            self.a.temperature_controller.setTemperatureControlSetup(channel = self.controlChannel, units='Kelvin', maxrange=100, delay_s=2, output='current', filterread='unfiltered')
            self.a.temperature_controller.setControlMode(controlmode = 'closed')
            self.a.temperature_controller.setTemperatureSetPoint(setpoint=0.035)
            self.a.temperature_controller.setRamp(rampmode = 'on' , ramprate = self.rampRate)
            self.a.temperature_controller.setHeaterRange(range=100)
            self.readyToRamp = False
            self.readyToControl = True
            time.sleep(2)

        elif self.readyToControl is False:
            print(f'tempControlTupac wont take control until the heaterOut is 0, get it there manually and try again. {heaterOut}')
        else:
            print('tempControlTupac thinks it is already controlling the temperature, so it didnt change anything')

    def goToTemp(self, tempTarget = 0.035):
        if self.readyToControl is True:
            self.a.temperature_controller.setReadChannelSetup(channel=self.controlChannel,
            exciterange=self.controlThermExcitation, resistancerange=self.baseTempResistance)
            time.sleep(3)
            self.a.temperature_controller.setTemperatureSetPoint(tempTarget)
        else:
            print("did not goToTemp because readyToControl is False")

    def safeAutorange(self):
        resistance = self.a.temperature_controller.getResistance(channel=self.controlChannel)
        new_r = resistance * 1.1 # hysteresis range = 10%
        oldstring = self.resistanceToResistanceRangeString(resistance).encode()
        newstring = self.resistanceToResistanceRangeString(new_r).encode()
        nowstring = self.getCurrentResistanceRangeString()
        if oldstring != nowstring and newstring != nowstring:
            # both calculated values disagree with the lakeshore, so update the lakeshore
            self.a.temperature_controller.setReadChannelSetup(
                channel=self.controlChannel,
                exciterange=self.controlThermExcitation, 
                resistancerange=new_r
            )
            print(("safeAutorange changing from %s to %s"%(nowstring, newstring)))
            print(f"Autorange reporting resistance={resistance}")
            return True
        # print("resistance {}, newstring {}, nowstring {}".format(resistance, newstring, nowstring))
        else:
            #if one of our two values still agrees with the lakeshore, 
            # defer switching modes until we're further out of range
            # basically adds hysteresis to the range change.
            return False
        """
        example behavior:
        R = 180 new_R = 198 olds = 11 news = 11 lakeshore = 11 -> do nothing
        R = 190 new_R = 209 olds = 11 news = 12 lakeshore = 11 -> do nothing
        R = 201 new_R = 221 olds = 12 news = 12 lakeshore = 11 -> update lakeshore
        R = 190 new_R = 209 olds = 11 news = 12 lakeshore = 12 -> do nothing
        R = 180 new_R = 198 olds = 11 news = 11 lakeshore = 12 -> update lakeshore
        """ 

    def getSetTemp(self):
        return self.a.temperature_controller.getTemperatureSetPoint()
    def setSetTemp(self,v):
        self.a.temperature_controller.setTemperatureSetPoint(v)
    def getTemp(self):
        return self.a.temperature_controller.getTemperature(channel=self.controlChannel)

    def getHeaterOut(self):
        return self.a.temperature_controller.getHeaterOut()

    def setHeaterOut(self,v):
        self.a.temperature_controller.setManualHeaterOut(v)

    def getTempError(self):
        setPoint = self.a.temperature_controller.getTemperatureSetPoint()
        currentTemp = self.getTemp()
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
        data = self.a.temperature_controller.ask("RDGRNG? {}".format(self.controlChannel))
        return data.split(b",")[2]
