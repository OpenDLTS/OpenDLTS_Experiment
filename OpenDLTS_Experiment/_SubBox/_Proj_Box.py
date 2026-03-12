from .._config import LOGGER_ODEXP as LOGGER, INIT_LOG_FILE
import ipywidgets as widgets
import tomllib
import tomli_w
import datetime

__all__ = ['Proj_Box']

class Proj_Box:
    def __init__(self, parent):
        self.parent = parent
        self._create_ui()
        self._set_confirm_event()
    def _create_ui(self):
        self.user_name_text = widgets.Text(value='Public', description='User:', placeholder='Input User', continuous_update=False, style={'description_width': 'initial'}, layout=widgets.Layout(width='10%'))
        self.proj_name_text = widgets.Text(value=f'DLTS_{datetime.date.today().strftime("%y%m%d")}', placeholder='Input Project', description='Project:', continuous_update=False, style={'description_width': 'initial'})
        self.confirm_btn = widgets.Button(description='Confirm', disabled=False, button_style='success', tooltip='Confirm User and Project Name', icon='check', layout=widgets.Layout(width='10%'))
        self.config_load_btn = widgets.Button(description='Load Config', button_style='info', layout=widgets.Layout(width='8%'), style={'description_width': 'initial'}, disabled=False, icon='download')
        self.config_load_text = widgets.Dropdown(options=['None'], value='None', description='Load Config Name:', style={'description_width': 'initial'}, layout=widgets.Layout(width='20%'), disabled=False)
        self.config_save_btn = widgets.Button(description='Save Config', button_style='primary', layout=widgets.Layout(width='8%'), style={'description_width': 'initial'}, disabled=False, icon='file')
        self.config_save_text = widgets.Text(value='config.toml', description='Save Config Name:', style={'description_width': 'initial'}, layout=widgets.Layout(width='20%'), disabled=False)
        self.box = widgets.HBox([self.user_name_text, self.proj_name_text, self.confirm_btn])
    def _set_confirm_event(self):
        self.confirm_btn.on_click(self._click_confirm_btn)
    def _set_observe_event(self):
        self.user_name_text.observe(self._observe_user_name, 'value')
        self.proj_name_text.observe(self._observe_proj_name, 'value')
        self.config_save_btn.on_click(self._click_config_save_btn)
        self.config_load_btn.on_click(self._click_config_load_btn)
    def _show_config_ui(self):
        self._update_load_config_text()
        self.box.children = [self.user_name_text, self.proj_name_text, self.config_load_text, self.config_load_btn, self.config_save_text, self.config_save_btn]
    def _click_confirm_btn(self, b):
        self.confirm_btn.disabled = True
        self.parent.main_init()
    def _observe_user_name(self, change):
        self.parent._update_path_header()
        LOGGER.info(f'Data Path Updated: {self.parent.path_header}')
        self._update_load_config_text()
        INIT_LOG_FILE(self.parent.path_header / 'main_log.log')
    def _observe_proj_name(self, change):
        self.parent._update_path_header()
        LOGGER.info(f'Data Path Updated: {self.parent.path_header}')
        INIT_LOG_FILE(self.parent.path_header / 'main_log.log')
    def _click_config_save_btn(self, b):
        config = self.parent.get_config()
        try:
            config_file_path = self.parent.path_header.parent / self.config_save_text.value
            with open(config_file_path, 'wb') as f:
                tomli_w.dump(config, f)
            LOGGER.info(f'Config File Saved To Path: {config_file_path}', extra={'color': '#FF0000'})
            self._update_load_config_text()
        except Exception as e:
            LOGGER.warning(f'Save Config Error: {str(e)}', extra={'color': '#FF0000'})
    def _click_config_load_btn(self, b):
        config_file_path = self.parent.path_header.parent / self.config_load_text.value
        try:
            with open(config_file_path, 'rb') as f:
                config = tomllib.load(f)
            LOGGER.info(f'Config File Loaded From Path: {config_file_path}', extra={'color': '#FF0000'})
            self._update_load_config_text()
            self.parent.load_config(config)
        except Exception as e:
            LOGGER.warning(f'Load Config Error: {str(e)}', extra={'color': '#FF0000'})
    def _update_load_config_text(self):
        config_file_dir = self.parent.path_header.parent
        if not config_file_dir.exists():
            return
        self.config_load_text.options = [file.name for file in config_file_dir.glob('*.toml')]
        if not self.config_load_text.options:
            self.config_load_text.options = ['None']
            self.config_load_text.value = 'None'
        else:
            self.config_load_text.value = self.config_load_text.options[0]
    def get_config(self):
        return {'user_name_text': self.user_name_text.value, 'config_save_text': self.config_save_text.value}
    def load_config(self, config):
        if 'user_name_text' in config: self.user_name_text.value = config['user_name_text']
        if 'config_save_text' in config: self.config_save_text.value = config['config_save_text']
