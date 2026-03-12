import ipywidgets as widgets
from .._typing import *
import inspect

__all__ = ['function_selector_multi', 'create_param_widget', 'create_widgets_from_function']

def create_widgets_from_function(input_fun: Callable, name_blacklist: list = []) -> Dict[str, widgets.Widget]:
    widgets_dict = {}
    import inspect
    for name,param in inspect.signature(input_fun).parameters.items():
        if name.startswith('__') or name=='self' or name in name_blacklist:
            continue
        default = param.default if param.default != inspect.Parameter.empty else 0
        desc = f"{name}:"
        if param.annotation == bool:
            widgets_dict[name] = widgets.Checkbox(
                value=default,
                description=name,
                style={'description_width': 'initial'},
                layout=widgets.Layout(
                    display='flex',
                    flex_flow='row'
                )
            )
        elif param.annotation == float:
            widgets_dict[name] = widgets.FloatText(
                value=default,
                description=desc,
                style={'description_width': 'initial'},
                layout=widgets.Layout(
                    display='flex',
                    flex_flow='row'
                )
            )
        elif param.annotation == int:
            widgets_dict[name] = widgets.IntText(
                value=default,
                description=desc,
                style={'description_width': 'initial'},
                layout=widgets.Layout(
                    display='flex',
                    flex_flow='row'
                )
            )
        elif param.annotation == list:
            widgets_dict[name] = widgets.Dropdown(
                options=default,
                value=default[0] if default else None,
                description=desc,
                style={'description_width': 'initial'},
                layout=widgets.Layout(
                    display='flex',
                    flex_flow='row'
                )
            )
        else:
            widgets_dict[name] = widgets.Text(
                value=str(default),
                description=desc,
                style={'description_width': 'initial'},
                layout=widgets.Layout(
                    display='flex',
                    flex_flow='row'
                )
            )
    return widgets_dict


class function_selector_multi:
    def __init__(self, fun_name_list: list[str], Function_Registry: Dict[str, Callable], tagsinput_label: str = 'Select Function:',
                 tab_label: str = 'Function Configuration:', total_width: str = '70%', widgets_per_row: int = 3,
                 tag_style: str = 'success'):
        self.fun_name_list = fun_name_list
        self.tagsinput_label = tagsinput_label
        self.tab_label = tab_label
        self.total_width = total_width
        self.Function_Registry = Function_Registry
        self.widgets_per_row = widgets_per_row
        self.tag_style = tag_style
        self._create_ui()
        self._set_event()
        # init expand
        self.tab_accordion_label.selected_index = 0
    def _create_ui(self):
        self.tagsinput_label = widgets.Label(
            self.tagsinput_label,
            layout = widgets.Layout(width=self.total_width, display='flex', align_items='stretch')
        )
        self.tagsinput = widgets.TagsInput(
            value = self.fun_name_list,
            allowed_tags = self.fun_name_list,
            allow_duplicates = False,
            layout = widgets.Layout(width=self.total_width, display='flex', align_items='stretch'),
            tag_style = self.tag_style
        )
        self.fun_params_widgets_dict = {}
        self.fun_params_widgets_list = {}
        self.fun_params_widgets_box = {}
        for fun_name in self.fun_name_list:
            self.fun_params_widgets_dict[fun_name] = create_widgets_from_function(self.Function_Registry[fun_name])
            self.fun_params_widgets_list[fun_name] = [v for _,v in self.fun_params_widgets_dict[fun_name].items()]
            temp_widgets = []
            for i in range(0, len(self.fun_params_widgets_list[fun_name]), self.widgets_per_row):
                temp = widgets.HBox(
                    self.fun_params_widgets_list[fun_name][i:i+self.widgets_per_row],
                    layout = widgets.Layout(width='95%', display='flex', align_items='stretch')
                )
                temp_widgets.append(temp)
            self.fun_params_widgets_box[fun_name] = widgets.VBox(
                temp_widgets,
                layout = widgets.Layout(width='95%', display='flex', align_items='stretch')
            )
        self.tab_accordion_label = widgets.Accordion(
            layout = widgets.Layout(width=self.total_width, display='flex', align_items='stretch')
        )
        self.tab = widgets.Tab(
            layout = widgets.Layout(width='95%', display='flex', align_items='stretch')
        )
        self.tab_accordion_label.children = [self.tab]
        self.tab_accordion_label.titles = [self.tab_label]
        self._update_tab()
        self.box = widgets.VBox([self.tagsinput_label, self.tagsinput, self.tab_accordion_label])
    def _update_tab(self):
        target_fun_name_list = self.tagsinput.value
        self.tab.children = [self.fun_params_widgets_box[fn] for fn in target_fun_name_list]
        self.tab.titles = target_fun_name_list
    def _set_event(self):
        self.tagsinput.observe(self._observe_tagsinput, names='value')
    def _observe_tagsinput(self, change):
        self._update_tab()


def create_param_widget(name, param):
    default = param.default if param.default != inspect.Parameter.empty else 0
    desc = f"{name}:"
    if param.annotation == float:
        return widgets.BoundedFloatText(value=default, min=-5e6, max=5e6, description=desc, layout=widgets.Layout(width='45%'), style={'description_width': 'initial'})
    elif param.annotation == int:
        return widgets.BoundedIntText(value=default, min=0, max=5e6, description=desc, layout=widgets.Layout(width='45%'), style={'description_width': 'initial'})
    elif param.annotation == bool:
        return widgets.Checkbox(value=default, description=name, indent=False)
    elif param.annotation == list:
        return widgets.Dropdown(options=default, value=default[0] if default else None, description=desc, layout=widgets.Layout(width='45%'), style={'description_width': 'initial'},)
    else:
        return widgets.Text(value=str(default), description=desc, layout=widgets.Layout(width='45%'), style={'description_width': 'initial'})
