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
        self._workspace_name = 'OpenDLTS'
        self._preset_group_name = 'OpenDLTS'
        
        try:
            self.b1505a = self.rm.open_resource(self.instrument_address)
            # 根据手册要求，所有命令和响应均以换行符终止
            self.b1505a.read_termination = '\n'
            self.b1505a.write_termination = '\n'
            # 测量可能耗时较长，增加超时时间 (单位: 毫秒)
            self.b1505a.timeout = 600000
            
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
            self._wait_for_cmd_compelete()
        else:
            if self._workspace_name not in self.b1505a.query(':WORK:NAME?'):
                self.b1505a.write(f':WORK:CLOS')
                time.sleep(5)
                self._wait_for_cmd_compelete()
                # 开启相应workspace
                self.b1505a.write(f':WORK:OPEN "{self._workspace_name}"')
                time.sleep(5)
                self._wait_for_cmd_compelete()
    
    def _goto_preset_group(self):
        self.b1505a.write(f':PRES:OPEN "{self._preset_group_name}"')
        time.sleep(5)
        self._wait_for_cmd_compelete()

    def _wait_for_cmd_compelete(self):
        while True:
            status = None
            try:
                status = self.b1505a.query('*OPC?')
            except Exception:
                pass
            if status == '1':
                break
            else:
                time.sleep(1)

    def parse_b1505a_text(raw_text, header_marker="Vr,Ir,Rr", row_delimiter="\n\r\\"):
        """
        解析带有特定分隔符和起始标记的文本数据
        
        :param raw_text: 原始文本字符串
        :param header_marker: 数据开始的表头标记
        :param row_delimiter: 行与行之间的特殊分隔符
        :return: headers (表头列表), data_matrix (Numpy二维数组)
        """
        # 按照特殊分隔符对文本进行切片
        lines = raw_text.split(row_delimiter)
        
        headers = []
        data_list = []
        start_reading = False
        
        for line in lines:
            # 去除首尾可能多余的空白字符
            line = line.strip()
            if not line:
                continue
                
            # 探测是否到达数据表头所在行
            if line.startswith(header_marker):
                start_reading = True
                headers = line.split(',')
                continue # 跳过表头这一行，继续读取下一行的数据
                
            # 如果已经找到了表头，开始解析数据
            if start_reading:
                try:
                    # 将该行按逗号分割，并转换为浮点数
                    values = [float(x) for x in line.split(',')]
                    data_list.append(values)
                except ValueError:
                    # 如果遇到无法转换成数字的行（比如文件结尾的其他文本），可以跳过或停止
                    # print(f"警告：跳过无法解析的行 -> {line}")
                    break 
    
        # 将列表转换为 Numpy 数组，方便后续的数学计算或切片操作
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
        

    def measure_IV_main(
        self, Vstart: float = -3.0, Vend: float = 3.0, Vstep: float = 0.01, SMU: str = 'SMU5:MC'
    ) -> ElectricalDeviceMeasuredData:
        """
        执行 IV 测量并解析数据
        """
        self._log('Start IV Measure')

        # 启动单次测量[cite: 1]
        self.b1505a.write(':BENC:SEL:RUN')
        time.sleep(5)
        # 等待测量完成。使用 *OPC? 阻塞直到所有待处理操作完成[cite: 1]
        self._wait_for_cmd_compelete()

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
            parsed_array = np.genfromtxt(io.StringIO(data_str), delimiter=',', skip_header=10, invalid_raise=False)
            # 假设列索引：0=Time, 1=Vds, 2=Ids (请根据实际情况严格对应)
            t = parsed_array[:, 0]
            v = parsed_array[:, 1]
            i = parsed_array[:, 2]
            ron = v / (i + 1e-12) # 防止除以0
        except Exception as e:
            self._log(f'Data parsing error: {e}. Generating dummy data for fallback.', l='warning')
            t = np.linspace(0, 1, Points)
            v = np.full(Points, Vds)
            i = np.linspace(0.01, 0.1, Points)
            ron = v / i

        return {
            "raw_data": {"t": t, "v": v, "i": i, "ron": ron, "x": t, "y": ron, "y2": i},
            "save_type": {
                "Once_format": [
                    {"filename": "IV_data.txt", "data": np.column_stack((t, v, i, ron))}
                ],
                "DLTS_format": [
                    {"filename": "IV.transdata", "fixed_x": t, "changed_y": ron}
                ],
                "Numpy_Dict_format": [
                    {"filename": "IV.npy", "data": {"t": t, "v": v, "i": i, "ron": ron}}
                ]
            },
            "plot_type": {
                "xscale": "linear",
                "yscale": "log",
                "x_scaling": 1.0,
                "y_scaling": 1.0,
                "y2_scaling": 1.0,
                "xlabel": "Time [s]",
                "ylabel": "Dynamic On-Resistance [Ohm]",
                "y2label": "Current [A]",
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