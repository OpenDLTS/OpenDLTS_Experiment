import logging
import ipywidgets as widgets
from ._typing import Path

LOGGER_ODEXP = logging.getLogger("__odexp__")
LOGGER_ODEXP.setLevel(logging.INFO)
LOGGER_ODEXP.handlers = []
LOGGER_ODEXP_FILE_FORMATTER = logging.Formatter('(ODEXP) %(asctime)s - %(name)s - %(levelname)s - %(message)s')
LOGGER_ODEXP_HTML_FORMATTER = logging.Formatter('(ODEXP) %(asctime)s - %(name)s - %(levelname)s - %(message)s')
LOGGER_ODEXP_FILE_HANDLER = None
LOGGER_ODEXP_HTML_HANDLER = None

class ExcludeMessagesFilter(logging.Filter):
    def filter(self, record):
        message = record.getMessage()
        if message.startswith(("Sent query", "Received response")):
            return False
        return True
LOGGER_ODEXP_FILTER = ExcludeMessagesFilter()
LOGGER_ODEXP.addFilter(LOGGER_ODEXP_FILTER)
LOGGER_ODEXP.propagate = False

class HtmlWidgetHandler(logging.Handler):
    def __init__(self, html_widget):
        super().__init__()
        self.html_widget = html_widget

    def emit(self, record):
        msg = self.format(record)
        color = getattr(record, 'color', '#778899')
        html_content = f'<div style="color: {color}; margin: 2px 0;">{msg}</div>'
        current_value = self.html_widget.value
        self.html_widget.value = html_content + current_value

def INIT_LOG_HTML_WIDGET(html_widget: widgets.HTML):
    global LOGGER_ODEXP_HTML_HANDLER
    if LOGGER_ODEXP_HTML_HANDLER is not None:
        LOGGER_ODEXP.removeHandler(LOGGER_ODEXP_HTML_HANDLER)
    LOGGER_ODEXP_HTML_HANDLER = HtmlWidgetHandler(html_widget)
    LOGGER_ODEXP_HTML_HANDLER.setFormatter(LOGGER_ODEXP_HTML_FORMATTER)
    LOGGER_ODEXP.addHandler(LOGGER_ODEXP_HTML_HANDLER)

def INIT_LOG_FILE(filepath: str | Path | None = None, clear_exist_log: bool = False) -> None:
    global LOGGER_ODEXP_FILE_HANDLER
    if filepath is not None:
        filepath = Path(filepath).resolve()
        if clear_exist_log:
            if filepath.exists():
                filepath.unlink()
        if LOGGER_ODEXP_FILE_HANDLER is not None:
            LOGGER_ODEXP.removeHandler(LOGGER_ODEXP_FILE_HANDLER)
        LOGGER_ODEXP_FILE_HANDLER = logging.FileHandler(filepath)
        LOGGER_ODEXP_FILE_HANDLER.setFormatter(LOGGER_ODEXP_FILE_FORMATTER)
        LOGGER_ODEXP.addHandler(LOGGER_ODEXP_FILE_HANDLER)
        LOGGER_ODEXP.info(f"ODEXP log file initialized at: {filepath}")
    
__all__ = [
    "LOGGER_ODEXP",
    "INIT_LOG_FILE",
    "INIT_LOG_HTML_WIDGET"
]




