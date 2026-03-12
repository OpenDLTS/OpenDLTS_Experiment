import ipywidgets as widgets
import numpy as np
from .._config import LOGGER_ODEXP as LOGGER

__all__ = ['PID_Box']

class PID_Box:
    def __init__(self, parent):
        self.parent = parent
        self._create_ui()
    def pid_curve(self,current_temp,target_temp):
        Plist = np.array(eval(self.p_box.value))
        Ilist = np.array(eval(self.i_box.value))
        Dlist = np.array(eval(self.d_box.value))
        P = np.interp(target_temp, Plist[:,0], Plist[:,1])
        I = np.interp(target_temp, Ilist[:,0], Ilist[:,1])
        D = np.interp(target_temp, Dlist[:,0], Dlist[:,1])
        return P, I, D
    def _create_ui(self):
        self.p_box = widgets.Textarea(
            value=np.array2string(np.array([
                [100,40],
                [200,25],
                [250,15],
                [300,10]
            ]), separator=', '),
            disabled=False,
            layout=widgets.Layout(width='90%',height='300px')
        )
        self.i_box = widgets.Textarea(
            value=np.array2string(np.array([
                [100,10],
                [200,10],
                [250,10],
                [300,10]
            ]), separator=', '),
            disabled=False,
            layout=widgets.Layout(width='90%',height='300px')
        )
        self.d_box = widgets.Textarea(
            value=np.array2string(np.array([
                [100,50],
                [200,50],
                [250,50],
                [300,50]
            ]), separator=', '),
            disabled=False,
            layout=widgets.Layout(width='90%',height='300px')
        )
        self.tab = widgets.Tab(children=[self.p_box, self.i_box, self.d_box])
        self.tab.set_title(0, 'P')
        self.tab.set_title(1, 'I')
        self.tab.set_title(2, 'D')
        self.box = widgets.VBox([widgets.Label('PID Configuration:',style=dict(font_weight='bold',font_size='18px')), self.tab])
    def get_config(self):
        return {
            'P': self.p_box.value,
            'I': self.i_box.value,
            'D': self.d_box.value
        }

    def load_config(self, config):
        try:
            if 'P' in config:
                self.p_box.value = config['P']
            if 'I' in config:
                self.i_box.value = config['I']
            if 'D' in config:
                self.d_box.value = config['D']
        except Exception as e:
            LOGGER.warning(f'PID Box Load Config Error: {str(e)}', extra={'color': '#FF0000'})