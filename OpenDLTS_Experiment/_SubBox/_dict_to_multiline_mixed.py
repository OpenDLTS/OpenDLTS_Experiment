import json
__all__ = ['dict_to_multiline_mixed']

def to_compact_str(obj):
    """
    辅助函数：生成紧凑的字符串，但强制使用 Python 的 True/False。
    同时保留 JSON 风格的双引号 key。
    """
    if isinstance(obj, bool):
        return str(obj)  # 返回 "True" 或 "False"
    elif obj is None:
        return "None"    # 如果需要 Python 风格的 None
    elif isinstance(obj, dict):
        # 手动拼接字典，确保 key 使用双引号 (json.dumps 处理 key)
        items = [f'{json.dumps(k, ensure_ascii=False)}: {to_compact_str(v)}' 
                 for k, v in obj.items()]
        return "{" + ", ".join(items) + "}"
    elif isinstance(obj, list):
        # 手动拼接列表
        items = [to_compact_str(x) for x in obj]
        return "[" + ", ".join(items) + "]"
    else:
        # 字符串、数字等其他类型仍然使用 json.dumps 以处理转义和双引号
        return json.dumps(obj, ensure_ascii=False)
def dict_to_multiline_mixed(obj, depth=0, max_depth=2, indent=4):
    """
    混合缩进格式化：
    1. 指定深度之前展开。
    2. 指定深度之后紧凑。
    3. 布尔值显示为 True/False (Python风格)。
    """
    space = ' ' * indent
    indent_str = space * depth
    next_indent_str = space * (depth + 1)
    # --- 关键修改：达到深度限制时，调用自定义的紧凑函数 ---
    if depth >= max_depth:
        return to_compact_str(obj)
    # 处理字典
    if isinstance(obj, dict):
        if not obj: return "{}"
        items = []
        for k, v in obj.items():
            key_str = json.dumps(k, ensure_ascii=False)
            val_str = dict_to_multiline_mixed(v, depth + 1, max_depth, indent)
            items.append(f"{next_indent_str}{key_str}: {val_str}")
        return "{\n" + ",\n".join(items) + "\n" + indent_str + "}"
    # 处理列表
    elif isinstance(obj, list):
        if not obj: return "[]"
        items = []
        for item in obj:
            val_str = dict_to_multiline_mixed(item, depth + 1, max_depth, indent)
            items.append(f"{next_indent_str}{val_str}")
        return "[\n" + ",\n".join(items) + "\n" + indent_str + "]"
    # 基本类型（如果在顶层被调用）
    return to_compact_str(obj)
