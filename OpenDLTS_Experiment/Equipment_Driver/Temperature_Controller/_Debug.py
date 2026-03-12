import time
import numpy as np
from ..._config import LOGGER_ODEXP as LOGGER

__all__ = ["Debug_Temperature_Controller"]

class Debug_Temperature_Controller:
    """
    Debug implementation of the Temperature Controller.
    Migrated from Temperature_Controller.Debug in the original notebook.
    """
    def __init__(self, *args, **kwargs):
        LOGGER.info("Initializing Debug_Temperature_Controller")
        self._current_temperature = 300.0
        self._target_temperature = 300.0
        self._t0 = time.time()
        self._T0 = 300.0
        self._Tinf = 300.0

    def setTemp(self, TargetT: float, P: float = 0, I: float = 0, D: float = 0):
        LOGGER.info(f'Target Temp.={round(TargetT,3)}, P={round(P,1)}, I={round(I,1)}, D={round(D,1)}')
        self._T0 = self.getTemp()
        self._Tinf = TargetT
        self._t0 = time.time()

    def getTemp(self) -> float:
        # Exponential approach simulation
        return self._Tinf + (self._T0 - self._Tinf) * np.exp(-1.0 * (time.time() - self._t0))

    def getPower(self) -> float:
        return 15.0

    def getPID(self):
        return 1, 1, 4

    def getRes(self):
        return 114.0
    
    def getResCold(self):
        return 114.0

    def getTempCold(self):
        return 50.0

    def setHeaterOFF(self):
        LOGGER.info("Debug_Temperature_Controller: Heater OFF")

    def setPower(self, TargetPower):
        LOGGER.info(f"Debug_Temperature_Controller: Set Power {TargetPower}")

    def close(self):
        LOGGER.info("Debug_Temperature_Controller: Closed")

    def is_alive(self):
        return True
