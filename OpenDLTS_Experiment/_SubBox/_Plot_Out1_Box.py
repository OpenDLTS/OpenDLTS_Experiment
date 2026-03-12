import ipywidgets as widgets
import matplotlib.pyplot as plt

__all__ = ['Plot_Out1_Box']

class Plot_Out1_Box:
    def __init__(self, parent):
        self.parent = parent
        self._create_ui()
        self._set_event()
    def _create_ui(self):
        plt.ioff()
        self.fig = plt.figure(figsize=(7,5), layout='tight')
        self.fig.canvas.header_visible = False
        self.fig.canvas.resizable = False
        self.ax = plt.gca()
        self.ax2 = self.ax.twinx()
        self.im1 = self.ax.plot([0,1], [-1,0])
        self.im2 = self.ax.plot([0,1], [-1,0])
        self.im1t = self.ax2.plot([0,1], [-1,0])
        self.im2t = self.ax2.plot([0,1], [-1,0])
        self.plot_out1_image = self.fig.canvas
        self.plot_out1_image.layout = widgets.Layout(width='700px', height='500px')
        self.ignore_points = widgets.BoundedIntText(value=10, min=0, max=100, description='Ignore Points:', layout=widgets.Layout(width='30%'), style={'description_width': 'initial'})
        self.show_pre = widgets.Checkbox(value=True, description='Show Previous Curve')
        self.show_y2 = widgets.Checkbox(value=False, description='Show Y2 Axis')
        self.box = widgets.VBox([self.plot_out1_image, widgets.HBox([self.ignore_points, self.show_pre, self.show_y2])])
    def _set_event(self):
        self.ignore_points.observe(self._update_plot, 'value')
        self.show_pre.observe(self._update_plot, 'value')
        self.show_y2.observe(self._update_plot, 'value')
    def _update_plot(self, change):
        tasklist = list(self.parent.measure_tab.methods.keys())
        if not tasklist: return
        taskname = tasklist[self.parent.measure_tab.tab.selected_index]
        self.parent.measure_tab._plot_out1_generate(taskname)
    def get_config(self):
        return {'ignore_points': self.ignore_points.value, 'show_pre': self.show_pre.value, 'show_y2': self.show_y2.value}
    def load_config(self, config):
        if 'ignore_points' in config: self.ignore_points.value = config['ignore_points']
        if 'show_pre' in config: self.show_pre.value = bool(config['show_pre'])
        if 'show_y2' in config: self.show_y2.value = bool(config['show_y2'])
