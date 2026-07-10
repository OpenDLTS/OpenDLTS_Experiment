import time
import numpy as np
from ..._config import LOGGER_ODEXP as LOGGER
from ..._typing import ElectricalDeviceMeasuredData
# 如果你的框架中需要用到重采样，可以取消下方注释
# from ._ReSampleFromTimeArray import ReSampleFromTimeArray

__all__ = ['B1505A']

class B1505A:
    def __init__(self, parent):
        self.parent = parent
        import pyvisa
        import io
        self.id = 'B1505A_EasyEXPERT'
        # Connect to EasyEXPERT via pyvisa
        self.rm = pyvisa.ResourceManager()
        self.instrument_address = 'TCPIP0::127.0.0.1::5025::SOCKET'
        self.GPIB_ADDRESS = 'GPIB0::18::INSTR'
        self._workspace_name = 'OpenDLTS'
        self._preset_group_name = 'OpenDLTS'
        # TC Method Needed
        self.CH_CMU = 4
        self.CH_HVSMU = 9
        
        try:
            self.b1505a = self.rm.open_resource(self.instrument_address)
            # 根据手册要求，所有命令和响应均以换行符终止
            self.b1505a.read_termination = '\n'
            self.b1505a.write_termination = '\n'
            # 测量可能耗时较长，增加超时时间 (单位: 毫秒)
            self.b1505a.timeout = 3600000
            
            # 清除错误队列
            self.b1505a.write('*CLS')
            idn = self.b1505a.query('*IDN?')
            self._log(f'{self.id} Connected... IDN: {idn}')
        except Exception as e:
            self._log(f'Failed to connect to {self.id}: {e}', l='warning')

    def _goto_workspace(self):
        # 检查并打开工作空间
        state = self.b1505a.query(':WORK:STAT?')
        if 'CLOS' in state:
            # 开启相应workspace
            self.b1505a.write(f':WORK:OPEN "{self._workspace_name}"')
            time.sleep(5)
            if self._wait_for_cmd_compelete():
                pass
        else:
            if self._workspace_name not in self.b1505a.query(':WORK:NAME?'):
                self.b1505a.write(f':WORK:CLOS')
                time.sleep(5)
                if self._wait_for_cmd_compelete():
                    pass
                # 开启相应workspace
                self.b1505a.write(f':WORK:OPEN "{self._workspace_name}"')
                time.sleep(5)
                if self._wait_for_cmd_compelete():
                    pass
    
    def _goto_preset_group(self):
        self.b1505a.write(f':PRES:OPEN "{self._preset_group_name}"')
        time.sleep(5)
        if self._wait_for_cmd_compelete():
            pass
    
    def _wait_for_cmd_compelete(self, timelimit=3600):
        status = None
        original_timeout = self.b1505a.timeout
        try:
            self.b1505a.timeout = timelimit * 1000
            status = self.b1505a.query('*OPC?')
        except Exception:
            pass
        finally:
            self.b1505a.timeout = original_timeout
        if status == '1':
            return True
        else:
            return False

    def parse_b1505a_text(self, raw_text, header_marker="Vf,If,Ta", row_delimiter="\\r\\n"):
        lines = raw_text.split(row_delimiter)
        
        headers = []
        data_list = []
        start_reading = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
    
            if line.startswith(header_marker):
                start_reading = True
                headers = line.split(',')
                continue
    
            if start_reading:
                try:
                    values = [float(x.strip()) if x.strip() != '' else np.nan for x in line.split(',')]
                    data_list.append(values)
                except ValueError as e:
                    break 
    
        data_matrix = np.array(data_list)
        return headers, data_matrix

    def _log(self, m, c='#778899', l='info'):
        if l == 'info':
            LOGGER.info(m, extra={'color': c})
        else:
            LOGGER.warning(m, extra={'color': '#FF0000'})
    
    def _set_progress(self, val, mn):
        self.parent.measure_tab.methods[mn].progress.value = val

    def _check_instrument_errors(self, command=""):
        """读取并记录系统错误队列中的所有错误"""
        while True:
            self.b1505a.write(':SYST:ERR?')
            error_string = self.b1505a.read()
            if error_string.startswith('+0') or error_string.startswith('0'):
                break
            else:
                self._log(f'B1505A ERROR after "{command}": {error_string.strip()}', l='warning')

    def close(self):
        self._log(f'{self.id} connection is closing.')
        self.b1505a.close()

    def is_alive(self):
        try:
            res = self.b1505a.query('*IDN?')
            return bool(res)
        except:
            return False


    
    # ----------------------------------------------------------------------
    # TC 测量方法
    # ----------------------------------------------------------------------

    def measure_TC_pre_set(self, **kwargs) -> None:
        self._set_progress(0, 'TC')


    def measure_TC_main(
        self, Vm: float = 30.0, Vf: float = 0.0, Tf: float = 1.0, Interval: float = 0.05, Points: int = 100, comp_current: float = 0.001,
        DeltaV: float = 0.1, Freq: int = 100e3
    ) -> ElectricalDeviceMeasuredData:
        """
        执行 TC 测量并解析数据
        """
        self._log('Start TC Measure')
        if (comp_current<1e-6) or (comp_current>8e-3):
            self._log(f"comp_current range: from 1e-6 to 8e-3; Use 8e-3 at this measurement")
            comp_current = 8e-3

        # ================= GPIB暂时连接与测量 =================
        import pyvisa
        import re
        rm = pyvisa.ResourceManager()
        try:
            b1505 = rm.open_resource(self.GPIB_ADDRESS)
            b1505.timeout = 3600000

            b1505.write("FMT 1,1")  
            b1505.write("TSC 1")    
            b1505.write(f"CN {self.CH_CMU},{self.CH_HVSMU}") 
            
            # 测量模式设置
            b1505.write("ACT 0, 2") 
            b1505.write("IMP 100")  
            b1505.write(f"RC {self.CH_CMU}, 0") 
        
            # 信号设置
            b1505.write(f"FC {self.CH_CMU}, {Freq}")
            b1505.write(f"ACV {self.CH_CMU}, {DeltaV}")
            b1505.write(f"MDCV {self.CH_CMU}, 0, 0, 0") 
        
            # 初始电压
            b1505.write(f"DV {self.CH_HVSMU}, 0, {Vf}, {comp_current}")
            time.sleep(Tf)
            b1505.write(f"DV {self.CH_HVSMU}, 0, {Vm}, {comp_current}")
        
            # 采样参数与触发
            b1505.write(f"MTDCV 0, {Interval}, {Points}, 0")
            b1505.write(f"MM 26, {self.CH_CMU}")
            b1505.write("TSR") 
            
            b1505.write("XE")  
            
            b1505.query("*OPC?") 
            
            raw_data = b1505.read()
        
        except Exception as e:
            self._log(f"测量过程中发生错误: {e}")
            raw_data = ""
        
        finally:
            self._set_progress(1.0, 'TC')
            self._log('End TC Measure')
            try:
                b1505.write("DZ") # 归零所有通道
            except:
                pass
            b1505.close()
        
        # ================= 数据处理 =================
        if raw_data:
            c = []
            t = []
            # 使用正则提取，例如匹配 "NDC+1.23456E-12"
            # ([A-Z]{3}) 匹配3个字母前缀
            # ([+-]\d+\.\d+E[+-]\d+) 匹配科学计数法数值
            pattern = r'([A-Z]{3})([+-]\d+\.\d+E[+-]\d+)'
            matches = re.findall(pattern, raw_data)
            
            for prefix, val_str in matches:
                val = float(val_str)
                data_type = prefix[2] # 提取第3个字母 (C=电容, T=时间, G=电导)
                if data_type == 'C':
                    c.append(val)
                elif data_type == 'T':
                    t.append(val)
        
            # 转换为 NumPy 数组
            t = np.array(t)
            c = np.array(c)
        
            # 由于返回数据中可能包含其他冗余块，确保时间和电容数组对齐
            min_len = min(len(t), len(c))
            t = t[:min_len]
            c = c[:min_len]
        
            if min_len > 0:
                return {
                    "raw_data": {"t": t, "c": c, "x": t, "y": c, "y2": c},
                    "save_type": {
                        "Once_format": [
                            {"filename": "TC_data.txt", "data": np.column_stack((t, c))}
                        ],
                        "DLTS_format": [
                            {"filename": "TC.transdata", "fixed_x": t, "changed_y": c}
                        ],
                        "Numpy_Dict_format": [
                            {"filename": "TC.npy", "data": {"t": t, "c": c}}
                        ]
                    },
                    "plot_type": {
                        "xscale": "linear",
                        "yscale": "linear",
                        "x_scaling": 1.0,
                        "y_scaling": 1e12,
                        "y2_scaling": 1e12,
                        "xlabel": "Time (s)",
                        "ylabel": "Capacitance (pF)",
                        "y2label": "Capacitance (pF)",
                        "ignore_points": True
                    }
                }
        else:
            self._log("No valid data")



    def measure_TC_post_set(self, **kwargs) -> None:
        """
        测量后执行的清理步骤
        """
        self._log('TC: Post-measurement cleanup...')

        



    
    # ----------------------------------------------------------------------
    # IV 测量方法
    # ----------------------------------------------------------------------

    def measure_IV_pre_set(self, **kwargs) -> None:
        """
        测量前准备工作：确认当前workspace，打开Preset空间，并加载指定的 Test setup
        """
        self._set_progress(0, 'IV')
        self._goto_workspace()
        self._goto_preset_group()
        
        self._current_app_name = 'IV'
        
        # 选择预设的 Test
        self.b1505a.write(f':PRES:SET:SEL "{self._current_app_name}"')
        self._check_instrument_errors("Select Preset Test")

        
        Vstart = kwargs['Vstart']
        Vend = kwargs['Vend']
        Vstep = kwargs['Vstep']
        SMU = kwargs['SMU']
        
        self.b1505a.write(f':STR "Scale", "LINEAR"')
        self.b1505a.write(f':STR "Anode", "{SMU}"')
        self.b1505a.write(f':NUMB "VfStart", {Vstart}')
        self.b1505a.write(f':NUMB "VfStop", {Vend}')
        self.b1505a.write(f':NUMB "VfLinearStep", {Vstep}')
        self.b1505a.write(f':STR "Cathode", "GNDU:GND"')
        self.b1505a.write(f':NUMB "PulseWidth", 500e-6')
        self.b1505a.write(f':STR "PulsePeriodMode", "AUTO"')
        self.b1505a.write(f':NUMB "ManualPulsePeriod", 50e-3')
        self._check_instrument_errors("Set Parameters")
        time.sleep(0.5)

    def measure_IV_main(
        self, Vstart: float = -3.0, Vend: float = 3.0, Vstep: float = 0.01, SMU: str = 'SMU5:MC'
    ) -> ElectricalDeviceMeasuredData:
        """
        执行 IV 测量并解析数据
        """
        self._log('Start IV Measure')

        while True:
            # 启动单次测量[cite: 1]
            self.b1505a.write(':BENC:SEL:RUN')
            time.sleep(2)
            # 等待测量完成。使用 *OPC? 阻塞直到所有待处理操作完成[cite: 1]
            if self._wait_for_cmd_compelete():
                break
            else:
                self._log(f'OPC timeout, restart measurement', l='warning')
                self.b1505a.write(':BENC:SEL:ABOR')
                time.sleep(10)
                continue

        # 设置数据获取格式：返回 TEXT 格式，且换行符编码设为 ON (\r\n)[cite: 1]
        self.b1505a.write(':RES:FORM TEXT')
        self.b1505a.write(':RES:FORM:ESC ON')
        
        # 请求最新测量结果[cite: 1]
        self.b1505a.write(':RES:FET?')
        
        # 读取原始字节流以解析 IEEE 明确长度的块数据 (Definite Length Arbitrary Block Data)[cite: 3]
        raw_data = self.b1505a.read_raw()
        
        header_str = raw_data[0:2].decode('ascii')
        if header_str.startswith('#'):
            num_digits = int(header_str[1])
            data_length = int(raw_data[2:2+num_digits].decode('ascii'))
            data_str = raw_data[2+num_digits : 2+num_digits+data_length].decode('ascii')
        else:
            # 如果格式异常，回退处理
            data_str = raw_data.decode('ascii')

        self._set_progress(1.0, 'IV')
        self._log('End IV Measure')

        # ---------------------------------------------------------
        # 解析返回的 EasyEXPERT 数据
        # EasyEXPERT TEXT 格式通常包含多行 MetaData (Headers) 以及纯数据列。
        # 以下是通用的 Numpy 解析方法。你需要根据你实际输出的 CSV 结构微调。
        # 假设返回数据中包含 Time, Vds, Ids 并且能计算 Ron。
        # ---------------------------------------------------------
        try:
            # 跳过非数值头部行，直接读取矩阵 (如有表头视情况调整 skip_header 参数)
            _, parsed_array = self.parse_b1505a_text(data_str, header_marker="Vf,If,Ta", row_delimiter="\\r\\n")
            v = parsed_array[:, 0]
            i = parsed_array[:, 1]
        except Exception as e:
            self._log(f'Data parsing error: {e}. Generating dummy data for fallback.', l='warning')

        return {
            "raw_data": {"v": v, "i": i, "x": v, "y": i, "y2": i},
            "save_type": {
                "Once_format": [
                    {"filename": "IV_data.txt", "data": np.column_stack((v, i))}
                ],
                "DLTS_format": [
                    {"filename": "IV.transdata", "fixed_x": v, "changed_y": i}
                ],
                "Numpy_Dict_format": [
                    {"filename": "IV.npy", "data": {"v": v, "i": i}}
                ]
            },
            "plot_type": {
                "xscale": "linear",
                "yscale": "linear",
                "x_scaling": 1.0,
                "y_scaling": 1.0,
                "y2_scaling": 1.0,
                "xlabel": "Voltage (V)",
                "ylabel": "Current (A)",
                "y2label": "Current (A)",
                "ignore_points": False
            }
        }

    def measure_IV_post_set(self, **kwargs) -> None:
        """
        测量后执行的清理步骤
        """
        self._log('IV: Post-measurement cleanup...')
        # 如果需要关闭工作空间，可以取消注释下面代码
        # self.b1505a.write(':WORK:CLOS')
        # self.b1505a.query('*OPC?')[cite: 1]


    # ----------------------------------------------------------------------
    # DRon_I 测量方法
    # ----------------------------------------------------------------------

    def measure_DRon_I_pre_set(self, **kwargs) -> None:
        """
        测量前准备工作：确认当前workspace，打开Preset空间，并加载指定的 Test setup
        """
        self._set_progress(0, 'DRon_I')
        self._goto_workspace()
        self._goto_preset_group()
        
        self._current_app_name = 'DRon_I'
        
        # 选择预设的 Test
        self.b1505a.write(f':PRES:SET:SEL "{self._current_app_name}"')
        self._check_instrument_errors("Select Preset Test")

        
        Gate = kwargs['Gate']
        VgOff = kwargs['VgOff']
        VgOn = kwargs['VgOn']
        SwitchControl = kwargs['SwitchControl']
        HCSMU = kwargs['HCSMU']
        HVSMU = kwargs['HVSMU']
        GNDU = kwargs['GNDU']
        Substrate = kwargs['Substrate']
        OffStressTime = kwargs['OffStressTime']
        VdOff = kwargs['VdOff']
        IdOn = kwargs['IdOn']
        VdOnLimit = kwargs['VdOnLimit']
        NumberOfSamples = kwargs['NumberOfSamples']
        SamplingInterval = kwargs['SamplingInterval']

        
        self.b1505a.write(f':STR "Gate", "{Gate}"')
        self.b1505a.write(f':NUMB "VgOff", {VgOff}')
        self.b1505a.write(f':NUMB "VgOn", {VgOn}')
        
        self.b1505a.write(f':STR "SwitchControl", "{SwitchControl}"')
        self.b1505a.write(f':STR "HCSMU", "{HCSMU}"')
        self.b1505a.write(f':STR "HVSMU", "{HVSMU}"')
        self.b1505a.write(f':STR "GNDU", "{GNDU}"')
        
        self.b1505a.write(f':STR "Substrate", "{Substrate}"')
        self.b1505a.write(f':NUMB "OffStressTime", {OffStressTime}')

        self.b1505a.write(f':NUMB "VdOff", {VdOff}')
        self.b1505a.write(f':NUMB "IdOn", {IdOn}')
        self.b1505a.write(f':NUMB "VdOnLimit", {VdOnLimit}')
        self.b1505a.write(f':NUMB "NumberOfSamples", {NumberOfSamples}')
        self.b1505a.write(f':NUMB "SamplingInterval", {SamplingInterval}')

        self._check_instrument_errors("Set Parameters")
        time.sleep(0.5)
        

    def measure_DRon_I_main(
        self, Gate: str = 'SMU4:MC', VgOff: float = -1.0, VgOn: float = 5.0, SwitchControl: str = 'SMU5:MC',
        HCSMU: str = 'SMU3:HC', HVSMU: str = 'SMU6:HV', GNDU: str = 'GNDU:GND', Substrate: str = 'GNDU:GND',
        OffStressTime: float = 1, VdOff: float = 10, IdOn: float = 0.1, VdOnLimit: float = 5.0,
        NumberOfSamples: int = 201, SamplingInterval: float = 200e-6
    ) -> ElectricalDeviceMeasuredData:
        """
        执行 DRon_I 测量并解析数据
        """
        self._log('Start DRon_I Measure')

        while True:
            # 启动单次测量[cite: 1]
            self.b1505a.write(':BENC:SEL:RUN')
            time.sleep(2)
            # 等待测量完成。使用 *OPC? 阻塞直到所有待处理操作完成[cite: 1]
            if self._wait_for_cmd_compelete():
                break
            else:
                self._log(f'OPC timeout, restart measurement', l='warning')
                self.b1505a.write(':BENC:SEL:ABOR')
                time.sleep(10)
                continue

        # 设置数据获取格式：返回 TEXT 格式，且换行符编码设为 ON (\r\n)[cite: 1]
        self.b1505a.write(':RES:FORM TEXT')
        self.b1505a.write(':RES:FORM:ESC ON')
        
        # 请求最新测量结果[cite: 1]
        self.b1505a.write(':RES:FET?')
        
        # 读取原始字节流以解析 IEEE 明确长度的块数据 (Definite Length Arbitrary Block Data)[cite: 3]
        raw_data = self.b1505a.read_raw()
        
        header_str = raw_data[0:2].decode('ascii')
        if header_str.startswith('#'):
            num_digits = int(header_str[1])
            data_length = int(raw_data[2:2+num_digits].decode('ascii'))
            data_str = raw_data[2+num_digits : 2+num_digits+data_length].decode('ascii')
        else:
            # 如果格式异常，回退处理
            data_str = raw_data.decode('ascii')

        self._set_progress(1.0, 'DRon_I')
        self._log('End DRon_I Measure')

        # ---------------------------------------------------------
        # 解析返回的 EasyEXPERT 数据
        # EasyEXPERT TEXT 格式通常包含多行 MetaData (Headers) 以及纯数据列。
        # 以下是通用的 Numpy 解析方法。你需要根据你实际输出的 CSV 结构微调。
        # 假设返回数据中包含 Time, Vds, Ids 并且能计算 Ron。
        # ---------------------------------------------------------
        try:
            # 跳过非数值头部行，直接读取矩阵 (如有表头视情况调整 skip_header 参数)
            _, parsed_array = self.parse_b1505a_text(data_str, header_marker="Time,Rds,Vds,Id,Vgs,Ig,V_HCSMU,I_HCSMU,V_HVSMU,I_HVSMU,V_SwitchControl,I_SwitchControl,Ta", row_delimiter="\\r\\n")
            t = parsed_array[:, 0]
            i = parsed_array[:, 3]
            r = parsed_array[:, 1]
            v = parsed_array[:, 2]
            data_mask = t>=0
            t = t[data_mask]
            i = i[data_mask]
            r = r[data_mask]
            v = v[data_mask]
        except Exception as e:
            self._log(f'Data parsing error: {e}. Generating dummy data for fallback.', l='warning')

        return {
            "raw_data": {"t": t, "i": i, "r": r, "v": v, "x": t, "y": r, "y2": v},
            "save_type": {
                "Once_format": [
                    {"filename": "DRon_I_data.txt", "data": np.column_stack((t, r, v, i))}
                ],
                "DLTS_format": [
                    {"filename": "DRon_I_tr.transdata", "fixed_x": t, "changed_y": r},
                    {"filename": "DRon_I_tv.transdata", "fixed_x": t, "changed_y": v}
                ],
                "Numpy_Dict_format": [
                    {"filename": "DRon_I.npy", "data": {"t": t, "i": i, "r": r, "v": v}}
                ]
            },
            "plot_type": {
                "xscale": "linear",
                "yscale": "linear",
                "x_scaling": 1.0,
                "y_scaling": 1e3,
                "y2_scaling": 1.0,
                "xlabel": "Time (s)",
                "ylabel": "Resistance (mOhm)",
                "y2label": "Voltage (V)",
                "ignore_points": True
            }
        }

    def measure_DRon_I_post_set(self, **kwargs) -> None:
        """
        测量后执行的清理步骤
        """
        #self._log('DRon_I: Post-measurement cleanup...')
        # 如果需要关闭工作空间，可以取消注释下面代码
        # self.b1505a.write(':WORK:CLOS')
        # self.b1505a.query('*OPC?')[cite: 1]


    # ----------------------------------------------------------------------
    # SIdVd 测量方法
    # ----------------------------------------------------------------------

    def measure_SIdVd_pre_set(self, **kwargs) -> None:
        """
        测量前准备工作：确认当前workspace，打开Preset空间，并加载指定的 Test setup
        """
        self._set_progress(0, 'SIdVd')
        self._goto_workspace()
        self._goto_preset_group()
        
        self._current_app_name = 'SIdVd'
        
        # 选择预设的 Test
        self.b1505a.write(f':PRES:SET:SEL "{self._current_app_name}"')
        self._check_instrument_errors("Select Preset Test")

        
        Gate = kwargs['Gate']
        VgOff = kwargs['VgOff']
        VgOn = kwargs['VgOn']
        SwitchControl = kwargs['SwitchControl']
        HCSMU = kwargs['HCSMU']
        HVSMU = kwargs['HVSMU']
        GNDU = kwargs['GNDU']
        Substrate = kwargs['Substrate']
        OffStressTime = kwargs['OffStressTime']
        VdOff = kwargs['VdOff']
        IdOnLimit = kwargs['IdOnLimit']
        VdStart = kwargs['VdStart']
        VdStop = kwargs['VdStop']
        StepTime = kwargs['StepTime']
        NOS = kwargs['NOS']

        
        self.b1505a.write(f':STR "Gate", "{Gate}"')
        self.b1505a.write(f':NUMB "VgOff", {VgOff}')
        self.b1505a.write(f':NUMB "VgOn", {VgOn}')
        
        self.b1505a.write(f':STR "SwitchControl", "{SwitchControl}"')
        self.b1505a.write(f':STR "HCSMU", "{HCSMU}"')
        self.b1505a.write(f':STR "HVSMU", "{HVSMU}"')
        self.b1505a.write(f':STR "GNDU", "{GNDU}"')
        
        self.b1505a.write(f':STR "Substrate", "{Substrate}"')
        self.b1505a.write(f':NUMB "OffStressTime", {OffStressTime}')

        self.b1505a.write(f':NUMB "VdOff", {VdOff}')
        self.b1505a.write(f':NUMB "IdOnLimit", {IdOnLimit}')
        self.b1505a.write(f':NUMB "VdStart", {VdStart}')
        self.b1505a.write(f':NUMB "VdStop", {VdStop}')
        self.b1505a.write(f':NUMB "StepTime", {StepTime}')
        self.b1505a.write(f':NUMB "NOS", {NOS}')

        self._check_instrument_errors("Set Parameters")
        time.sleep(0.5)
        

    def measure_SIdVd_main(
        self, Gate: str = 'SMU4:MC', VgOff: float = -1.4, VgOn: float = 5.0, SwitchControl: str = 'SMU5:MC',
        HCSMU: str = 'SMU3:HC', HVSMU: str = 'SMU6:HV', GNDU: str = 'GNDU:GND', Substrate: str = 'GNDU:GND',
        OffStressTime: float = 1, VdOff: float = 10, IdOnLimit: float = 0.1, VdStart: float = 0.0,
        VdStop: float = 1.0, StepTime: float = 2e-3, NOS: int = 51
    ) -> ElectricalDeviceMeasuredData:
        """
        执行 SIdVd 测量并解析数据
        """
        self._log('Start SIdVd Measure')

        while True:
            # 启动单次测量[cite: 1]
            self.b1505a.write(':BENC:SEL:RUN')
            time.sleep(2)
            # 等待测量完成。使用 *OPC? 阻塞直到所有待处理操作完成[cite: 1]
            if self._wait_for_cmd_compelete():
                break
            else:
                self._log(f'OPC timeout, restart measurement', l='warning')
                self.b1505a.write(':BENC:SEL:ABOR')
                time.sleep(10)
                continue

        # 设置数据获取格式：返回 TEXT 格式，且换行符编码设为 ON (\r\n)[cite: 1]
        self.b1505a.write(':RES:FORM TEXT')
        self.b1505a.write(':RES:FORM:ESC ON')
        
        # 请求最新测量结果[cite: 1]
        self.b1505a.write(':RES:FET?')
        
        # 读取原始字节流以解析 IEEE 明确长度的块数据 (Definite Length Arbitrary Block Data)[cite: 3]
        raw_data = self.b1505a.read_raw()
        
        header_str = raw_data[0:2].decode('ascii')
        if header_str.startswith('#'):
            num_digits = int(header_str[1])
            data_length = int(raw_data[2:2+num_digits].decode('ascii'))
            data_str = raw_data[2+num_digits : 2+num_digits+data_length].decode('ascii')
        else:
            # 如果格式异常，回退处理
            data_str = raw_data.decode('ascii')

        self._set_progress(1.0, 'SIdVd')
        self._log('End SIdVd Measure')

        # ---------------------------------------------------------
        # 解析返回的 EasyEXPERT 数据
        # EasyEXPERT TEXT 格式通常包含多行 MetaData (Headers) 以及纯数据列。
        # 以下是通用的 Numpy 解析方法。你需要根据你实际输出的 CSV 结构微调。
        # 假设返回数据中包含 Time, Vds, Ids 并且能计算 Ron。
        # ---------------------------------------------------------
        try:
            # 跳过非数值头部行，直接读取矩阵 (如有表头视情况调整 skip_header 参数)
            _, parsed_array = self.parse_b1505a_text(
                data_str,
                header_marker="Vds,Id,Vgs,Ig,V_HCSMU,I_HCSMU,V_HVSMU,I_HVSMU,V_SwitchControl,I_SwitchControl,Ta,Time@OffState,Vds@OffState,Id@OffState",
                row_delimiter="\\r\\n"
            )
            v = parsed_array[:, 0]
            i = parsed_array[:, 1]
            data_mask = (v>=VdStart)&(v<=VdStop)&(~np.isnan(v))&(~np.isnan(i))
            v = v[data_mask]
            i = i[data_mask]

        except Exception as e:
            self._log(f'Data parsing error: {e}. Generating dummy data for fallback.', l='warning')

        return {
            "raw_data": {"v": v, "i": i, "x": v, "y": i, "y2": i},
            "save_type": {
                "Once_format": [
                    {"filename": "SIdVd_data.txt", "data": np.column_stack((v, i))}
                ],
                "DLTS_format": [
                    {"filename": "SIdVd.transdata", "fixed_x": v, "changed_y": i},
                ],
                "Numpy_Dict_format": [
                    {"filename": "SIdVd.npy", "data": {"v": v, "i": i}}
                ]
            },
            "plot_type": {
                "xscale": "linear",
                "yscale": "linear",
                "x_scaling": 1.0,
                "y_scaling": 1e3,
                "y2_scaling": 1e3,
                "xlabel": "Voltage (V)",
                "ylabel": "Current (mA)",
                "y2label": "Current (mA)",
                "ignore_points": False
            }
        }

    def measure_SIdVd_post_set(self, **kwargs) -> None:
        """
        测量后执行的清理步骤
        """
        #self._log('DRon_I: Post-measurement cleanup...')
        # 如果需要关闭工作空间，可以取消注释下面代码
        # self.b1505a.write(':WORK:CLOS')
        # self.b1505a.query('*OPC?')[cite: 1]


    
    # ----------------------------------------------------------------------
    # IdVds 测量方法
    # ----------------------------------------------------------------------
    
    def measure_IdVds_pre_set(self, **kwargs) -> None:
        """
        测量前准备工作：确认当前workspace，打开Preset空间，并加载指定的 Test setup
        """
        self._set_progress(0, 'IdVds')
        self._goto_workspace()
        self._goto_preset_group()
        
        self._current_app_name = 'Id-Vds'
        
        # 选择预设的 Test
        self.b1505a.write(f':PRES:SET:SEL "{self._current_app_name}"')
        self._check_instrument_errors("Select Preset Test")

        
        Gate = kwargs['Gate']
        VgStart = kwargs['VgStart']
        VgStop = kwargs['VgStop']
        VgStep = kwargs['VgStep']
        
        Source = kwargs['Source']

        Drain = kwargs['Drain']
        VdStart = kwargs['VdStart']
        VdStop = kwargs['VdStop']
        VdLinearStep = kwargs['VdLinearStep']
        IdLimit = kwargs['IdLimit']
        PdLimit = kwargs['PdLimit']

        
        
        self.b1505a.write(f':STR "Gate", "{Gate}"')
        self.b1505a.write(f':NUMB "VgStart", {VgStart}')
        self.b1505a.write(f':NUMB "VgStop", {VgStop}')
        self.b1505a.write(f':NUMB "VgStep", {VgStep}')
        
        self.b1505a.write(f':STR "Source", "{Source}"')
        
        self.b1505a.write(f':STR "Drain", "{Drain}"')
        self.b1505a.write(f':NUMB "VdStart", {VdStart}')
        self.b1505a.write(f':NUMB "VdStop", {VdStop}')
        self.b1505a.write(f':NUMB "VdLinearStep", {VdLinearStep}')
        self.b1505a.write(f':NUMB "IdLimit", {IdLimit}')
        self.b1505a.write(f':NUMB "PdLimit", {PdLimit}')


        self._check_instrument_errors("Set Parameters")
        time.sleep(0.5)
        

    def measure_IdVds_main(
        self, Gate: str = 'SMU1:HP', VgStart: float = 0.0, VgStop: float = 6.0, VgStep: float = 1.0, Source: str = 'GNDU:GND',
        Drain: str = 'SMU3:HC', VdStart: float = 0.0, VdStop: float = 4.0, VdLinearStep: float = 0.1, IdLimit: float = 20, PdLimit: float = 40.0
    ) -> ElectricalDeviceMeasuredData:
        """
        执行 IdVds 测量并解析数据
        """
        self._log('Start IdVds Measure')

        while True:
            # 启动单次测量[cite: 1]
            self.b1505a.write(':BENC:SEL:RUN')
            time.sleep(2)
            # 等待测量完成。使用 *OPC? 阻塞直到所有待处理操作完成[cite: 1]
            if self._wait_for_cmd_compelete():
                break
            else:
                self._log(f'OPC timeout, restart measurement', l='warning')
                self.b1505a.write(':BENC:SEL:ABOR')
                time.sleep(10)
                continue

        # 设置数据获取格式：返回 TEXT 格式，且换行符编码设为 ON (\r\n)[cite: 1]
        self.b1505a.write(':RES:FORM TEXT')
        self.b1505a.write(':RES:FORM:ESC ON')
        
        # 请求最新测量结果[cite: 1]
        self.b1505a.write(':RES:FET?')
        
        # 读取原始字节流以解析 IEEE 明确长度的块数据 (Definite Length Arbitrary Block Data)[cite: 3]
        raw_data = self.b1505a.read_raw()
        
        header_str = raw_data[0:2].decode('ascii')
        if header_str.startswith('#'):
            num_digits = int(header_str[1])
            data_length = int(raw_data[2:2+num_digits].decode('ascii'))
            data_str = raw_data[2+num_digits : 2+num_digits+data_length].decode('ascii')
        else:
            # 如果格式异常，回退处理
            data_str = raw_data.decode('ascii')

        self._set_progress(1.0, 'IdVds')
        self._log('End IdVds Measure')

        # ---------------------------------------------------------
        # 解析返回的 EasyEXPERT 数据
        # EasyEXPERT TEXT 格式通常包含多行 MetaData (Headers) 以及纯数据列。
        # 以下是通用的 Numpy 解析方法。你需要根据你实际输出的 CSV 结构微调。
        # 假设返回数据中包含 Time, Vds, Ids 并且能计算 Ron。
        # ---------------------------------------------------------
        try:
            # 跳过非数值头部行，直接读取矩阵 (如有表头视情况调整 skip_header 参数)
            _, parsed_array = self.parse_b1505a_text(data_str, header_marker="Vdrain,Idrain,Vgate,Igate,Ta", row_delimiter="\\r\\n")
            Vds = parsed_array[:, 0]
            Ids = parsed_array[:, 1]
            Vgs = parsed_array[:, 2]
            Igs = parsed_array[:, 3]
        except Exception as e:
            self._log(f'Data parsing error: {e}. Generating dummy data for fallback.', l='warning')

        return {
            "raw_data": {"Vds": Vds, "Ids": Ids, "Vgs": Vgs, "Igs": Igs, "x": Vds, "y": Ids, "y2": Ids},
            "save_type": {
                "Once_format": [
                    {"filename": "VdIds_data.txt", "data": np.column_stack((Vds, Ids, Vgs, Igs))}
                ],
                "DLTS_format": [],
                "Numpy_Dict_format": [
                    {"filename": "VdIds.npy", "data": {"Vds": Vds, "Ids": Ids, "Vgs": Vgs, "Igs": Igs}}
                ]
            },
            "plot_type": {
                "xscale": "linear",
                "yscale": "linear",
                "x_scaling": 1.0,
                "y_scaling": 1.0,
                "y2_scaling": 1.0,
                "xlabel": "Voltage (V)",
                "ylabel": "Current (A)",
                "y2label": "Current (A)",
                "ignore_points": False
            }
        }

    def measure_IdVds_post_set(self, **kwargs) -> None:
        """
        测量后执行的清理步骤
        """
        #self._log('DRon_I: Post-measurement cleanup...')
        # 如果需要关闭工作空间，可以取消注释下面代码
        # self.b1505a.write(':WORK:CLOS')
        # self.b1505a.query('*OPC?')[cite: 1]
    





    # ----------------------------------------------------------------------
    # IdVgs 测量方法
    # ----------------------------------------------------------------------
    
    def measure_IdVgs_pre_set(self, **kwargs) -> None:
        """
        测量前准备工作：确认当前workspace，打开Preset空间，并加载指定的 Test setup
        """
        self._set_progress(0, 'IdVgs')
        self._goto_workspace()
        self._goto_preset_group()
        
        self._current_app_name = 'Id-Vgs'
        
        # 选择预设的 Test
        self.b1505a.write(f':PRES:SET:SEL "{self._current_app_name}"')
        self._check_instrument_errors("Select Preset Test")

        
        Gate = kwargs['Gate']
        VgStart = kwargs['VgStart']
        VgStop = kwargs['VgStop']
        VgStep = kwargs['VgStep']
        
        Source = kwargs['Source']

        Drain = kwargs['Drain']
        VdStart = kwargs['VdStart']
        VdStop = kwargs['VdStop']
        VdPoint = kwargs['VdPoint']
        IdLimit = kwargs['IdLimit']

        
        
        self.b1505a.write(f':STR "Gate", "{Gate}"')
        self.b1505a.write(f':NUMB "VgStart", {VgStart}')
        self.b1505a.write(f':NUMB "VgStop", {VgStop}')
        self.b1505a.write(f':NUMB "VgStep", {VgStep}')
        
        self.b1505a.write(f':STR "Source", "{Source}"')
        
        self.b1505a.write(f':STR "Drain", "{Drain}"')
        self.b1505a.write(f':NUMB "VdStart", {VdStart}')
        self.b1505a.write(f':NUMB "VdStop", {VdStop}')
        self.b1505a.write(f':NUMB "VdPoint", {VdPoint}')
        self.b1505a.write(f':NUMB "IdLimit", {IdLimit}')


        self._check_instrument_errors("Set Parameters")
        time.sleep(0.5)
        

    def measure_IdVgs_main(
        self, Gate: str = 'SMU1:HP', VgStart: float = 0.0, VgStop: float = 6.0, VgStep: float = 0.1, Source: str = 'GNDU:GND',
        Drain: str = 'SMU3:HC', VdStart: float = 0.1, VdStop: float = 1.0, VdPoint: int = 2, IdLimit: float = 5
    ) -> ElectricalDeviceMeasuredData:
        """
        执行 IdVgs 测量并解析数据
        """
        self._log('Start IdVgs Measure')

        while True:
            # 启动单次测量[cite: 1]
            self.b1505a.write(':BENC:SEL:RUN')
            time.sleep(2)
            # 等待测量完成。使用 *OPC? 阻塞直到所有待处理操作完成[cite: 1]
            if self._wait_for_cmd_compelete():
                break
            else:
                self._log(f'OPC timeout, restart measurement', l='warning')
                self.b1505a.write(':BENC:SEL:ABOR')
                time.sleep(10)
                continue

        # 设置数据获取格式：返回 TEXT 格式，且换行符编码设为 ON (\r\n)[cite: 1]
        self.b1505a.write(':RES:FORM TEXT')
        self.b1505a.write(':RES:FORM:ESC ON')
        
        # 请求最新测量结果[cite: 1]
        self.b1505a.write(':RES:FET?')
        
        # 读取原始字节流以解析 IEEE 明确长度的块数据 (Definite Length Arbitrary Block Data)[cite: 3]
        raw_data = self.b1505a.read_raw()
        
        header_str = raw_data[0:2].decode('ascii')
        if header_str.startswith('#'):
            num_digits = int(header_str[1])
            data_length = int(raw_data[2:2+num_digits].decode('ascii'))
            data_str = raw_data[2+num_digits : 2+num_digits+data_length].decode('ascii')
        else:
            # 如果格式异常，回退处理
            data_str = raw_data.decode('ascii')

        self._set_progress(1.0, 'IdVgs')
        self._log('End IdVgs Measure')

        # ---------------------------------------------------------
        # 解析返回的 EasyEXPERT 数据
        # EasyEXPERT TEXT 格式通常包含多行 MetaData (Headers) 以及纯数据列。
        # 以下是通用的 Numpy 解析方法。你需要根据你实际输出的 CSV 结构微调。
        # 假设返回数据中包含 Time, Vds, Ids 并且能计算 Ron。
        # ---------------------------------------------------------
        try:
            # 跳过非数值头部行，直接读取矩阵 (如有表头视情况调整 skip_header 参数)
            _, parsed_array = self.parse_b1505a_text(data_str, header_marker="Vgate,gfs,Idrain,Vdrain,Igate,Ta,gfsMax,Vth", row_delimiter="\\r\\n")
            Ids = parsed_array[:, 2]
            Vgs = parsed_array[:, 0]
        except Exception as e:
            self._log(f'Data parsing error: {e}. Generating dummy data for fallback.', l='warning')

        return {
            "raw_data": {"Vgs": Vgs, "Ids": Ids, "x": Vgs, "y": Ids, "y2": Ids},
            "save_type": {
                "Once_format": [
                    {"filename": "IdVgs_data.txt", "data": np.column_stack((Vgs, Ids))}
                ],
                "DLTS_format": [],
                "Numpy_Dict_format": [
                    {"filename": "IdVgs.npy", "data": {"Vgs": Vgs, "Ids": Ids}}
                ]
            },
            "plot_type": {
                "xscale": "linear",
                "yscale": "linear",
                "x_scaling": 1.0,
                "y_scaling": 1.0,
                "y2_scaling": 1.0,
                "xlabel": "Voltage (V)",
                "ylabel": "Current (A)",
                "y2label": "Current (A)",
                "ignore_points": False
            }
        }

    def measure_IdVgs_post_set(self, **kwargs) -> None:
        """
        测量后执行的清理步骤
        """
        #self._log('DRon_I: Post-measurement cleanup...')
        # 如果需要关闭工作空间，可以取消注释下面代码
        # self.b1505a.write(':WORK:CLOS')
        # self.b1505a.query('*OPC?')[cite: 1]





    # ----------------------------------------------------------------------
    # IgVg 测量方法
    # ----------------------------------------------------------------------
    
    def measure_IgVg_pre_set(self, **kwargs) -> None:
        """
        测量前准备工作：确认当前workspace，打开Preset空间，并加载指定的 Test setup
        """
        self._set_progress(0, 'IgVg')
        self._goto_workspace()
        self._goto_preset_group()
        
        self._current_app_name = 'IgVg'
        
        # 选择预设的 Test
        self.b1505a.write(f':PRES:SET:SEL "{self._current_app_name}"')
        self._check_instrument_errors("Select Preset Test")


        self._check_instrument_errors("Set Parameters")
        time.sleep(0.5)
        

    def measure_IgVg_main(
        self
    ) -> ElectricalDeviceMeasuredData:
        """
        执行 IgVg 测量并解析数据
        """
        self._log('Start IgVg Measure')

        while True:
            # 启动单次测量[cite: 1]
            self.b1505a.write(':BENC:SEL:RUN')
            time.sleep(2)
            # 等待测量完成。使用 *OPC? 阻塞直到所有待处理操作完成[cite: 1]
            if self._wait_for_cmd_compelete():
                break
            else:
                self._log(f'OPC timeout, restart measurement', l='warning')
                self.b1505a.write(':BENC:SEL:ABOR')
                time.sleep(10)
                continue

        # 设置数据获取格式：返回 TEXT 格式，且换行符编码设为 ON (\r\n)[cite: 1]
        self.b1505a.write(':RES:FORM TEXT')
        self.b1505a.write(':RES:FORM:ESC ON')
        
        # 请求最新测量结果[cite: 1]
        self.b1505a.write(':RES:FET?')
        
        # 读取原始字节流以解析 IEEE 明确长度的块数据 (Definite Length Arbitrary Block Data)[cite: 3]
        raw_data = self.b1505a.read_raw()
        
        header_str = raw_data[0:2].decode('ascii')
        if header_str.startswith('#'):
            num_digits = int(header_str[1])
            data_length = int(raw_data[2:2+num_digits].decode('ascii'))
            data_str = raw_data[2+num_digits : 2+num_digits+data_length].decode('ascii')
        else:
            # 如果格式异常，回退处理
            data_str = raw_data.decode('ascii')

        self._set_progress(1.0, 'IgVg')
        self._log('End IgVg Measure')

        # ---------------------------------------------------------
        # 解析返回的 EasyEXPERT 数据
        # EasyEXPERT TEXT 格式通常包含多行 MetaData (Headers) 以及纯数据列。
        # 以下是通用的 Numpy 解析方法。你需要根据你实际输出的 CSV 结构微调。
        # 假设返回数据中包含 Time, Vds, Ids 并且能计算 Ron。
        # ---------------------------------------------------------
        try:
            # 跳过非数值头部行，直接读取矩阵 (如有表头视情况调整 skip_header 参数)
            _, parsed_array = self.parse_b1505a_text(data_str, header_marker="Vgs,Igs", row_delimiter="\\r\\n")
            Igs = parsed_array[:, 1]
            Vgs = parsed_array[:, 0]
        except Exception as e:
            self._log(f'Data parsing error: {e}. Generating dummy data for fallback.', l='warning')

        return {
            "raw_data": {"Vgs": Vgs, "Igs": Igs, "x": Vgs, "y": Igs, "y2": Igs},
            "save_type": {
                "Once_format": [
                    {"filename": "IgVg_data.txt", "data": np.column_stack((Vgs, Igs))}
                ],
                "DLTS_format": [],
                "Numpy_Dict_format": [
                    {"filename": "IgVg.npy", "data": {"Vgs": Vgs, "Igs": Igs}}
                ]
            },
            "plot_type": {
                "xscale": "linear",
                "yscale": "linear",
                "x_scaling": 1.0,
                "y_scaling": 1.0,
                "y2_scaling": 1.0,
                "xlabel": "Voltage (V)",
                "ylabel": "Current (A)",
                "y2label": "Current (A)",
                "ignore_points": False
            }
        }

    def measure_IgVg_post_set(self, **kwargs) -> None:
        """
        测量后执行的清理步骤
        """
        #self._log('DRon_I: Post-measurement cleanup...')
        # 如果需要关闭工作空间，可以取消注释下面代码
        # self.b1505a.write(':WORK:CLOS')
        # self.b1505a.query('*OPC?')[cite: 1]


        

        
    '''
    # ----------------------------------------------------------------------
    # IdVd 测量方法
    # ----------------------------------------------------------------------
    
    def measure_IdVd_pre_set(self, **kwargs) -> None:
        """
        测量前准备工作：确认当前workspace，打开Preset空间，并加载指定的 Test setup
        """
        self._set_progress(0, 'IdVd')
        self._goto_workspace()
        self._goto_preset_group()
        
        self._current_app_name = 'IdVd'
        
        # 选择预设的 Test
        self.b1505a.write(f':PRES:SET:SEL "{self._current_app_name}"')
        self._check_instrument_errors("Select Preset Test")

        
        Gate = kwargs['Gate']
        VgStart = kwargs['VgStart']
        VgStop = kwargs['VgStop']
        VgStep = kwargs['VgStep']
        
        Source = kwargs['Source']

        Drain = kwargs['Drain']
        VdStart = kwargs['VdStart']
        VdStop = kwargs['VdStop']
        VdLinearStep = kwargs['VdLinearStep']
        IdLimit = kwargs['IdLimit']
        PdLimit = kwargs['PdLimit']

        PulsePeriodMode = kwargs['PulsePeriodMode']
        ManualPulsePeriod = kwargs['ManualPulsePeriod']
        PulseWidth = kwargs['PulseWidth']
        
        
        self.b1505a.write(f':STR "Gate", "{Gate}"')
        self.b1505a.write(f':NUMB "VgStart", {VgStart}')
        self.b1505a.write(f':NUMB "VgStop", {VgStop}')
        self.b1505a.write(f':NUMB "VgStep", {VgStep}')
        
        self.b1505a.write(f':STR "Source", "{Source}"')
        
        self.b1505a.write(f':STR "Drain", "{Drain}"')
        self.b1505a.write(f':NUMB "VdStart", {VdStart}')
        self.b1505a.write(f':NUMB "VdStop", {VdStop}')
        self.b1505a.write(f':NUMB "VdLinearStep", {VdLinearStep}')
        self.b1505a.write(f':NUMB "IdLimit", {IdLimit}')
        self.b1505a.write(f':NUMB "PdLimit", {PdLimit}')

        self.b1505a.write(f':STR "PulsePeriodMode", "{PulsePeriodMode}"')
        self.b1505a.write(f':NUMB "ManualPulsePeriod", {ManualPulsePeriod}')
        self.b1505a.write(f':NUMB "PulseWidth", {PulseWidth}')

        self._check_instrument_errors("Set Parameters")
        time.sleep(0.5)
        

    def measure_IdVd_main(
        self, Gate: str = 'SMU4:MC', VgStart: float = 4.0, VgStop: float = 6.0, VgStep: float = 1.0, Source: str = 'GNDU:GND',
        Drain: str = 'SMU3:HC', VdStart: float = 0.0, VdStop: float = 1.0, VdLinearStep: float = 0.02, IdLimit: float = 0.5, PdLimit: float = 0.1,
        PulsePeriodMode: str = 'AUTO', ManualPulsePeriod: float = 50e-3, PulseWidth: float = 500e-6
    ) -> ElectricalDeviceMeasuredData:
        """
        执行 IdVd 测量并解析数据
        """
        self._log('Start IdVd Measure')

        while True:
            # 启动单次测量[cite: 1]
            self.b1505a.write(':BENC:SEL:RUN')
            time.sleep(2)
            # 等待测量完成。使用 *OPC? 阻塞直到所有待处理操作完成[cite: 1]
            if self._wait_for_cmd_compelete():
                break
            else:
                self._log(f'OPC timeout, restart measurement', l='warning')
                self.b1505a.write(':BENC:SEL:ABOR')
                time.sleep(10)
                continue

        # 设置数据获取格式：返回 TEXT 格式，且换行符编码设为 ON (\r\n)[cite: 1]
        self.b1505a.write(':RES:FORM TEXT')
        self.b1505a.write(':RES:FORM:ESC ON')
        
        # 请求最新测量结果[cite: 1]
        self.b1505a.write(':RES:FET?')
        
        # 读取原始字节流以解析 IEEE 明确长度的块数据 (Definite Length Arbitrary Block Data)[cite: 3]
        raw_data = self.b1505a.read_raw()
        
        header_str = raw_data[0:2].decode('ascii')
        if header_str.startswith('#'):
            num_digits = int(header_str[1])
            data_length = int(raw_data[2:2+num_digits].decode('ascii'))
            data_str = raw_data[2+num_digits : 2+num_digits+data_length].decode('ascii')
        else:
            # 如果格式异常，回退处理
            data_str = raw_data.decode('ascii')

        self._set_progress(1.0, 'IdVd')
        self._log('End IdVd Measure')

        # ---------------------------------------------------------
        # 解析返回的 EasyEXPERT 数据
        # EasyEXPERT TEXT 格式通常包含多行 MetaData (Headers) 以及纯数据列。
        # 以下是通用的 Numpy 解析方法。你需要根据你实际输出的 CSV 结构微调。
        # 假设返回数据中包含 Time, Vds, Ids 并且能计算 Ron。
        # ---------------------------------------------------------
        try:
            # 跳过非数值头部行，直接读取矩阵 (如有表头视情况调整 skip_header 参数)
            _, parsed_array = self.parse_b1505a_text(data_str, header_marker="Time,Rds,Vds,Id,Vgs,Ig,V_HCSMU,I_HCSMU,V_HVSMU,I_HVSMU,V_SwitchControl,I_SwitchControl,Ta", row_delimiter="\\r\\n")
            t = parsed_array[:, 0]
            i = parsed_array[:, 3]
            r = parsed_array[:, 1]
            v = parsed_array[:, 2]
            data_mask = t>=0
            t = t[data_mask]
            i = i[data_mask]
            r = r[data_mask]
            v = v[data_mask]
        except Exception as e:
            self._log(f'Data parsing error: {e}. Generating dummy data for fallback.', l='warning')

        return {
            "raw_data": {"t": t, "i": i, "r": r, "v": v, "x": t, "y": r, "y2": v},
            "save_type": {
                "Once_format": [
                    {"filename": "DRon_I_data.txt", "data": np.column_stack((t, r, v, i))}
                ],
                "DLTS_format": [
                    {"filename": "DRon_I_tr.transdata", "fixed_x": t, "changed_y": r},
                    {"filename": "DRon_I_tv.transdata", "fixed_x": t, "changed_y": v}
                ],
                "Numpy_Dict_format": [
                    {"filename": "DRon_I.npy", "data": {"t": t, "i": i, "r": r, "v": v}}
                ]
            },
            "plot_type": {
                "xscale": "linear",
                "yscale": "linear",
                "x_scaling": 1.0,
                "y_scaling": 1e3,
                "y2_scaling": 1.0,
                "xlabel": "Time (s)",
                "ylabel": "Resistance (mOhm)",
                "y2label": "Voltage (V)",
                "ignore_points": True
            }
        }

    def measure_IdVd_post_set(self, **kwargs) -> None:
        """
        测量后执行的清理步骤
        """
        #self._log('DRon_I: Post-measurement cleanup...')
        # 如果需要关闭工作空间，可以取消注释下面代码
        # self.b1505a.write(':WORK:CLOS')
        # self.b1505a.query('*OPC?')[cite: 1]
    '''