import time
import numpy as np
from ..._config import LOGGER_ODEXP as LOGGER
from ..._typing import ElectricalDeviceMeasuredData

__all__ = ["Debug_CapMeter"]

class Debug_CapMeter:
    """
    Debug implementation of the Capacitance Meter.
    Migrated from CapMETER.Debug in the original notebook.
    """
    def __init__(self, *args, **kwargs):
        LOGGER.info("Initializing Debug_CapMeter")
        self._t0 = time.time()
        self._em0 = 1
        self._eminf = 10

    def close(self):
        LOGGER.info("Debug_CapMeter: Closed")
    
    def is_alive(self):
        return True

    def measure_CV(self, Vstart: float = -5, Vend: float = -0.5, Points: int = 100, freq: float = 100e3, DeltaV: float = 0.1) -> ElectricalDeviceMeasuredData:
        LOGGER.info("Start CV Measure")
        v = np.linspace(Vstart, Vend, Points)
        # Simulate C-V curve: C ~ V^2
        c = 1e-12 * 20 * (v - Vstart)**2 + np.random.normal(0, 1e-14, Points)
        r = np.ones(Points)
        time.sleep(0.5)
        LOGGER.info("End CV Measure")
        
        return {
            "raw_data": {"v": v, "c": c, "r": r, "x": v, "y": c, "y2": r},
            "save_type": {
                "Once_format": [{"filename": "CV_data.txt", "data": np.column_stack((v, c, r))}],
                "DLTS_format": [],
                "Numpy_Dict_format": []
            },
            "plot_type": {
                "xscale": "linear",
                "yscale": "linear",
                "x_scaling": 1.0,
                "y_scaling": 1e12,
                "y2_scaling": 1.0,
                "x_label": "Voltage (V)",
                "y_label": "Capacitance (pF)",
                "y2_label": "Resistance (Ohm)",
                "ignore_points": False
            }
        }

    def measure_Ad(self, Fstart: float = 50e3, Fend: float = 1e6, Points: int = 100, Vbias: float = -2, DeltaV: float = 0.1) -> ElectricalDeviceMeasuredData:
        LOGGER.info("Start Admittance Measure")
        f = np.logspace(np.log10(Fstart), np.log10(Fend), Points)
        c = 1e-12 * 20 * np.ones_like(f)
        r = np.ones(Points)
        time.sleep(0.5)
        LOGGER.info("End Admittance Measure")
        
        return {
            "raw_data": {"f": f, "c": c, "r": r, "x": f, "y": c, "y2": r},
            "save_type": {
                "Once_format": [{"filename": "Ad_data.txt", "data": np.column_stack((f, c, r))}],
                "DLTS_format": [],
                "Numpy_Dict_format": []
            },
            "plot_type": {
                "xscale": "log",
                "yscale": "linear",
                "x_scaling": 1.0,
                "y_scaling": 1e12,
                "y2_scaling": 1.0,
                "x_label": "Frequency (Hz)",
                "y_label": "Capacitance (pF)",
                "y2_label": "Resistance (Ohm)",
                "ignore_points": False
            }
        }

    def measure_IV(self, Vstart: float = -3, Vend: float = 3, Points: int = 40) -> ElectricalDeviceMeasuredData:
        LOGGER.info("Start IV Measure")
        v = np.linspace(Vstart, Vend, Points)
        i = 1e-6 * 10 * v 
        time.sleep(0.5)
        LOGGER.info("End IV Measure")
        
        return {
            "raw_data": {"v": v, "i": i, "x": v, "y": i, "y2": i+2},
            "save_type": {
                "Once_format": [{"filename": "IV_data.txt", "data": np.column_stack((v, i))}],
                "DLTS_format": [],
                "Numpy_Dict_format": []
            },
            "plot_type": {
                "xscale": "linear",
                "yscale": "linear",
                "x_scaling": 1.0,
                "y_scaling": 1e6,
                "y2_scaling": 1e6,
                "x_label": "Voltage (V)",
                "y_label": "Current (uA)",
                "y2_label": "Current (uA)",
                "ignore_points": False
            }
        }

    def measure_TC(self, Vm: float = -3, Tm: float = 2e-2, Vf: float = -0.5, Tf: float = 6e-2, freq: float = 100e3, DeltaV: float = 0.1, AverageTimes: int = 100, TimeConstant: float = 2.4e-6, DataRate: int = 107000, order: int = 8, maxbandwidth: float = 100, ifFillTrans: bool = False) -> ElectricalDeviceMeasuredData:
        """
        Transient Capacitance Measurement
        """
        LOGGER.info("Start Transient Capacitance Measure")
        t = 0.001 * np.arange(100)
        # Simulate transient decay
        em = self._eminf + (self._em0 - self._eminf) * np.exp(-0.05 * (time.time() - self._t0))
        c = 60 + (55 - 60) * np.exp(-em * t) + np.random.normal(0, 0.05, size=100)
        c = c * 1e-12
        r = np.ones(100)
        i = r - 1
        v = r - 2
        time.sleep(0.5)
        LOGGER.info("End Transient Capacitance Measure")
        
        return {
            "raw_data": {"t": t, "c": c, "r": r, "i": i, "v": v, "x": t, "y": c, "y2": i},
            "save_type": {
                "Once_format": [{"filename": "TC.txt", "data": np.column_stack((t, c, r, i, v))}],
                "DLTS_format": [{"filename": "TC.transdata", "fixed_x": t, "changed_y": c}],
                "Numpy_Dict_format": [{"filename": "TC.npy", "data": {"t": t, "c": c, "r": r, "i": i, "v": v}}]
            },
            "plot_type": {
                "xscale": "linear",
                "yscale": "linear",
                "x_scaling": 1.0,
                "y_scaling": 1e12,
                "y2_scaling": 1e6,
                "x_label": "Time (s)",
                "y_label": "Capacitance (pF)",
                "y2_label": "Current (uA)",
                "ignore_points": True
            }
        }
