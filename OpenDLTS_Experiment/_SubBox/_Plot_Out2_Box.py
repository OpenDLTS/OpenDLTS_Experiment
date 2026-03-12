import ipywidgets as widgets
import matplotlib.pyplot as plt

__all__ = ['Plot_Out2_Box']

class Plot_Out2_Box:
    def __init__(self, parent):
        self.parent = parent
        self._create_ui()
    def _create_ui(self):
        plt.ioff()
        self.fig = plt.figure(figsize=(12,2.5), layout='tight')
        self.fig.canvas.header_visible = False
        self.fig.canvas.resizable = False
        self.fig.canvas.footer_visible = False
        self.ax = plt.gca()
        self.ax.grid()
        self.im = self.ax.plot([0,1], [1,0])
        self.plot_out2_image = self.fig.canvas
        self.plot_out2_image.layout = widgets.Layout(width='1200px', height='250px')
        self.box = widgets.VBox([self.plot_out2_image])