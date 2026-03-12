import time
import numpy as np
import inspect
from ..._config import LOGGER_ODEXP as LOGGER
from ..._typing import ElectricalDeviceMeasuredData
from ._ReSampleFromTimeArray import ReSampleFromTimeArray

__all__ = ['MFIA']

class MFIA:
    def __init__(self, parent):
        self.parent = parent
        import zhinst.core
        # Connect To Local Data Server
        self.daq = zhinst.core.ziDAQServer('127.0.0.1', 8004, 6)
        # Device Serial
        self._serial = 7449
        self.id = 'dev'+str(self._serial)
        # Connect To Device
        self.daq.connectDevice(self.id, '1GbE')
        self._roundBs = 8
        # Close IA and Signal Output and Signal_add
        self.daq.setInt('/{}/imps/0/enable'.format(self.id), 0)
        self.daq.setInt('/{}/sigouts/0/add'.format(self.id), 0)
        self.daq.setInt('/{}/imps/0/output/on'.format(self.id), 0)
        time.sleep(5)
        # 2 terminal mode
        self.daq.setInt('/{}/imps/0/mode'.format(self.id), 1)
        # AC amplitude manual setting mode
        self.daq.setInt('/{}/imps/0/auto/output'.format(self.id), 0)
        # AC amplitude
        dV = 0.1
        self.daq.setDouble('/{}/imps/0/output/amplitude'.format(self.id), round(dV,self._roundBs))
        # Ac init freq
        freq = 100e3
        self.daq.setDouble('/{}/imps/0/freq'.format(self.id), round(freq,self._roundBs))
        # manual Lock-in setting
        self.daq.setInt('/{}/system/impedance/filter'.format(self.id), 1)
        # Manually set the Lock-in filter bandwidth
        self.daq.setInt('/{}/imps/0/auto/bw'.format(self.id), 0)
        # Lock-in filter bandwidth
        #maxbandwidth = 100.0
        #self.daq.setDouble('/{}/imps/0/maxbandwidth'.format(self.id), round(maxbandwidth,self._roundBs))
        # Lock-in filter order
        order = 8
        self.daq.setInt('/{}/imps/0/demod/order'.format(self.id), order)
        # enable Lock-in sinc filter
        self.daq.setInt('/{}/imps/0/demod/sinc'.format(self.id), 1)
        # Lock-in filter timeconstant
        timeconstant=2.4e-6
        self.daq.setDouble('/{}/imps/0/demod/timeconstant'.format(self.id), round(timeconstant,self._roundBs))
        # Data Rate 107k
        rate = 107e3
        self.daq.setDouble('/{}/imps/0/demod/rate'.format(self.id), round(rate,self._roundBs))
        # Voltage output range
        outputrange = 10.0
        self.daq.setDouble('/{}/imps/0/output/range'.format(self.id), round(outputrange,self._roundBs))
        # capacitor model uses a capacitor-resistor parallel model.
        self.daq.setInt('/{}/imps/0/model'.format(self.id), 0)
        # Compensation cable length 1.5m
        self.daq.setDouble('/{}/system/impedance/calib/cablelength'.format(self.id), 1.50000000)
        # open IA and signal output
        self.daq.setInt('/{}/imps/0/output/on'.format(self.id), 1)
        self.daq.setInt('/{}/imps/0/enable'.format(self.id), 1)
        time.sleep(5)
        self._log(f'MFIA ID:{self.id} Connected...')
        
    def _log(self,m,c='#778899',l='info'):
        if l == 'info':
            LOGGER.info(m, extra={'color': c})
        else:
            LOGGER.warning(m, extra={'color': '#FF0000'})
    
    def _set_progress(self, val, mn):
        self.parent.measure_tab.methods[mn].progress.value=val
        
    def close(self):
        self._log(f'MFIA ID:{self.id} is shutting down now, it is safe to power it off once the front LED turns red or off.')
        self.daq.setInt('/{}/system/shutdown'.format(self.id), 1)

    def is_alive(self):
        return True




    # CV
    def measure_CV_pre_set(self, **kwargs) -> None:
        DeltaV = kwargs['DeltaV']
        freq = kwargs['freq']
        IfAutoRange = kwargs['IfAutoRange']
        ManualRange = kwargs['ManualRange']
        # progress clear
        self._set_progress(0,'CV')
        # Ensure Output1 Signal ON
        if self.daq.getInt('/{}/imps/0/output/on'.format(self.id)) != 1:
            self._log(f'CV: Opening Output1 Signal...')
            self.daq.setInt('/{}/imps/0/output/on'.format(self.id), 1)
            time.sleep(5)
        # Ensure Signal Add Disabled
        if self.daq.getInt('/{}/sigouts/0/add'.format(self.id)) != 0:
            self._log(f'CV: Closing Signal Add...')
            self.daq.setInt('/{}/sigouts/0/add'.format(self.id), 0)
            time.sleep(5)
        # Ensure IA Enabled
        if self.daq.getInt('/{}/imps/0/enable'.format(self.id)) != 1:
            self._log(f'CV: Opening IA...')
            self.daq.setInt('/{}/imps/0/enable'.format(self.id), 1)
            time.sleep(3)
        # Ensure Bias ON and Set to 0V
        if self.daq.getInt('/{}/imps/0/bias/enable'.format(self.id)) == 0:
            self.daq.setInt('/{}/imps/0/bias/enable'.format(self.id), 1)
            time.sleep(3)
        if self.daq.getDouble('/{}/imps/0/bias/value'.format(self.id)) !=0:
            self.daq.setDouble('/{}/imps/0/bias/value'.format(self.id), 0)
            time.sleep(2)
        # Read Current AC Amplitude
        self.tempdV = self.daq.getDouble('/{}/imps/0/output/amplitude'.format(self.id))
        # Read Current AC Frequency
        self.tempfreq = self.daq.getDouble('/{}/imps/0/freq'.format(self.id))
        # Read RangeMode
        self.temprangemode = self.daq.getInt('/{}/imps/0/auto/inputrange'.format(self.id))
        # Read Range
        self.temprange = self.daq.getDouble('/{}/imps/0/current/range'.format(self.id))
        # Set Target AC Amplitude
        self.daq.setDouble('/{}/imps/0/output/amplitude'.format(self.id), round(DeltaV,self._roundBs))
        # Set Target AC Frequency
        self.daq.setDouble('/{}/imps/0/freq'.format(self.id), round(freq,self._roundBs))
        # Set Range
        if IfAutoRange:
            if self.temprangemode != 1:
                self.daq.setInt('/{}/imps/0/auto/inputrange'.format(self.id), 1)
        else:
            self.daq.setInt('/{}/imps/0/auto/inputrange'.format(self.id), 0)
            self.daq.setDouble('/{}/imps/0/current/range'.format(self.id), ManualRange)
    
    def measure_CV_main(
        self, Vstart: float = -5, Vend: float = -0.5, Points: int = 100, freq: int = 100000, DeltaV: float = 0.1,
        IfAutoRange: bool = True, ManualRange: float = 0.000100
    ) -> ElectricalDeviceMeasuredData:
        sweeper = self.daq.sweep()
        # Sweeper Device
        sweeper.set('device', '{}'.format(self.id))
        # Once
        sweeper.set('endless', 0)
        # Advanced Filtermode
        sweeper.set('filtermode', 1)
        # Sweep Voltage
        sweeper.set('gridnode', '/{}/sigouts/0/offset'.format(self.id))
        sweeper.set('historylength', 100)
        # Sweep Points
        sweeper.set('samplecount', round(Points))
        # Linear mapping=0, log mapping=1
        sweeper.set('xmapping', 0)
        # Averaging Times Per Point
        sweeper.set('averaging/sample', 20)
        sweeper.set('averaging/tc', 15.00000000)
        sweeper.set('averaging/time', 0.10000000)
        if Vstart<=Vend:
            sweeper.set('scan', 0)
            sweeper.set('start', round(Vstart,self._roundBs))
            sweeper.set('stop', round(Vend,self._roundBs))
        else:
            sweeper.set('scan', 3)
            sweeper.set('start', round(Vend,self._roundBs))
            sweeper.set('stop', round(Vstart,self._roundBs))
        sweeper.set('settling/inaccuracy', 0.01000000)
        sweeper.set('averaging/sample', 20)
        sweeper.set('averaging/tc', 15.00000000)
        sweeper.set('averaging/time', 0.10000000)
        sweeper.set('bandwidth', 10.00000000)
        sweeper.set('maxbandwidth', 100.00000000)
        sweeper.set('bandwidthoverlap', 1)
        sweeper.set('omegasuppression', 80.00000000)
        sweeper.set('order', 8)
        sweeper.subscribe('/{}/imps/0/sample'.format(self.id))
        sweeper.subscribe('/{}/demods/0/sample'.format(self.id))
        sweeper.execute()
        # To read the acquired data from the module, use a
        # while loop like the one below. This will allow the
        # data to be plotted while the measurement is ongoing.
        # Note that any device nodes that enable the streaming
        # of data to be acquired, must be set before the while loop.
        result = 0
        self._log(f'Start CV Measure')
        while sweeper.progress() < 1.0 and not sweeper.finished():
            # update progress
            self._set_progress(float(sweeper.progress()[0]),'CV')
            time.sleep(1)
            result = sweeper.read()
        self._log(f'End CV Measure')
        sweeper.finish()
        sweeper.unsubscribe('*')
        # Voltage
        v = result['{}'.format(self.id)]['imps']['0']['sample'][0][0]['grid']
        # Capacitance
        c = result['{}'.format(self.id)]['imps']['0']['sample'][0][0]['param1']
        # Resistance
        r = result['{}'.format(self.id)]['imps']['0']['sample'][0][0]['param0']
        # Demod R
        i = result['{}'.format(self.id)]['demods']['0']['sample'][0][0]['r']
        return {
            "raw_data": {"v": v, "c": c, "r": r, "i": i, "x": v, "y": c, "y2": r},
            "save_type": {
                "Once_format": [
                    {"filename": "CV_data.txt", "data": np.column_stack((v, c, r))}
                ],
                "DLTS_format": [
                    {"filename": "CV.transdata", "fixed_x": v, "changed_y": c}
                ],
                "Numpy_Dict_format": [
                    {"filename": "CV.npy", "data": {"v": v, "c": c, "r": r, "i": i}}
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
                "y2_label": "Resistance (Ohm)",
                "ignore_points": False
            }
        }
    def measure_CV_post_set(self, **kwargs) -> None:
        # Set Bias Voltage to 0V
        self.daq.setDouble('/{}/imps/0/bias/value'.format(self.id), 0.00000000)
        # Set AC Frequency
        self.daq.setDouble('/{}/imps/0/freq'.format(self.id), round(self.tempfreq,self._roundBs))
        # Set AC Amplitude
        self.daq.setDouble('/{}/imps/0/output/amplitude'.format(self.id), round(self.tempdV,self._roundBs))
        # Set Range
        self.daq.setInt('/{}/imps/0/auto/inputrange'.format(self.id), self.temprangemode)
        if self.temprangemode != 1:
            self.daq.setDouble('/{}/imps/0/current/range'.format(self.id), self.temprange)

    # Ad
    def measure_Ad_pre_set(self, **kwargs):
        IfAutoRange = kwargs['IfAutoRange']
        Vbias = kwargs['Vbias']
        ManualRange = kwargs['ManualRange']
        # progress clear
        self._set_progress(0,'Ad')
        # Ensure Output1 Signal ON
        if self.daq.getInt('/{}/imps/0/output/on'.format(self.id)) != 1:
            self._log(f'Ad: Opening Output1 Signal...')
            self.daq.setInt('/{}/imps/0/output/on'.format(self.id), 1)
            time.sleep(5)
        # Ensure Signal Add Disabled
        if self.daq.getInt('/{}/sigouts/0/add'.format(self.id)) != 0:
            self._log(f'Ad: Closing Signal Add...')
            self.daq.setInt('/{}/sigouts/0/add'.format(self.id), 0)
            time.sleep(5)
        # Ensure IA Enabled
        if self.daq.getInt('/{}/imps/0/enable'.format(self.id)) != 1:
            self._log(f'Ad: Opening IA...')
            self.daq.setInt('/{}/imps/0/enable'.format(self.id), 1)
            time.sleep(3)
        # Ensure Bias ON ans set to 0V
        if self.daq.getInt('/{}/imps/0/bias/enable'.format(self.id)) == 0:
            self.daq.setInt('/{}/imps/0/bias/enable'.format(self.id), 1)
            time.sleep(3)
        if self.daq.getDouble('/{}/imps/0/bias/value'.format(self.id)) !=0:
            self.daq.setDouble('/{}/imps/0/bias/value'.format(self.id), 0)
            time.sleep(2)
        # Read Current AC Amplitude
        self.tempdV = self.daq.getDouble('/{}/imps/0/output/amplitude'.format(self.id))
        # Read Current AC Frequency
        self.tempfreq = self.daq.getDouble('/{}/imps/0/freq'.format(self.id))
        # Set Target Bias Voltage
        #self.daq.setInt('/{}/imps/0/bias/enable'.format(self.id), 1)
        #time.sleep(1)
        self.daq.setDouble('/{}/imps/0/bias/value'.format(self.id), round(Vbias,self._roundBs))
        # Read RangeMode
        self.temprangemode = self.daq.getInt('/{}/imps/0/auto/inputrange'.format(self.id))
        # Read Range
        self.temprange = self.daq.getDouble('/{}/imps/0/current/range'.format(self.id))
        # Set Range
        if IfAutoRange:
            if self.temprangemode != 1:
                self.daq.setInt('/{}/imps/0/auto/inputrange'.format(self.id), 1)
        else:
            self.daq.setInt('/{}/imps/0/auto/inputrange'.format(self.id), 0)
            self.daq.setDouble('/{}/imps/0/current/range'.format(self.id), ManualRange)
    def measure_Ad_main(
        self, Fstart:int=50000, Fend:int=1000000, Points:int=100, Vbias:float=-2, DeltaV:float=0.1, IfAutoRange:bool=True, ManualRange:float=0.000100
    ):
        sweeper = self.daq.sweep()
        # Sweeper Device
        sweeper.set('device', '{}'.format(self.id))
        # Once
        sweeper.set('endless', 0)
        # Advanced Filtermode
        sweeper.set('filtermode', 1)
        # Sweep Frequency
        sweeper.set('gridnode', '/{}/oscs/0/freq'.format(self.id))
        sweeper.set('historylength', 100)
        # Sweep Points
        sweeper.set('samplecount', round(Points))
        # Linear mapping=0, log mapping=1
        sweeper.set('xmapping', 1)
        # Average Times Per Point
        sweeper.set('averaging/sample', 20)
        sweeper.set('averaging/tc', 15.00000000)
        sweeper.set('averaging/time', 0.10000000)
        # Sweep Freq Start
        sweeper.set('start', round(Fstart,self._roundBs))
        # Sweep Freq End
        sweeper.set('stop', round(Fend,self._roundBs))
        sweeper.set('settling/inaccuracy', 0.01000000)
        sweeper.set('averaging/sample', 20)
        sweeper.set('averaging/tc', 15.00000000)
        sweeper.set('averaging/time', 0.10000000)
        sweeper.set('bandwidth', 10.00000000)
        sweeper.set('maxbandwidth', 100.00000000)
        sweeper.set('bandwidthoverlap', 1)
        sweeper.set('omegasuppression', 80.00000000)
        sweeper.set('order', 8)
        sweeper.subscribe('/{}/imps/0/sample'.format(self.id))
        sweeper.subscribe('/{}/demods/0/sample'.format(self.id))
        sweeper.execute()
        # To read the acquired data from the module, use a
        # while loop like the one below. This will allow the
        # data to be plotted while the measurement is ongoing.
        # Note that any device nodes that enable the streaming
        # of data to be acquired, must be set before the while loop.
        result = 0
        self._log(f'Start Ad Measure')
        while sweeper.progress() < 1.0 and not sweeper.finished():
            # Update Progress
            self._set_progress(float(sweeper.progress()[0]),'Ad')
            time.sleep(1)
            result = sweeper.read()
        self._log(f'End Ad Measure')
        sweeper.finish()
        sweeper.unsubscribe('*')
        # Frequency
        f = result['{}'.format(self.id)]['imps']['0']['sample'][0][0]['grid']
        # Capacitance
        c = result['{}'.format(self.id)]['imps']['0']['sample'][0][0]['param1']
        # Resistance
        r = result['{}'.format(self.id)]['imps']['0']['sample'][0][0]['param0']
        # Demod R
        i = result['{}'.format(self.id)]['demods']['0']['sample'][0][0]['r']
        return {
            "raw_data": {"f": f, "c": c, "r": r, "i": i, "x": f, "y": c, "y2": i},
            "save_type": {
                "Once_format": [
                    {"filename": "Ad_data.txt", "data": np.column_stack((f, c, r))}
                ],
                "DLTS_format": [
                    {"filename": "Ad_freq_c.transdata", "fixed_x": f, "changed_y": c},
                    {"filename": "Ad_freq_r.transdata", "fixed_x": f, "changed_y": r}
                ],
                "Numpy_Dict_format": [
                    {"filename": "Ad.npy", "data": {"f": f, "c": c, "r": r, "i": i}}
                ]
            },
            "plot_type": {
                'xscale':'log',
                'yscale':'linear',
                'x_scaling':1.0,
                'xlabel':'Frequency [Hz]',
                'y_scaling':1e12,
                'ylabel':'Capacitance [pF]',
                'y2_scaling':1e6,
                'y2label':'Current [uA]',
                'ignore_points':False
            }
        }
    def measure_Ad_post_set(self, **kwargs):
        # Set Bias Voltage to 0V
        self.daq.setDouble('/{}/imps/0/bias/value'.format(self.id), 0.00000000)
        #self.daq.setInt('/{}/imps/0/bias/enable'.format(self.id), 0)
        # Set Previous AC Frequency
        self.daq.setDouble('/{}/imps/0/freq'.format(self.id), round(self.tempfreq,self._roundBs))
        # Set Previous AC Amplitude
        self.daq.setDouble('/{}/imps/0/output/amplitude'.format(self.id), round(self.tempdV,self._roundBs))
        # Set Range
        self.daq.setInt('/{}/imps/0/auto/inputrange'.format(self.id), self.temprangemode)
        if self.temprangemode != 1:
            self.daq.setDouble('/{}/imps/0/current/range'.format(self.id), self.temprange)

    # IV
    def measure_IV_pre_set(self, **kwargs):
        IfAutoRange = kwargs['IfAutoRange']
        ManualRange = kwargs['ManualRange']
        Vaux2 = kwargs['Vaux2']
        DataRateMode = kwargs['DataRateMode']
        steptime = kwargs['steptime']
        # progress clear
        self._set_progress(0,'IV')
        # Ensure Output1 Signal ON
        if self.daq.getInt('/{}/imps/0/output/on'.format(self.id)) != 1:
            self._log(f'IV: Opening Output1 Signal...')
            self.daq.setInt('/{}/imps/0/output/on'.format(self.id), 1)
            time.sleep(5)
        # Ensure Signal Add Disabled
        if self.daq.getInt('/{}/sigouts/0/add'.format(self.id)) != 0:
            self._log(f'IV: Closing Signal Add...')
            self.daq.setInt('/{}/sigouts/0/add'.format(self.id), 0)
            time.sleep(5)
        # Ensure IA Enabled
        if self.daq.getInt('/{}/imps/0/enable'.format(self.id)) != 1:
            self._log(f'IV: Opening IA...')
            self.daq.setInt('/{}/imps/0/enable'.format(self.id), 1)
            time.sleep(3)
        # Ensure Bias ON and set to 0V
        if self.daq.getInt('/{}/imps/0/bias/enable'.format(self.id)) == 0:
            self.daq.setInt('/{}/imps/0/bias/enable'.format(self.id), 1)
            time.sleep(3)
        if self.daq.getDouble('/{}/imps/0/bias/value'.format(self.id)) !=0:
            self.daq.setDouble('/{}/imps/0/bias/value'.format(self.id), 0)
            time.sleep(2)
        '''
        # Read Current AC Frequency
        self.tempfreq = self.daq.getDouble('/{}/imps/0/freq'.format(self.id))
        # Set AC Frequency = 0
        self.daq.setDouble('/{}/imps/0/freq'.format(self.id), 0.00000000)
        '''
        # Read Current AC Amplitude
        self.tempdV = self.daq.getDouble('/{}/imps/0/output/amplitude'.format(self.id))
        # Read Current AC Frequency
        self.tempfreq = self.daq.getDouble('/{}/imps/0/freq'.format(self.id))
        # set 0 AC Amplitude
        self.daq.setDouble('/{}/imps/0/output/amplitude'.format(self.id), 0)
        # set 0 AC Frequency
        self.daq.setDouble('/{}/imps/0/freq'.format(self.id), 0)
        
        # Read RangeMode
        self.temprangemode = self.daq.getInt('/{}/imps/0/auto/inputrange'.format(self.id))
        # Read Range
        self.temprange = self.daq.getDouble('/{}/imps/0/current/range'.format(self.id))
        # Set Range
        if IfAutoRange:
            if self.temprangemode != 1:
                self.daq.setInt('/{}/imps/0/auto/inputrange'.format(self.id), 1)
        else:
            self.daq.setInt('/{}/imps/0/auto/inputrange'.format(self.id), 0)
            self.daq.setDouble('/{}/imps/0/current/range'.format(self.id), ManualRange)

        # 设定Aux2手动输出
        self.daq.setInt('/{}/auxouts/1/outputselect'.format(self.id), -1)
        # 设定Aux2输出电压
        self.daq.setDouble('/{}/auxouts/1/offset'.format(self.id), Vaux2)

        # 示波器设置
        # 激活通道1和2
        self.daq.setInt('/{}/scopes/0/channel'.format(self.id), 3)
        # 通道1选择为电流1输入
        self.daq.setInt('/{}/scopes/0/channels/0/inputselect'.format(self.id), 1)
        # 通道2选择为信号输出1
        self.daq.setInt('/{}/scopes/0/channels/1/inputselect'.format(self.id), 12)
        
        # 示波器采样率模式12=14.6k
        real_rate = 60e6/2**np.arange(17)[DataRateMode]
        self.daq.setInt('/{}/scopes/0/time'.format(self.id), DataRateMode)
        # 采样点数
        daqpoints = int(steptime*real_rate)
        self.daq.setInt('/{}/scopes/0/length'.format(self.id), daqpoints)

        # 关闭示波器采集触发
        self.daq.setInt('/{}/scopes/0/trigenable'.format(self.id), 0)
        # 参考0，即从0s开始记录信号
        self.daq.setDouble('/{}/scopes/0/trigreference'.format(self.id), 0.00000000)
        # 信号延迟0s
        self.daq.setDouble('/{}/scopes/0/trigdelay'.format(self.id), 0.00000000)
        # 开启示波器采集，可以在绘图模块中引入
        self.daq.setInt('/{}/scopes/0/stream/enables/0'.format(self.id), 1)
        self.daq.setInt('/{}/scopes/0/stream/enables/1'.format(self.id), 1)
        # 示波器采集频率默认107k=9
        self.daq.setInt('/{}/scopes/0/stream/rate'.format(self.id), 9)
        time.sleep(3)
    def measure_IV_main(
        self, Vstart:float=-3, Vend:float=3, Points:int=40, Vaux2:float=0.1, DataRateMode:int=12, steptime:float=1, stopcurrent:float=0.005, IfAutoRange:bool=True, ManualRange:float=0.010000
    ):
        time_limit = 60
        Task_something_wrong = False
        while True:
            if Task_something_wrong:
                Task_something_wrong = False
            IfAutoRange = True
            scope = self.daq.scopeModule()
            # 横轴时间
            scope.set('mode', 1)
            # 不启用平均
            scope.set('averager/enable', 0)
            # 启用均一权重
            scope.set('averager/method', 1)
            # 示波器采样率模式12=14.6k
            real_rate = 60e6/2**np.arange(17)[DataRateMode]
            daqpoints = int(steptime*real_rate)
            # 开始采集
            self._log(f'Start IV Measure')
            rawdata = []
            v_ramp_list = np.linspace(Vstart,Vend,Points)
            real_i_list = []
            real_v_list = []
            # 对每个偏置电压测量电流
            for i,v_ramp in enumerate(v_ramp_list):
                # 设置偏置电压
                self.daq.setDouble('/{}/imps/0/bias/value'.format(self.id), v_ramp)
                # 采集一次
                scope.unsubscribe('*')
                scope.subscribe('/{}/scopes/0/wave'.format(self.id))
                scope.execute()
                self.daq.setInt('/{}/scopes/0/single'.format(self.id), 1)
                self.daq.setInt('/{}/scopes/0/enable'.format(self.id), 1)
                get_data_flag = False
                result = []
                temp_time0 = time.time()
                # 每隔0.5s尝试cope.read()获取数据
                while not get_data_flag:
                    time.sleep(0.3)
                    tempresult = scope.read()
                    try:
                        tempdatalen = len(tempresult[self.id]['scopes']['0']['wave'])
                    except:
                        tempdatalen = 0
                    if tempdatalen != 0:
                        # 采集结束
                        self.daq.setInt('/{}/scopes/0/enable'.format(self.id), 0)
                        scope.finish()
                        scope.unsubscribe('*')
                        get_data_flag = True
                        # Update Progress
                        self._set_progress((i+1)/len(v_ramp_list),'IV')
                    else:
                        if time.time()-temp_time0 >= time_limit:
                            Task_something_wrong = True
                            self._log('Something went wrong, restart current task...')
                            # 采集结束
                            self.daq.setInt('/{}/scopes/0/enable'.format(self.id), 0)
                            scope.finish()
                            scope.unsubscribe('*')
                            break
                if not Task_something_wrong:
                    i_stream = tempresult[self.id]['scopes']['0']['wave'][0][0]['wave'][0]
                    v_stream = tempresult[self.id]['scopes']['0']['wave'][0][0]['wave'][1]
                    rawdata.append({'i_stream':i_stream,'v_stream':v_stream})
                    start_idx = int(len(i_stream)*0.9)
                    end_idx = -1
                    real_i = np.average(i_stream[start_idx:end_idx])
                    real_v = np.average(v_stream[start_idx:end_idx])
                    real_i_list.append(real_i)
                    real_v_list.append(real_v)
                    if np.abs(real_i) >= stopcurrent:
                        break
                else:
                    break
            if not Task_something_wrong:
                self._log(f'End IV Measure')
                break
            else:
                time.sleep(2)
        # time
        t = np.linspace(0, (daqpoints-1)/real_rate, daqpoints)
        i = np.array(real_i_list)
        v = np.array(real_v_list)
        return {
            "raw_data": {"t": t, "i": i, "v": v, "x": v, "y": i, "y2": i},
            "save_type": {
                "Once_format": [
                    {"filename": "IV_data.txt", "data": np.column_stack((v, i))}
                ],
                "DLTS_format": [
                    {"filename": "IV.transdata", "fixed_x": i, "changed_y": v}
                ],
                "Numpy_Dict_format": [
                    {"filename": "IV.npy", "data": {"t": t, "i": i, "v": v}},
                ]
            },
            "plot_type": {
                'xscale':'linear',
                'yscale':'linear',
                'x_scaling':1.0,
                'xlabel':'Voltage [V]',
                'y_scaling':1e6,
                'ylabel':'Current [uA]',
                'y2_scaling':1e6,
                'y2label':'Current [uA]',
                'ignore_points':False
            }
        }
    def measure_IV_post_set(self, **kwargs):
        # 设定Aux2输出电压为0
        self.daq.setDouble('/{}/auxouts/1/offset'.format(self.id), 0)
        # Set Bias Voltage to 0V
        self.daq.setDouble('/{}/imps/0/bias/value'.format(self.id), 0.00000000)
        # Set Previous Frequency
        self.daq.setDouble('/{}/imps/0/freq'.format(self.id), round(self.tempfreq,self._roundBs))
        # Set Previous AC Amplitude
        self.daq.setDouble('/{}/imps/0/output/amplitude'.format(self.id), round(self.tempdV,self._roundBs))
        # Set Range
        self.daq.setInt('/{}/imps/0/auto/inputrange'.format(self.id), self.temprangemode)
        if self.temprangemode != 1:
            self.daq.setDouble('/{}/imps/0/current/range'.format(self.id), self.temprange)

    # TC
    def measure_TC_pre_set(self, **kwargs):
        DeltaV = kwargs['DeltaV']
        freq = kwargs['freq']
        order = kwargs['order']
        TimeConstant = kwargs['TimeConstant']
        DataRate = kwargs['DataRate']
        Tm = kwargs['Tm']
        Tm2 = kwargs['Tm2']
        Tf = kwargs['Tf']
        Vm = kwargs['Vm']
        Vf = kwargs['Vf']
        ManualRange = kwargs['ManualRange']
        IfAutoRange = kwargs['IfAutoRange']
        # progress clear
        self._set_progress(0,'TC')
        # Ensure Output1 Signal ON
        if self.daq.getInt('/{}/imps/0/output/on'.format(self.id)) != 1:
            self._log(f'TC: Opening Output1 Signal...')
            self.daq.setInt('/{}/imps/0/output/on'.format(self.id), 1)
            time.sleep(5)
        # Ensure IA Enabled
        if self.daq.getInt('/{}/imps/0/enable'.format(self.id)) != 1:
            self._log(f'TC: Opening IA...')
            self.daq.setInt('/{}/imps/0/enable'.format(self.id), 1)
            time.sleep(3)
        # Ensure Bias ON and set to 0V
        if self.daq.getInt('/{}/imps/0/bias/enable'.format(self.id)) == 0:
            self.daq.setInt('/{}/imps/0/bias/enable'.format(self.id), 1)
            time.sleep(3)
        if self.daq.getDouble('/{}/imps/0/bias/value'.format(self.id)) !=0:
            self.daq.setDouble('/{}/imps/0/bias/value'.format(self.id), 0)
            time.sleep(2)
        # Read Current AC Amplitude
        self.tempdV = self.daq.getDouble('/{}/imps/0/output/amplitude'.format(self.id))
        # Read Current AC Frequency
        self.tempfreq = self.daq.getDouble('/{}/imps/0/freq'.format(self.id))
        # set Target AC Amplitude
        self.daq.setDouble('/{}/imps/0/output/amplitude'.format(self.id), round(DeltaV,self._roundBs))
        # set Target AC Frequency
        self.daq.setDouble('/{}/imps/0/freq'.format(self.id), round(freq,self._roundBs))
        # Manual bw
        self.daq.setInt('/{}/imps/0/auto/bw'.format(self.id), 0)
        # set bw
        #self.daq.setDouble('/{}/imps/0/maxbandwidth'.format(self.id), round(maxbandwidth,self._roundBs))
        # Filter Order
        self.daq.setInt('/{}/imps/0/demod/order'.format(self.id), order)
        self.daq.setInt('/{}/imps/0/demod/sinc'.format(self.id), 1)
        # timeconstant
        self.daq.setDouble('/{}/imps/0/demod/timeconstant'.format(self.id), round(TimeConstant,self._roundBs))
        # DataRate
        self.daq.setDouble('/{}/imps/0/demod/rate'.format(self.id), round(DataRate,self._roundBs))
        # Ensure Signal Add Disabled
        if self.daq.getInt('/{}/sigouts/0/add'.format(self.id))==1:
            self.daq.setInt('/{}/sigouts/0/add'.format(self.id), 0)
            time.sleep(5)
        # Set TU
        self.daq.setInt('/{}/tu/thresholds/0/input'.format(self.id), 59)
        self.daq.setInt('/{}/tu/thresholds/0/inputchannel'.format(self.id), 0)
        self.daq.setInt('/{}/tu/logicunits/0/inputs/0/not'.format(self.id), 1)
        self.daq.setInt('/{}/tu/logicunits/0/inputs/0/channel'.format(self.id), 0)
        self.daq.setInt('/{}/tu/logicunits/0/ops/0/value'.format(self.id), 0)
        # Actual Tm = (Tm+Tm2)*1.01
        self.daq.setDouble('/{}/tu/thresholds/0/deactivationtime'.format(self.id), round((Tm+Tm2)*1.01,8))
        # Actual Tf = Tf*1.01
        self.daq.setDouble('/{}/tu/thresholds/0/activationtime'.format(self.id), round(Tf*1.01,8))
        # Set TU
        #self.daq.setInt('/{}/tu/thresholds/1/input'.format(self.id), 59)
        #self.daq.setInt('/{}/tu/thresholds/1/inputchannel'.format(self.id), 0)
        #self.daq.setInt('/{}/tu/logicunits/1/inputs/0/not'.format(self.id), 1)
        #self.daq.setDouble('/{}/tu/thresholds/1/activationtime'.format(self.id), 0)
        #self.daq.setDouble('/{}/tu/thresholds/1/deactivationtime'.format(self.id), 0)
        # Set Aux1
        self.daq.setInt('/{}/auxouts/0/outputselect'.format(self.id), 13)
        self.daq.setInt('/{}/auxouts/0/demodselect'.format(self.id), 0)
        self.daq.setDouble('/{}/auxouts/0/scale'.format(self.id), round(Vf-Vm,8))
        self.daq.setDouble('/{}/auxouts/0/offset'.format(self.id), round(Vm,8))
        # Enable Signal Add
        self.daq.setInt('/{}/sigouts/0/add'.format(self.id), 1)
        # Read RangeMode
        self.temprangemode = self.daq.getInt('/{}/imps/0/auto/inputrange'.format(self.id))
        # Read Range
        self.temprange = self.daq.getDouble('/{}/imps/0/current/range'.format(self.id))
        # Set Range
        if IfAutoRange:
            if self.temprangemode != 1:
                self.daq.setInt('/{}/imps/0/auto/inputrange'.format(self.id), 1)
        else:
            self.daq.setInt('/{}/imps/0/auto/inputrange'.format(self.id), 0)
            self.daq.setDouble('/{}/imps/0/current/range'.format(self.id), ManualRange)
        time.sleep(3)
    def measure_TC_main(
        self, Vm:float=-3, Tm:float=2e-2, Tm2:float=0.0, Vf:float=-0.5, Tf:float=6e-2, freq:int=100000, DeltaV:float=0.1,
        AverageTimes:int=100, TimeConstant:float=2.4e-6, DataRate:int=107000, order:int=8, maxbandwidth:float=100,
        IfAutoRange:bool=True, ManualRange:float=0.000100,
        IfLogScaleReSample:bool=False, LogScaleReSamplePoints:int=0
    ):
        daq_module = self.daq.dataAcquisitionModule()
        daq_module.set('device', '{}'.format(self.id))
        daq_module.set('endless', 0)
        # Once
        daq_module.set('count', 1)
        # AverageTimes
        daq_module.set('grid/repetitions', round(AverageTimes))
        # Sampling points is obtained according to the Data rate.
        # For example, if the sampling time is 10ms and the sampling rate is 107k, the number of sampling points is 107k*10ms=1070
        #if ifFillTrans:
        #    daq_module.set('grid/cols', round(Tf*DataRate))
        #else:
        #    daq_module.set('grid/cols', round(Tm*DataRate))
        
        # get all data in one period
        daq_module.set('grid/cols', round((Tm*1.01+Tf*1.00)*DataRate))
        
        # Align sampling time mode.
        daq_module.set('grid/mode', 4)
        daq_module.set('grid/rows', 1)
        
        # Set Hardware trigger, from trigger input 1, make sure the front panel auxiliary output 2 is connected to the rear panel trigger input 1
        #daq_module.set('type', 6)
        #daq_module.set('triggernode', '/{}/demods/0/sample.TrigIn1'.format(self.id))
        # Set AuxIn0 as trigger
        daq_module.set('type', 1)
        #daq_module.set('triggernode', '/{}/auxins/0/sample.AuxIn0'.format(self.id))
        daq_module.set('triggernode', '/{}/demods/0/sample.AuxIn0'.format(self.id))
        
        # Set trigger edge
        #if ifFillTrans:
        #    daq_module.set('edge', 0)
        #else:
        #    daq_module.set('edge', 2)
        
        if Vm>Vf:
            # up edge
            daq_module.set('edge', 1)
        else:
            # down
            daq_module.set('edge', 2)

        # Set trigger level
        daq_module.set('level', (Vm+Vf)/2)
        
        daq_module.set('holdoff/time', 0.0)
        daq_module.set('delay', 0.0)
        self.daq.sync()
        # Subscribe to the voltage value of auxiliary input 1,
        # demodulator R value (current value at 0 frequency),
        # parallel resistance value (Param0),
        # parallel capacitance value (Param1)
        daq_module.subscribe('/{}/demods/0/sample.AuxIn0.avg'.format(self.id))
        daq_module.subscribe('/{}/demods/0/sample.R.avg'.format(self.id))
        daq_module.subscribe('/{}/imps/0/sample.Param0.avg'.format(self.id))
        daq_module.subscribe('/{}/imps/0/sample.Param1.avg'.format(self.id))
        daq_module.execute()
        # To read the acquired data from the module, use a
        # while loop like the one below. This will allow the
        # data to be plotted while the measurement is ongoing.
        # Note that any device nodes that enable the streaming
        # of data to be acquired, must be set before the while loop.
        result = 0
        self._log(f'Start TC Measure')
        while daq_module.progress() < 1.0 and not daq_module.finished():
            # Update Progress
            self._set_progress(float(daq_module.progress()[0]),'TC')
            time.sleep(1)
            result = daq_module.read()
        self._log(f'End TC Measure')
        daq_module.finish()
        daq_module.unsubscribe('*')

        self.tempresult = result
        # time
        to = result['{}'.format(self.id)]['imps']['0']['sample.param1.avg'][0]['timestamp'][0]
        t = np.linspace(0,(to[-1]-to[0])/6e7, len(to))
        tm_index0 = 0
        tm_index1 = np.searchsorted(t, Tm)
        tf_index0 = np.searchsorted(t, Tm*1.01)
        tf_index1 = -1
        # Parallel Capacitance
        c = result['{}'.format(self.id)]['imps']['0']['sample.param1.avg'][0]['value'][0]
        # Parallel Resistance
        r = result['{}'.format(self.id)]['imps']['0']['sample.param0.avg'][0]['value'][0]
        # Demods R，AC Current
        i = result['{}'.format(self.id)]['demods']['0']['sample.r.avg'][0]['value'][0]
        # AUX1, Voltage
        v = result['{}'.format(self.id)]['demods']['0']['sample.auxin0.avg'][0]['value'][0]

        t_f = t[tf_index0:tf_index1]
        if len(t_f)<=1:
            t_f = -1
            self._log('tf daq failed')
        else:
            t_f = t_f - t_f[0]
        c_f = c[tf_index0:tf_index1]
        r_f = r[tf_index0:tf_index1]
        i_f = i[tf_index0:tf_index1]
        v_f = v[tf_index0:tf_index1]
        
        t_m = t[tm_index0:tm_index1]
        t_m = t_m - t_m[0]
        c_m = c[tm_index0:tm_index1]
        r_m = r[tm_index0:tm_index1]
        i_m = i[tm_index0:tm_index1]
        v_m = v[tm_index0:tm_index1]

        if IfLogScaleReSample:
            if LogScaleReSamplePoints<=0:
                tm_indices = ReSampleFromTimeArray(t_m,len(t_m))
                t_m = t_m[tm_indices]
                c_m = c_m[tm_indices]
                r_m = r_m[tm_indices]
                i_m = i_m[tm_indices]
                v_m = v_m[tm_indices]
                tf_indices = ReSampleFromTimeArray(t_f,len(t_f))
                t_f = t_f[tf_indices]
                c_f = c_f[tf_indices]
                r_f = r_f[tf_indices]
                i_f = i_f[tf_indices]
                v_f = v_f[tf_indices]
            else:
                tm_indices = ReSampleFromTimeArray(t_m,LogScaleReSamplePoints)
                t_m = t_m[tm_indices]
                c_m = c_m[tm_indices]
                r_m = r_m[tm_indices]
                i_m = i_m[tm_indices]
                v_m = v_m[tm_indices]
                tf_indices = ReSampleFromTimeArray(t_f,LogScaleReSamplePoints)
                t_f = t_f[tf_indices]
                c_f = c_f[tf_indices]
                r_f = r_f[tf_indices]
                i_f = i_f[tf_indices]
                v_f = v_f[tf_indices]

        
        return {
            "raw_data": {"t": t_m, "c": c_m, "r": r_m, "i": i_m, "v": v_m, "t_f": t_f, "c_f": c_f, "r_f": r_f,
                         "i_f": i_f, "v_f": v_f, 'x':t_m, 'y':c_m, 'y2':i_m},
            "save_type": {
                "Once_format": [
                    {"filename": "TC_data_m.txt", "data": np.column_stack((t_m, c_m, r_m, i_m, v_m))},
                    {"filename": "TC_data_f.txt", "data": np.column_stack((t_f, c_f, r_f, i_f, v_f))}
                ],
                "DLTS_format": [
                    {"filename": "TC_m.transdata", "fixed_x": t_m, "changed_y": c_m},
                    {"filename": "TC_f.transdata", "fixed_x": t_f, "changed_y": c_f}
                ],
                "Numpy_Dict_format": [
                    {"filename": "TC.npy", "data": {"t": t_m, "c": c_m, "r": r_m, "i": i_m, "v": v_m,
                                                    "t_f": t_f, "c_f": c_f, "r_f": r_f,"i_f": i_f, "v_f": v_f}}
                ]
            },
            "plot_type": {
                'xscale':'linear',
                'yscale':'linear',
                'x_scaling':1.0,
                'xlabel':'Time [s]',
                'y_scaling':1e12,
                'ylabel':'Capacitance [pF]',
                'y2_scaling':1e6,
                'y2label':'Current [uA]',
                'ignore_points':True
            }
        }
    def measure_TC_post_set(self, **kwargs):
        # Close Signal Add
        self.daq.setInt('/{}/sigouts/0/add'.format(self.id), 0)
        time.sleep(2)
        # Set Previous AC Frequency
        self.daq.setDouble('/{}/imps/0/freq'.format(self.id), round(self.tempfreq,self._roundBs))
        # Set Previous AC Amplitude
        self.daq.setDouble('/{}/imps/0/output/amplitude'.format(self.id), round(self.tempdV,self._roundBs))
        # Set Range
        self.daq.setInt('/{}/imps/0/auto/inputrange'.format(self.id), self.temprangemode)
        if self.temprangemode != 1:
            self.daq.setDouble('/{}/imps/0/current/range'.format(self.id), self.temprange)

    # STC
    def measure_STC_pre_set(self, **kwargs):
        DeltaV = kwargs['DeltaV']
        freq = kwargs['freq']
        order = kwargs['order']
        TimeConstant = kwargs['TimeConstant']
        DataRate = kwargs['DataRate']
        Tm = kwargs['Tm']
        Tm2 = kwargs['Tm2']
        Tf = kwargs['Tf']
        Vm = kwargs['Vm']
        Vf = kwargs['Vf']
        Ts = kwargs['Ts']
        Td = kwargs['Td']
        Vs = kwargs['Vs']
        Vr = kwargs['Vr']
        ManualRange = kwargs['ManualRange']
        IfAutoRange = kwargs['IfAutoRange']
        # progress clear
        self._set_progress(0,'STC')
        # Ensure Output1 Signal ON
        if self.daq.getInt('/{}/imps/0/output/on'.format(self.id)) != 1:
            self._log(f'STC: Opening Output1 Signal...')
            self.daq.setInt('/{}/imps/0/output/on'.format(self.id), 1)
            time.sleep(5)
        # Ensure IA Enabled
        if self.daq.getInt('/{}/imps/0/enable'.format(self.id)) != 1:
            self._log(f'STC: Opening IA...')
            self.daq.setInt('/{}/imps/0/enable'.format(self.id), 1)
            time.sleep(3)
        # Ensure Bias ON and set to 0V
        if self.daq.getInt('/{}/imps/0/bias/enable'.format(self.id)) == 0:
            self.daq.setInt('/{}/imps/0/bias/enable'.format(self.id), 1)
            time.sleep(3)
        if self.daq.getDouble('/{}/imps/0/bias/value'.format(self.id)) !=0:
            self.daq.setDouble('/{}/imps/0/bias/value'.format(self.id), 0)
            time.sleep(2)
        # Read Current AC Amplitude
        self.tempdV = self.daq.getDouble('/{}/imps/0/output/amplitude'.format(self.id))
        # Read Current AC Frequency
        self.tempfreq = self.daq.getDouble('/{}/imps/0/freq'.format(self.id))
        # set Target AC Amplitude
        self.daq.setDouble('/{}/imps/0/output/amplitude'.format(self.id), round(DeltaV,self._roundBs))
        # set Target AC Frequency
        self.daq.setDouble('/{}/imps/0/freq'.format(self.id), round(freq,self._roundBs))
        # Manual bw
        self.daq.setInt('/{}/imps/0/auto/bw'.format(self.id), 0)
        # set bw
        #self.daq.setDouble('/{}/imps/0/maxbandwidth'.format(self.id), round(maxbandwidth,self._roundBs))
        # Filter Order
        self.daq.setInt('/{}/imps/0/demod/order'.format(self.id), order)
        self.daq.setInt('/{}/imps/0/demod/sinc'.format(self.id), 1)
        # timeconstant
        self.daq.setDouble('/{}/imps/0/demod/timeconstant'.format(self.id), round(TimeConstant,self._roundBs))
        # DataRate
        self.daq.setDouble('/{}/imps/0/demod/rate'.format(self.id), round(DataRate,self._roundBs))
        # Ensure Signal Add Disabled
        if self.daq.getInt('/{}/sigouts/0/add'.format(self.id))==1:
            self.daq.setInt('/{}/sigouts/0/add'.format(self.id), 0)
            time.sleep(5)
        # Set TU
        # 1,2,3,4阈值输出都是基于阈值判断输出
        self.daq.setInt('/{}/tu/thresholds/0/input'.format(self.id), 59)
        self.daq.setInt('/{}/tu/thresholds/1/input'.format(self.id), 59)
        self.daq.setInt('/{}/tu/thresholds/2/input'.format(self.id), 59)
        self.daq.setInt('/{}/tu/thresholds/3/input'.format(self.id), 59)
        # 对应逻辑通道
        self.daq.setInt('/{}/tu/thresholds/0/inputchannel'.format(self.id), 0)
        self.daq.setInt('/{}/tu/thresholds/1/inputchannel'.format(self.id), 1)
        self.daq.setInt('/{}/tu/thresholds/2/inputchannel'.format(self.id), 2)
        self.daq.setInt('/{}/tu/thresholds/3/inputchannel'.format(self.id), 3)

        # 逻辑a输入
        self.daq.setInt('/{}/tu/logicunits/0/inputs/0/channel'.format(self.id), 2)#TU3
        self.daq.setInt('/{}/tu/logicunits/1/inputs/0/channel'.format(self.id), 1)#TU2
        self.daq.setInt('/{}/tu/logicunits/2/inputs/0/channel'.format(self.id), 1)#TU2
        self.daq.setInt('/{}/tu/logicunits/3/inputs/0/channel'.format(self.id), 1)#TU2
        # 逻辑a反
        self.daq.setInt('/{}/tu/logicunits/0/inputs/0/not'.format(self.id), 1)
        self.daq.setInt('/{}/tu/logicunits/1/inputs/0/not'.format(self.id), 1)
        self.daq.setInt('/{}/tu/logicunits/2/inputs/0/not'.format(self.id), 1)
        self.daq.setInt('/{}/tu/logicunits/3/inputs/0/not'.format(self.id), 1)
        # 逻辑a操作
        self.daq.setInt('/{}/tu/logicunits/0/ops/0/value'.format(self.id), 3)#异或
        self.daq.setInt('/{}/tu/logicunits/0/inputs/1/not'.format(self.id), 1)#反
        self.daq.setInt('/{}/tu/logicunits/0/inputs/1/channel'.format(self.id), 3)#TU4
        self.daq.setInt('/{}/tu/logicunits/1/ops/0/value'.format(self.id), 0)#None
        self.daq.setInt('/{}/tu/logicunits/2/ops/0/value'.format(self.id), 0)#None
        self.daq.setInt('/{}/tu/logicunits/3/ops/0/value'.format(self.id), 0)#None
        '''
        # 保持宽度
        self.daq.setDouble('/{}/tu/logicunits/0/pulsewidth'.format(self.id), 0.00000000)
        self.daq.setDouble('/{}/tu/logicunits/1/pulsewidth'.format(self.id), 0.00000000)
        self.daq.setDouble('/{}/tu/logicunits/2/pulsewidth'.format(self.id), Ts+Tf*1.01)
        self.daq.setDouble('/{}/tu/logicunits/3/pulsewidth'.format(self.id), Ts+Td)

        #Enable&Disable Setup
        self.daq.setDouble('/{}/tu/thresholds/0/activationtime'.format(self.id), 0.00000000)
        self.daq.setDouble('/{}/tu/thresholds/0/deactivationtime'.format(self.id), 0.00000000)
        self.daq.setDouble('/{}/tu/thresholds/1/activationtime'.format(self.id), Ts)
        self.daq.setDouble('/{}/tu/thresholds/1/deactivationtime'.format(self.id), (Tf+Tm+Tm2)*1.01)
        self.daq.setDouble('/{}/tu/thresholds/2/activationtime'.format(self.id), 0.00000000)
        self.daq.setDouble('/{}/tu/thresholds/2/deactivationtime'.format(self.id), 0.00000000)
        self.daq.setDouble('/{}/tu/thresholds/3/activationtime'.format(self.id), 0.00000000)
        self.daq.setDouble('/{}/tu/thresholds/3/deactivationtime'.format(self.id), 0.00000000)
        '''
        # 保持宽度
        self.daq.setDouble('/{}/tu/logicunits/0/pulsewidth'.format(self.id), 0.00000000)
        self.daq.setDouble('/{}/tu/logicunits/1/pulsewidth'.format(self.id), 0.00000000)
        self.daq.setDouble('/{}/tu/logicunits/2/pulsewidth'.format(self.id), Ts+Td+Tf*1.01)
        self.daq.setDouble('/{}/tu/logicunits/3/pulsewidth'.format(self.id), Ts+Td)

        #Enable&Disable Setup
        self.daq.setDouble('/{}/tu/thresholds/0/activationtime'.format(self.id), 0.00000000)
        self.daq.setDouble('/{}/tu/thresholds/0/deactivationtime'.format(self.id), 0.00000000)
        self.daq.setDouble('/{}/tu/thresholds/1/activationtime'.format(self.id), Ts)
        if self.daq.getDouble('/{}/tu/logicunits/3/pulsewidth'.format(self.id))==self.daq.getDouble('/{}/tu/thresholds/1/activationtime'.format(self.id)):
            self._log('Td too small')
        self.daq.setDouble('/{}/tu/thresholds/1/deactivationtime'.format(self.id), Td+(Tf+Tm+Tm2)*1.01)
        self.daq.setDouble('/{}/tu/thresholds/2/activationtime'.format(self.id), 0.00000000)
        self.daq.setDouble('/{}/tu/thresholds/2/deactivationtime'.format(self.id), 0.00000000)
        self.daq.setDouble('/{}/tu/thresholds/3/activationtime'.format(self.id), 0.00000000)
        self.daq.setDouble('/{}/tu/thresholds/3/deactivationtime'.format(self.id), 0.00000000)
        # Set Aux
        self.daq.setInt('/{}/auxouts/0/outputselect'.format(self.id), 13)
        self.daq.setInt('/{}/auxouts/1/outputselect'.format(self.id), 13)
        self.daq.setInt('/{}/auxouts/0/demodselect'.format(self.id), 0)
        self.daq.setInt('/{}/auxouts/1/demodselect'.format(self.id), 1)
        self.daq.setDouble('/{}/auxouts/0/scale'.format(self.id), round(Vf-Vm,8))
        self.daq.setDouble('/{}/auxouts/0/offset'.format(self.id), round(Vm,8))
        self.daq.setDouble('/{}/auxouts/1/scale'.format(self.id), round(Vs-Vr,8))
        self.daq.setDouble('/{}/auxouts/1/offset'.format(self.id), round(Vr,8))
        
        # Enable Signal Add
        self.daq.setInt('/{}/sigouts/0/add'.format(self.id), 1)
        # Read RangeMode
        self.temprangemode = self.daq.getInt('/{}/imps/0/auto/inputrange'.format(self.id))
        # Read Range
        self.temprange = self.daq.getDouble('/{}/imps/0/current/range'.format(self.id))
        # Set Range
        if IfAutoRange:
            if self.temprangemode != 1:
                self.daq.setInt('/{}/imps/0/auto/inputrange'.format(self.id), 1)
        else:
            self.daq.setInt('/{}/imps/0/auto/inputrange'.format(self.id), 0)
            self.daq.setDouble('/{}/imps/0/current/range'.format(self.id), ManualRange)
        time.sleep(3)
    def measure_STC_main(
        self, Vm:float=0, Tm:float=2e-2, Tm2:float=2e-2, Vf:float=2.5, Tf:float=6e-2, Vs:float=5, Ts:float=0.1, Vr:float=0, Td:float=1e-3, freq:int=100000, DeltaV:float=0.1,
        AverageTimes:int=10, TimeConstant:float=2.4e-6, DataRate:int=107000, order:int=8, maxbandwidth:float=100,
        IfAutoRange:bool=True, ManualRange:float=0.000100
    ):
        daq_module = self.daq.dataAcquisitionModule()
        daq_module.set('device', '{}'.format(self.id))
        daq_module.set('endless', 0)
        # Once
        daq_module.set('count', 1)
        # AverageTimes
        daq_module.set('grid/repetitions', round(AverageTimes))
        # Sampling points is obtained according to the Data rate.
        # For example, if the sampling time is 10ms and the sampling rate is 107k, the number of sampling points is 107k*10ms=1070
        #if ifFillTrans:
        #    daq_module.set('grid/cols', round(Tf*DataRate))
        #else:
        #    daq_module.set('grid/cols', round(Tm*DataRate))

        real_Tf = self.daq.getDouble('/{}/tu/logicunits/2/pulsewidth'.format(self.id))-self.daq.getDouble('/{}/tu/logicunits/3/pulsewidth'.format(self.id))
        # get all data in one period
        daq_module.set('grid/cols', round((Tm*1.01+real_Tf)*DataRate))
        
        # Align sampling time mode.
        daq_module.set('grid/mode', 4)
        daq_module.set('grid/rows', 1)
        
        # Set Hardware trigger, from trigger input 1, make sure the front panel auxiliary output 2 is connected to the rear panel trigger input 1
        #daq_module.set('type', 6)
        #daq_module.set('triggernode', '/{}/demods/0/sample.TrigIn1'.format(self.id))
        # Set AuxIn0 as trigger
        daq_module.set('type', 1)
        #daq_module.set('triggernode', '/{}/auxins/0/sample.AuxIn0'.format(self.id))
        daq_module.set('triggernode', '/{}/demods/0/sample.AuxIn0'.format(self.id))
        
        # Set trigger edge
        #if ifFillTrans:
        #    daq_module.set('edge', 0)
        #else:
        #    daq_module.set('edge', 2)
        
        if Vm>Vf:
            # up edge
            daq_module.set('edge', 1)
        else:
            # down
            daq_module.set('edge', 2)

        # Set trigger level
        daq_module.set('level', (Vm+Vf)/2)
        
        daq_module.set('holdoff/time', 0.0)
        daq_module.set('delay', -real_Tf)
        self.daq.sync()
        # Subscribe to the voltage value of auxiliary input 1,
        # demodulator R value (current value at 0 frequency),
        # parallel resistance value (Param0),
        # parallel capacitance value (Param1)
        daq_module.subscribe('/{}/demods/0/sample.AuxIn0.avg'.format(self.id))
        daq_module.subscribe('/{}/demods/0/sample.R.avg'.format(self.id))
        daq_module.subscribe('/{}/imps/0/sample.Param0.avg'.format(self.id))
        daq_module.subscribe('/{}/imps/0/sample.Param1.avg'.format(self.id))
        daq_module.execute()
        # To read the acquired data from the module, use a
        # while loop like the one below. This will allow the
        # data to be plotted while the measurement is ongoing.
        # Note that any device nodes that enable the streaming
        # of data to be acquired, must be set before the while loop.
        result = 0
        self._log(f'Start STC Measure')
        while daq_module.progress() < 1.0 and not daq_module.finished():
            # Update Progress
            self._set_progress(float(daq_module.progress()[0]),'STC')
            time.sleep(1)
            result = daq_module.read()
        self._log(f'End STC Measure')
        daq_module.finish()
        daq_module.unsubscribe('*')
        
        # time
        to = result['{}'.format(self.id)]['imps']['0']['sample.param1.avg'][0]['timestamp'][0]
        t = np.linspace(0,(to[-1]-to[0])/6e7, len(to))
        tm_index0 = np.searchsorted(t, real_Tf)
        tm_index1 = np.searchsorted(t, real_Tf+Tm)
        tf_index0 = 0
        tf_index1 = np.searchsorted(t, Tf)
        # Parallel Capacitance
        c = result['{}'.format(self.id)]['imps']['0']['sample.param1.avg'][0]['value'][0]
        # Parallel Resistance
        r = result['{}'.format(self.id)]['imps']['0']['sample.param0.avg'][0]['value'][0]
        # Demods R，AC Current
        i = result['{}'.format(self.id)]['demods']['0']['sample.r.avg'][0]['value'][0]
        # AUX1, Voltage
        v = result['{}'.format(self.id)]['demods']['0']['sample.auxin0.avg'][0]['value'][0]

        t_f = t[tf_index0:tf_index1]
        t_f = t_f - t_f[0]
        c_f = c[tf_index0:tf_index1]
        r_f = r[tf_index0:tf_index1]
        i_f = i[tf_index0:tf_index1]
        v_f = v[tf_index0:tf_index1]
        
        t_m = t[tm_index0:tm_index1]
        t_m = t_m - t_m[0]
        c_m = c[tm_index0:tm_index1]
        r_m = r[tm_index0:tm_index1]
        i_m = i[tm_index0:tm_index1]
        v_m = v[tm_index0:tm_index1]

        return {
            "raw_data": {"t": t_m, "c": c_m, "r": r_m, "i": i_m, "v": v_m, "t_f": t_f, "c_f": c_f, "r_f": r_f,
                         "i_f": i_f, "v_f": v_f, 'x':t_m, 'y':c_m, 'y2':i_m},
            "save_type": {
                "Once_format": [
                    {"filename": "STC_data_m.txt", "data": np.column_stack((t_m, c_m, r_m, i_m, v_m))},
                    {"filename": "STC_data_f.txt", "data": np.column_stack((t_f, c_f, r_f, i_f, v_f))}
                ],
                "DLTS_format": [
                    {"filename": "STC_m.transdata", "fixed_x": t_m, "changed_y": c_m},
                    {"filename": "STC_f.transdata", "fixed_x": t_f, "changed_y": c_f}
                ],
                "Numpy_Dict_format": [
                    {"filename": "STC.npy", "data": {"t": t_m, "c": c_m, "r": r_m, "i": i_m, "v": v_m,
                                                    "t_f": t_f, "c_f": c_f, "r_f": r_f,"i_f": i_f, "v_f": v_f}}
                ]
            },
            "plot_type": {
                'xscale':'linear',
                'yscale':'linear',
                'x_scaling':1.0,
                'xlabel':'Time [s]',
                'y_scaling':1e12,
                'ylabel':'Capacitance [pF]',
                'y2_scaling':1e6,
                'y2label':'Current [uA]',
                'ignore_points':True
            }
        }
    def measure_STC_post_set(self, **kwargs):
        # Close Aux2 Output
        self.daq.setDouble('/{}/auxouts/1/scale'.format(self.id), 0.0)
        self.daq.setDouble('/{}/auxouts/1/offset'.format(self.id), 0.0)
        time.sleep(1)
        # Close Signal Add
        self.daq.setInt('/{}/sigouts/0/add'.format(self.id), 0)
        time.sleep(2)
        # Set Previous AC Frequency
        self.daq.setDouble('/{}/imps/0/freq'.format(self.id), round(self.tempfreq,self._roundBs))
        # Set Previous AC Amplitude
        self.daq.setDouble('/{}/imps/0/output/amplitude'.format(self.id), round(self.tempdV,self._roundBs))
        # Set Range
        self.daq.setInt('/{}/imps/0/auto/inputrange'.format(self.id), self.temprangemode)
        if self.temprangemode != 1:
            self.daq.setDouble('/{}/imps/0/current/range'.format(self.id), self.temprange)
    







    # 定义两个脉冲：测量脉冲Vm1_gs,Vm2_gs(SignalOutput)和外置脉冲Vaux_ds_s,Vaux_ds_m(Aux Out2)
    def measure_SMOSTI_pre_set(self, **kwargs):
        Vm1_gs = kwargs['Vm1_gs']
        Vm2_gs = kwargs['Vm2_gs']
        Tm1_gs = kwargs['Tm1_gs']
        Tm2_gs = kwargs['Tm2_gs']
        Td = kwargs['Td']
        Tm2_gs2 = kwargs['Tm2_gs2'] 
        Vaux_ds_s = kwargs['Vaux_ds_s']
        Vaux_ds_m = kwargs['Vaux_ds_m']
        Taux_ds_s = kwargs['Taux_ds_s']
        ManualRange = kwargs['ManualRange']
        DataRateMode = kwargs['DataRateMode']
        IfAutoRange = kwargs['IfAutoRange']
        # progress clear
        self._set_progress(0,'SMOSTI')
        # Ensure Output1 Signal ON
        if self.daq.getInt('/{}/imps/0/output/on'.format(self.id)) != 1:
            self._log(f'SMOSTI: Opening Output1 Signal...')
            self.daq.setInt('/{}/imps/0/output/on'.format(self.id), 1)
            time.sleep(5)
        # Ensure IA Enabled
        if self.daq.getInt('/{}/imps/0/enable'.format(self.id)) != 1:
            self._log(f'SMOSTI: Opening IA...')
            self.daq.setInt('/{}/imps/0/enable'.format(self.id), 1)
            time.sleep(3)
        # Ensure Bias ON and set to 0V
        if self.daq.getInt('/{}/imps/0/bias/enable'.format(self.id)) == 0:
            self.daq.setInt('/{}/imps/0/bias/enable'.format(self.id), 1)
            time.sleep(3)
        if self.daq.getDouble('/{}/imps/0/bias/value'.format(self.id)) !=0:
            self.daq.setDouble('/{}/imps/0/bias/value'.format(self.id), 0)
            time.sleep(2)

        # Read RangeMode
        self.temprangemode = self.daq.getInt('/{}/imps/0/auto/inputrange'.format(self.id))
        # Read Range
        self.temprange = self.daq.getDouble('/{}/imps/0/current/range'.format(self.id))
        # Set Range
        if IfAutoRange:
            if self.temprangemode != 1:
                self.daq.setInt('/{}/imps/0/auto/inputrange'.format(self.id), 1)
        else:
            self.daq.setInt('/{}/imps/0/auto/inputrange'.format(self.id), 0)
            self.daq.setDouble('/{}/imps/0/current/range'.format(self.id), ManualRange)
            time.sleep(1)

        # Read Current AC Amplitude
        self.tempdV = self.daq.getDouble('/{}/imps/0/output/amplitude'.format(self.id))
        # Read Current AC Frequency
        self.tempfreq = self.daq.getDouble('/{}/imps/0/freq'.format(self.id))
        # set 0 AC Amplitude
        self.daq.setDouble('/{}/imps/0/output/amplitude'.format(self.id), 0)
        # set 0 AC Frequency
        self.daq.setDouble('/{}/imps/0/freq'.format(self.id), 0)

        # Ensure Signal Add Disabled
        if self.daq.getInt('/{}/sigouts/0/add'.format(self.id))==1:
            self.daq.setInt('/{}/sigouts/0/add'.format(self.id), 0)
            time.sleep(5)


        if Vaux_ds_s == Vaux_ds_m:
            # Set TU
            self.daq.setInt('/{}/tu/thresholds/0/input'.format(self.id), 59)
            self.daq.setInt('/{}/tu/thresholds/0/inputchannel'.format(self.id), 0)
            self.daq.setInt('/{}/tu/logicunits/0/inputs/0/not'.format(self.id), 1)#取反
            self.daq.setInt('/{}/tu/logicunits/0/inputs/0/channel'.format(self.id), 0)#
            self.daq.setInt('/{}/tu/logicunits/0/ops/0/value'.format(self.id), 0)#none
            # Actual Tm = Tm*1.01
            self.daq.setDouble('/{}/tu/thresholds/0/deactivationtime'.format(self.id), round((Tm2_gs+Tm2_gs2)*1.01,8))
            # Actual Tf = Tf*1.01
            self.daq.setDouble('/{}/tu/thresholds/0/activationtime'.format(self.id), round(Tm1_gs*1.01,8))
            # Set Aux1
            self.daq.setInt('/{}/auxouts/0/outputselect'.format(self.id), 13)
            self.daq.setInt('/{}/auxouts/0/demodselect'.format(self.id), 0)
            self.daq.setDouble('/{}/auxouts/0/scale'.format(self.id), round(Vm1_gs-Vm2_gs,8))
            self.daq.setDouble('/{}/auxouts/0/offset'.format(self.id), round(Vm2_gs,8))
            # Set Aux2
            # 手动设置aux2电压
            self.daq.setInt('/{}/auxouts/1/outputselect'.format(self.id), -1)
            self.daq.setDouble('/{}/auxouts/1/offset'.format(self.id), round(Vaux_ds_s,8))
        else:
            # Set TU
            # 1,2,3,4阈值输出都是基于阈值判断输出
            self.daq.setInt('/{}/tu/thresholds/0/input'.format(self.id), 59)
            self.daq.setInt('/{}/tu/thresholds/1/input'.format(self.id), 59)
            self.daq.setInt('/{}/tu/thresholds/2/input'.format(self.id), 59)
            self.daq.setInt('/{}/tu/thresholds/3/input'.format(self.id), 59)
            # 对应逻辑通道
            self.daq.setInt('/{}/tu/thresholds/0/inputchannel'.format(self.id), 0)
            self.daq.setInt('/{}/tu/thresholds/1/inputchannel'.format(self.id), 1)
            self.daq.setInt('/{}/tu/thresholds/2/inputchannel'.format(self.id), 2)
            self.daq.setInt('/{}/tu/thresholds/3/inputchannel'.format(self.id), 3)

            # 逻辑a输入
            self.daq.setInt('/{}/tu/logicunits/0/inputs/0/channel'.format(self.id), 2)#TU3
            self.daq.setInt('/{}/tu/logicunits/1/inputs/0/channel'.format(self.id), 1)#TU2
            self.daq.setInt('/{}/tu/logicunits/2/inputs/0/channel'.format(self.id), 1)#TU2
            self.daq.setInt('/{}/tu/logicunits/3/inputs/0/channel'.format(self.id), 1)#TU2
            # 逻辑a反
            self.daq.setInt('/{}/tu/logicunits/0/inputs/0/not'.format(self.id), 1)
            self.daq.setInt('/{}/tu/logicunits/1/inputs/0/not'.format(self.id), 1)
            self.daq.setInt('/{}/tu/logicunits/2/inputs/0/not'.format(self.id), 1)
            self.daq.setInt('/{}/tu/logicunits/3/inputs/0/not'.format(self.id), 1)
            # 逻辑a操作
            self.daq.setInt('/{}/tu/logicunits/0/ops/0/value'.format(self.id), 3)#异或
            self.daq.setInt('/{}/tu/logicunits/0/inputs/1/not'.format(self.id), 1)#反
            self.daq.setInt('/{}/tu/logicunits/0/inputs/1/channel'.format(self.id), 3)#TU4
            self.daq.setInt('/{}/tu/logicunits/1/ops/0/value'.format(self.id), 0)#None
            self.daq.setInt('/{}/tu/logicunits/2/ops/0/value'.format(self.id), 0)#None
            self.daq.setInt('/{}/tu/logicunits/3/ops/0/value'.format(self.id), 0)#None
            
            # 保持宽度
            self.daq.setDouble('/{}/tu/logicunits/0/pulsewidth'.format(self.id), 0.00000000)
            self.daq.setDouble('/{}/tu/logicunits/1/pulsewidth'.format(self.id), 0.00000000)
            self.daq.setDouble('/{}/tu/logicunits/2/pulsewidth'.format(self.id), Taux_ds_s+Td+Tm1_gs*1.01)
            self.daq.setDouble('/{}/tu/logicunits/3/pulsewidth'.format(self.id), Taux_ds_s+Td)

            #Enable&Disable Setup
            self.daq.setDouble('/{}/tu/thresholds/0/activationtime'.format(self.id), 0.00000000)
            self.daq.setDouble('/{}/tu/thresholds/0/deactivationtime'.format(self.id), 0.00000000)
            self.daq.setDouble('/{}/tu/thresholds/1/activationtime'.format(self.id), Taux_ds_s)
            if self.daq.getDouble('/{}/tu/logicunits/3/pulsewidth'.format(self.id))==self.daq.getDouble('/{}/tu/thresholds/1/activationtime'.format(self.id)):
                self._log('Td too small')
            self.daq.setDouble('/{}/tu/thresholds/1/deactivationtime'.format(self.id), Td+(Tm1_gs+Tm2_gs+Tm2_gs2)*1.01)
            self.daq.setDouble('/{}/tu/thresholds/2/activationtime'.format(self.id), 0.00000000)
            self.daq.setDouble('/{}/tu/thresholds/2/deactivationtime'.format(self.id), 0.00000000)
            self.daq.setDouble('/{}/tu/thresholds/3/activationtime'.format(self.id), 0.00000000)
            self.daq.setDouble('/{}/tu/thresholds/3/deactivationtime'.format(self.id), 0.00000000)
            
            # Set Aux
            self.daq.setInt('/{}/auxouts/0/outputselect'.format(self.id), 13)
            self.daq.setInt('/{}/auxouts/1/outputselect'.format(self.id), 13)
            self.daq.setInt('/{}/auxouts/0/demodselect'.format(self.id), 0)
            self.daq.setInt('/{}/auxouts/1/demodselect'.format(self.id), 1)
            self.daq.setDouble('/{}/auxouts/0/scale'.format(self.id), round(Vm1_gs-Vm2_gs,8))
            self.daq.setDouble('/{}/auxouts/0/offset'.format(self.id), round(Vm2_gs,8))
            self.daq.setDouble('/{}/auxouts/1/scale'.format(self.id), round(Vaux_ds_s-Vaux_ds_m,8))
            self.daq.setDouble('/{}/auxouts/1/offset'.format(self.id), round(Vaux_ds_m,8))
        
        # Enable Signal Add
        self.daq.setInt('/{}/sigouts/0/add'.format(self.id), 1)
        
            
        # 示波器设置
        # 只激活通道1
        self.daq.setInt('/{}/scopes/0/channel'.format(self.id), 1)
        # 通道1选择为电流1输入
        self.daq.setInt('/{}/scopes/0/channels/0/inputselect'.format(self.id), 1)
        # 示波器采样率模式8=234k
        real_rate = 60e6/2**np.arange(17)[DataRateMode]
        self.daq.setInt('/{}/scopes/0/time'.format(self.id), DataRateMode)
        # 采样点数
        if Vaux_ds_s == Vaux_ds_m:
            real_Tm1_gs = self.daq.getDouble('/{}/tu/thresholds/0/activationtime'.format(self.id))
        else:
            real_Tm1_gs = self.daq.getDouble('/{}/tu/logicunits/2/pulsewidth'.format(self.id))-self.daq.getDouble('/{}/tu/logicunits/3/pulsewidth'.format(self.id))
        daqpoints = int((Tm2_gs*1.01+real_Tm1_gs)*real_rate)
        self.daq.setInt('/{}/scopes/0/length'.format(self.id), daqpoints)
        # 启用示波器触发
        self.daq.setInt('/{}/scopes/0/trigenable'.format(self.id), 1)
        
        # 使用触发输入1作为触发信号
        #self.daq.setInt('/{}/scopes/0/trigchannel'.format(self.id), 2)
        # 使用辅助输入1作为触发信号
        self.daq.setInt('/{}/scopes/0/trigchannel'.format(self.id), 8)
        
        # 从m1_gs过程开始测
        if Vm1_gs>Vm2_gs:
            # 上升沿
            self.daq.setInt('/{}/scopes/0/trigslope'.format(self.id), 1)
        else:
            # 下降沿
            self.daq.setInt('/{}/scopes/0/trigslope'.format(self.id), 2)
        
        # 迟滞
        self.daq.setDouble('/{}/scopes/0/trighysteresis/absolute'.format(self.id), 0.00000000)
        
        # 启用触发门控
        #self.daq.setInt('/{}/scopes/0/triggate/enable'.format(self.id), 1)
        # 关闭触发门控
        self.daq.setInt('/{}/scopes/0/triggate/enable'.format(self.id), 0)

        # 触发电平
        self.daq.setDouble('/{}/scopes/0/triglevel'.format(self.id), (Vm1_gs+Vm2_gs)/2)
        
        
        # 释抑时间10u
        self.daq.setDouble('/{}/scopes/0/trigholdoff'.format(self.id), 0.00000100)
        # 参考0，即从0s开始记录信号
        self.daq.setDouble('/{}/scopes/0/trigreference'.format(self.id), 0.00000000)
        # 信号延迟0s
        self.daq.setDouble('/{}/scopes/0/trigdelay'.format(self.id), 0.00000000)
        # 开启示波器采集，可以在绘图模块中引入
        self.daq.setInt('/{}/scopes/0/stream/enables/0'.format(self.id), 1)
        # 示波器采集频率默认107k=9
        self.daq.setInt('/{}/scopes/0/stream/rate'.format(self.id), 9)
        time.sleep(3)
    def measure_SMOSTI_main(
        self, Vm1_gs:float=2.5, Vm2_gs:float=0, Tm1_gs:float=2e-2, Tm2_gs:float=2e-2, Td:float=1e-3,
        Tm2_gs2:float=0, Vaux_ds_s:float=0.05, Vaux_ds_m:float=0.01, Taux_ds_s:float=0.1,
        AverageTimes:int=10, DataRateMode:int=8, IfAutoRange:bool=True, ManualRange:float=0.00100,
        IfLogScaleReSample:bool=False, LogScaleReSamplePoints:int=0
    ):
        
        # 好像有时候会卡在这个loop里......
        # 设置一个time_limit来观察CurrentDataLen有没有发生变化
        time_limit = 60
        Task_something_wrong = False
        while True:
            if Task_something_wrong:
                Task_something_wrong = False
            scope = self.daq.scopeModule()
            # 横轴时间
            scope.set('mode', 1)
            # 启用平均
            scope.set('averager/enable', 1)
            # 启用均一权重
            scope.set('averager/method', 1)
            # 示波器采样率模式8=234k
            real_rate = 60e6/2**np.arange(17)[DataRateMode]
            if Vaux_ds_s == Vaux_ds_m:
                real_Tm1_gs = self.daq.getDouble('/{}/tu/thresholds/0/activationtime'.format(self.id))
            else:
                real_Tm1_gs = self.daq.getDouble('/{}/tu/logicunits/2/pulsewidth'.format(self.id))-self.daq.getDouble('/{}/tu/logicunits/3/pulsewidth'.format(self.id))
            daqpoints = int((Tm2_gs*1.01+real_Tm1_gs)*real_rate)
            scope.unsubscribe('*')
            scope.subscribe('/{}/scopes/0/wave'.format(self.id))
            scope.execute()
            # 开始采集
            self._log(f'Start SMOSTI Measure')
            self.daq.setInt('/{}/scopes/0/enable'.format(self.id), 1)
            TargetAverageTimes = AverageTimes
            CurrentDataLen = 0
            CurrentDataLen_before = 0
            temp_time0 = time.time()
            result = []
            # 每隔1s进行scope.read()获取数据，直到获得指定次数的数据
            while CurrentDataLen < TargetAverageTimes:
                if CurrentDataLen_before != CurrentDataLen:
                    temp_time0 = time.time()
                    CurrentDataLen_before = CurrentDataLen
                else:
                    if time.time()-temp_time0>=time_limit:
                        self._log('Something went wrong, restart current task...')
                        Task_something_wrong = True
                        break
                time.sleep(1)
                tempresult = scope.read()
                try:
                    tempdatalen = len(tempresult[self.id]['scopes']['0']['wave'])
                except:
                    tempdatalen = 0
                CurrentDataLen += tempdatalen
                if tempdatalen != 0:
                    for i in range(tempdatalen):
                        result.append(tempresult[self.id]['scopes']['0']['wave'][i][0]['wave'][0])
                # Update Progress
                if CurrentDataLen/TargetAverageTimes <= 1:
                    self._set_progress(CurrentDataLen/TargetAverageTimes,'SMOSTI')
                else:
                    self._set_progress(1.0,'SMOSTI')
            # 结束采集
            self.daq.setInt('/{}/scopes/0/enable'.format(self.id), 0)
            scope.finish()
            scope.unsubscribe('*')
            self._log(f'End SMOSTI Measure')
            if not Task_something_wrong:
                break
            else:
                time.sleep(2)
        
        result = np.array(result)
        result = result[0:TargetAverageTimes]
        result = np.average(result,axis=0)
        # time
        t = np.linspace(0, (daqpoints-1)/real_rate, daqpoints)
        tm1_index0 = 0
        tm1_index1 = np.searchsorted(t, Tm1_gs)
        tm2_index0 = np.searchsorted(t, real_Tm1_gs)
        tm2_index1 = np.searchsorted(t, real_Tm1_gs+Tm2_gs)
        
        # Current
        i = result
        raw = result
        
        t_m1 = t[tm1_index0:tm1_index1]
        t_m1 = t_m1 - t_m1[0]
        i_m1 = i[tm1_index0:tm1_index1]
        t_m2 = t[tm2_index0:tm2_index1]
        t_m2 = t_m2 - t_m2[0]
        i_m2 = i[tm2_index0:tm2_index1]

        #时间加上Td
        if Vaux_ds_s == Vaux_ds_m:
            real_Td = 0
        else:
            real_Td = self.daq.getDouble('/{}/tu/logicunits/3/pulsewidth'.format(self.id))-self.daq.getDouble('/{}/tu/thresholds/1/activationtime'.format(self.id))
        #t_m1 = t_m1 + real_Td
        #t_m2 = t_m2 + real_Td
        
        if IfLogScaleReSample:
            if LogScaleReSamplePoints<=0:
                tm1_indices = ReSampleFromTimeArray(t_m1,len(t_m1))
                t_m1 = t_m1[tm1_indices]
                i_m1 = i_m1[tm1_indices]
                tm2_indices = ReSampleFromTimeArray(t_m2,len(t_m2))
                t_m2 = t_m2[tm2_indices]
                i_m2 = i_m2[tm2_indices]
            else:
                tm1_indices = ReSampleFromTimeArray(t_m1,LogScaleReSamplePoints)
                t_m1 = t_m1[tm1_indices]
                i_m1 = i_m1[tm1_indices]
                tm2_indices = ReSampleFromTimeArray(t_m2,LogScaleReSamplePoints)
                t_m2 = t_m2[tm2_indices]
                i_m2 = i_m2[tm2_indices]
        
        return {
            "raw_data": {"t": t_m1, "i": i_m1, "t_m2": t_m2, "i_m2": i_m2, "Td": real_Td,
                         'x':t_m1, 'y':i_m1, 'y2':i_m2},
            "save_type": {
                "Once_format": [
                    {"filename": "SMOSTI_data_m1.txt", "data": np.column_stack((t_m1, i_m1))},
                    {"filename": "SMOSTI_data_m2.txt", "data": np.column_stack((t_m2, i_m2))}
                ],
                "DLTS_format": [
                    {"filename": "SMOSTI_m1.transdata", "fixed_x": t_m1, "changed_y": i_m1},
                    {"filename": "SMOSTI_m2.transdata", "fixed_x": t_m2, "changed_y": i_m2}
                ],
                "Numpy_Dict_format": [
                    {"filename": "SMOSTI.npy", "data": {"t": t_m1, "i": i_m1, "t_m2": t_m2, "i_m2": i_m2, "Td": real_Td}}
                ]
            },
            "plot_type": {
                'xscale':'linear',
                'yscale':'linear',
                'x_scaling':1.0,
                'xlabel':'Time [s]',
                'y_scaling':1e6,
                'ylabel':'Current [uA]',
                'y2_scaling':1e6,
                'y2label':'Current [uA]',
                'ignore_points':True
            }
        }

    def measure_SMOSTI_post_set(self, **kwargs):
        # Close Aux2 Output
        self.daq.setDouble('/{}/auxouts/1/scale'.format(self.id), 0.0)
        self.daq.setDouble('/{}/auxouts/1/offset'.format(self.id), 0.0)
        time.sleep(1)
        # Close Signal Add
        self.daq.setInt('/{}/sigouts/0/add'.format(self.id), 0)
        time.sleep(2)
        # Set Previous AC Frequency
        self.daq.setDouble('/{}/imps/0/freq'.format(self.id), round(self.tempfreq,self._roundBs))
        # Set Previous AC Amplitude
        self.daq.setDouble('/{}/imps/0/output/amplitude'.format(self.id), round(self.tempdV,self._roundBs))
        # Set Range
        self.daq.setInt('/{}/imps/0/auto/inputrange'.format(self.id), self.temprangemode)
        if self.temprangemode != 1:
            self.daq.setDouble('/{}/imps/0/current/range'.format(self.id), self.temprange)

    # TI
    def measure_TI_pre_set(self, **kwargs):
        Vm = kwargs['Vm']
        Tm = kwargs['Tm']
        Vf = kwargs['Vf']
        Tf = kwargs['Tf']
        ManualRange = kwargs['ManualRange']
        DataRateMode = kwargs['DataRateMode']
        IfAutoRange = kwargs['IfAutoRange']
        # progress clear
        self._set_progress(0,'TI')
        # Ensure Output1 Signal ON
        if self.daq.getInt('/{}/imps/0/output/on'.format(self.id)) != 1:
            self._log(f'TI: Opening Output1 Signal...')
            self.daq.setInt('/{}/imps/0/output/on'.format(self.id), 1)
            time.sleep(5)
        # Ensure IA Enabled
        if self.daq.getInt('/{}/imps/0/enable'.format(self.id)) != 1:
            self._log(f'TI: Opening IA...')
            self.daq.setInt('/{}/imps/0/enable'.format(self.id), 1)
            time.sleep(3)
        # Ensure Bias ON and set to 0V
        if self.daq.getInt('/{}/imps/0/bias/enable'.format(self.id)) == 0:
            self.daq.setInt('/{}/imps/0/bias/enable'.format(self.id), 1)
            time.sleep(3)
        if self.daq.getDouble('/{}/imps/0/bias/value'.format(self.id)) !=0:
            self.daq.setDouble('/{}/imps/0/bias/value'.format(self.id), 0)
            time.sleep(2)
        # Read Current AC Amplitude
        self.tempdV = self.daq.getDouble('/{}/imps/0/output/amplitude'.format(self.id))
        # Read Current AC Frequency
        self.tempfreq = self.daq.getDouble('/{}/imps/0/freq'.format(self.id))
        # set 0 AC Amplitude
        self.daq.setDouble('/{}/imps/0/output/amplitude'.format(self.id), 0)
        # set 0 AC Frequency
        self.daq.setDouble('/{}/imps/0/freq'.format(self.id), 0)
        # Ensure Signal Add Disabled
        if self.daq.getInt('/{}/sigouts/0/add'.format(self.id))==1:
            self.daq.setInt('/{}/sigouts/0/add'.format(self.id), 0)
            time.sleep(5)
        # Set TU
        self.daq.setInt('/{}/tu/thresholds/0/input'.format(self.id), 59)
        self.daq.setInt('/{}/tu/thresholds/0/inputchannel'.format(self.id), 0)
        self.daq.setInt('/{}/tu/logicunits/0/inputs/0/not'.format(self.id), 1)
        # Input 1
        self.daq.set('/{}/tu/logicunits/0/inputs/0/channel'.format(self.id), 0)
        # op=None
        self.daq.set('/{}/tu/logicunits/0/ops/0/value'.format(self.id), 0)
        # Actual Tm = Tm*1.01
        self.daq.setDouble('/{}/tu/thresholds/0/deactivationtime'.format(self.id), round(Tm*1.01,8))
        # Actual Tf = Tf*1.01
        self.daq.setDouble('/{}/tu/thresholds/0/activationtime'.format(self.id), round(Tf*1.01,8))
        # Set TU
        #self.daq.setInt('/{}/tu/thresholds/1/input'.format(self.id), 59)
        #self.daq.setInt('/{}/tu/thresholds/1/inputchannel'.format(self.id), 0)
        #self.daq.setInt('/{}/tu/logicunits/1/inputs/0/not'.format(self.id), 1)
        #self.daq.setDouble('/{}/tu/thresholds/1/activationtime'.format(self.id), 0)
        #self.daq.setDouble('/{}/tu/thresholds/1/deactivationtime'.format(self.id), 0)
        # Set Aux1
        self.daq.setInt('/{}/auxouts/0/outputselect'.format(self.id), 13)
        self.daq.setInt('/{}/auxouts/0/demodselect'.format(self.id), 0)
        self.daq.setDouble('/{}/auxouts/0/scale'.format(self.id), round(Vf-Vm,8))
        self.daq.setDouble('/{}/auxouts/0/offset'.format(self.id), round(Vm,8))
        # Set Aux2, the falling edge corresponds to the falling edge from Vf to Vm
        self.daq.setInt('/{}/auxouts/1/outputselect'.format(self.id), 13)
        self.daq.setInt('/{}/auxouts/1/demodselect'.format(self.id), 1)
        self.daq.setDouble('/{}/auxouts/1/scale'.format(self.id), -5.0)
        self.daq.setDouble('/{}/auxouts/1/offset'.format(self.id), 5.0)
        # Enable Signal Add
        self.daq.setInt('/{}/sigouts/0/add'.format(self.id), 1)
        # Read RangeMode
        self.temprangemode = self.daq.getInt('/{}/imps/0/auto/inputrange'.format(self.id))
        # Read Range
        self.temprange = self.daq.getDouble('/{}/imps/0/current/range'.format(self.id))
        # Set Range
        if IfAutoRange:
            if self.temprangemode != 1:
                self.daq.setInt('/{}/imps/0/auto/inputrange'.format(self.id), 1)
        else:
            self.daq.setInt('/{}/imps/0/auto/inputrange'.format(self.id), 0)
            self.daq.setDouble('/{}/imps/0/current/range'.format(self.id), ManualRange)
        # 只激活通道1
        self.daq.setInt('/{}/scopes/0/channel'.format(self.id), 1)
        # 通道1选择为电流1输入
        self.daq.setInt('/{}/scopes/0/channels/0/inputselect'.format(self.id), 1)
        # 示波器采样率模式8=234k
        real_rate = 60e6/2**np.arange(17)[DataRateMode]
        self.daq.setInt('/{}/scopes/0/time'.format(self.id), DataRateMode)
        # 采样点数
        #if ifFillTrans:
        #    daqpoints = int(Tf*real_rate)
        #else:
        #    daqpoints = int(Tm*real_rate)
        daqpoints = int((Tm*1.01+Tf)*real_rate)
        self.daq.setInt('/{}/scopes/0/length'.format(self.id), daqpoints)
        # 启用示波器触发
        self.daq.setInt('/{}/scopes/0/trigenable'.format(self.id), 1)
        
        # 使用触发输入1作为触发信号
        #self.daq.setInt('/{}/scopes/0/trigchannel'.format(self.id), 2)
        # 使用辅助输入1作为触发信号
        self.daq.setInt('/{}/scopes/0/trigchannel'.format(self.id), 8)
        
        #if ifFillTrans:
            # 使用上升沿作为触发
        #    self.daq.setInt('/{}/scopes/0/trigslope'.format(self.id), 1)
        #else:
            # 使用下降沿作为触发
        #    self.daq.setInt('/{}/scopes/0/trigslope'.format(self.id), 2)
        
        if Vm>Vf:
            # 上升沿
            self.daq.setInt('/{}/scopes/0/trigslope'.format(self.id), 1)
        else:
            # 下降沿
            self.daq.setInt('/{}/scopes/0/trigslope'.format(self.id), 2)
        
        # 迟滞
        self.daq.setDouble('/{}/scopes/0/trighysteresis/absolute'.format(self.id), 0.00000000)
        
        # 启用触发门控
        #self.daq.setInt('/{}/scopes/0/triggate/enable'.format(self.id), 1)
        # 关闭触发门控
        self.daq.setInt('/{}/scopes/0/triggate/enable'.format(self.id), 0)

        # 触发电平
        self.daq.setDouble('/{}/scopes/0/triglevel'.format(self.id), (Vf+Vm)/2)
        
        #if ifFillTrans:
            # 触发输入1高作为触发
        #    self.daq.setInt('/{}/scopes/0/triggate/inputselect'.format(self.id), 0)
        #else:
            # 触发输入1低作为触发
        #    self.daq.setInt('/{}/scopes/0/triggate/inputselect'.format(self.id), 1)
        
        # 释抑时间10u
        self.daq.setDouble('/{}/scopes/0/trigholdoff'.format(self.id), 0.00000100)
        # 参考0，即从0s开始记录信号
        self.daq.setDouble('/{}/scopes/0/trigreference'.format(self.id), 0.00000000)
        # 信号延迟0s
        self.daq.setDouble('/{}/scopes/0/trigdelay'.format(self.id), 0.00000000)
        # 开启示波器采集，可以在绘图模块中引入
        self.daq.setInt('/{}/scopes/0/stream/enables/0'.format(self.id), 1)
        # 示波器采集频率默认107k=9
        self.daq.setInt('/{}/scopes/0/stream/rate'.format(self.id), 9)
        time.sleep(3)
    
    def measure_TI_main(
        self, Vm:float=-3, Tm:float=2e-2, Vf:float=-0.5, Tf:float=6e-2,
        AverageTimes:int=100, DataRateMode:int=8,
        IfAutoRange:bool=True, ManualRange:float=0.000100,
        IfLogScaleReSample:bool=False, LogScaleReSamplePoints:int=0
    ):
        # 好像有时候会卡在这个loop里......
        # 设置一个time_limit来观察CurrentDataLen有没有发生变化
        time_limit = 60
        Task_something_wrong = False
        while True:
            if Task_something_wrong:
                Task_something_wrong = False
            scope = self.daq.scopeModule()
            # 横轴时间
            scope.set('mode', 1)
            # 启用平均
            scope.set('averager/enable', 1)
            # 启用均一权重
            scope.set('averager/method', 1)
            # 示波器采样率模式8=234k, 9=117k, 10=59k, 11=29k
            real_rate = 60e6/2**np.arange(17)[DataRateMode]
            # 采样点数
            #if ifFillTrans:
            #    daqpoints = int(Tf*real_rate)
            #else:
            #    daqpoints = int(Tm*real_rate)
            daqpoints = int((Tm*1.01+Tf)*real_rate)
            
            scope.unsubscribe('*')
            scope.subscribe('/{}/scopes/0/wave'.format(self.id))
            scope.execute()
            # 开始采集
            self._log(f'Start TI Measure')
            self.daq.setInt('/{}/scopes/0/enable'.format(self.id), 1)
            TargetAverageTimes = AverageTimes
            CurrentDataLen = 0
            CurrentDataLen_before = 0
            temp_time0 = time.time()
            result = []
            # 每隔1s进行scope.read()获取数据，直到获得指定次数的数据
            while CurrentDataLen < TargetAverageTimes:
                if CurrentDataLen_before != CurrentDataLen:
                    temp_time0 = time.time()
                    CurrentDataLen_before = CurrentDataLen
                else:
                    if time.time()-temp_time0>=time_limit:
                        self._log('Something went wrong, restart current task...')
                        Task_something_wrong = True
                        break
                time.sleep(1)
                tempresult = scope.read()
                try:
                    tempdatalen = len(tempresult[self.id]['scopes']['0']['wave'])
                except:
                    tempdatalen = 0
                CurrentDataLen += tempdatalen
                if tempdatalen != 0:
                    for i in range(tempdatalen):
                        result.append(tempresult[self.id]['scopes']['0']['wave'][i][0]['wave'][0])
                # Update Progress
                if CurrentDataLen/TargetAverageTimes <= 1:
                    self._set_progress(CurrentDataLen/TargetAverageTimes,'TI')
                else:
                    self._set_progress(1.0,'TI')
            # 结束采集
            self.daq.setInt('/{}/scopes/0/enable'.format(self.id), 0)
            scope.finish()
            scope.unsubscribe('*')
            self._log(f'End TI Measure')
            if not Task_something_wrong:
                break
            else:
                time.sleep(2)


        
        result = np.array(result)
        result = result[0:TargetAverageTimes]
        result = np.average(result,axis=0)
        # time
        t = np.linspace(0, (daqpoints-1)/real_rate, daqpoints)
        tm_index0 = 0
        tm_index1 = np.searchsorted(t, Tm)
        tf_index0 = np.searchsorted(t, Tm*1.01)
        tf_index1 = -1
        
        # Current
        i = result
        raw = result
        
        t_m = t[tm_index0:tm_index1]
        t_m = t_m - t_m[0]
        i_m = i[tm_index0:tm_index1]
        t_f = t[tf_index0:tf_index1]
        t_f = t_f - t_f[0]
        i_f = i[tf_index0:tf_index1]

        if IfLogScaleReSample:
            if LogScaleReSamplePoints<=0:
                tm_indices = ReSampleFromTimeArray(t_m,len(t_m))
                t_m = t_m[tm_indices]
                i_m = i_m[tm_indices]
                tf_indices = ReSampleFromTimeArray(t_f,len(t_f))
                t_f = t_f[tf_indices]
                i_f = i_f[tf_indices]
            else:
                tm_indices = ReSampleFromTimeArray(t_m,LogScaleReSamplePoints)
                t_m = t_m[tm_indices]
                i_m = i_m[tm_indices]
                tf_indices = ReSampleFromTimeArray(t_f,LogScaleReSamplePoints)
                t_f = t_f[tf_indices]
                i_f = i_f[tf_indices]
        return {
            "raw_data": {"t": t_m, "i": i_m, "t_f": t_f, 'i_f':i_f, 'x':t_m, 'y':i_m, 'y2':i_f},
            "save_type": {
                "Once_format": [
                    {"filename": "TI_data_m.txt", "data": np.column_stack((t_m, i_m))},
                    {"filename": "TI_data_f.txt", "data": np.column_stack((t_f, i_f))}
                ],
                "DLTS_format": [
                    {"filename": "TI_m.transdata", "fixed_x": t_m, "changed_y": i_m},
                    {"filename": "TI_f.transdata", "fixed_x": t_f, "changed_y": i_f}
                ],
                "Numpy_Dict_format": [
                    {"filename": "TI.npy", "data": {"t": t_m, "i": i_m, "t_f": t_f, 'i_f':i_f}}
                ]
            },
            "plot_type": {
                'xscale':'linear',
                'yscale':'linear',
                'x_scaling':1.0,
                'xlabel':'Time [s]',
                'y_scaling':1e6,
                'ylabel':'Current [uA]',
                'y2_scaling':1e6,
                'y2label':'Current [uA]',
                'ignore_points':True
            }
        }
    def measure_TI_post_set(self, **kwargs):
        # Close Signal Add
        self.daq.setInt('/{}/sigouts/0/add'.format(self.id), 0)
        time.sleep(2)
        # Set Previous AC Frequency
        self.daq.setDouble('/{}/imps/0/freq'.format(self.id), round(self.tempfreq,self._roundBs))
        time.sleep(2)
        # Set Previous AC Amplitude
        self.daq.setDouble('/{}/imps/0/output/amplitude'.format(self.id), round(self.tempdV,self._roundBs))
        # Set Range
        self.daq.setInt('/{}/imps/0/auto/inputrange'.format(self.id), self.temprangemode)
        if self.temprangemode != 1:
            self.daq.setDouble('/{}/imps/0/current/range'.format(self.id), self.temprange)

    
