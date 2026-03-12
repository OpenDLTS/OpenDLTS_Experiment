import ipywidgets as widgets

__all__ = ['Task_Temp_Box']

class Task_Temp_Box:
    def __init__(self, parent):
        self.parent = parent
        self._create_ui()
        self._set_event()
    def _create_ui(self):
        self.T_start = widgets.BoundedFloatText(value=200.0, min=10, max=550, description='T_start (K):', layout=widgets.Layout(width='20%'))
        self.T_end = widgets.BoundedFloatText(value=210.0, min=10, max=550, description='T_end (K):', layout=widgets.Layout(width='20%'))
        self.T_step = widgets.BoundedFloatText(value=2.0, min=0.01, max=550, description='T_step (K):', layout=widgets.Layout(width='20%'))
        self.T_manual_list = widgets.Textarea(value='np.array([100, 110, 130, 160, 200])', placeholder='Typed string will be eval()', description='Manual List:')
        self.T_idle = widgets.BoundedFloatText(value=295.0, min=4, max=550, description='T_idle (K):', layout=widgets.Layout(width='20%'))
        self.T_stability_range = widgets.BoundedFloatText(value=0.2, min=0.01, max=100, description='Temp. Stablility Range (K):', style={'description_width': 'initial'}, layout=widgets.Layout(width='30%'))
        self.T_stability_rate = widgets.BoundedFloatText(value=0.1, min=0.01, max=100, description='Temp. Stablility Rate (K/Min):', style={'description_width': 'initial'}, layout=widgets.Layout(width='30%'))
        self.T_stability_rate_calc_time = widgets.BoundedFloatText(value=2, min=1, max=10, description='Temp. Stablility Rate Calc. Time (s):', style={'description_width': 'initial'}, layout=widgets.Layout(width='30%'))
        self.TC_set_temp = widgets.BoundedFloatText(value=295, min=10, max=450, description='Target Temperature(K) Set:', style={'description_width': 'initial'}, layout=widgets.Layout(width='20%'))
        self.TC_set_temp_P = widgets.BoundedFloatText(
            value=50,
            min=0,
            max=1000,
            #step=0.1,
            description='P:',
            style = {'description_width': 'initial'},
            disabled=False,
            layout=widgets.Layout(width='10%')
        )
        self.TC_set_temp_I = widgets.BoundedFloatText(
            value=10,
            min=0,
            max=1000,
            #step=0.1,
            description='I:',
            style = {'description_width': 'initial'},
            disabled=False,
            layout=widgets.Layout(width='10%')
        )
        self.TC_set_temp_D = widgets.BoundedFloatText(
            value=50,
            min=0,
            max=200,
            #step=0.1,
            description='D:',
            style = {'description_width': 'initial'},
            disabled=False,
            layout=widgets.Layout(width='10%')
        )
        self.TC_set_temp_btn = widgets.Button(description='Set Temperature', button_style='danger', icon='temperature-high', layout=widgets.Layout(width='20%'))
        self.TC_heater_off_btn = widgets.Button(description='Heater OFF', button_style='primary', icon='temperature-low', layout=widgets.Layout(width='20%'))
        self.TC_Accordion_Label = widgets.Accordion()
        self.TC_Accordion_Label.children = [widgets.HBox([self.TC_set_temp,self.TC_set_temp_P,self.TC_set_temp_I,self.TC_set_temp_D, self.TC_set_temp_btn, self.TC_heater_off_btn])]
        self.TC_Accordion_Label.titles = ['Temperature Controller Mannual Control:']
        self.T_list_chosen_Label = widgets.Label('Method to create T List:')
        self.T_list_chosen = widgets.Select(
            options=['Set T_step', 'Manual Input'],
            value='Set T_step',
            disabled=False,
            layout=widgets.Layout(width='20%')
        )
        self.T_list_params_container = widgets.HBox([self.T_start, self.T_end, self.T_step])
        self.box = widgets.VBox([
            self.TC_Accordion_Label,
            widgets.Label('Task Temperature Setup:', style=dict(font_weight='bold', font_size='18px')),
            widgets.HBox([self.T_list_chosen_Label, self.T_list_chosen, self.T_list_params_container]),
            self.T_idle,
            widgets.HBox([self.T_stability_range, self.T_stability_rate, self.T_stability_rate_calc_time])
        ])
    def get_current_T_List(self):
        import numpy as np
        if self.T_list_chosen.value == 'Manual Input':
            return eval(self.T_manual_list.value)
        elif self.T_list_chosen.value == 'Set T_step':
            if self.T_start.value < self.T_end.value:
                temp_range = np.arange(self.T_start.value, self.T_end.value + self.T_step.value, self.T_step.value)
            else:
                temp_range = np.arange(self.T_start.value, self.T_end.value - self.T_step.value, -self.T_step.value)
            return temp_range
    def _set_event(self):
        self.TC_set_temp_btn.on_click(self._click_TC_set_temp_btn)
        self.TC_heater_off_btn.on_click(self._click_TC_heater_off_btn)
        self.T_list_chosen.observe(self._obs_T_list_chosen, names='value')
    def _click_TC_set_temp_btn(self, b):
        T = self.TC_set_temp.value
        P = self.TC_set_temp_P.value
        I = self.TC_set_temp_I.value
        D = self.TC_set_temp_D.value
        self.parent.temp_controller.setTemp(T,P,I,D)
    def _click_TC_heater_off_btn(self, b):
        self.parent.temp_controller.setHeaterOFF()
    def _obs_T_list_chosen(self, change):
        if change['new'] == 'Manual Input':
            self.T_list_params_container.children = [self.T_manual_list]
        elif change['new'] == 'Set T_step':
            self.T_list_params_container.children = [self.T_start, self.T_end, self.T_step]
    def get_config(self):
        return {k: getattr(self, k).value for k in ['T_start', 'T_end', 'T_step', 'T_manual_list', 'T_idle', 'T_stability_range', 'T_stability_rate', 'T_stability_rate_calc_time', 'TC_set_temp', 'TC_set_temp_P', 'TC_set_temp_I', 'TC_set_temp_D', 'T_list_chosen']}
    def load_config(self, config):
        for k, v in config.items():
            if hasattr(self, k): getattr(self, k).value = v