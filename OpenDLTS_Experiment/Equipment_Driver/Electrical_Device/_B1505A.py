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
        self.CH_HCSMU = 5
        self.CH_HVSMU = 9
        self.CH_MCSMU4 = 7
        self.CH_MCSMU5 = 8



        
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
    # HVTC 测量方法
    # ----------------------------------------------------------------------

    def measure_HVTC_pre_set(self, **kwargs) -> None:
        self._set_progress(0, 'HVTC')


    def measure_HVTC_main(
        self, Vm: float = 30.0, Vf: float = 0.0, Tf: float = 1.0, Interval: float = 0.05, Points: int = 100, comp_current: float = 0.001,
        DeltaV: float = 0.1, Freq: int = 100e3
    ) -> ElectricalDeviceMeasuredData:
        """
        执行 HVTC 测量并解析数据
        """
        self._log('Start HVTC Measure')
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
            b1505.write("ACT 0, 1") 
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
            self._set_progress(1.0, 'HVTC')
            self._log('End HVTC Measure')
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
                            {"filename": "HVTC_data.txt", "data": np.column_stack((t, c))}
                        ],
                        "DLTS_format": [
                            {"filename": "HVTC.transdata", "fixed_x": t, "changed_y": c}
                        ],
                        "Numpy_Dict_format": [
                            {"filename": "HVTC.npy", "data": {"t": t, "c": c}}
                        ]
                    },
                    "plot_type": {
                        "xscale": "linear",
                        "yscale": "linear",
                        "x_scaling": 1.0,
                        "y_scaling": 1e12,
                        "y2_scaling": 1e12,
                        "x_label": "Time (s)",
                        "y_label": "Capacitance (pF)",
                        "y2_label": "Capacitance (pF)",
                        "ignore_points": True
                    }
                }
        else:
            self._log("No valid data")



    def measure_HVTC_post_set(self, **kwargs) -> None:
        """
        测量后执行的清理步骤
        """
        self._log('HVTC: Post-measurement cleanup...')

        
# ----------------------------------------------------------------------
# HVTI 瞬态电流测量方法 (MM10 Sampling, SMU6:HV / Ch9)
# ----------------------------------------------------------------------

    def measure_HVTI_pre_set(self, **kwargs) -> None:
        self._set_progress(0, 'HVTI')


    def measure_HVTI_main(
        self,
        Vf: float = -100.0,
        Tf: float = 10.0,
        Vm: float = -10.0,
        Interval: float = 0.1,
        Points: int = 101,
        comp_current: float = 0.008,
        MLMode: int = 1,
    ) -> ElectricalDeviceMeasuredData:
        """
        Transient I-t measurement using MM10 sampling.
        HVSMU applies fill voltage Vf for Tf seconds,
        then switches to Vm and samples current.

        MLMode: 1=linear (default), 2-7=logarithmic (10–500 pts/decade).
                Log mode forces interval >= 0.002 s per B1500 spec.
        """
        is_linear = MLMode == 1
        actual_interval = Interval if is_linear or Interval >= 0.002 else 0.002
        mode_label = 'Linear' if is_linear else f'Log(ML{MLMode})'

        self._log(f'Start HVTI [{mode_label}]  Vf={Vf}V Tf={Tf}s Vm={Vm}V '
                  f'Interval={actual_interval}s N={Points}')

        if comp_current < 1e-6 or comp_current > 8e-3:
            self._log(f"comp_current out of range [{1e-6}, {8e-3}]; using 8e-3")
            comp_current = 8e-3

        import pyvisa
        import re

        rm = pyvisa.ResourceManager()
        try:
            b1505 = rm.open_resource(self.GPIB_ADDRESS)
            b1505.timeout = 3600000

            ch = self.CH_HVSMU

            b1505.write(f"CN {ch}")
            b1505.write(f"SSRX {ch},0")
            b1505.write(f"FL 1,{ch}")

            b1505.write("MCC")
            b1505.write(f"ML {MLMode}")
            b1505.write(f"MT 0,{actual_interval},{Points},{Tf}")
            b1505.write("MSC 1,2")

            b1505.write("WAT 1,1,0")
            b1505.write("WAT 2,1,0")

            b1505.write("AIT 0,0,1")
            b1505.write("AZ 0")
            b1505.write("AIT 1,0,6")

            b1505.write(f"AAD {ch},0")
            b1505.write(f"CMM {ch},4")
            b1505.write(f"RI {ch},12")
            b1505.write(f"RM {ch},1")

            b1505.write("PAD 1")
            b1505.write(f"MM 10,{ch}")
            b1505.write("FMT 1,0")
            b1505.write("TSC 1")

            b1505.write(f"MV {ch},0,{Vf},{Vm},{comp_current}")

            b1505.write("TSR")
            b1505.write("XE")
            b1505.query("*OPC?")

            raw_data = b1505.read()

        except Exception as e:
            self._log(f"HVTI measurement error: {e}")
            raw_data = ""

        finally:
            self._set_progress(1.0, 'HVTI')
            self._log('End HVTI')
            try:
                b1505.write(f"IN {self.CH_HVSMU}")
                b1505.write("DZ")
            except Exception:
                pass
            b1505.close()

        if not raw_data:
            self._log("HVTI: no data received")
            return

        pattern = r'([A-Z]{2,3})([+-]\d+\.\d+E[+-]\d+)'
        matches = re.findall(pattern, raw_data)

        TOKENS_PER_SAMPLE = 3
        n = len(matches) // TOKENS_PER_SAMPLE
        if n < 1:
            self._log(f"HVTI: incomplete tokens ({len(matches)}, "
                      f"need {TOKENS_PER_SAMPLE}/sample; "
                      f"prefixes={set(m[0] for m in matches)})")
            return

        vals = [float(m[1]) for m in matches][: n * TOKENS_PER_SAMPLE]
        data = np.array(vals).reshape(n, TOKENS_PER_SAMPLE)

        time_raw = data[:, 0]
        current_arr = data[:, 1]
        voltage_arr = data[:, 2]

        # Per MT spec: time_data = t + h_bias + (idx-1)*interval
        # where t = moment of base→bias voltage switch.
        # With h_bias=0, the first sample's timestamp IS the switch moment.
        # Normalize so t=0 at the voltage switch.
        t_switch = time_raw[0]
        time_arr = time_raw - t_switch

        return {
            "raw_data": {
                "t": time_arr,
                "i": current_arr,
                "v": voltage_arr,
                "x": time_arr,
                "y": current_arr,
                "y2": voltage_arr,
            },
            "save_type": {
                "Once_format": [
                    {"filename": "HVTI_data.txt",
                     "data": np.column_stack((time_arr, current_arr, voltage_arr))}
                ],
                "DLTS_format": [
                    {"filename": "HVTI.transdata",
                     "fixed_x": time_arr,
                     "changed_y": current_arr}
                ],
                "Numpy_Dict_format": [
                    {"filename": "HVTI.npy",
                     "data": {"t": time_arr, "i": current_arr, "v": voltage_arr}}
                ],
            },
            "plot_type": {
                "xscale": "linear" if is_linear else "log",
                "yscale": "linear",
                "x_scaling": 1.0,
                "y_scaling": 1e9,
                "y2_scaling": 1.0,
                "x_label": "Time (s)",
                "y_label": "Current (nA)",
                "y2_label": "Voltage (V)",
                "ignore_points": True,
            },
        }


    def measure_HVTI_post_set(self, **kwargs) -> None:
        self._log('HVTI: Post-measurement cleanup...')





# ----------------------------------------------------------------------
# DRon_I_Bulk: 动态导通电阻测量（恒流漏极 + 衬底应力）
# MM10 Sampling, 3-channel synchronous
#   Ch7 (SMU4:MC) → Gate:  DV — constant Vgs
#   Ch5 (SMU3:HC) → Drain: DI — constant Ids
#   Ch9 (SMU6:HV) → Bulk:  MV — base:VbStress → bias:VbMeasure
# ----------------------------------------------------------------------

    def measure_DRon_I_Bulk_pre_set(self, **kwargs) -> None:
        self._set_progress(0, 'DRon_I_Bulk')

    def measure_DRon_I_Bulk_main(
        self,
        IfLogSampling: bool = False,
        LogSamplingMode: int = 2,
        Interval: float = 0.01,
        Points: int = 1001,
        StressTime: float = 10.0,
        Vgs: float = 5.0,
        IgsLimit: float = 0.1,
        Ids: float = 0.1,
        VdsLimit: float = 5.0,
        VbStress: float = -100.0,
        VbMeasure: float = 0.0,
        IbsLimit: float = 0.008,
    ) -> ElectricalDeviceMeasuredData:
        """
        Dynamic On-Resistance measurement with bulk stress,
        using constant drain current (DI).

        Measurement sequence:
          1. Gate (DV) and Drain (DI) turn on immediately → device ON
          2. Bulk stress applied (MV base=VbStress) during StressTime
          3. Bulk switches to VbMeasure → high-speed sampling begins
          4. Ron(t) = Vds(t) / Id(t)

        IfLogSampling: False=linear (ML=1), True=logarithmic (ML=LogSamplingMode)
        LogSamplingMode: 2-7 (10/25/50/100/250/500 pts/decade)
        Interval: sampling interval in seconds (≥2 ms for log mode)
        Points: number of sampling points
        StressTime: base hold time (bias stress duration) in seconds
        Vgs / IgsLimit: gate voltage and current compliance
        Ids / VdsLimit: drain current and voltage compliance
        VbStress: bulk base voltage (stress level)
        VbMeasure: bulk bias voltage (measure level, typically 0 V)
        IbsLimit: bulk current compliance
        """
        MLMode = 1 if not IfLogSampling else LogSamplingMode
        is_linear = MLMode == 1
        actual_interval = Interval if is_linear or Interval >= 0.002 else 0.002
        mode_label = 'Linear' if is_linear else f'Log(ML{MLMode})'

        self._log(f'Start DRon_I_Bulk [{mode_label}]  '
                  f'Vgs={Vgs}V Ids={Ids}A Vb:{VbStress}->{VbMeasure}V '
                  f'Stress={StressTime}s Interval={actual_interval}s N={Points}')

        import pyvisa
        import re
        import numpy as np

        CH_GATE = self.CH_MCSMU4       # 7 by default (SMU4:MC)
        CH_DRAIN = self.CH_HCSMU     # 5 by default (SMU3:HC)
        CH_BULK = self.CH_HVSMU       # 9 by default (SMU6:HV)

        rm = pyvisa.ResourceManager()
        try:
            b1505 = rm.open_resource(self.GPIB_ADDRESS)
            b1505.timeout = max(3600000, int((StressTime + Points * actual_interval + 30) * 1000))

            # ----- close unrelated channels ---------------------------------
            b1505.write("ERRMSK0,0")
            for ch in (8, 3, 1, 4):
                b1505.write(f"CL{ch}")

            # ----- enable measurement channels -------------------------------
            b1505.write(f"CNX{CH_GATE}")
            b1505.write(f"CNX{CH_DRAIN}")
            b1505.write(f"CNX{CH_BULK}")

            # ----- series resistor OFF, filter setup ------------------------
            for ch in (CH_GATE, CH_DRAIN, CH_BULK):
                b1505.write(f"SSR{ch},0")
                if ch == CH_BULK:
                    b1505.write(f"FL1,{ch}")       # filter ON for HVSMU
                else:
                    b1505.write(f"FL0,{ch}")

            # ----- sampling measurement configuration -----------------------
            b1505.write("MCC")
            b1505.write(f"ML{MLMode}")
            b1505.write(f"MT0,{actual_interval},{Points},{StressTime}")
            b1505.write("MSC1,2")

            # ----- ADC and wait time setup ----------------------------------
            b1505.write("WAT1,1,0")
            b1505.write("WAT2,1,0")
            b1505.write("AIT0,0,1")
            b1505.write("AZ0")
            b1505.write("AIT1,0,6")

            # ----- measurement channel configuration ------------------------
            # All channels: high-speed ADC (AAD=0), CMM=4 (I+V sync)
            # Fixed ranging (RM=1)
            for ch in (CH_GATE, CH_DRAIN, CH_BULK):
                b1505.write(f"AAD{ch},0")
                b1505.write(f"CMM{ch},4")
                b1505.write(f"RM{ch},1")

            # Gate: current measurement range for Ig
            if IgsLimit <= 0.01:
                b1505.write(f"RI{CH_GATE},18")
            elif IgsLimit <= 0.1:
                b1505.write(f"RI{CH_GATE},15")
            else:
                b1505.write(f"RI{CH_GATE},14")

            # Drain: voltage measurement range for Vds
            if VdsLimit <= 2.0:
                b1505.write(f"RV{CH_DRAIN},16")
            elif VdsLimit <= 20.0:
                b1505.write(f"RV{CH_DRAIN},18")
            elif VdsLimit <= 40.0:
                b1505.write(f"RV{CH_DRAIN},19")
            else:
                b1505.write(f"RV{CH_DRAIN},20")

            # Drain: current measurement range for Id (force side = current)
            if Ids <= 1e-4:
                b1505.write(f"RI{CH_DRAIN},15")
            elif Ids <= 1e-3:
                b1505.write(f"RI{CH_DRAIN},14")
            elif Ids <= 1e-2:
                b1505.write(f"RI{CH_DRAIN},13")
            elif Ids <= 0.1:
                b1505.write(f"RI{CH_DRAIN},12")
            else:
                b1505.write(f"RI{CH_DRAIN},11")

            # Bulk: current measurement range for Ib
            b1505.write(f"RI{CH_BULK},12")

            # ----- measurement mode setup -----------------------------------
            b1505.write("PAD1")
            b1505.write(f"MM10,{CH_GATE},{CH_DRAIN},{CH_BULK}")
            b1505.write("FMT1,0")
            b1505.write("TSC1")
            b1505.write("TSR")

            # ----- source setup ---------------------------------------------
            # Gate: DV — constant voltage output (starts immediately)
            b1505.write(f"DV{CH_GATE},0,{Vgs},{IgsLimit},0,0")

            # Drain: DI — constant current output (starts immediately)
            b1505.write(f"DI{CH_DRAIN},0,{Ids},{VdsLimit},0,0")

            # Bulk: TSR + MV — timer reset at bulk output start,
            #        MV waits for XE trigger
            b1505.write(f"TSR{CH_BULK}")
            b1505.write(f"MV{CH_BULK},0,{VbStress},{VbMeasure},{IbsLimit}")

            # ----- trigger measurement --------------------------------------
            b1505.write("XE")
            b1505.query("*OPC?")

            raw_data = b1505.read()

        except Exception as e:
            self._log(f"DRon_I_Bulk measurement error: {e}")
            raw_data = ""

        finally:
            self._set_progress(1.0, 'DRon_I_Bulk')
            self._log('End DRon_I_Bulk')
            try:
                for ch in (CH_BULK, CH_DRAIN, CH_GATE):
                    b1505.write(f"CNX{ch}")
                for ch in (CH_BULK, CH_DRAIN, CH_GATE):
                    b1505.write(f"IN{ch}")
                b1505.write("DZ")
            except Exception:
                pass
            b1505.close()

        if not raw_data:
            self._log("DRon_I_Bulk: no data received")
            return

        # ----- parse ASCII data (FMT1,0) ------------------------------------
        pattern = r'([A-Z]{2,3})([+-]\d+\.\d+E[+-]\d+)'
        matches = re.findall(pattern, raw_data)

        # 3 channels × CMM=4 (2 values each) + TSC time stamp + status tokens
        # Empirically: 9 tokens per sample
        TOKENS_PER_SAMPLE = 9
        n = len(matches) // TOKENS_PER_SAMPLE
        if n < 1:
            self._log(f"DRon_I_Bulk: incomplete tokens ({len(matches)}, "
                      f"need {TOKENS_PER_SAMPLE}/sample; "
                      f"prefixes={set(m[0] for m in matches)})")
            return

        vals = [float(m[1]) for m in matches][: n * TOKENS_PER_SAMPLE]
        data = np.array(vals).reshape(n, TOKENS_PER_SAMPLE)

        # Column mapping — B1500 FMT1 header encoding:
        #   Status letter + Channel letter + Data type letter
        #   Channel letters: G=ch7(gate), E=ch5(drain), I=ch9(bulk)
        #   MM10 order (7,5,9) × CMM=4 (compliance+force) × per-ch timestamp:
        #     0: NGT=time    1: NGI=Ig     2: NGV=Vgs
        #     3: NET=time    4: NEV=Vds    5: NEI=Id
        #     6: NIT=time    7: NII=Ib     8: NIV=Vb
        time_raw = data[:, 0]
        ig_arr = data[:, 1]
        vgs_arr = data[:, 2]
        vds_arr = data[:, 4]
        id_arr = data[:, 5]
        ib_arr = data[:, 7]
        vb_arr = data[:, 8]

        # Time normalization: t=0 at voltage switch (base→bias)
        t_switch = time_raw[0]
        time_arr = time_raw - t_switch

        # Dynamic on-resistance
        with np.errstate(divide='ignore', invalid='ignore'):
            ron_arr = np.abs(vds_arr / id_arr)
            ron_arr[~np.isfinite(ron_arr)] = np.nan

        return {
            "raw_data": {
                "t": time_arr,
                "Id": id_arr,
                "Vds": vds_arr,
                "Ig": ig_arr,
                "Vgs": vgs_arr,
                "Ib": ib_arr,
                "Vb": vb_arr,
                "Ron": ron_arr,
                "x": time_arr,
                "y": ron_arr,
                "y2": id_arr,
            },
            "save_type": {
                "Once_format": [
                    {"filename": "DRon_I_Bulk_data.txt",
                     "data": np.column_stack((time_arr, id_arr, vds_arr,
                                              ig_arr, vgs_arr, ib_arr, vb_arr,
                                              ron_arr))}
                ],
                "DLTS_format": [
                    {"filename": "DRon_I_Bulk.transdata",
                     "fixed_x": time_arr,
                     "changed_y": ron_arr},
                    {"filename": "DRon_I_Bulk_Ib.transdata",
                     "fixed_x": time_arr,
                     "changed_y": ib_arr},
                    {"filename": "DRon_I_Bulk_Ig.transdata",
                     "fixed_x": time_arr,
                     "changed_y": ig_arr}
                ],
                "Numpy_Dict_format": [
                    {"filename": "DRon_I_Bulk.npy",
                     "data": {
                         "t": time_arr,
                         "Id": id_arr,
                         "Vds": vds_arr,
                         "Ig": ig_arr,
                         "Vgs": vgs_arr,
                         "Ib": ib_arr,
                         "Vb": vb_arr,
                         "Ron": ron_arr,
                     }}
                ],
            },
            "plot_type": {
                "xscale": "linear" if is_linear else "log",
                "yscale": "linear",
                "x_scaling": 1.0,
                "y_scaling": 1e3,
                "y2_scaling": 1e3,
                "x_label": "Time (s)",
                "y_label": "Ron (mOhm)",
                "y2_label": "Id (mA)",
                "ignore_points": True,
            },
        }

    def measure_DRon_I_Bulk_post_set(self, **kwargs) -> None:
        self._log('DRon_I_Bulk: Post-measurement cleanup...')



    # ----------------------------------------------------------------------
    # SHVCV: Stress High Voltage CV ????
    # MM18 CV (DC bias) sweep measurement
    #   Ch9 (HVSMU) ? Drain-Source DC bias via High Voltage Bias Tee
    #   Ch4 (CMU)   ? Capacitance measurement via High Voltage Bias Tee
    #
    # Stress: DV StressVoltage ? sleep(StressTime) ? DV VdStart ? sweep.
    # Sweep: WDCV {VdStart?VdStop} ? WTDCV hold=0 ? MM18 ? XE.
    # ----------------------------------------------------------------------

    def measure_SHVCV_pre_set(self, **kwargs) -> None:
        self._set_progress(0, 'SHVCV')

    def measure_SHVCV_main(
        self,
        IntegTime: str = "MEDIUM",
        StressVoltage: float = 50.0,
        StressTime: float = 10.0,
        Frequency: float = 100e3,
        OscLevel: float = 0.1,
        VdStart: float = 0.0,
        VdStop: float = 50.0,
        VdLinearStep: float = 1.0,
        IdLimit: float = 0.008,
    ) -> ElectricalDeviceMeasuredData:
        """
        Stress High Voltage CV measurement for GaN Cds characterization.

        Stress: DV applies StressVoltage, held via time.sleep(StressTime),
        then transitions to VdStart before sweep begins.

        IntegTime: "SHORT" | "MEDIUM" | "LONG" ? MFCMU integration time
                   SHORT:  ACT 0,1  (minimal averaging)
                   MEDIUM: ACT 0,3  (moderate averaging)
                   LONG:   ACT 0,5  (heavy averaging)
        StressVoltage: Vds stress voltage (V), can differ from VdStart
        StressTime: stress duration (s), via time.sleep
        Frequency: CMU measurement frequency (Hz)
        OscLevel: CMU AC oscillation level (V), 0 to 0.25
        VdStart: CV sweep start voltage (V)
        VdStop: CV sweep end voltage (V)
        VdLinearStep: voltage step size (V), negative for downward sweep
        IdLimit: HVSMU current compliance (A), 1e-6 to 8e-3
        """
        integ_map = {"SHORT": (0, 1), "MEDIUM": (0, 3), "LONG": (0, 5)}
        act_mode, act_n = integ_map.get(IntegTime, (0, 3))

        sweep_steps = int(abs(VdStop - VdStart) / abs(VdLinearStep)) + 1
        if sweep_steps < 1 or sweep_steps > 1001:
            self._log(f"SHVCV: invalid sweep_steps={sweep_steps}, clamping to [1,1001]")
            sweep_steps = max(1, min(sweep_steps, 1001))

        if IdLimit < 1e-6 or IdLimit > 8e-3:
            self._log(f"SHVCV: IdLimit={IdLimit} out of range [1e-6, 8e-3]; using 8e-3")
            IdLimit = 8e-3

        self._log(f'Start SHVCV [{IntegTime}]  '
                  f'Stress={StressVoltage}V/{StressTime}s  '
                  f'Freq={Frequency}Hz Osc={OscLevel}V  '
                  f'Sweep: {VdStart}?{VdStop}V step={VdLinearStep}V ({sweep_steps}pts)  '
                  f'IdLimit={IdLimit}A ACT={act_mode},{act_n}')

        import pyvisa
        import re
        import numpy as np
        import time

        CH_CMU   = self.CH_CMU
        CH_HVSMU = self.CH_HVSMU

        rm = pyvisa.ResourceManager()
        try:
            b1505 = rm.open_resource(self.GPIB_ADDRESS)
            b1505.timeout = max(3600000, int((StressTime + sweep_steps * 0.5 + 120) * 1000))

            b1505.write(f"CN {CH_CMU},{CH_HVSMU}")

            b1505.write(f"SSR {CH_HVSMU},0")
            b1505.write(f"FL 1,{CH_HVSMU}")

            b1505.write(f"DV {CH_HVSMU},0,{StressVoltage},{IdLimit}")

            self._log(f"SHVCV: Stress {StressVoltage}V for {StressTime}s (DV + sleep)")
            time.sleep(StressTime)

            b1505.write(f"DV {CH_HVSMU},0,{VdStart},{IdLimit}")
            self._log(f"SHVCV: Transition to sweep start {VdStart}V")

            b1505.write(f"ACT {act_mode},{act_n}")
            b1505.write("IMP 100")
            b1505.write(f"RC {CH_CMU},0")
            b1505.write(f"FC {CH_CMU},{Frequency}")
            b1505.write(f"ACV {CH_CMU},{OscLevel}")

            b1505.write(f"WDCV {CH_HVSMU},1,{VdStart},{VdStop},{sweep_steps},{IdLimit}")
            b1505.write("WMDCV 1")

            b1505.write("WTDCV 0,0.001")

            b1505.write("FMT 1,1")
            b1505.write("TSC 1")
            b1505.write(f"MM 18,{CH_CMU},{CH_HVSMU}")

            b1505.write("XE")
            b1505.query("*OPC?")

            raw_data = b1505.read()

        except Exception as e:
            self._log(f"SHVCV measurement error: {e}")
            raw_data = ""

        finally:
            self._set_progress(1.0, 'SHVCV')
            self._log('End SHVCV')
            try:
                b1505.write("DZ")
            except Exception:
                pass
            b1505.close()

        if not raw_data:
            self._log("SHVCV: no data received")
            return

        pattern = r'([A-Z]{3})([+-]\d+\.\d+E[+-]\d+)'
        matches = re.findall(pattern, raw_data)

        # MM18 per-point token structure (CMU ch4 + HVSMU ch9):
        #   NDT=CMU_time  NDC=capacitance  NDY=conductance
        #   NIT=HV_time   NII=HV_current   NIV=measured_Vds  WIV=setpoint_Vds
        TOKENS_PER_POINT = 7
        n_points = len(matches) // TOKENS_PER_POINT

        if n_points < 1:
            self._log(f"SHVCV: incomplete tokens ({len(matches)}, "
                      f"need {TOKENS_PER_POINT}/point; "
                      f"prefixes={set(m[0] for m in matches)})")
            return

        c_arr = []
        v_arr = []
        for i in range(n_points):
            point_tokens = matches[i * TOKENS_PER_POINT : (i + 1) * TOKENS_PER_POINT]
            for prefix, val_str in point_tokens:
                val = float(val_str)
                if prefix == 'NDC':
                    c_arr.append(val)
                elif prefix == 'NIV':
                    v_arr.append(val)

        c_arr = np.array(c_arr)
        v_arr = np.array(v_arr)
        min_len = min(len(v_arr), len(c_arr))
        v_arr = v_arr[:min_len]
        c_arr = c_arr[:min_len]

        if min_len < 1:
            self._log("SHVCV: no valid C-V pairs extracted")
            return

        v_ds = np.abs(v_arr)
        c_ds = np.abs(c_arr)

        return {
            "raw_data": {
                "v": v_ds,
                "c": c_ds,
                "x": v_ds,
                "y": c_ds,
                "y2": c_ds,
            },
            "save_type": {
                "Once_format": [
                    {"filename": "SHVCV_data.txt",
                     "data": np.column_stack((v_ds, c_ds))}
                ],
                "DLTS_format": [
                    {"filename": "SHVCV.transdata",
                     "fixed_x": v_ds,
                     "changed_y": c_ds}
                ],
                "Numpy_Dict_format": [
                    {"filename": "SHVCV.npy",
                     "data": {"Vds": v_ds, "Cds": c_ds}}
                ],
            },
            "plot_type": {
                "xscale": "linear",
                "yscale": "linear",
                "x_scaling": 1.0,
                "y_scaling": 1e12,
                "y2_scaling": 1e12,
                "x_label": "Vds (V)",
                "y_label": "Cds (pF)",
                "y2_label": "Cds (pF)",
                "ignore_points": False,
            },
        }

    def measure_SHVCV_post_set(self, **kwargs) -> None:
        self._log('SHVCV: Post-measurement cleanup...')


    

    
    # ----------------------------------------------------------------------
    # HVCV 测量方法
    # ----------------------------------------------------------------------
    
    def measure_HVCV_pre_set(self, **kwargs) -> None:
        """
        测量前准备工作：确认当前workspace，打开Preset空间，并加载指定的 Test setup
        """
        self._set_progress(0, 'HVCV')
        self._goto_workspace()
        self._goto_preset_group()
        
        self._current_app_name = 'HVCV'
        
        # 选择预设的 Test
        self.b1505a.write(f':PRES:SET:SEL "{self._current_app_name}"')
        self._check_instrument_errors("Select Preset Test")

        # SHORT | MEDIUM | LONG
        IntegTime = kwargs['IntegTime']
        Frequency = kwargs['Frequency']
        OscLevel = kwargs['OscLevel']
        Scale = kwargs['Scale']
        Drain = kwargs['Drain']
        VdBias = kwargs['VdBias']
        VdStart = kwargs['VdStart']
        VdStop = kwargs['VdStop']
        VdLinearStep = kwargs['VdLinearStep']
        IdLimit = kwargs['IdLimit']

        
        self.b1505a.write(f':STR "IntegTime", "{IntegTime}"')
        self.b1505a.write(f':NUMB "Frequency", {Frequency}')
        self.b1505a.write(f':NUMB "OscLevel", {OscLevel}')
        
        self.b1505a.write(f':STR "Scale", "{Scale}"')
        self.b1505a.write(f':STR "Drain", "{Drain}"')
        self.b1505a.write(f':STR "VdBias", "{VdBias}"')
        self.b1505a.write(f':NUMB "VdStart", {VdStart}')
        self.b1505a.write(f':NUMB "VdStop", {VdStop}')
        self.b1505a.write(f':NUMB "VdLinearStep", {VdLinearStep}')
        self.b1505a.write(f':NUMB "IdLimit", {IdLimit}')


        self._check_instrument_errors("Set Parameters")
        time.sleep(0.5)
        

    def measure_HVCV_main(
        self, IntegTime: str = 'SHORT', Frequency: int = 100e3, OscLevel: float = 0.1, Scale: str = 'LINEAR',
        Drain: str = 'CMU1:MF', VdBias: str = 'SMU6:HV', VdStart: float = 0, VdStop: float = 30, VdLinearStep: float = 2.0,
        IdLimit: float = 8e-3
    ) -> ElectricalDeviceMeasuredData:
        """
        执行 HVCV 测量并解析数据
        """
        self._log('Start HVCV Measure')

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

        self._set_progress(1.0, 'HVCV')
        self._log('End HVCV Measure')

        # ---------------------------------------------------------
        # 解析返回的 EasyEXPERT 数据
        # EasyEXPERT TEXT 格式通常包含多行 MetaData (Headers) 以及纯数据列。
        # 以下是通用的 Numpy 解析方法。你需要根据你实际输出的 CSV 结构微调。
        # 假设返回数据中包含 Time, Vds, Ids 并且能计算 Ron。
        # ---------------------------------------------------------
        try:
            # 跳过非数值头部行，直接读取矩阵 (如有表头视情况调整 skip_header 参数)
            _, parsed_array = self.parse_b1505a_text(data_str, header_marker="Vdrain,Cds,Ids,Ta", row_delimiter="\\r\\n")
            Vds = parsed_array[:, 0]
            Cds = parsed_array[:, 1]
            Ids = parsed_array[:, 2]
            
        except Exception as e:
            self._log(f'Data parsing error: {e}. Generating dummy data for fallback.', l='warning')

        return {
            "raw_data": {"v": Vds, "c": Cds, "i":Ids, "x": Vds, "y": Cds, "y2": Ids},
            "save_type": {
                "Once_format": [
                    {"filename": "HVCV_data.txt", "data": np.column_stack((Vds, Cds, Ids))}
                ],
                "DLTS_format": [
                    {"filename": "HVCV.transdata", "fixed_x": Vds, "changed_y": Cds}
                ],
                "Numpy_Dict_format": [
                    {"filename": "HVCV.npy", "data": {"Vds": Vds, "Cds": Cds, "Ids":Ids}}
                ]
            },
            "plot_type": {
                "xscale": "linear",
                "yscale": "linear",
                "x_scaling": 1.0,
                "y_scaling": 1e12,
                "y2_scaling": 1.0,
                "x_label": "Voltage (V)",
                "y_label": "Capacitance (pF)",
                "y2_label": "Current (A)",
                "ignore_points": False
            }
        }

    def measure_HVCV_post_set(self, **kwargs) -> None:
        """
        测量后执行的清理步骤
        """
        #self._log('DRon_I: Post-measurement cleanup...')
        # 如果需要关闭工作空间，可以取消注释下面代码
        # self.b1505a.write(':WORK:CLOS')
        # self.b1505a.query('*OPC?')[cite: 1]


    




    
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
                "x_label": "Voltage (V)",
                "y_label": "Current (A)",
                "y2_label": "Current (A)",
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
            ig = parsed_array[:, 5]
            data_mask = t>=0
            t = t[data_mask]
            i = i[data_mask]
            r = r[data_mask]
            v = v[data_mask]
            ig = ig[data_mask]
        except Exception as e:
            self._log(f'Data parsing error: {e}. Generating dummy data for fallback.', l='warning')

        return {
            "raw_data": {"t": t, "i": i, "r": r, "v": v, "ig":ig, "x": t, "y": r, "y2": ig},
            "save_type": {
                "Once_format": [
                    {"filename": "DRon_I_data.txt", "data": np.column_stack((t, r, v, i, ig))}
                ],
                "DLTS_format": [
                    {"filename": "DRon_I_tr.transdata", "fixed_x": t, "changed_y": r},
                    {"filename": "DRon_I_tig.transdata", "fixed_x": t, "changed_y": ig}
                ],
                "Numpy_Dict_format": [
                    {"filename": "DRon_I.npy", "data": {"t": t, "i": i, "r": r, "v": v, "ig":ig}}
                ]
            },
            "plot_type": {
                "xscale": "linear",
                "yscale": "linear",
                "x_scaling": 1.0,
                "y_scaling": 1e3,
                "y2_scaling": 1.0,
                "x_label": "Time (s)",
                "y_label": "Resistance (mOhm)",
                "y2_label": "Current (A)",
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
                "x_label": "Voltage (V)",
                "y_label": "Current (mA)",
                "y2_label": "Current (mA)",
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
                "x_label": "Voltage (V)",
                "y_label": "Current (A)",
                "y2_label": "Current (A)",
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
                "x_label": "Voltage (V)",
                "y_label": "Current (A)",
                "y2_label": "Current (A)",
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
                "x_label": "Voltage (V)",
                "y_label": "Current (A)",
                "y2_label": "Current (A)",
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
                "x_label": "Time (s)",
                "y_label": "Resistance (mOhm)",
                "y2_label": "Voltage (V)",
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