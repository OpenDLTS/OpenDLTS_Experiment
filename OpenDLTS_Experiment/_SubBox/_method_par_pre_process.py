import numpy as np
from .._typing import Dict,Any
from .._config import LOGGER_ODEXP as LOGGER

__all__ = ['method_par_pre_process','get_par_fun_T_dict_from_decorator_kwargs']

def method_par_pre_process(method_par: dict, T: float, par_fun_T_dict: Dict[str, str] = {}) -> dict:
    new_method_par = method_par.copy()
    for par_name in par_fun_T_dict.keys():
        if par_name in method_par.keys():
            new_method_par[par_name] = eval(par_fun_T_dict[par_name])(T)
        else:
            LOGGER.warning(f'No such parameter name: {par_name}, pass method_par_pre_process')
    return new_method_par


def get_par_fun_T_dict_from_decorator_kwargs(decorator_kwargs: Dict[str, Any]) -> Dict[str, str]:
    if decorator_kwargs['If_Task_Param_Calc_T']:
        par_fun_T_dict = {}
        temp_par_dict = {}
        temp_fun_dict = {}
        for pn in decorator_kwargs.keys():
            if pn.startswith('Task_Param_Calc_T_Target_Par'):
                par_index = pn.replace('Task_Param_Calc_T_Target_Par','')
                temp_par_dict[par_index] = decorator_kwargs[pn]
            if pn.startswith('Task_Param_Calc_T_User_Fun'):
                par_index = pn.replace('Task_Param_Calc_T_User_Fun','')
                temp_fun_dict[par_index] = decorator_kwargs[pn]
        for pi,pn in temp_par_dict.items():
            if pi in temp_fun_dict.keys():
                if pn:
                    par_fun_T_dict[pn] = temp_fun_dict[pi]
        return par_fun_T_dict
    else:
        return {}
