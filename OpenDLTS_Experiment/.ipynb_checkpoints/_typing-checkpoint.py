from typing import TypedDict, List, Dict, NewType, Any, Callable
from pathlib import Path
import numpy as np



class _ElectricalDeviceMeasuredData_savetype_Once_format(TypedDict):
    filename: str | Path
    data: np.ndarray
class _ElectricalDeviceMeasuredData_savetype_DLTS_format(TypedDict):
    filename: str | Path
    fixed_x: np.ndarray             # e.g. time array for DLTS
    changed_y: np.ndarray           # e.g. capacitance array for DLTS
class _ElectricalDeviceMeasuredData_savetype_Numpy_Dict_format(TypedDict):
    filename: str | Path            # data will be saved in .npy file use np.save('', dict)
    data: Dict[str, np.ndarray | float | int]

class _ElectricalDeviceMeasuredData_savetype(TypedDict):
    Once_format: List[_ElectricalDeviceMeasuredData_savetype_Once_format]
    DLTS_format: List[_ElectricalDeviceMeasuredData_savetype_DLTS_format]
    Numpy_Dict_format: List[_ElectricalDeviceMeasuredData_savetype_Numpy_Dict_format]

class _ElectricalDeviceMeasuredData_plottype(TypedDict):
    xscale: str                     # 'linear' | 'log'
    yscale: str                     # 'linear' | 'log'
    x_scaling: float
    y_scaling: float
    y2_scaling: float
    x_label: str
    y_label: str
    y2_label: str
    ignore_points: bool

_ElectricalDeviceMeasuredData_rawdata = Dict[str, np.ndarray]
class ElectricalDeviceMeasuredData(TypedDict):
    raw_data: _ElectricalDeviceMeasuredData_rawdata
    save_type: _ElectricalDeviceMeasuredData_savetype
    plot_type: _ElectricalDeviceMeasuredData_plottype

TaskDecoratoeRegistryType = Dict[str, Callable]

class _FunDictType(TypedDict):
    name: str                       
    params: Dict[str, float | bool | int | str | Dict[str, Any]]

_TaskDecoratorType = _FunDictType       # Name of Decorator must be in TASK_DECORATOE_REGISTRY: TaskDecoratoeRegistryType

class ExperimentTaskType(TypedDict):
    savefileprefix: str
    decorator_list: List[_TaskDecoratorType]
    measure_method: _FunDictType
    decorator_kwargs: Dict[str, Any] 


ExperimentTaskListType = List[ExperimentTaskType]



__all__ = [
    "ElectricalDeviceMeasuredData",
    "ExperimentTaskType",
    "ExperimentTaskListType",
    "TaskDecoratoeRegistryType",
    "Path",
    "List",
    "Dict",
    "NewType",
    "Any",
    "Callable",
]