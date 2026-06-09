import re
from collections import OrderedDict
from datetime import datetime


class IPClassifier:
    """基于规则的 IP 分类引擎。"""

    def __init__(self, rules: OrderedDict):
        self._rules = rules

    @property
    def categories(self) -> list:
        return list(self._rules.keys())

    @property
    def rule_count(self) -> int:
        total = 0
        for cat_def in self._rules.values():
            total += len(cat_def.get("patterns", []))
        return total

    def classify(self, ip_data: dict) -> dict:
        """对 IP 数据进行分类。

        Args:
            ip_data: IP 的全量数据字典

        Returns:
            分类结果字典，包含 category/label/description/matched_by/need_deep_query/classify_time
        """
        for cat_key, cat_def in self._rules.items():
            patterns = cat_def.get("patterns", [])
            for pattern in patterns:
                field_value = self._extract_field(ip_data, pattern["field"])
                if field_value is None:
                    continue
                if self._match_pattern(field_value, pattern):
                    return {
                        "category": cat_key,
                        "label": cat_def.get("label", cat_key),
                        "description": cat_def.get("description", ""),
                        "matched_by": [
                            {
                                "rule_source": cat_def.get("_source", "builtin"),
                                "field": pattern["field"],
                                "pattern": pattern["match"],
                                "type": pattern.get("type", "contains"),
                                "value": str(field_value),
                                "note": pattern.get("note", ""),
                            }
                        ],
                        "need_deep_query": cat_def.get("need_deep_query", True),
                        "classify_time": datetime.now().isoformat(),
                    }

        return {
            "category": "other",
            "label": "其他",
            "description": "未匹配任何已知规则",
            "matched_by": [],
            "need_deep_query": True,
            "classify_time": datetime.now().isoformat(),
        }

    @staticmethod
    def _extract_field(data: dict, field_path: str):
        parts = field_path.split(".")
        current = data
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
            if current is None:
                return None
        return current

    @staticmethod
    def _match_pattern(field_value, pattern: dict) -> bool:
        match_str = pattern["match"]
        match_type = pattern.get("type", "contains")

        if field_value is None:
            return False

        value_str = str(field_value).lower()
        match_str_lower = match_str.lower()

        if match_type == "suffix":
            return value_str.endswith(match_str_lower)
        elif match_type == "contains":
            return match_str_lower in value_str
        elif match_type == "prefix":
            return value_str.startswith(match_str_lower)
        elif match_type == "exact":
            return value_str == match_str_lower
        elif match_type == "regex":
            return bool(re.match(match_str, value_str))
        return False
