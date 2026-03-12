import ipywidgets as widgets
import numpy as np
import time
import threading
from .._config import LOGGER_ODEXP as LOGGER

__all__ = ['TLog_Box']

class TLog_Box:
    def __init__(self, parent):
        self.parent = parent
        self._create_ui()
        self.TLog_init()
        self._set_event()
        self.tlog_running = False
    def _create_ui(self):
        self.update_rate = widgets.BoundedFloatText(value=0.5, min=0.1, max=100000, description='Update Rate(s):', layout=widgets.Layout(width='80%'), style={'description_width': 'initial'})
        self.time_range = widgets.BoundedFloatText(value=0, min=0, max=10000, description='Time Range(min):', layout=widgets.Layout(width='80%'), style={'description_width': 'initial'})
        self.tlog_toggle = widgets.ToggleButton(value=False, description='Start TLog', button_style='success', icon='play')
        self.box = widgets.VBox([self.update_rate, self.time_range, self.tlog_toggle])
    def _set_event(self):
        self.tlog_toggle.observe(self._on_auto_toggle, 'value')
    def _on_auto_toggle(self, change):
        if change['new']: self.TLog_on()
        else: self.TLog_off()
    def TLog_init(self):
        self._tlog_data_t = np.array([])
        self._tlog_data_T = np.array([])
        self.filename = self.parent.path_header / (self.parent.proj_box.proj_name_text.value + '.tlog')
    def _get_data(self):
        try:
            t = time.time()
            T = self.parent.temp_controller.getTemp()
            return t, T
        except Exception as e:
            LOGGER.error(str(e))
            return time.time(), 0
    def _save_data(self, t, T):
        self.filename = self.parent.path_header / (self.parent.proj_box.proj_name_text.value + '.tlog')
        with open(self.filename, 'a') as file:
            file.write(f"{t}\t{T}\n")
    def _generate_plot(self):
        try:
            x = self._tlog_data_t - self._tlog_data_t[0]
            y = self._tlog_data_T
            if self.time_range.value > 0:
                starti = np.where(x > x[-1] - self.time_range.value * 60)[0]
                if len(starti) > 0:
                    x = x[starti[0]:]
                    y = y[starti[0]:]
            self.parent.plot_out2_box.im[0].set_data(x, y)
            self.parent.plot_out2_box.ax.set_xlabel('Time (s)')
            self.parent.plot_out2_box.ax.set_ylabel('Temperature (K)')
            self.parent.plot_out2_box.ax.relim()
            self.parent.plot_out2_box.ax.autoscale_view()
            self.parent.plot_out2_box.plot_out2_image.draw()
            self.parent.plot_out2_box.plot_out2_image.flush_events()
        except Exception as e:
            LOGGER.error(str(e))
    def TLog_auto_thread(self):
        while self.tlog_running:
            with self.parent.temp_controller_lock:
                t, T = self._get_data()
            self._save_data(t, T)
            self._tlog_data_t = np.append(self._tlog_data_t, t)
            self._tlog_data_T = np.append(self._tlog_data_T, T)
            self._generate_plot()
            time.sleep(self.update_rate.value)
    def TLog_on(self):
        if not self.tlog_running:
            self.filename = self.parent.path_header / ('Temperature' + '.log')
            if self.filename.exists():
                self.filename.rename(str(self.filename) + '.pre')
                LOGGER.warning(f"tlog file existed, renamed to .pre", extra={'color': '#FF0000'})
            self.TLog_init()
            self.tlog_running = True
            self.auto_thread = threading.Thread(target=self.TLog_auto_thread)
            self.auto_thread.start()
            self.tlog_toggle.description = 'Stop TLog'
            self.tlog_toggle.button_style = 'danger'
            self.tlog_toggle.icon = 'stop'
    def TLog_off(self):
        if self.tlog_running:
            self.tlog_running = False
            if self.auto_thread: self.auto_thread.join(timeout=1)
            self.tlog_toggle.description = 'Start TLog'
            self.tlog_toggle.button_style = 'success'
            self.tlog_toggle.icon = 'play'
    def get_config(self):
        return {'update_rate': self.update_rate.value, 'time_range': self.time_range.value}
    def load_config(self, config):
        if 'update_rate' in config: self.update_rate.value = config['update_rate']
        if 'time_range' in config: self.time_range.value = config['time_range']
