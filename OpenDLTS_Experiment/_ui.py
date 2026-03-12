import threading
import ipywidgets as widgets
import tomllib
from IPython.display import display
from ._config import LOGGER_ODEXP as LOGGER, INIT_LOG_HTML_WIDGET, INIT_LOG_FILE
from ._typing import *
from ._SubBox import *

__all__ = ['UI']

class UI:
    """
    User Interface for DLTS Experiment.
    """
    def __init__(self, init_user_name='Public', init_temperature_controller_name='Debug_Temperature_Controller', init_capacitance_meter_name='Debug_CapMeter',
        init_config_file_path=None, ifskipconfirm=False, root_header: str | Path = './Data_Files', logfile_name: str = 'odexp.log'):
        """
        Initialize the UI with instrument instances.
        """
        self.root_header = Path(root_header).resolve()
        self.proj_box = Proj_Box(self)
        self.proj_box.user_name_text.value = init_user_name
        self._update_path_header()
        self.logfile_name = logfile_name
        self.device_box = Device_Box(self)
        self.box = widgets.VBox([self.device_box.box, self.proj_box.box])
        self.device_box._selected_temp_controller_widget.value = init_temperature_controller_name
        self.device_box._selected_cap_meter_widget.value = init_capacitance_meter_name
        display(self.box)
        if init_config_file_path is not None:
            try:
                with open(init_config_file_path, 'rb') as f:
                    self.init_config_file = tomllib.load(f)
            except Exception as e:
                print(f'init_config_file_path Error:{str(e)}')
        else:
            self.init_config_file = None
        if ifskipconfirm:
            self.proj_box.confirm_btn.click()


    def main_init(self):
        # Temperature Controller Thread Lock
        self.temp_controller_lock = threading.Lock()
        # Capacitance Meter Thread Lock
        self.cap_meter_lock = threading.Lock()
        # Log operation/add hanler/delete hanler thread lock
        self.log_lock = threading.Lock()
        # plotout1 Thread Lock
        self.plot_out1_lock = threading.Lock()
        # plotout1 Thread Event
        self.plot_out1_event = threading.Event()
        self.plot_out1_event.clear()
        # Update Global Path Header
        self._update_path_header()
        # Show Main Log
        self.main_log_box = Main_Log_Box(self)
        self.box.children = [self.device_box.box, self.proj_box.box, self.main_log_box.box]
        # Init Logger
        INIT_LOG_HTML_WIDGET(self.main_log_box.main_log)
        INIT_LOG_FILE(self.path_header / self.logfile_name)
        # Observe Uaer and Proj Name
        self.proj_box._set_observe_event()
        # Show Config UI
        self.proj_box._show_config_ui()
        try:
            # Init Temperature Controller
            self.temp_controller = self.device_box._init_temp_controller_dev()
            # Init Capacitance Meter
            self.cap_meter = self.device_box._init_cap_meter_dev()
        except Exception as e:
            LOGGER.warning(f'Init Device Failed: {str(e)}', extra={'color': '#FF0000'})
        # Create Main Box
        self.main_box = widgets.GridspecLayout(7,8,width='100%')
        self.measure_tab_container = widgets.VBox([])
        self.plot_out1_box_container = widgets.VBox([])
        self.plot_out2_box_container = widgets.VBox([])
        self.tlog_box_container = widgets.VBox([])
        self.task_temp_box_container = widgets.VBox([])
        self.task_cap_box_container = widgets.VBox([])
        self.pid_box_container = widgets.VBox([])
        self.temperature_power_mapping_box_container = widgets.VBox([])
        # Main Box Layout
        self.main_box[0:2, 0:4] = self.measure_tab_container
        self.main_box[0:2, 4:8] = self.plot_out1_box_container
        self.main_box[2, 0:7] = self.plot_out2_box_container
        self.main_box[2, 7] = self.tlog_box_container
        self.main_box[3, 0:7] = self.task_temp_box_container
        self.main_box[4:7, 0:7] = self.task_cap_box_container
        self.main_box[3:5, 7:8] = self.pid_box_container
        self.main_box[5:7, 7:8] = self.temperature_power_mapping_box_container
        self.box.children = [self.device_box.box, self.proj_box.box, self.main_box, self.main_log_box.box]
        # Measure Tab
        try:
            self.measure_tab = Measure_Tab(self)
            self.measure_tab_container.children = [self.measure_tab.tab]
        except Exception as e:
            LOGGER.warning(f'Init Measure Tab Failed: {str(e)}', extra={'color': '#FF0000'})
        # Plot Out1 Box
        try:
            self.plot_out1_box = Plot_Out1_Box(self)
            self.plot_out1_box_container.children = [self.plot_out1_box.box]
        except Exception as e:
            LOGGER.warning(f'Init Plot Out1 Box Failed: {str(e)}', extra={'color': '#FF0000'})
        # Plot Out2 Box
        try:
            self.plot_out2_box = Plot_Out2_Box(self)
            self.plot_out2_box_container.children = [self.plot_out2_box.box]
        except Exception as e:
            LOGGER.warning(f'Init Plot Out2 Box Failed: {str(e)}', extra={'color': '#FF0000'})
        # TLog Box
        try:
            self.tlog_box = TLog_Box(self)
            self.tlog_box_container.children = [self.tlog_box.box]
        except Exception as e:
            LOGGER.warning(f'Init TLog Box Failed: {str(e)}', extra={'color': '#FF0000'})
        # Task Temp Box
        try:
            self.task_temp_box = Task_Temp_Box(self)
            self.task_temp_box_container.children = [self.task_temp_box.box]
        except Exception as e:
            LOGGER.warning(f'Init Task Temp Box Failed: {str(e)}', extra={'color': '#FF0000'})
        # Task Cap Box
        try:
            self.task_cap_box = Task_Cap_Box(self)
            self.task_cap_box_container.children = [self.task_cap_box.box]
        except Exception as e:
            LOGGER.warning(f'Init Task Cap Box Failed: {str(e)}', extra={'color': '#FF0000'})
        # PID Box
        try:
            self.pid_box = PID_Box(self)
            self.pid_box_container.children = [self.pid_box.box]
        except Exception as e:
            LOGGER.warning(f'Init PID Box Failed: {str(e)}', extra={'color': '#FF0000'})
        # Temperature Power Mapping Box
        try:
            self.temperature_power_mapping_box = Temperature_Power_Mapping_Box(self)
            self.temperature_power_mapping_box_container.children = [self.temperature_power_mapping_box.box]
        except Exception as e:
            LOGGER.warning(f'Init Temperature Power Mapping Box Failed: {str(e)}', extra={'color': '#FF0000'})
        # Load Init Config File
        if self.init_config_file is not None:
            try:
                # load
                self.load_config(self.init_config_file)
            except Exception as e:
                LOGGER.warning(f'Load Init Config Error: {str(e)}', extra={'color': '#FF0000'})

    def _update_path_header(self, root_header: Path | str | None = None, user_name: str | None = None, proj_name: str | None = None):
        target_root_header = self.root_header if root_header is None else Path(root_header).resolve()
        target_user_name = self.proj_box.user_name_text.value if user_name is None else user_name
        target_proj_name = self.proj_box.proj_name_text.value if proj_name is None else proj_name
        dir_path = target_root_header / target_user_name / target_proj_name
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
        self.path_header = dir_path

    def get_config(self):
        return {
            'proj_box': self.proj_box.get_config(),
            'measure_tab': self.measure_tab.get_config(),
            'plot_out1_box': self.plot_out1_box.get_config(),
            #'plot_out2_box': self.plot_out2_box.get_config(),
            'tlog_box': self.tlog_box.get_config(),
            'task_temp_box': self.task_temp_box.get_config(),
            'task_cap_box': self.task_cap_box.get_config(),
            'pid_box': self.pid_box.get_config(),
            #'temperature_power_mapping_box': self.temperature_power_mapping_box.get_config(),
        }

    def load_config(self, config):
        if 'proj_box' in config: self.proj_box.load_config(config['proj_box'])
        if 'measure_tab' in config: self.measure_tab.load_config(config['measure_tab'])
        if 'plot_out1_box' in config: self.plot_out1_box.load_config(config['plot_out1_box'])
        #if 'plot_out2_box' in config: self.plot_out2_box.load_config(config['plot_out2_box'])
        if 'tlog_box' in config: self.tlog_box.load_config(config['tlog_box'])
        if 'task_temp_box' in config: self.task_temp_box.load_config(config['task_temp_box'])
        if 'task_cap_box' in config: self.task_cap_box.load_config(config['task_cap_box'])
        if 'pid_box' in config: self.pid_box.load_config(config['pid_box'])
        #if 'temperature_power_mapping_box' in config: self.temperature_power_mapping_box.load_config(config['temperature_power_mapping_box'])
