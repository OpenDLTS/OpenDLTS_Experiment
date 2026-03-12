import ipywidgets as widgets

__all__ = ['Main_Log_Box']

class Main_Log_Box:
    def __init__(self, parent):
        self.parent = parent
        self._create_ui()
    def _create_ui(self):
        self.main_log_label = widgets.Label('Main Log:',style=dict(font_weight='bold',font_size='18px'))
        self.main_log = widgets.HTML(
            value='',
            placeholder='Log Will Showed Here',
            disable = True,
            layout=widgets.Layout(width='100%', height='300px'),
            style={'description_width': 'initial'}
        )
        self.box = widgets.VBox([self.main_log_label, self.main_log])