# Issue #6: reporter/excel_exporter 迁移到 trace_utils

## What to build

将 `reporter.py` 和 `excel_exporter.py` 中的 9 个重复领域函数替换为 `from trace_utils import ...`。

重复函数清单（已在 trace_utils.py 中实现并测试）：
- `is_china_ip` / `_is_china_ip`
- `extract_all_domains` / `_extract_all_domains`
- `extract_fofa_ports` / `_extract_fofa_ports`
- `has_domains` / `_has_domains`
- `has_ports` / `_has_ports`
- `trace_priority` / `_trace_priority`
- `sort_key` / `_sort_key`
- `cat_display` / `_cat_display`
- `trace_action` / `_trace_action`

常量迁移：`LABEL_MAP` / `CAT_WEIGHT`

注意：`extract_all_domains` 返回值类型不同（reporter 返回字典列表，excel_exporter 返回字符串列表），excel_exporter 需要适配。

## Acceptance criteria

- [ ] reporter.py 中 9 个本地函数/闭包替换为 `from trace_utils import ...`
- [ ] excel_exporter.py 中 9 个本地函数替换为 `from trace_utils import ...`
- [ ] excel_exporter 的 `extract_all_domains` 适配（从字典列表提取域名）
- [ ] excel_exporter 的 `extract_fofa_ports` 适配（从字典列表格式化为字符串）
- [ ] `LABEL_MAP` / `CAT_WEIGHT` 常量迁移
- [ ] reporter/excel_exporter 行为与重构前完全一致
- [ ] 全量测试通过

## Blocked by

None - can start immediately
