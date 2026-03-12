import threading
import inspect
import numpy as np
import ipywidgets as widgets
from ._widget_create_fun import create_param_widget
from .._typing import *
from .._config import LOGGER_ODEXP as LOGGER

__all__ = ['Measure_Tab']

class MeasurementMethod:
    def __init__(self, parent, method, name):
        self.parent = parent
        self.method = method
        self.name = name
        self.widgets = {}
        self._create_ui()
        self._setup_parameters()
        self.plot_x = None
        self.plot_y = None
        self.plot_y2 = None
        self.plot_label = None
        self.plot_x_pre = None
        self.plot_y_pre = None
        self.plot_y2_pre = None
        self.plot_label_pre = None
        self.plot_params = None
        self.plot_params_pre = None
    def _plot_data_push(self, x=None, y=None, y2=None, label=None, plot_params=None):
        self.plot_x_pre = self.plot_x
        self.plot_y_pre = self.plot_y
        self.plot_y2_pre = self.plot_y2
        self.plot_label_pre = self.plot_label
        self.plot_params_pre = self.plot_params
        self.plot_x = x
        self.plot_y = y
        self.plot_y2 = y2
        self.plot_label = label
        self.plot_params = plot_params
    def _create_ui(self):
        self.start_btn = widgets.Button(description='Start Measure', button_style='warning', icon='play', layout=widgets.Layout(width='60%'))
        self.save_check = widgets.Checkbox(value=True, description='Save Data', style={'description_width': 'initial'})
        self.progress = widgets.FloatProgress(value=0, min=0, max=1, description='Progress:', bar_style='success', layout=widgets.Layout(width='100%'))
        self.replot_btn = widgets.Button(description='Replot', button_style='info', icon='pen', layout=widgets.Layout(width='40%'))
        self.log_output = widgets.Text(value=f'{self.name} related log will show here', disabled=True, layout=widgets.Layout(width='90%'))
        self.param_container = widgets.VBox()
        self.box = widgets.VBox([widgets.HBox([self.start_btn, self.save_check, self.progress, self.replot_btn]), self.log_output, self.param_container])
    def _setup_parameters(self):
        sig = inspect.signature(self.method.main)
        param_widgets = []
        for name, param in sig.parameters.items():
            if name == 'self': continue
            widget = create_param_widget(name, param)
            self.widgets[name] = widget
            param_widgets.append(widget)
        rows = []
        for i in range(0, len(param_widgets), 2):
            rows.append(widgets.HBox(param_widgets[i:i+2]))
        self.param_container.children = rows
    def load_config(self, config):
        for name, widget in self.widgets.items():
            if name in config:
                if isinstance(widget, widgets.Checkbox): widget.value = bool(config[name])
                elif isinstance(widget, (widgets.BoundedFloatText, widgets.BoundedIntText)): widget.value = config[name]
                else: widget.value = str(config[name])
    def get_config(self):
        return {name: widget.value for name, widget in self.widgets.items()}

from dataclasses import dataclass
@dataclass
class method_wrapper:
    pre_set: Callable
    main: Callable
    post_set: Callable
    def __call__(self, *args, **kwargs):
        self.pre_set(*args, **kwargs)
        result = self.main(*args, **kwargs)
        self.post_set(*args, **kwargs)
        return result

def method_donothing(*args, **kwargs):
    pass
class Measure_Tab:
    def __init__(self, parent):
        self.parent = parent
        # Find methods starting with 'measure_' in cap_meter
        self.loaded_method_list = [name for name, obj in inspect.getmembers(parent.cap_meter) if name.startswith('measure_')]
        self.methods = {}
        temp_method_list = []
        temp_method_with_main_list = []
        temp_method_with_pre_set_list = []
        temp_method_with_post_set_list = []
        for mn in self.loaded_method_list:
            if mn.endswith('_main'):
                if mn.replace('_main', '') not in temp_method_with_main_list:
                    temp_method_with_main_list.append(mn.replace('_main', ''))
                else:
                    raise ValueError('methods with the same name')
                if mn.replace('_main', '') not in temp_method_list:
                    temp_method_list.append(mn.replace('_main', ''))
            elif mn.endswith('_pre_set'):
                if mn.replace('_pre_set', '') not in temp_method_with_pre_set_list:
                    temp_method_with_pre_set_list.append(mn.replace('_pre_set', ''))
                else:
                    raise ValueError('methods with the same name')
                if mn.replace('_pre_set', '') not in temp_method_list:
                    temp_method_list.append(mn.replace('_pre_set', ''))
            elif mn.endswith('_post_set'):
                if mn.replace('_post_set', '') not in temp_method_with_post_set_list:
                    temp_method_with_post_set_list.append(mn.replace('_post_set', ''))
                else:
                    raise ValueError('methods with the same name')
                if mn.replace('_post_set', '') not in temp_method_list:
                    temp_method_list.append(mn.replace('_post_set', ''))
            else:
                if mn not in temp_method_list:
                    temp_method_list.append(mn)
                else:
                    raise ValueError('methods with the same name')
        for method_name in temp_method_list:
            if method_name in temp_method_with_main_list:
                temp_main_method = getattr(parent.cap_meter, method_name + '_main')
            else:
                temp_main_method = getattr(parent.cap_meter, method_name)
            if method_name in temp_method_with_pre_set_list:
                temp_pre_set_method = getattr(parent.cap_meter, method_name + '_pre_set')
            else:
                temp_pre_set_method = method_donothing
            if method_name in temp_method_with_post_set_list:
                temp_post_set_method = getattr(parent.cap_meter, method_name + '_post_set')
            else:
                temp_post_set_method = method_donothing
            method = method_wrapper(temp_pre_set_method, temp_main_method, temp_post_set_method)
            self.methods[method_name.replace('measure_', '')] = MeasurementMethod(parent, method, method_name.replace('measure_', ''))
        self._create_tab()
        self._set_event()
        self.enable()
    def _create_tab(self):
        self.tab = widgets.Tab()
        self.tab.children = [method.box for method in self.methods.values()]
        for i, name in enumerate(self.methods.keys()):
            self.tab.set_title(i, name)
    def _set_event(self):
        def MethodClick_fun(mname):
            def MethodClick(b):
                Par = self.methods[mname].get_config()
                self.disable()
                try:
                    with self.parent.cap_meter_lock:
                        # Call the measurement method
                        data: ElectricalDeviceMeasuredData = self.methods[mname].method(**Par)
                except Exception as e:
                    self.methods[mname].log_output.value = f'Measure Failed: {str(e)}'
                    self.enable()
                    return
                finally:
                    self.enable()
                # Save Data
                if self.methods[mname].save_check.value:
                    save_type = data.get('save_type', {})
                    # Handle Once_format
                    for item in save_type.get('Once_format', []):
                        filename = self.parent.path_header / item['filename']
                        np.savetxt(filename, item['data'])
                        self.methods[mname].log_output.value = f'{mname} Data Saved To: {filename}'
                # Plot Data
                raw = data.get('raw_data', {})
                # Assume raw_data has 'x', 'y', 'y2' keys populated by Debug_CapMeter
                x = raw.get('x')
                y = raw.get('y')
                y2 = raw.get('y2')
                plot_params = data.get('plot_type', {})
                
                self.methods[mname]._plot_data_push(x=x, y=y, y2=y2, plot_params=plot_params)
                self._plot_out1_generate(method_name=mname)
            return MethodClick

        def MethodRePlotclick_fun(mname):
            def MethodRePlotclick(b):
                self._plot_out1_generate(method_name=mname)
            return MethodRePlotclick

        for name in self.methods:
            self.methods[name].start_btn.on_click(MethodClick_fun(name))
            self.methods[name].replot_btn.on_click(MethodRePlotclick_fun(name))

    def _plot_out1_generate(self, method_name=None, x=None, y=None, x_pre=None, y_pre=None, lNow='Now', lPre='Pre', use_label_from_stack=False):
        with self.parent.plot_out1_lock:
            if self.parent.plot_out1_event.is_set(): return
            self.parent.plot_out1_event.set()
            threading.Thread(target=self._plot_out1_generate_thread_fun, args=(method_name, x, y, x_pre, y_pre, lNow, lPre, use_label_from_stack)).start()

    def _plot_out1_generate_thread_fun(self, method_name=None, x=None, y=None, x_pre=None, y_pre=None, lNow='Now', lPre='Pre', use_label_from_stack=False):
        with self.parent.plot_out1_lock:
            self.parent.plot_out1_event.set()
            try:
                ifPlotPre = self.parent.plot_out1_box.show_pre.value
                ifPlotY2 = self.parent.plot_out1_box.show_y2.value
                if method_name is None: return
                
                x = self.methods[method_name].plot_x
                y = self.methods[method_name].plot_y
                y2 = self.methods[method_name].plot_y2
                params = self.methods[method_name].plot_params
                if x is None or y is None: return
                
                x_pre = self.methods[method_name].plot_x_pre
                y_pre = self.methods[method_name].plot_y_pre
                y2_pre = self.methods[method_name].plot_y2_pre
                
                if use_label_from_stack:
                    lNow = self.methods[method_name].plot_label
                    lPre = self.methods[method_name].plot_label_pre

                if params.get('ignore_points', False):
                    ip = self.parent.plot_out1_box.ignore_points.value
                    x = x[ip:]
                    y = y[ip:]
                    if y2 is not None: y2 = y2[ip:]
                
                # Update Plot
                self.parent.plot_out1_box.im1[0].set_data(x * params.get('x_scaling', 1.0), y * params.get('y_scaling', 1.0))
                self.parent.plot_out1_box.im1[0].set_label(lNow)
                
                # Clear previous lines
                if self.parent.plot_out1_box.im1t[0] in self.parent.plot_out1_box.ax2.lines: self.parent.plot_out1_box.im1t[0].remove()
                if self.parent.plot_out1_box.im2[0] in self.parent.plot_out1_box.ax.lines: self.parent.plot_out1_box.im2[0].remove()
                if self.parent.plot_out1_box.im2t[0] in self.parent.plot_out1_box.ax2.lines: self.parent.plot_out1_box.im2t[0].remove()

                if ifPlotY2 and y2 is not None:
                    self.parent.plot_out1_box.ax2.set_visible(True)
                    self.parent.plot_out1_box.ax2.set_ylabel(params.get('y2_label', ''))
                    self.parent.plot_out1_box.im1t = self.parent.plot_out1_box.ax2.plot(x * params.get('x_scaling', 1.0), y2 * params.get('y2_scaling', 1.0), linestyle='-.', color='#1f77b4')
                else:
                    self.parent.plot_out1_box.ax2.set_visible(False)

                if ifPlotPre and x_pre is not None and y_pre is not None:
                    if params.get('ignore_points', False):
                        x_pre = x_pre[ip:]
                        y_pre = y_pre[ip:]
                    self.parent.plot_out1_box.im2 = self.parent.plot_out1_box.ax.plot(x_pre * params.get('x_scaling', 1.0), y_pre * params.get('y_scaling', 1.0), label=lPre, color='red')

                self.parent.plot_out1_box.ax.set_xlabel(params.get('x_label', ''))
                self.parent.plot_out1_box.ax.set_ylabel(params.get('y_label', ''))
                self.parent.plot_out1_box.ax.set_xscale(params.get('xscale', 'linear'))
                self.parent.plot_out1_box.ax.set_yscale(params.get('yscale', 'linear'))
                self.parent.plot_out1_box.ax.relim()
                self.parent.plot_out1_box.ax.autoscale_view()
                self.parent.plot_out1_box.ax2.relim()
                self.parent.plot_out1_box.ax2.autoscale_view()
                self.parent.plot_out1_box.ax.legend()
                self.parent.plot_out1_box.ax.grid(True)
                self.parent.plot_out1_box.plot_out1_image.draw()
                self.parent.plot_out1_box.plot_out1_image.flush_events()
            except Exception as e:
                LOGGER.error(str(e))
            finally:
                self.parent.plot_out1_event.clear()

    def enable(self):
        for method in self.methods.values():
            method.start_btn.disabled = False
            method.save_check.disabled = False
            for widget in method.widgets.values(): widget.disabled = False
    def disable(self):
        for method in self.methods.values():
            method.start_btn.disabled = True
            method.save_check.disabled = True
            for widget in method.widgets.values(): widget.disabled = True
    def get_config(self):
        return {name: method.get_config() for name, method in self.methods.items()}
    def load_config(self, config):
        for name, method in self.methods.items():
            method.load_config(config.get(name, {}))
    def _get_selected_param(self):
        tasklist = list(self.methods.keys())
        taskname = tasklist[self.tab.selected_index]
        return taskname, self.methods[taskname].get_config()

