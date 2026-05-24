import json
import os
from collections import OrderedDict


def load_rules(builtin_path: str, custom_path: str | None = None) -> OrderedDict:
    """加载并合并 builtin + custom 分类规则。

    Args:
        builtin_path: 内置规则文件路径
        custom_path: 自定义规则文件路径（可选）

    Returns:
        OrderedDict，builtin 在前，custom 在后。
        每个规则条目包含 `_source` 字段标记来源。
    """
    merged = OrderedDict()

    builtin = _load_json_file(builtin_path)
    if builtin:
        for key, val in builtin.items():
            val["_source"] = "builtin"
            merged[key] = val

    if custom_path and os.path.exists(custom_path):
        custom = _load_json_file(custom_path)
        if custom:
            for key, val in custom.items():
                val["_source"] = "custom"
                merged[key] = val

    return merged


def _load_json_file(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        content = f.read().strip()
        if not content:
            return {}
        return json.loads(content)
