import json
import os
import re
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class ClassifyResult:
    category: str
    label: str
    description: str
    matched_by: list = field(default_factory=list)
    need_deep_query: bool = True
    classify_time: str = ""

    def to_dict(self) -> dict:
        return {
            'category': self.category,
            'label': self.label,
            'description': self.description,
            'matched_by': self.matched_by,
            'need_deep_query': self.need_deep_query,
            'classify_time': self.classify_time,
        }


class IPClassifier:

    def __init__(self, builtin_path: str, custom_path: Optional[str] = None):
        self._builtin_count = 0
        self._rules = self._load_and_merge_rules(builtin_path, custom_path)

    @property
    def categories(self) -> list:
        return list(self._rules.keys())

    @property
    def rule_count(self) -> int:
        total = 0
        for cat_def in self._rules.values():
            total += len(cat_def.get('patterns', []))
        return total

    def classify(self, ip_data: dict) -> ClassifyResult:
        for idx, (cat_key, cat_def) in enumerate(self._rules.items()):
            patterns = cat_def.get('patterns', [])
            for pattern in patterns:
                field_value = self._extract_field(ip_data, pattern['field'])
                if field_value is None:
                    continue
                if self._match_pattern(field_value, pattern):
                    return ClassifyResult(
                        category=cat_key,
                        label=cat_def.get('label', cat_key),
                        description=cat_def.get('description', ''),
                        matched_by=[{
                            'rule_source': 'builtin' if idx < self._builtin_count else 'custom',
                            'field': pattern['field'],
                            'pattern': pattern['match'],
                            'type': pattern['type'],
                            'value': str(field_value),
                            'note': pattern.get('note', ''),
                        }],
                        need_deep_query=cat_def.get('need_deep_query', True),
                        classify_time=datetime.now().isoformat(),
                    )

        return ClassifyResult(
            category='other',
            label='其他',
            description='未匹配任何已知规则',
            matched_by=[],
            need_deep_query=True,
            classify_time=datetime.now().isoformat(),
        )

    def _load_and_merge_rules(self, builtin_path: str, custom_path: Optional[str]) -> OrderedDict:
        merged = OrderedDict()

        builtin = self._load_json_file(builtin_path)
        if builtin:
            for key, val in builtin.items():
                merged[key] = val
        self._builtin_count = len(merged)

        if custom_path and os.path.exists(custom_path):
            custom = self._load_json_file(custom_path)
            if custom:
                for key, val in custom.items():
                    merged[key] = val

        return merged

    @staticmethod
    def _load_json_file(path: str) -> dict:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {}
            return json.loads(content)

    @staticmethod
    def _extract_field(data: dict, field_path: str):
        parts = field_path.split('.')
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
        match_str = pattern['match']
        match_type = pattern.get('type', 'contains')

        if field_value is None:
            return False

        value_str = str(field_value).lower()
        match_str_lower = match_str.lower()

        if match_type == 'suffix':
            return value_str.endswith(match_str_lower)
        elif match_type == 'contains':
            return match_str_lower in value_str
        elif match_type == 'prefix':
            return value_str.startswith(match_str_lower)
        elif match_type == 'exact':
            return value_str == match_str_lower
        elif match_type == 'regex':
            return bool(re.match(match_str, value_str))
        return False
