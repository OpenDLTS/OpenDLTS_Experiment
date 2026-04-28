from .._config import LOGGER_ODEXP as LOGGER
from .._typing import *
from ._widget_create_fun import function_selector_multi
from ._dict_to_multiline_mixed import dict_to_multiline_mixed
from ._method_par_pre_process import method_par_pre_process,get_par_fun_T_dict_from_decorator_kwargs
import threading
import inspect
import numpy as np
import ipywidgets as widgets
import tomli_w
import time
from scipy.stats import shapiro
import random
from ._Measure_Tab import method_wrapper,method_donothing

__all__ = ['Task_Cap_Box']

def DLTS_format(x):
    formatted = f"{x:.7E}"
    if 'E-0' in formatted:
        formatted = formatted.replace('E-0', 'E-')
    elif 'E+0' in formatted:
        formatted = formatted.replace('E+0', 'E+')
    return formatted
DLTS_format = np.vectorize(DLTS_format)

# decorator function used to generate widgets
def Task_Wait(Before_Wait_Time: float = 0, After_Wait_Time: float = 3):
    pass
def Task_Temp_Stability(Allow_Temp_Delta: float = 0.1, Interval_Time: float = 5, Max_Attempt: int = 10):
    pass
def Task_RawFile_Save():
    pass
def Task_Value_Stability(Method : list = ['Shapiro_Wilk'], Interval_Time: float = 5, P_Value: float = 0.15,
                         Ignore_Ratio: float = 0.05, Max_Attempt: int = 5) -> None:
    pass
def Task_Param_Calc(
    Ref_Task_Num1: int = 1, Target_Par1: str = 'Vm1_gs', User_Fun1: str = "lambda i,v: float(np.interp(500e-6,i,v))",
    Ref_Task_Num2: int = 2, Target_Par2: str = '', User_Fun2: str = "",
):
    pass
def Task_Param_Calc_T(
        Target_Par1: str = 'Vm1_gs', User_Fun1: str = "lambda T: float(np.interp(T,[200,300],[0,1]))",
        Target_Par2: str = '', User_Fun2: str = ""
):
    pass

TASK_DECORATOE_REGISTRY:TaskDecoratoeRegistryType = {
    'Task_Wait': Task_Wait,
    'Task_Temp_Stability': Task_Temp_Stability,
    'Task_RawFile_Save': Task_RawFile_Save,
    'Task_Value_Stability': Task_Value_Stability,
    'Task_Param_Calc': Task_Param_Calc,
    'Task_Param_Calc_T': Task_Param_Calc_T
}

class task_decorator_function_selector_multi(function_selector_multi):
    @property
    def task_decorator_total_kwargs(self):
        temp_kwargs = {}
        for fn in self.fun_name_list:
            if fn in self.tagsinput.value:
                temp_kwargs['If_'+fn] = True
            else:
                temp_kwargs['If_'+fn] = False
            for param_name,param_widget in self.fun_params_widgets_dict[fn].items():
                temp_kwargs[fn+'_'+param_name] = param_widget.value
        return temp_kwargs
    @property
    def task_decorator_current_simple_list(self):
        temp_list = []
        for fn in self.fun_name_list:
            temp_dict = {}
            if fn in self.tagsinput.value:
                temp_dict['name'] = fn
                temp_dict['params'] = {}
                for param_name,param_widget in self.fun_params_widgets_dict[fn].items():
                    temp_dict['params'][param_name] = param_widget.value
            if temp_dict:
                temp_list.append(temp_dict)
        return temp_list

class Task_Cap_Box:
    def __init__(self, parent):
        self.parent = parent
        # ExperimentTaskListType
        self.task_list = []
        self._write_firstline = True
        self._stop_measure_event = threading.Event()
        self._create_ui()
        self._set_event()
        self._current_task_file_prefix = ''
        self._current_task_index = -1
        self._current_task_method_name = ''
        self._current_task_method_par = {}
        self._current_task_method:method_wrapper = method_wrapper(method_donothing,method_donothing,method_donothing)
        self._inner_current_task_text = None
    def _set_event(self):
        #self.task_from_text_btn.on_click(self._click_task_from_text_btn)
        self.task_from_tab_btn.on_click(self._click_task_from_tab_btn)
        #self.delete_last_task_btn.on_click(self._click_delete_last_task_btn)
        self.start_task_btn.on_click(self._click_start_task_btn)
        self.stop_task_btn.on_click(self._click_stop_task_btn)
        self.current_task_text.observe(self._obs_current_task_text, names='value')
    '''
    # update current task text value depend on task_list
    def _update_current_task_text_from_task_list(self):
        TaskString = ''
        for i,task in enumerate(self.task_list):
            TaskString += f'##Task{i+1}:\n'
            temp_task = {k:v for k,v in task.items() if k!='decorator_kwargs'}
            TaskString += dict_to_multiline_mixed(temp_task, max_depth=2)
            TaskString += '\n'
        self.current_task_text.value = TaskString
    '''
    def _update_inner_current_task_text(self):
        self._inner_current_task_text = self.current_task_text.value
    def _update_task_list_decorator_kwargs(self):
        for i,task in enumerate(self.task_list):
            temp_kwargs = {}
            for fn in self._task_decorator_selector_multi.fun_name_list:
                current_valid_decorator_dict = {temp_deco['name']:temp_deco['params'] for temp_deco in task['decorator_list']}
                if fn in current_valid_decorator_dict.keys():
                    temp_kwargs['If_'+fn] = True
                    import inspect
                    current_decorator_all_param_name_list = []
                    current_decorator_all_param_default_dict = {}
                    for name,param in inspect.signature(TASK_DECORATOE_REGISTRY[fn]).parameters.items():
                        current_decorator_all_param_name_list.append(name)
                        current_decorator_all_param_default_dict[name] = param.default[0] if param.annotation == list else param.default
                    for param_name in current_decorator_all_param_name_list:
                        if param_name in current_valid_decorator_dict[fn].keys():
                            temp_kwargs[fn+'_'+param_name] = current_valid_decorator_dict[fn][param_name]
                        else:
                            temp_kwargs[fn+'_'+param_name] = current_decorator_all_param_default_dict[param_name]
                else:
                    temp_kwargs['If_'+fn] = False
                    current_decorator_all_param_name_list = []
                    current_decorator_all_param_default_dict = {}
                    for name,param in inspect.signature(TASK_DECORATOE_REGISTRY[fn]).parameters.items():
                        current_decorator_all_param_name_list.append(name)
                        current_decorator_all_param_default_dict[name] = param.default[0] if param.annotation == list else param.default
                    for param_name in current_decorator_all_param_name_list:
                        temp_kwargs[fn+'_'+param_name] = current_decorator_all_param_default_dict[param_name]
            self.task_list[i]['decorator_kwargs'] = temp_kwargs
    ##########################################################
    # All changes to task_list should go through this function
    ##########################################################
    def _obs_current_task_text(self,change):
        self._set_current_task_list_status('Updating')
        from ._parse_task_string import parse_task_string
        if change['new'] == self._inner_current_task_text:
            self._set_current_task_list_status('Updated')
        else:
            temp_task_list = parse_task_string(change['new'])
            if temp_task_list is not None:
                self.task_list = temp_task_list
                self._update_task_list_decorator_kwargs()
                self._update_inner_current_task_text()
                self._set_current_task_list_status('Updated')
            else:
                self._set_current_task_list_status('Error')
    #def _click_task_from_text_btn(self,b):
    #    self.task_list.append(eval(self.task_from_text.value))
    #    self._update_task_list_decorator_kwargs()
    #    self._update_current_task_text()
    def _click_task_from_tab_btn(self,b):
        from ._parse_task_string import parse_task_string
        target_savefileprefix = f"{'Task'+str(len(self.task_list)+1)}"
        target_decorator_list = self._task_decorator_selector_multi.task_decorator_current_simple_list
        target_measure_method = {}
        _target_method_name, _target_method_par = self.parent.measure_tab._get_selected_param()
        target_measure_method['name'] = _target_method_name
        target_measure_method['params'] = _target_method_par
        temp_task = {}
        temp_task['savefileprefix'] = target_savefileprefix
        temp_task['decorator_list'] = target_decorator_list
        temp_task['measure_method'] = target_measure_method
        TaskSrting = ''
        TaskSrting += f'##Task{len(self.task_list)+1}:\n'
        temp_task_simple = {k:v for k,v in temp_task.items()}
        TaskSrting += dict_to_multiline_mixed(temp_task_simple, max_depth=2)
        TaskSrting += '\n'
        if self.current_task_text.value.strip().startswith('##The specified measurement tasks will be displayed here'):
            self.current_task_text.value = TaskSrting
        else:
            self.current_task_text.value = self.current_task_text.value + TaskSrting
        '''
        self.task_list.append(temp_task)
        self._update_task_list_decorator_kwargs()
        self._update_current_task_text()
        self._update_inner_current_task_text()
        '''

        
    '''
    def _click_delete_last_task_btn(self,b):
        if len(self.task_list)>0:
            self.task_list = self.task_list[:-1]
        self._update_current_task_text()
    '''
    def _click_start_task_btn(self,b):
        self.start_task_btn.disabled = True
        self.parent.measure_tab.disable()
        self.task_from_tab_btn.disabled = True
        self.current_task_text.disabled = True
        # 根据Task List创建一个存储某一温度循环的数据的list
        self._current_temp_task_data_list = [None]*len(self.task_list)
        # Save Experiment Config & Task Config
        try:
            task_config_file_path = self.parent.path_header / 'Task_Config.txt'
            if task_config_file_path.exists():
                new_task_config_file_path = task_config_file_path.parent / (task_config_file_path.stem + '.pre')
                if new_task_config_file_path.exists():
                    new_task_config_file_path.unlink()
                task_config_file_path.rename(new_task_config_file_path)
                LOGGER.info(f'Task Config File: Task_Config.txt Existed. Renamed To Task_Config.txt.pre')
            # save current task config
            task_config = self.current_task_text.value
            task_config_file_path.write_text(task_config)
            LOGGER.info(f'Task Config Saved To Task_Config.txt')

            exp_config_file_path = self.parent.path_header / 'Experiment_Config.toml'
            if exp_config_file_path.exists():
                new_exp_config_file_path = exp_config_file_path.parent / (exp_config_file_path.stem + '.pre')
                if new_exp_config_file_path.exists():
                    new_exp_config_file_path.unlink()
                exp_config_file_path.rename(new_exp_config_file_path)
                LOGGER.info(f'Experiment Config File: Experiment_Config.toml Existed. Renamed To Experiment_Config.toml.pre')
            # save current config
            exp_config = self.parent.get_config()
            with open(exp_config_file_path, 'wb') as f:
                tomli_w.dump(exp_config, f)
            LOGGER.info(f'Experiment Config Saved To Experiment_Config.toml')

        except Exception as e:
            LOGGER.warning(f'Save Experiment Config Error: {str(e)}', extra={'color': '#FF0000'})
        self._start_measure()
        self.stop_task_btn.disabled = False
    def _click_stop_task_btn(self,b):
        self.stop_task_btn.disabled = True
        self._stop_measure_event.set()
        if self._measure_thread is not None:
            self._measure_thread.join(timeout=1)
        self.start_task_btn.disabled = False
        self.parent.measure_tab.enable()
        self.task_from_tab_btn.disabled = False
        self.current_task_text.disabled = False
        LOGGER.warning('Task Stop', extra={'color': '#FF0000'})
    def _start_measure(self):
        self._measure_thread = threading.Thread(target=self._start_measure_thread_fun)
        self._measure_thread.start()
        #measure_thread.join()
    def _post_and_pre_set_thread_fun(self,T):
        # Post Set and Pre Set
        # First Temperature Don't Need Post Set
        if not self._write_firstline:
            method_name = self.task_list[-1]['measure_method']['name']
            method_par = self.task_list[-1]['measure_method']['params']
            # 预处理method_par
            decorator_kwargs = self.task_list[-1]['decorator_kwargs']
            method_par = method_par_pre_process(method_par=method_par, T=T, par_fun_T_dict=get_par_fun_T_dict_from_decorator_kwargs(decorator_kwargs))
            with self.parent.cap_meter_lock:
                self.parent.measure_tab.methods[method_name].method.post_set(**method_par)
        # Pre Set For First Task
        method_name = self.task_list[0]['measure_method']['name']
        method_par = self.task_list[0]['measure_method']['params']
        # 预处理method_par
        decorator_kwargs = self.task_list[0]['decorator_kwargs']
        method_par = method_par_pre_process(method_par=method_par, T=T, par_fun_T_dict=get_par_fun_T_dict_from_decorator_kwargs(decorator_kwargs))
        with self.parent.cap_meter_lock:
                self.parent.measure_tab.methods[method_name].method.pre_set(**method_par)
        self._method_pre_set_ok = True
    def _start_measure_thread_fun(self):
        # unset _stop_measure_event
        self._stop_measure_event.clear()
        # tasklist
        LOGGER.warning('Task Started', extra={'color': '#FF0000'})
        self._task_file_pre_process(ifremove=False)
        # First Line Set
        self._write_firstline = True
        # First Task Pre Set Not Ready
        self._method_pre_set_ok = False
        TempRange = self.parent.task_temp_box.T_stability_range.value
        # time to calc. rate
        TempRateRange = self.parent.task_temp_box.T_stability_rate_calc_time.value
        TsRate = self.parent.task_temp_box.T_stability_rate.value
        # get T_List from task_temp_box
        temp_range = self.parent.task_temp_box.get_current_T_List()
        for temp_index,temp_target in enumerate(temp_range):
            # New Temperature Loop, clear self._current_temp_task_data_list
            self._current_temp_task_data_list = [None]*len(self.task_list)
            if self._stop_measure_event.is_set():
                break
            # Realtime Update Parameters
            TempRange = self.parent.task_temp_box.T_stability_range.value
            TempRateRange = self.parent.task_temp_box.T_stability_rate_calc_time.value
            TsRate = self.parent.task_temp_box.T_stability_rate.value
            # Go To Target Temperature
            with self.parent.temp_controller_lock:
                P, I, D = self.parent.pid_box.pid_curve(self.parent.temp_controller.getTemp(),temp_target)
                self.parent.temp_controller.setTemp(temp_target, P, I, D)
            # Sub Thread of Pre Set and Post Set
            sub_thread = threading.Thread(
                target=self._post_and_pre_set_thread_fun,
                args=(temp_target,)
            )
            sub_thread.start()
            # Wait Until Temperature Stabled
            tempflag = True
            while True:
                if self._stop_measure_event.is_set():
                    break
                with self.parent.temp_controller_lock:
                    time_new = time.time()
                    temp_new = self.parent.temp_controller.getTemp()
                if tempflag:
                    tempflag = False
                else:
                    if abs(temp_new - temp_target) <= TempRange:
                        temp_rate = (temp_new - temp_old) / (time_new-time_old) * 60
                        if abs(temp_rate) < TsRate:
                            LOGGER.info(f'Current T: {round(temp_new,2)}K, Current T Rate: {round(temp_rate,2)} K/Min < {TsRate}')
                            break
                time_old = time_new
                temp_old = temp_new
                time.sleep(TempRateRange)
            # Temperature Stabled, Start Measure
            if not self._stop_measure_event.is_set():
                def measure_sub_thread_1():
                    for task_index,temptask in enumerate(self.task_list):
                        self._current_task_index = task_index
                        self._current_task_file_prefix = temptask['savefileprefix']
                        decorator_param = temptask['decorator_kwargs']
                        self._current_task_method_name = temptask['measure_method']['name']
                        method_par = temptask['measure_method']['params']
                        # 预处理_current_task_method_par
                        self._set_current_task_method_par(
                            input_method_par = method_par,
                            targetT = temp_target,
                            decorator_param = decorator_param
                        )
                        self._current_task_method = self.parent.measure_tab.methods[self._current_task_method_name].method
                        # First Task Has No Pre Set
                        if self._current_task_index == 0:
                            # wait pre set done
                            while True:
                                if self._method_pre_set_ok:
                                    self._method_pre_set_ok = False
                                    break
                                else:
                                    time.sleep(0.5)
                        else:
                            self._current_task_method.pre_set(**self._current_task_method_par)
                        # method.main decorate
                        self._task_decorator(**decorator_param)
                        # Last Task Has No Post Set
                        if self._current_task_index == len(self.task_list)-1:
                            pass
                        else:
                            self._current_task_method.post_set(**self._current_task_method_par)
                        if self._stop_measure_event.is_set():
                            break
                sub_thread1 = threading.Thread(target=measure_sub_thread_1)
                sub_thread1.start()
                sub_thread1.join()
            # Goto Next Temperature
            if self._write_firstline:
                self._write_firstline = False
        # Task Compeleted
        if self._stop_measure_event.is_set():
            LOGGER.warning('Task Stop', extra={'color': '#FF0000'})
        else:
            # Last Task Post Set
            method_name = self.task_list[-1]['measure_method']['name']
            method_par = self.task_list[-1]['measure_method']['params']
            # 预处理method_par
            decorator_kwargs = self.task_list[-1]['decorator_kwargs']
            method_par = method_par_pre_process(method_par=method_par, T=temp_target, par_fun_T_dict=get_par_fun_T_dict_from_decorator_kwargs(decorator_kwargs))
            with self.parent.cap_meter_lock:
                self.parent.measure_tab.methods[method_name].method.post_set(**method_par)
            LOGGER.warning('Task Compeleted, Set Target Temperature To T_idle', extra={'color': '#FF0000'})
            with self.parent.temp_controller_lock:
                self.parent.temp_controller.setTemp(self.parent.task_temp_box.T_idle.value, 50, 20, 50)
        self.stop_task_btn.disabled = True
        self._stop_measure_event.set()
        self.start_task_btn.disabled = False
        self.parent.measure_tab.enable()
        self.task_from_tab_btn.disabled = False
        self.current_task_text.disabled = False
    def _task_file_pre_process(self, ifremove=False):
        for task in self.task_list:
            task_fileprefix = task['savefileprefix']
            # Find all files starting with task_filename
            for task_filepath in self.parent.path_header.glob(f"{task_fileprefix}*"):
                if task_filepath.exists() and not task_filepath.name.endswith('.pre'):
                    if ifremove:
                        task_filepath.unlink()
                        LOGGER.warning(f'task file: {task_filepath.name} existed, removed', extra={'color': '#FF0000'})
                    else:
                        new_task_filename = task_filepath.name + '.pre'
                        new_task_filepath = task_filepath.parent/new_task_filename
                        task_filepath.rename(new_task_filepath)
                        LOGGER.warning(f'task file: {task_filepath.name} existed, the old file has been renamed: {new_task_filename}, note that file saving', extra={'color': '#FF0000'})
    def _set_current_task_method_par(self,input_method_par,targetT,decorator_param):
        # 根据decorator_param进行Task_Param_Calc_T预处理
        new_method_par = method_par_pre_process(method_par=input_method_par, T=targetT, par_fun_T_dict=get_par_fun_T_dict_from_decorator_kwargs(decorator_param))
        # 根据decorator_param进行Task_Param_Calc预处理
        if decorator_param['If_Task_Param_Calc']:
            #提取变量
            temp_ref_task_dict = {}
            temp_par_dict = {}
            temp_fun_dict = {}
            for pn in decorator_param.keys():
                if pn.startswith('Task_Param_Calc_Ref_Task_Num'):
                    par_index = pn.replace('Task_Param_Calc_Ref_Task_Num','')
                    temp_ref_task_dict[par_index] = decorator_param[pn]
                if pn.startswith('Task_Param_Calc_Target_Par'):
                    par_index = pn.replace('Task_Param_Calc_Target_Par','')
                    temp_par_dict[par_index] = decorator_param[pn]
                if pn.startswith('Task_Param_Calc_User_Fun'):
                    par_index = pn.replace('Task_Param_Calc_User_Fun','')
                    temp_fun_dict[par_index] = decorator_param[pn]
            for pi,_ in temp_ref_task_dict.items():
                ref_task_index = temp_ref_task_dict[pi]-1
                if ref_task_index < 0 or ref_task_index > len(self.task_list)-1:
                    LOGGER.info(f'Task_Param_Calc_Ref_Task_Num{pi} Wrong, skip')
                    continue
                target_par = temp_par_dict[pi]
                if type(target_par)==str:
                    if target_par not in list(input_method_par.keys()):
                        LOGGER.info(f'Task_Param_Calc_Target_Par{pi} Wrong, skip')
                        continue
                elif type(target_par)==list:
                    for tpi in target_par:
                        if tpi not in list(input_method_par.keys()):
                            LOGGER.info(f'Task_Param_Calc_Target_Par{pi} Wrong, skip')
                            continue
                else:
                    LOGGER.info(f'Task_Param_Calc_Target_Par{pi} Should be str or list, skip')
                    continue
                if temp_fun_dict[pi] == '':
                    LOGGER.info(f"Task_Param_Calc_User_Fun{pi} Should not be '', skip")
                    continue
                else:
                    udf = eval(temp_fun_dict[pi])
                LOGGER.info(f'Task_Param_Calc: Ref Task={ref_task_index+1}; Target Par={target_par}')

                try:
                    # 获取refdata的键
                    ref_data_name_list = [n for n,_ in inspect.signature(udf).parameters.items()]
                    # 获取refdata
                    if self._current_temp_task_data_list[ref_task_index] is not None:
                        ref_data_kwargs = {k:self._current_temp_task_data_list[ref_task_index]['raw_data'][k] for k in ref_data_name_list}
                    else:
                        LOGGER.info(f"No TASK{ref_task_index+1}'s data at {targetT}K. Skip")
                        continue
                    # 执行函数并赋值
                    if type(target_par)==str:
                        new_method_par[target_par] = udf(**ref_data_kwargs)
                    elif type(target_par)==list:
                        for tpi in target_par:
                            new_method_par[tpi] = udf(**ref_data_kwargs)
                except Exception as e:
                    LOGGER.info(f'_set_current_task_method_par Wrong: {str(e)}. Skip')
                    continue
            
            """
            ref_task_index = decorator_param['Task_Param_Calc_Ref_Task_Num'] - 1
            if ref_task_index < 0 or ref_task_index > len(self.task_list)-1:
                raise ValueError('Task_Param_Calc_Ref_Task_Num Wrong')
            target_par = decorator_param['Task_Param_Calc_Target_Par']
            if type(target_par)==str:
                if target_par not in list(input_method_par.keys()):
                    raise ValueError('Task_Param_Calc_Target_Par Wrong')
            elif type(target_par)==list:
                for tpi in target_par:
                    if tpi not in list(input_method_par.keys()):
                        raise ValueError('Task_Param_Calc_Target_Par Wrong')
            else:
                raise ValueError('Task_Param_Calc_Target_Par Should be str or list')
            udf = eval(decorator_param['Task_Param_Calc_User_Fun'])
            try:
                # 获取refdata的键
                ref_data_name_list = [n for n,_ in inspect.signature(udf).parameters.items()]
                # 获取refdata
                if self._current_temp_task_data_list[ref_task_index] is not None:
                    ref_data_kwargs = {k:self._current_temp_task_data_list[ref_task_index]['raw_data'][k] for k in ref_data_name_list}
                else:
                    LOGGER.info(f"No TASK{ref_task_index+1}'s data at {targetT}K")
                # 执行函数并赋值
                if type(target_par)==str:
                    new_method_par[target_par] = udf(**ref_data_kwargs)
                elif type(target_par)==list:
                    for tpi in target_par:
                        new_method_par[tpi] = udf(**ref_data_kwargs)
            except Exception as e:
                raise ValueError(f'_set_current_task_method_par Wrong: {str(e)}')
            """
        # 更新_current_task_method_par
        self._current_task_method_par = new_method_par
    # decorate method.main function
    def _task_decorator(
        self,
        If_Task_Wait: bool = False,
        Task_Wait_Before_Wait_Time: float = 0.0,
        Task_Wait_After_Wait_Time: float = 3.0,
        If_Task_Temp_Stability: bool = False,
        Task_Temp_Stability_Allow_Temp_Delta: float = 0.1,
        Task_Temp_Stability_Interval_Time: float = 5.0,
        Task_Temp_Stability_Max_Attempt: int = 10,
        If_Task_RawFile_Save: bool = False,
        If_Task_Value_Stability: bool = False,
        Task_Value_Stability_Method: str = 'Shapiro_Wilk',
        Task_Value_Stability_Interval_Time: float = 5.0,
        Task_Value_Stability_P_Value: float = 0.15,
        Task_Value_Stability_Ignore_Ratio: float = 0.05,
        Task_Value_Stability_Max_Attempt: int = 5,
        If_Task_Param_Calc: bool = False,
        Task_Param_Calc_Ref_Task_Num1: int = 1,
        Task_Param_Calc_Target_Par1: str = 'Vm1_gs',
        Task_Param_Calc_User_Fun1: str = 'lambda i,v: float(np.interp(500e-6,i,v))',
        Task_Param_Calc_Ref_Task_Num2: int = 2,
        Task_Param_Calc_Target_Par2: str = '',
        Task_Param_Calc_User_Fun2: str = '',
        If_Task_Param_Calc_T: bool = False,
        Task_Param_Calc_T_Target_Par1: str = 'Vm1_gs',
        Task_Param_Calc_T_User_Fun1: str = "lambda T: float(np.interp(T,[200,300],[0,1]))",
        Task_Param_Calc_T_Target_Par2: str = '',
        Task_Param_Calc_T_User_Fun2: str = ""
    ):
        if If_Task_Wait:
            time.sleep(Task_Wait_Before_Wait_Time)
        LOGGER.info(f"Task{self._current_task_index+1} Started, Method={self._current_task_method_name}, Par={self._current_task_method_par}")
        First_Flag = True
        VS_Flag = False
        VS_attempt_times = 0
        ATT_Flag = False
        ATT_attempt_times = 0
        while True:
            if self._stop_measure_event.is_set():
                break
            # Execuce main function of current method
            with self.parent.temp_controller_lock:
                start_temp = self.parent.temp_controller.getTemp()
            with self.parent.cap_meter_lock:
                data_new = self._current_task_method.main(**self._current_task_method_par)
            with self.parent.temp_controller_lock:
                end_temp = self.parent.temp_controller.getTemp()
            if If_Task_Temp_Stability:
                if abs(end_temp-start_temp)<=Task_Temp_Stability_Allow_Temp_Delta:
                    break
                else:
                    ATT_attempt_times += 1
                    LOGGER.info(f"Task_Temp_Delta={abs(end_temp-start_temp)} >{Task_Temp_Stability_Allow_Temp_Delta}, wait {Task_Temp_Stability_Interval_Time}s and retry")
                    time.sleep(Task_Temp_Stability_Interval_Time)
                if ATT_attempt_times > Task_Temp_Stability_Max_Attempt:
                    LOGGER.info(f"Task_Temp_Delta Attempted times >={Task_Temp_Stability_Max_Attempt}, skip this temperature point")
                    ATT_Flag = True
                    break
            else:
                break
        if If_Task_Value_Stability:
            while True:
                if self._stop_measure_event.is_set():
                    break
                if First_Flag:
                    First_Flag = False
                else:
                    if If_Task_Temp_Stability:
                        while not ATT_Flag:
                            # Execuce main function of current method
                            with self.parent.temp_controller_lock:
                                start_temp = self.parent.temp_controller.getTemp()
                            with self.parent.cap_meter_lock:
                                data_new = self._current_task_method.main(**self._current_task_method_par)
                            with self.parent.temp_controller_lock:
                                end_temp = self.parent.temp_controller.getTemp()
                            if abs(end_temp-start_temp)<=Task_Temp_Stability_Allow_Temp_Delta:
                                break
                            else:
                                ATT_attempt_times += 1
                                LOGGER.info(f"Task_Temp_Delta={abs(end_temp-start_temp)} >{Task_Temp_Stability_Allow_Temp_Delta}, wait {Task_Temp_Stability_Interval_Time}s and retry")
                                time.sleep(Task_Temp_Stability_Interval_Time)
                            if ATT_attempt_times > Task_Temp_Stability_Max_Attempt:
                                LOGGER.info(f"Task_Temp_Delta Attempted times >={Task_Temp_Stability_Max_Attempt}, skip this temperature point")
                                ATT_Flag = True
                                break
                        if ATT_Flag:
                            break
                    if Task_Value_Stability_Method == 'Shapiro_Wilk':
                        dy = data_old['raw_data']['y'] - data_new['raw_data']['y']
                        dy = np.array(dy)
                        starti = round(len(dy)*Task_Value_Stability_Ignore_Ratio)
                        dy = dy[starti:]
                        if len(dy) > 4000:
                            dy = random.sample(list(dy), 4000)
                        _, p_value = shapiro(dy)
                        if p_value > Task_Value_Stability_P_Value:
                            LOGGER.info(f"Shapiro-Wilk: p_value={round(p_value,2)}>{Task_Value_Stability_P_Value}")
                            VS_Flag = True
                        else:
                            LOGGER.info(f"Shapiro-Wilk: p_value={round(p_value,2)}<={Task_Value_Stability_P_Value}")
                    else:
                        VS_Flag = True
                data_old = data_new
                if not VS_Flag:
                    VS_attempt_times += 1
                    if VS_attempt_times >= Task_Value_Stability_Max_Attempt:
                        LOGGER.info(f"Attempted times >={Task_Value_Stability_Max_Attempt}, skip this temperature point")
                        break
                    LOGGER.info(f"Value unstable. Wait {Task_Value_Stability_Interval_Time}s for next test. Attempted times: {VS_attempt_times-1}")
                    time.sleep(Task_Value_Stability_Interval_Time)
                else:
                    LOGGER.info(f"Value stabled, writing data...")
                    # Save data to self._current_temp_task_data_list
                    self._current_temp_task_data_list[self._current_task_index] = data_new
                    # write data
                    dut_temp = (float(start_temp) + float(end_temp))/2
                    self._data_handler(dut_temp, data_new, if_raw_file_save=If_Task_RawFile_Save)
                    break
        else:
            if not ATT_Flag:
                # Save data to self._current_temp_task_data_list
                self._current_temp_task_data_list[self._current_task_index] = data_new
                # write data
                dut_temp = (float(start_temp) + float(end_temp))/2
                self._data_handler(dut_temp, data_new, if_raw_file_save=If_Task_RawFile_Save)
            else:
                # 失败了，不写入数据
                pass
        if If_Task_Wait:
            LOGGER.info(f"Task{self._current_task_index+1} compelete, wait {Task_Wait_After_Wait_Time}s")
            time.sleep(Task_Wait_After_Wait_Time)
        else:
            LOGGER.info(f"Task{self._current_task_index+1} compelete")
    def _data_handler(self, temperature: float, data: ElectricalDeviceMeasuredData, if_raw_file_save: bool = False) -> None:
        # current real Temperature
        T = temperature
        mname = self._current_task_method_name
        # Save data
        save_type = data.get('save_type', {})
        # DLTS_format
        for item in save_type.get('DLTS_format', []):
            filename = item['filename']
            fixed_x = item['fixed_x']
            changed_y = item['changed_y']
            new_filename = f"{self._current_task_file_prefix}_{filename}"
            filepath = self.parent.path_header / new_filename


            if self._write_firstline:
                with open(filepath, 'a') as f:
                    np.savetxt(f, DLTS_format(np.insert(fixed_x, 0, 0.0).reshape(1, -1)), fmt='%s', delimiter='\t')
                aligned_y = changed_y
            else:
                with open(filepath, 'r') as f_read:
                    first_line = f_read.readline()
                    x0 = np.array(first_line.strip().split('\t'))[1:].astype(float)
                if x0.shape == fixed_x.shape:
                    if (x0 == fixed_x).all():
                        aligned_y = changed_y
                    else:
                        aligned_y = np.interp(x0, fixed_x, changed_y)
                else:
                    aligned_y = np.interp(x0, fixed_x, changed_y)
                        
            with open(filepath, 'a') as f:
                np.savetxt(f, DLTS_format(np.insert(aligned_y, 0, T).reshape(1, -1)), fmt='%s', delimiter='\t')
            '''
            with open(filepath, 'a') as f:
                if self._write_firstline:
                    np.savetxt(f, DLTS_format(np.insert(fixed_x, 0, 0.0).reshape(1, -1)), fmt='%s', delimiter='\t')
                np.savetxt(f, DLTS_format(np.insert(changed_y, 0, T).reshape(1, -1)), fmt='%s', delimiter='\t')
            '''
        if if_raw_file_save:
            # Numpy_Dict_format
            # List[Dict[str, np.ndarray]]
            for item in save_type.get('Numpy_Dict_format', []):
                filename = item['filename']
                data_dict = item['data']
                fname_path = Path(filename)
                data_dict['T'] = T
                new_filename = f"{self._current_task_file_prefix}_{fname_path.stem}"+'.npy'
                filepath = self.parent.path_header / new_filename
                if filepath.exists():
                    data_dict_old = np.load(filepath, allow_pickle=True).tolist()
                    data_to_save = data_dict_old + [data_dict]
                else:
                    data_to_save = [data_dict]
                np.save(filepath, np.array(data_to_save), allow_pickle=True)

        # plot out1
        raw_data = data.get('raw_data', {})
        plot_type = data.get('plot_type', {})
        self.parent.measure_tab.methods[mname]._plot_data_push(x=raw_data.get('x'),y=raw_data.get('y'),y2=raw_data.get('y2'),label=f'T{round(temperature,1)}',plot_params=plot_type)
        self.parent.measure_tab._plot_out1_generate(method_name=mname,use_label_from_stack=True)
    def _set_current_task_list_status(self, status: str):
        if status in ['Updated', 'undated']:
            self.current_task_list_status.description = 'Updated'
            self.current_task_list_status.button_style = 'success'
            self.current_task_list_status.tooltip = 'Task List Updated'
            self.current_task_list_status.icon = 'check'
        elif status in ['Updating', 'updating']:
            self.current_task_list_status.description = 'Updating...'
            self.current_task_list_status.button_style = 'info'
            self.current_task_list_status.tooltip = 'Task List Updating'
            self.current_task_list_status.icon = 'refresh'
        elif status in ['Error', 'error']:
            self.current_task_list_status.description = 'Error'
            self.current_task_list_status.button_style = 'danger'
            self.current_task_list_status.tooltip = 'Task List Update Error, use previous valid Task List   '
            self.current_task_list_status.icon = 'skull-crossbones'

    def _create_ui(self):
        self.task_setting_label = widgets.Label('Task Decorator Setup:',style=dict(font_weight='bold',font_size='18px'))
        self._task_decorator_param_container = widgets.VBox()
        # widgets contain all Task Decorator's params
        self._task_decorator_selector_multi = task_decorator_function_selector_multi(
            fun_name_list=list(TASK_DECORATOE_REGISTRY.keys()),
            Function_Registry=TASK_DECORATOE_REGISTRY,
            tagsinput_label='Select Decorators for Current Task:',
            tab_label='Decorator Params Setup:',
            total_width='90%',
            widgets_per_row=3,
            tag_style='success'
        )
        '''
        self.task_from_text_btn = widgets.Button(
            description='Add Task From Text Below',
            disabled=False,
            button_style='info',
            tooltip='Add Task From Text Below',
            icon='plus',
            layout=widgets.Layout(width='30%')
        )
        '''
        self.task_from_tab_btn = widgets.Button(
            description='Add Task From Measure Tab And Task Decorator',
            disabled=False,
            button_style='success',
            tooltip='Add Task From Measure Tab And Task Decorator',
            icon='plus',
            layout=widgets.Layout(width='30%')
        )
        '''
        self.delete_last_task_btn = widgets.Button(
            description='Delete Last Task',
            disabled=False,
            button_style='danger',
            tooltip='Delete Last Task',
            icon='trash',
            layout=widgets.Layout(width='30%')
        )
        
        self.task_from_text = widgets.Textarea(
            value="",
            disabled=False,
            layout=widgets.Layout(width='90%')
        )
        '''
        # decorator
        self.current_task_text_label = widgets.Label('Current Measure Task List:',style=dict(font_weight='bold',font_size='18px'))
        self.current_task_list_status_label = widgets.Label('Task List Status:')
        self.current_task_list_status = widgets.Button(
            description='Updated',
            disabled=True,
            button_style='success',
            tooltip='Task List Updated',
            icon='check'
        )
        self.current_task_text = widgets.Textarea(
            value='##The specified measurement tasks will be displayed here',
            disabled=False,
            layout=widgets.Layout(width='90%',height='300px')
        )
        self.start_task_btn = widgets.Button(
            description='Start Task',
            disabled=False,
            button_style='success',
            tooltip='Start Measurement Task',
            icon='lightbulb',
            layout=widgets.Layout(width='20%')
        )
        self.stop_task_btn = widgets.Button(
            description='Stop Task',
            disabled=True,
            button_style='danger',
            tooltip='Stop Measurement Task',
            icon='trash',
            layout=widgets.Layout(width='20%')
        )
        self.box = widgets.VBox([
            self.task_setting_label,
            self._task_decorator_selector_multi.box,
            #widgets.HBox([self.task_from_text_btn, self.task_from_tab_btn, self.delete_last_task_btn]),
            widgets.HBox([self.task_from_tab_btn]),
            #self.task_from_text,
            widgets.HBox([self.current_task_text_label, self.start_task_btn, self.stop_task_btn]),
            widgets.HBox([self.current_task_list_status_label,self.current_task_list_status]),
            self.current_task_text
        ])
    def load_config(self, config):
        try:
            if 'task_list' in config:
                temp_task_list = config['task_list']
                TaskString = ''
                for i,task in enumerate(temp_task_list):
                    TaskString += f'##Task{i+1}:\n'
                    temp_task = {k:v for k,v in task.items() if k!='decorator_kwargs'}
                    TaskString += dict_to_multiline_mixed(temp_task, max_depth=2)
                    TaskString += '\n'
                self.current_task_text.value = TaskString
            if 'task_decorator' in config:
                temp_valid_fun_name_list = []
                for fn,widget_dict in self._task_decorator_selector_multi.fun_params_widgets_dict.items():
                    name = 'If_'+fn
                    if name in config['task_decorator']:
                        if bool(config['task_decorator'][name]):
                            temp_valid_fun_name_list.append(fn)
                    for param_name,param_widget in widget_dict.items():
                        name = fn+'_'+param_name
                        if name in config['task_decorator']:
                            if isinstance(param_widget, (widgets.BoundedFloatText, widgets.BoundedIntText)):
                                param_widget.value = config['task_decorator'][name]
                            elif isinstance(param_widget, widgets.Checkbox):
                                param_widget.value = bool(config['task_decorator'][name])
                            else:
                                param_widget.value = str(config['task_decorator'][name])
                self._task_decorator_selector_multi.tagsinput.value = temp_valid_fun_name_list
                self._task_decorator_selector_multi._update_tab()

        except Exception as e:
            LOGGER.warning(f'Task Cap. Box Load Config Error: {str(e)}', extra={'color': '#FF0000'})
    def get_task_decorator_config(self):
        #return {name: widget.value for name, widget in self._task_decorator_param_widgets.items()}
        return self._task_decorator_selector_multi.task_decorator_total_kwargs
    def get_config(self):
        return {
            'task_list': self.task_list,
            'task_decorator': self.get_task_decorator_config()
        }

