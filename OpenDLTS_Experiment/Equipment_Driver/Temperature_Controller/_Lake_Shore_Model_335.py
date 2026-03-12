from ..._config import LOGGER_ODEXP as LOGGER
import time
import logging

__all__ = ['Lake_Shore_Model_335']

# Lake Shore Model 335 Temperature Controller
class Lake_Shore_Model_335:
    def __init__(self, parent):
        from lakeshore import Model335, Model335InputSensorSettings
        self.parent = parent
        self._my_model_335 = Model335(57600)
        # throw away original log
        lakeshore_log = logging.getLogger('lakeshore')
        lakeshore_log.propagate = False
        time.sleep(5)
        try:
            self._my_model_335.get_all_kelvin_reading()
        except Exception as e:
            self._log('Lake_Shore_Model_335: '+str(e), '#FF0000', 'warning')
        self._heateroutput = 1
        # Set Heater OFF
        #if self._my_model_335.get_heater_range(self._heateroutput)._name_ != 'OFF':
        #    self._my_model_335.set_heater_range(self._heateroutput,self._my_model_335.HeaterRange.OFF)
        self._log('Lake Shore Model 335 Connected...')
    def _log(self,m,c='#778899',l='info'):
        if l == 'info':
            LOGGER.info(m, extra={'color': c})
        else:
            LOGGER.warning(m, extra={'color': '#FF0000'})
    def getTemp(self):
        #return self._my_model_335.get_all_kelvin_reading()[0]
        return self._my_model_335.get_kelvin_reading('A')
    def getTempCold(self):
        #return self._my_model_335.get_all_kelvin_reading()[1]
        return self._my_model_335.get_kelvin_reading('B')
    def getPower(self):
        return self._my_model_335.get_heater_output(self._heateroutput)
    def getRes(self):
        return self._my_model_335.get_sensor_reading('A')
    def getResCold(self):
        return self._my_model_335.get_sensor_reading('B')
    def getPID(self):
        p = self._my_model_335.get_heater_pid(self._heateroutput)['gain']
        i = self._my_model_335.get_heater_pid(self._heateroutput)['integral']
        d = self._my_model_335.get_heater_pid(self._heateroutput)['ramp_rate']
        return p,i,d
    def setTemp(self,TargetT,P,I,D):
        P = round(P,1)
        if P<0:
            self._log('P too small, use P=0 instead. Should be 0<=P<=1000', '#FF6D2D', 'warning')
            P = 0
        if P>1000:
            self._log('P too big, use P=1000 instead. Should be 0<=P<=1000', '#FF6D2D', 'warning')
            P = 1000
        I = round(I,1)
        if I<0:
            self._log('I too small, use I=0 instead. Should be 0<=I<=1000', '#FF6D2D', 'warning')
            I = 0
        if I>1000:
            self._log('I too big, use I=1000 instead. Should be 1<=I<=1000', '#FF6D2D', 'warning')
            I = 1000
        D = int(D)
        if D<0:
            self._log('D too small, use D=0 instead. Should be 0<=D<=200', '#FF6D2D', 'warning')
            D = 0
        if D>200:
            self._log('D too big, use D=200 instead. Should be 0<=D<=200', '#FF6D2D', 'warning')
            D = 200
        # set Manunal Power 0
        if self._my_model_335.get_manual_output(self._heateroutput) != 0:
            self._my_model_335.set_manual_output(self._heateroutput,0)
        TargetT = round(TargetT,2)
        if TargetT<0:
            self._log('Temperature Unit should be in K', '#FF6D2D', 'warning')
            TargetT = 273.15
        # set heat output PID
        self._my_model_335.set_heater_pid(self._heateroutput,P,I,D)
        # set target temperature
        self._my_model_335.set_control_setpoint(self._heateroutput,TargetT)
        # heater on
        if self._my_model_335.get_heater_range(self._heateroutput)._name_ != 'HIGH':
            self._my_model_335.set_heater_range(self._heateroutput,self._my_model_335.HeaterRange.HIGH)
        self._log(f'Target Temp.={round(TargetT,3)}, P={round(P,1)}, I={round(I,1)}, D={round(D,1)}')
    def setPower(self,TargetPower):
        # set heat output PID
        if self._my_model_335.get_heater_pid(self._heateroutput)['gain'] != 0:
            self._my_model_335.set_heater_pid(self._heateroutput,0,0,0)
        # TargetPower unit: [%]
        if TargetPower<0 or TargetPower>100:
            self._log('Heater power out of range. set 0 instead. Should be 0<=Power<=100', '#FF6D2D', 'warning')
            TargetPower=0
        self._my_model_335.set_manual_output(self._heateroutput,TargetPower)
        # heater on
        if self._my_model_335.get_heater_range(self._heateroutput)._name_ != 'HIGH':
            self._my_model_335.set_heater_range(self._heateroutput,self._my_model_335.HeaterRange.HIGH)
        self._log(f'Manually Set Heater Power={TargetPower}%')
    def setHeaterOFF(self):
        self._my_model_335.set_heater_range(self._heateroutput,self._my_model_335.HeaterRange.OFF)
        self._log('Heater Power Off')
    def close(self):
        # disconnect
        self._my_model_335.disconnect_usb()
        self._log('Lake Shore Model 335 Disconnected...')
    def is_alive(self):
        return True