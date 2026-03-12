import ipywidgets as widgets
import numpy as np
from .._config import LOGGER_ODEXP as LOGGER

__all__ = ['Temperature_Power_Mapping_Box']

class Temperature_Power_Mapping_Box:
    def __init__(self, parent):
        self.parent = parent
        self._create_ui()
    def power_curve(self,target_temp):
        Powerlist = np.array(eval(self.power_box.value))
        Power = np.interp(target_temp, Powerlist[:,0], Powerlist[:,1])
        return Power
    def _create_ui(self):
        self.power_box = widgets.Textarea(
            value=np.array2string(np.array([
                [100,40],
                [200,25],
                [250,15],
                [300,10]
            ]), separator=', '),
            disabled=False,
            layout=widgets.Layout(width='90%',height='300px')
        )
        self.box = widgets.VBox([widgets.Label('Power Mapping:',style=dict(font_weight='bold',font_size='18px')), self.power_box])
    def get_config(self):
        return {
            'Power': self.power_box.value
        }

    def load_config(self, config):
        try:
            if 'Power' in config:
                self.power_box.value = config['Power']
        except Exception as e:
            LOGGER.warning(f'Temperature Power Mapping Box Load Config Error: {str(e)}', extra={'color': '#FF0000'})