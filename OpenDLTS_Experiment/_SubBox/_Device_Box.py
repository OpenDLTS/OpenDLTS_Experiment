import ipywidgets as widgets
from ..Equipment_Driver import Electrical_Device, Temperature_Controller

__all__ = ['Device_Box']

def get_class_method_names(cls):
    method_names = []
    for name, value in cls.__dict__.items():
        if callable(value) or isinstance(value, (classmethod, staticmethod)):
            method_names.append(name)
    return method_names

class Device_Box:
    def __init__(self, parent):
        self.parent = parent
        self._create_ui()
    def _create_ui(self):
        self._available_temp_controller_list = get_class_method_names(Temperature_Controller)
        self._available_cap_meter_list = get_class_method_names(Electrical_Device)
        self._selected_temp_controller_widget = widgets.Dropdown(
            options = self._available_temp_controller_list,
            value = self._available_temp_controller_list[0],
            description = 'Chose Temperature Controller:',
            layout=widgets.Layout(width='30%'),
            style={'description_width': 'initial'},
            disabled = False
        )
        self._selected_cap_meter_widget = widgets.Dropdown(
            options = self._available_cap_meter_list,
            value = self._available_cap_meter_list[0],
            description = 'Chose Capacitance Meter:',
            layout=widgets.Layout(width='30%'),
            style={'description_width': 'initial'},
            disabled = False
        )
        self.box = widgets.HBox([self._selected_temp_controller_widget,self._selected_cap_meter_widget])
    def _init_temp_controller_dev(self):
        return getattr(Temperature_Controller, self._selected_temp_controller_widget.value)(self.parent)
    def _init_cap_meter_dev(self):
        return getattr(Electrical_Device, self._selected_cap_meter_widget.value)(self.parent)