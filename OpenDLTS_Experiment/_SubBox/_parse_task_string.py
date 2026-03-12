import json
from .._config import LOGGER_ODEXP
__all__ = ['parse_task_string']

def parse_task_string(raw_text) -> list | None:
    lines = [line for line in raw_text.splitlines() if not line.strip().startswith("##")]
    clean_text = "\n".join(lines).strip()
    clean_text = clean_text.replace("False", "false")
    clean_text = clean_text.replace("True", "true")
    clean_text = clean_text.replace("None", "null") 
    tasks = []
    decoder = json.JSONDecoder()
    pos = 0
    while pos < len(clean_text):
        while pos < len(clean_text) and clean_text[pos].isspace():
            pos += 1
        
        if pos >= len(clean_text):
            break
            
        try:
            obj, end_pos = decoder.raw_decode(clean_text, idx=pos)
            tasks.append(obj)
            pos = end_pos
        except json.JSONDecodeError as e:
            LOGGER_ODEXP.error(f"Task Parsing Error: {e}")
            return None
    return tasks