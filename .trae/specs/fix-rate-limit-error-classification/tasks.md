# Tasks — 修复限流错误分类

- [x] Task 1: 修改 ipinfo_free — HTTP 429 改为 ChannelError
  - [x] 1.1: 修改 `src/ip_info/channel/ipinfo_free.py`：`ChannelPermanentError` → `ChannelError`
  - [x] 1.2: 修改 `tests/unit/channel/test_ipinfo_free.py`：429 测试改为 `ChannelError` + disabled 不变
  - [x] 1.3: 清理不再使用的 `ChannelPermanentError` import

- [x] Task 2: 修改 ipinfo_api — HTTP 429 改为 ChannelError
  - [x] 2.1: 修改 `src/ip_info/channel/ipinfo_api.py`：`ChannelPermanentError` → `ChannelError`
  - [x] 2.2: 修改 `tests/unit/channel/test_ipinfo_api.py`：429 测试改为 `ChannelError`

- [x] Task 3: 运行全量测试 + ruff 检查

- [x] Task 4: git-commit（含中文翻译）
